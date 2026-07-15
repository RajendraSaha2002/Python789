import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path


class AnonymisationError(Exception):
    pass


def read_csv_file(file_path):
    path = Path(file_path.strip().strip('"'))

    if not path.is_file():
        raise FileNotFoundError(f"CSV file not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as file_handle:
        reader = csv.DictReader(file_handle)

        if not reader.fieldnames:
            raise AnonymisationError("CSV file has no header row.")

        rows = list(reader)

    if not rows:
        raise AnonymisationError("CSV file contains no data rows.")

    return path, reader.fieldnames, rows


def is_numeric_column(rows, column):
    try:
        for row in rows:
            value = row.get(column, "").strip()

            if value:
                float(value)

        return True

    except ValueError:
        return False


def numeric_generalise(value, minimum, maximum, level):
    if not value.strip():
        return "[MISSING]"

    number = float(value)

    if level == 0:
        return value

    data_range = maximum - minimum

    if data_range == 0:
        return str(int(minimum)) if minimum.is_integer() else str(minimum)

    bucket_count = max(1, 20 // (2 ** (level - 1)))
    bucket_width = data_range / bucket_count

    if bucket_width <= 0:
        return value

    bucket_start = minimum + (
        math.floor((number - minimum) / bucket_width) * bucket_width
    )

    bucket_end = min(bucket_start + bucket_width, maximum)

    return f"[{bucket_start:.2f}-{bucket_end:.2f}]"


def text_generalise(value, level):
    value = value.strip()

    if not value:
        return "[MISSING]"

    if level == 0:
        return value

    if level >= len(value):
        return "*"

    visible_length = max(1, len(value) - level)
    return value[:visible_length] + ("*" * level)


def prepare_column_information(rows, quasi_identifiers):
    information = {}

    for column in quasi_identifiers:
        numeric = is_numeric_column(rows, column)

        if numeric:
            values = [
                float(row[column])
                for row in rows
                if row[column].strip()
            ]

            information[column] = {
                "numeric": True,
                "minimum": min(values),
                "maximum": max(values),
            }
        else:
            information[column] = {
                "numeric": False,
            }

    return information


def generalise_row(row, quasi_identifiers, information, level):
    result = row.copy()

    for column in quasi_identifiers:
        value = row.get(column, "")

        if information[column]["numeric"]:
            result[column] = numeric_generalise(
                value,
                information[column]["minimum"],
                information[column]["maximum"],
                level,
            )
        else:
            result[column] = text_generalise(value, level)

    return result


def create_equivalence_classes(rows, quasi_identifiers):
    groups = defaultdict(list)

    for row in rows:
        key = tuple(
            row.get(column, "")
            for column in quasi_identifiers
        )

        groups[key].append(row)

    return groups


def anonymise_for_k(rows, quasi_identifiers, k_value):
    if k_value < 2:
        raise AnonymisationError("k must be at least 2.")

    information = prepare_column_information(
        rows,
        quasi_identifiers,
    )

    max_level = 12
    best_rows = []
    best_level = 0
    best_suppressed = len(rows)

    for level in range(max_level + 1):
        generalised_rows = [
            generalise_row(
                row,
                quasi_identifiers,
                information,
                level,
            )
            for row in rows
        ]

        groups = create_equivalence_classes(
            generalised_rows,
            quasi_identifiers,
        )

        kept_rows = []
        suppressed_count = 0

        for group_rows in groups.values():
            if len(group_rows) >= k_value:
                kept_rows.extend(group_rows)
            else:
                suppressed_count += len(group_rows)

        if suppressed_count < best_suppressed:
            best_rows = kept_rows
            best_level = level
            best_suppressed = suppressed_count

        if suppressed_count == 0:
            return {
                "rows": kept_rows,
                "generalisation_level": level,
                "suppressed_rows": 0,
                "equivalence_classes": groups,
            }

    final_groups = create_equivalence_classes(
        best_rows,
        quasi_identifiers,
    )

    return {
        "rows": best_rows,
        "generalisation_level": best_level,
        "suppressed_rows": best_suppressed,
        "equivalence_classes": final_groups,
    }


def calculate_l_diversity(groups, sensitive_column):
    diversity_values = []

    for group_rows in groups.values():
        values = {
            row.get(sensitive_column, "[MISSING]")
            for row in group_rows
        }

        diversity_values.append(len(values))

    if not diversity_values:
        return {
            "minimum_l_diversity": 0,
            "average_l_diversity": 0.0,
        }

    return {
        "minimum_l_diversity": min(diversity_values),
        "average_l_diversity": round(
            statistics.fmean(diversity_values),
            3,
        ),
    }


def distribution(rows, sensitive_column):
    counts = Counter(
        row.get(sensitive_column, "[MISSING]")
        for row in rows
    )

    total = sum(counts.values())

    if total == 0:
        return {}

    return {
        value: count / total
        for value, count in counts.items()
    }


def calculate_t_closeness(groups, rows, sensitive_column):
    global_distribution = distribution(rows, sensitive_column)
    distances = []

    for group_rows in groups.values():
        group_distribution = distribution(
            group_rows,
            sensitive_column,
        )

        all_values = (
            set(global_distribution)
            | set(group_distribution)
        )

        total_variation_distance = 0.5 * sum(
            abs(
                global_distribution.get(value, 0.0)
                - group_distribution.get(value, 0.0)
            )
            for value in all_values
        )

        distances.append(total_variation_distance)

    if not distances:
        return {
            "maximum_t_closeness": 0.0,
            "average_t_closeness": 0.0,
        }

    return {
        "maximum_t_closeness": round(max(distances), 4),
        "average_t_closeness": round(
            statistics.fmean(distances),
            4,
        ),
    }


def calculate_reidentification_risk(groups, row_count):
    risks = []

    for group_rows in groups.values():
        group_size = len(group_rows)

        if group_size:
            risks.extend([1 / group_size] * group_size)

    if not risks or row_count == 0:
        return {
            "average_reidentification_risk": 0.0,
            "maximum_reidentification_risk": 0.0,
        }

    return {
        "average_reidentification_risk": round(
            statistics.fmean(risks),
            4,
        ),
        "maximum_reidentification_risk": round(
            max(risks),
            4,
        ),
    }


def write_anonymised_csv(file_path, fieldnames, rows):
    with Path(file_path).open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)


def print_report(report):
    print("\n" + "=" * 72)
    print("DATA ANONYMISATION AND RE-IDENTIFICATION RISK REPORT")
    print("=" * 72)
    print(f"Input rows: {report['input_rows']}")
    print(f"Output rows: {report['output_rows']}")
    print(f"Suppressed rows: {report['suppressed_rows']}")
    print(f"k-anonymity target: {report['k_target']}")
    print(
        "Generalisation level: "
        f"{report['generalisation_level']}"
    )
    print(f"Equivalence classes: {report['equivalence_class_count']}")

    print("\nl-diversity:")
    print(
        "  Minimum distinct sensitive values per class: "
        f"{report['l_diversity']['minimum_l_diversity']}"
    )
    print(
        "  Average distinct sensitive values per class: "
        f"{report['l_diversity']['average_l_diversity']}"
    )

    print("\nt-closeness:")
    print(
        "  Maximum total variation distance: "
        f"{report['t_closeness']['maximum_t_closeness']}"
    )
    print(
        "  Average total variation distance: "
        f"{report['t_closeness']['average_t_closeness']}"
    )

    print("\nRe-identification risk:")
    print(
        "  Average risk: "
        f"{report['reidentification_risk']['average_reidentification_risk']}"
    )
    print(
        "  Maximum risk: "
        f"{report['reidentification_risk']['maximum_reidentification_risk']}"
    )

    print("\nNote: risk scores are estimates, not guarantees of anonymity.")


def main():
    print("Data Anonymisation and Re-Identification Risk Scorer")
    print("=" * 72)
    print("This tool operates only on local CSV files.\n")

    csv_path = input("CSV file path: ").strip()

    try:
        source_path, fieldnames, rows = read_csv_file(csv_path)

        print("\nAvailable columns:")
        print(", ".join(fieldnames))

        quasi_input = input(
            "\nQuasi-identifier columns "
            "(comma-separated, e.g. Age,City,Gender): "
        ).strip()

        quasi_identifiers = [
            column.strip()
            for column in quasi_input.split(",")
            if column.strip()
        ]

        if not quasi_identifiers:
            raise AnonymisationError(
                "Enter at least one quasi-identifier column."
            )

        for column in quasi_identifiers:
            if column not in fieldnames:
                raise AnonymisationError(
                    f"Unknown quasi-identifier column: {column}"
                )

        sensitive_column = input(
            "Sensitive attribute column: "
        ).strip()

        if sensitive_column not in fieldnames:
            raise AnonymisationError(
                f"Unknown sensitive column: {sensitive_column}"
            )

        k_value = int(
            input("k-anonymity value [3]: ").strip() or "3"
        )

        result = anonymise_for_k(
            rows,
            quasi_identifiers,
            k_value,
        )

        anonymised_rows = result["rows"]
        groups = create_equivalence_classes(
            anonymised_rows,
            quasi_identifiers,
        )

        report = {
            "source_file": str(source_path.resolve()),
            "input_rows": len(rows),
            "output_rows": len(anonymised_rows),
            "suppressed_rows": result["suppressed_rows"],
            "quasi_identifiers": quasi_identifiers,
            "sensitive_column": sensitive_column,
            "k_target": k_value,
            "generalisation_level": result["generalisation_level"],
            "equivalence_class_count": len(groups),
            "l_diversity": calculate_l_diversity(
                groups,
                sensitive_column,
            ),
            "t_closeness": calculate_t_closeness(
                groups,
                anonymised_rows,
                sensitive_column,
            ),
            "reidentification_risk": calculate_reidentification_risk(
                groups,
                len(anonymised_rows),
            ),
        }

        output_csv = "anonymised_output.csv"
        output_json = "anonymisation_risk_report.json"

        write_anonymised_csv(
            output_csv,
            fieldnames,
            anonymised_rows,
        )

        with open(output_json, "w", encoding="utf-8") as file_handle:
            json.dump(report, file_handle, indent=2)

        print_report(report)
        print(f"\nAnonymised CSV saved: {output_csv}")
        print(f"Risk report saved: {output_json}")

    except FileNotFoundError as error:
        print(f"File error: {error}")

    except ValueError:
        print("Input error: k must be a whole number.")

    except AnonymisationError as error:
        print(f"Anonymisation error: {error}")

    except OSError as error:
        print(f"File system error: {error}")

    except KeyboardInterrupt:
        print("\nOperation cancelled.")

    except Exception as error:
        print(f"Unexpected error: {error}")


if __name__ == "__main__":
    main()