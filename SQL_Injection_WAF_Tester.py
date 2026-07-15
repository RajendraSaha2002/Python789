import itertools
import json
import re
import string


SAFE_TEST_MARKERS = {
    "quote_handling": [
        "TEST_SINGLE_QUOTE_MARKER",
        "TEST_DOUBLE_QUOTE_MARKER",
    ],
    "boolean_logic": [
        "TEST_BOOLEAN_TRUE_MARKER",
        "TEST_BOOLEAN_FALSE_MARKER",
    ],
    "union_pattern": [
        "TEST_UNION_QUERY_MARKER",
    ],
    "error_pattern": [
        "TEST_DATABASE_ERROR_MARKER",
    ],
    "time_pattern": [
        "TEST_DELAY_FUNCTION_MARKER",
    ],
    "stacked_query": [
        "TEST_SECOND_STATEMENT_MARKER",
    ],
}


WAF_RULES = {
    "quote_marker": r"test_(single|double)_quote_marker",
    "boolean_marker": r"test_boolean_(true|false)_marker",
    "union_marker": r"test_union_query_marker",
    "error_marker": r"test_database_error_marker",
    "delay_marker": r"test_delay_function_marker",
    "stacked_marker": r"test_second_statement_marker",
    "suspicious_encoding": r"(%27|%22|%3b|%2d%2d)",
}


def normalise_input(value):
    value = value.lower()
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def simulated_waf_check(value):
    normalised = normalise_input(value)
    matched_rules = []

    for rule_name, pattern in WAF_RULES.items():
        if re.search(pattern, normalised, flags=re.IGNORECASE):
            matched_rules.append(rule_name)

    if matched_rules:
        return {
            "classification": "BLOCKED",
            "matched_rules": matched_rules,
        }

    return {
        "classification": "ALLOWED",
        "matched_rules": [],
    }


def create_test_variants(marker):
    variants = {
        marker,
        marker.lower(),
        marker.upper(),
        marker.replace("_", " "),
        marker.replace("_", "%20"),
    }

    return sorted(variants)


def generate_test_cases():
    test_cases = []

    for category, markers in SAFE_TEST_MARKERS.items():
        for marker in markers:
            for variant in create_test_variants(marker):
                test_cases.append(
                    {
                        "category": category,
                        "marker": marker,
                        "test_value": variant,
                    }
                )

    return test_cases


def run_waf_tests():
    results = []

    for test_case in generate_test_cases():
        waf_result = simulated_waf_check(test_case["test_value"])

        results.append(
            {
                "category": test_case["category"],
                "marker": test_case["marker"],
                "test_value": test_case["test_value"],
                "classification": waf_result["classification"],
                "matched_rules": waf_result["matched_rules"],
            }
        )

    return results


def print_report(results):
    blocked = [
        result
        for result in results
        if result["classification"] == "BLOCKED"
    ]

    allowed = [
        result
        for result in results
        if result["classification"] == "ALLOWED"
    ]

    print("\n" + "=" * 72)
    print("SIMULATED WAF DEFENSIVE TEST REPORT")
    print("=" * 72)
    print(f"Total test cases: {len(results)}")
    print(f"Blocked: {len(blocked)}")
    print(f"Allowed: {len(allowed)}")

    print("\nResults:")

    for result in results:
        print(
            f"\nCategory: {result['category']}"
            f"\nTest: {result['test_value']}"
            f"\nClassification: {result['classification']}"
        )

        if result["matched_rules"]:
            print(
                "Matched rules: "
                + ", ".join(result["matched_rules"])
            )
        else:
            print("Matched rules: None")


def main():
    print("Simulated SQL Injection WAF Defensive Tester")
    print("This program uses safe markers only; it does not attack databases.")

    results = run_waf_tests()
    print_report(results)

    save_choice = input("\nSave JSON report? (y/n): ").strip().lower()

    if save_choice == "y":
        report = {
            "tool": "Simulated WAF Defensive Tester",
            "test_mode": "Safe markers only",
            "results": results,
        }

        try:
            with open(
                "simulated_waf_test_report.json",
                "w",
                encoding="utf-8",
            ) as file_handle:
                json.dump(report, file_handle, indent=2)

            print("Saved: simulated_waf_test_report.json")

        except OSError as error:
            print(f"Could not save report: {error}")


if __name__ == "__main__":
    main()