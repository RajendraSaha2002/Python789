import csv
import math
import random
import statistics


class DifferentialPrivacyError(Exception):
    pass


def load_csv_numeric_column(file_path, column_name):
    values = []

    with open(
        file_path,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file_handle:
        reader = csv.DictReader(file_handle)

        if not reader.fieldnames:
            raise DifferentialPrivacyError(
                "CSV file does not contain headers."
            )

        if column_name not in reader.fieldnames:
            raise DifferentialPrivacyError(
                f"Column not found: {column_name}"
            )

        for row in reader:
            value = row.get(column_name, "").strip()

            if value:
                try:
                    values.append(float(value))
                except ValueError:
                    continue

    if not values:
        raise DifferentialPrivacyError(
            "No numeric values found in the selected column."
        )

    return values


def laplace_noise(sensitivity, epsilon):
    if epsilon <= 0:
        raise DifferentialPrivacyError("Epsilon must be greater than zero.")

    scale = sensitivity / epsilon
    uniform_value = random.random() - 0.5

    return -scale * math.copysign(
        math.log(1 - 2 * abs(uniform_value)),
        uniform_value,
    )


def gaussian_noise(sensitivity, epsilon, delta):
    if epsilon <= 0:
        raise DifferentialPrivacyError("Epsilon must be greater than zero.")

    if not 0 < delta < 1:
        raise DifferentialPrivacyError(
            "Delta must be greater than 0 and less than 1."
        )

    sigma = (
        sensitivity
        * math.sqrt(2 * math.log(1.25 / delta))
        / epsilon
    )

    return random.gauss(0, sigma), sigma


def laplace_count(values, epsilon):
    true_count = len(values)
    noisy_count = true_count + laplace_noise(1.0, epsilon)

    return {
        "true_value": true_count,
        "noisy_value": round(noisy_count, 3),
        "sensitivity": 1.0,
        "epsilon": epsilon,
        "mechanism": "Laplace mechanism",
    }


def laplace_sum(values, epsilon, lower_bound, upper_bound):
    if lower_bound >= upper_bound:
        raise DifferentialPrivacyError(
            "Lower bound must be smaller than upper bound."
        )

    clipped_values = [
        min(max(value, lower_bound), upper_bound)
        for value in values
    ]

    true_sum = sum(clipped_values)
    sensitivity = upper_bound - lower_bound
    noisy_sum = true_sum + laplace_noise(sensitivity, epsilon)

    return {
        "true_value": round(true_sum, 3),
        "noisy_value": round(noisy_sum, 3),
        "sensitivity": sensitivity,
        "epsilon": epsilon,
        "mechanism": "Laplace mechanism",
    }


def laplace_mean(values, epsilon, lower_bound, upper_bound):
    clipped_values = [
        min(max(value, lower_bound), upper_bound)
        for value in values
    ]

    true_mean = statistics.fmean(clipped_values)
    sensitivity = (upper_bound - lower_bound) / len(clipped_values)
    noisy_mean = true_mean + laplace_noise(sensitivity, epsilon)

    return {
        "true_value": round(true_mean, 3),
        "noisy_value": round(noisy_mean, 3),
        "sensitivity": round(sensitivity, 6),
        "epsilon": epsilon,
        "mechanism": "Laplace mechanism",
    }


def gaussian_mean(values, epsilon, delta, lower_bound, upper_bound):
    clipped_values = [
        min(max(value, lower_bound), upper_bound)
        for value in values
    ]

    true_mean = statistics.fmean(clipped_values)
    sensitivity = (upper_bound - lower_bound) / len(clipped_values)

    noise, sigma = gaussian_noise(
        sensitivity,
        epsilon,
        delta,
    )

    return {
        "true_value": round(true_mean, 3),
        "noisy_value": round(true_mean + noise, 3),
        "sensitivity": round(sensitivity, 6),
        "epsilon": epsilon,
        "delta": delta,
        "noise_standard_deviation": round(sigma, 6),
        "mechanism": "Gaussian mechanism",
    }


def randomized_response(true_answer, epsilon):
    """
    Returns a privacy-preserving yes/no answer.

    Larger epsilon means higher probability of returning the true answer.
    """
    if epsilon <= 0:
        raise DifferentialPrivacyError("Epsilon must be greater than zero.")

    truth_probability = math.exp(epsilon) / (
        math.exp(epsilon) + 1
    )

    if random.random() < truth_probability:
        response = true_answer
    else:
        response = not true_answer

    return {
        "input_answer": true_answer,
        "private_answer": response,
        "probability_of_truthful_response": round(
            truth_probability,
            4,
        ),
        "epsilon": epsilon,
        "mechanism": "Randomized response",
    }


def exponential_mechanism(categories, utility_scores, epsilon):
    """
    Privately selects a category.
    Higher utility score means higher selection probability.
    """
    if not categories:
        raise DifferentialPrivacyError(
            "At least one category is required."
        )

    if len(categories) != len(utility_scores):
        raise DifferentialPrivacyError(
            "Categories and utility scores must have equal length."
        )

    if epsilon <= 0:
        raise DifferentialPrivacyError("Epsilon must be greater than zero.")

    sensitivity = max(
        1.0,
        max(utility_scores) - min(utility_scores),
    )

    weights = [
        math.exp(
            epsilon * score / (2 * sensitivity)
        )
        for score in utility_scores
    ]

    total_weight = sum(weights)
    selection_point = random.random() * total_weight
    cumulative = 0.0

    for category, weight in zip(categories, weights):
        cumulative += weight

        if selection_point <= cumulative:
            return {
                "selected_category": category,
                "categories": categories,
                "utility_scores": utility_scores,
                "epsilon": epsilon,
                "mechanism": "Exponential mechanism",
            }

    return {
        "selected_category": categories[-1],
        "categories": categories,
        "utility_scores": utility_scores,
        "epsilon": epsilon,
        "mechanism": "Exponential mechanism",
    }


def print_result(result):
    print("\n" + "-" * 72)
    print(result["mechanism"])

    for key, value in result.items():
        if key != "mechanism":
            label = key.replace("_", " ").title()
            print(f"{label}: {value}")


def compare_epsilon_values(values, lower_bound, upper_bound):
    print("\n" + "=" * 72)
    print("EPSILON / UTILITY COMPARISON")
    print("=" * 72)
    print("Lower epsilon = more privacy, more noise.")
    print("Higher epsilon = less privacy, less noise.\n")

    for epsilon in [0.1, 0.5, 1.0, 2.0, 5.0]:
        result = laplace_mean(
            values,
            epsilon,
            lower_bound,
            upper_bound,
        )

        error = abs(
            result["true_value"] - result["noisy_value"]
        )

        bar_length = min(40, int(error * 2))
        bar = "#" * bar_length

        print(
            f"Epsilon {epsilon:<4} | "
            f"Noisy mean: {result['noisy_value']:<10} | "
            f"Absolute error: {error:<8.3f} | {bar}"
        )


def get_sample_dataset():
    return [
        21, 25, 31, 28, 42, 35, 29, 50, 41, 38,
        24, 33, 47, 36, 44, 27, 30, 39, 52, 34,
    ]


def main():
    print("Differential Privacy Noise Engine")
    print("=" * 72)
    print("1 - Use built-in sample numeric data")
    print("2 - Load a numeric column from local CSV")

    source_choice = input("\nChoose data source (1 or 2): ").strip()

    try:
        if source_choice == "1":
            values = get_sample_dataset()
            print(f"Loaded {len(values)} sample values.")

        elif source_choice == "2":
            file_path = input("CSV file path: ").strip().strip('"')
            column_name = input("Numeric column name: ").strip()

            values = load_csv_numeric_column(
                file_path,
                column_name,
            )

            print(f"Loaded {len(values)} numeric values.")

        else:
            print("Error: choose 1 or 2.")
            return

        lower_bound = float(
            input(
                f"Lower clipping bound [{min(values):.2f}]: "
            ).strip()
            or str(min(values))
        )

        upper_bound = float(
            input(
                f"Upper clipping bound [{max(values):.2f}]: "
            ).strip()
            or str(max(values))
        )

        epsilon = float(
            input("Privacy epsilon [1.0]: ").strip() or "1.0"
        )

        delta = float(
            input("Privacy delta [0.00001]: ").strip()
            or "0.00001"
        )

        print("\nTrue statistics:")
        print(f"Count: {len(values)}")
        print(f"Sum: {sum(values):.3f}")
        print(f"Mean: {statistics.fmean(values):.3f}")

        print_result(laplace_count(values, epsilon))

        print_result(
            laplace_sum(
                values,
                epsilon,
                lower_bound,
                upper_bound,
            )
        )

        print_result(
            laplace_mean(
                values,
                epsilon,
                lower_bound,
                upper_bound,
            )
        )

        print_result(
            gaussian_mean(
                values,
                epsilon,
                delta,
                lower_bound,
                upper_bound,
            )
        )

        private_answer = randomized_response(
            true_answer=True,
            epsilon=epsilon,
        )

        print_result(private_answer)

        category_result = exponential_mechanism(
            categories=["Option A", "Option B", "Option C"],
            utility_scores=[10, 6, 3],
            epsilon=epsilon,
        )

        print_result(category_result)

        compare_epsilon_values(
            values,
            lower_bound,
            upper_bound,
        )

    except FileNotFoundError:
        print("Error: CSV file not found.")

    except ValueError:
        print("Error: enter valid numeric values.")

    except DifferentialPrivacyError as error:
        print(f"Differential privacy error: {error}")

    except KeyboardInterrupt:
        print("\nOperation cancelled.")

    except Exception as error:
        print(f"Unexpected error: {error}")


if __name__ == "__main__":
    main()