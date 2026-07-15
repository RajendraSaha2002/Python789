import hashlib
import re
import string


COMMON_PASSWORDS = {
    "password", "password1", "123456", "12345678", "123456789",
    "qwerty", "abc123", "letmein", "welcome", "admin", "admin123",
    "iloveyou", "monkey", "dragon", "football", "baseball",
    "login", "princess", "master", "sunshine", "passw0rd",
}


KEYBOARD_PATTERNS = [
    "qwerty", "asdf", "zxcv", "1234", "2345", "3456",
    "4567", "5678", "6789", "7890", "qaz", "wsx", "edc",
]


def estimate_character_pool(password):
    pool_size = 0

    if any(character.islower() for character in password):
        pool_size += 26

    if any(character.isupper() for character in password):
        pool_size += 26

    if any(character.isdigit() for character in password):
        pool_size += 10

    if any(character in string.punctuation for character in password):
        pool_size += len(string.punctuation)

    if any(not character.isascii() for character in password):
        pool_size += 100

    return pool_size


def estimate_entropy(password):
    pool_size = estimate_character_pool(password)

    if not password or pool_size == 0:
        return 0.0

    import math
    return round(len(password) * math.log2(pool_size), 2)


def contains_keyboard_pattern(password):
    lowered = password.lower()

    return [
        pattern
        for pattern in KEYBOARD_PATTERNS
        if pattern in lowered
    ]


def contains_date_pattern(password):
    patterns = [
        r"\b(19|20)\d{2}\b",
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b(0[1-9]|1[0-2])\d{2}\b",
    ]

    return any(
        re.search(pattern, password)
        for pattern in patterns
    )


def has_repeated_characters(password):
    return bool(re.search(r"(.)\1\1", password))


def has_repeated_sequence(password):
    return bool(
        re.search(r"(.{2,4})\1{2,}", password)
    )


def analyse_password(password):
    findings = []
    score = 0

    if len(password) >= 15:
        score += 3
    elif len(password) >= 12:
        score += 2
    elif len(password) >= 8:
        score += 1
    else:
        findings.append("Password is shorter than 8 characters.")

    lowered = password.lower()

    if lowered in COMMON_PASSWORDS:
        findings.append("Password appears in a common-password list.")
        score -= 5

    if any(word in lowered for word in COMMON_PASSWORDS):
        findings.append("Password contains a common password word.")
        score -= 2

    keyboard_matches = contains_keyboard_pattern(password)

    if keyboard_matches:
        findings.append(
            "Keyboard walk pattern found: "
            + ", ".join(keyboard_matches)
        )
        score -= 2

    if contains_date_pattern(password):
        findings.append("Possible date or year pattern found.")
        score -= 1

    if has_repeated_characters(password):
        findings.append("Repeated characters found.")
        score -= 1

    if has_repeated_sequence(password):
        findings.append("Repeated sequence found.")
        score -= 1

    character_types = sum(
        [
            any(char.islower() for char in password),
            any(char.isupper() for char in password),
            any(char.isdigit() for char in password),
            any(char in string.punctuation for char in password),
        ]
    )

    if character_types >= 3:
        score += 2
    elif character_types == 2:
        score += 1
    else:
        findings.append(
            "Password uses limited character variety."
        )

    entropy = estimate_entropy(password)

    if entropy >= 80:
        score += 3
    elif entropy >= 60:
        score += 2
    elif entropy >= 40:
        score += 1
    else:
        findings.append("Estimated entropy is low.")

    if score >= 7:
        strength = "STRONG"
    elif score >= 4:
        strength = "MODERATE"
    else:
        strength = "WEAK"

    if not findings:
        findings.append(
            "No obvious weakness patterns were detected."
        )

    return {
        "length": len(password),
        "estimated_entropy_bits": entropy,
        "character_pool_size": estimate_character_pool(password),
        "character_types_used": character_types,
        "score": score,
        "strength": strength,
        "findings": findings,
    }


def create_pbkdf2_hash(password):
    """
    Creates a secure PBKDF2-SHA256 password hash for your own application.
    """
    salt = hashlib.sha256(
        password.encode("utf-8")
        + b"local-demo-salt"
    ).digest()[:16]

    iterations = 310000

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )

    return {
        "algorithm": "PBKDF2-HMAC-SHA256",
        "iterations": iterations,
        "salt_hex": salt.hex(),
        "hash_hex": password_hash.hex(),
    }


def print_report(report):
    print("\n" + "=" * 72)
    print("PASSWORD STRENGTH REPORT")
    print("=" * 72)
    print(f"Length: {report['length']}")
    print(f"Character pool size: {report['character_pool_size']}")
    print(f"Character types used: {report['character_types_used']}")
    print(
        f"Estimated entropy: "
        f"{report['estimated_entropy_bits']} bits"
    )
    print(f"Score: {report['score']}")
    print(f"Strength: {report['strength']}")

    print("\nFindings:")

    for finding in report["findings"]:
        print(f"  - {finding}")

    print(
        "\nRecommendation: use a unique password manager-generated "
        "password or a long, random passphrase."
    )


def main():
    print("Password Strength Analyzer")
    print("=" * 72)

    password = input("Enter a password to analyse: ")

    if not password:
        print("Error: password cannot be empty.")
        return

    report = analyse_password(password)
    print_report(report)

    hash_choice = input(
        "\nCreate a PBKDF2-SHA256 demo hash? (y/n): "
    ).strip().lower()

    if hash_choice == "y":
        hash_info = create_pbkdf2_hash(password)

        print("\nPBKDF2 Hash Information")
        print(f"Algorithm: {hash_info['algorithm']}")
        print(f"Iterations: {hash_info['iterations']}")
        print(f"Salt: {hash_info['salt_hex']}")
        print(f"Hash: {hash_info['hash_hex']}")


if __name__ == "__main__":
    main()