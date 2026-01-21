def mean(DATA):
    """Calculate the mean of a list of numbers."""
    return sum(DATA) / len(DATA) if DATA else 0

def median(DATA):
    """Calculate the median of a list of numbers."""
    sorted_data = sorted(DATA)
    n = len(sorted_data)
    if n == 0:
        return 0
    mid = n // 2
    if n % 2 == 0:
        return (sorted_data[mid - 1] + sorted_data[mid]) / 2
    else:
        return sorted_data[mid]

def mode(DATA):
    """Calculate the mode of a list of numbers."""
    from collections import Counter
    if not DATA:
        return None
    counts = Counter(DATA)
    max_count = max(counts.values())
    modes = [k for k, v in counts.items() if v == max_count]
    return modes

def variance(DATA):
    """Calculate the variance of a list of numbers."""
    if len(DATA) < 2:
        return 0
    M = mean(DATA)
    return sum((p - M) ** 2 for p in DATA) / (len(DATA) - 1)

def std_deviation(DATA):
    """Calculate the standard deviation of a list of numbers."""
    import math
    return math.sqrt(variance(DATA))

def linear_regression(P, Q):
    """Perform simple linear regression y = mx + c."""
    if len(P) != len(Q) or len(P) < 2:
        return None, None
    n = len(P)
    mean_x = mean(P)
    mean_y = mean(Q)
    numerator = sum((P[i] - mean_x) * (Q[i] - mean_y) for i in range(n))
    denominator = sum((P[i] - mean_x) ** 2 for i in range(n))
    M = numerator / denominator
    C = mean_y - M * mean_x
    return M, C

# Example usage
if __name__ == "__main__":
    data = [1, 2, 2, 3, 4, 4, 4, 5, 6]
    print("Data:", data)
    print("Mean:", mean(data))
    print("Median:", median(data))
    print("Mode:", mode(data))
    print("Variance:", variance(data))
    print("Standard Deviation:", std_deviation(data))

    # Linear regression example
    x = [1, 2, 3, 4, 5]
    y = [2, 4, 5, 4, 5]
    m, c = linear_regression(x, y)
    print(f"Linear regression line: y = {m:.2f}x + {c:.2f}")