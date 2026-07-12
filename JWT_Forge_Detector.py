import base64
import hashlib
import hmac
import json


def base64url_decode(value):
    """Decode Base64URL text safely."""
    value += "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value.encode("utf-8"))


def base64url_encode(data):
    """Encode bytes as Base64URL without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def decode_json_segment(segment, segment_name):
    """Decode a JWT segment and parse it as JSON."""
    try:
        raw = base64url_decode(segment)
        return json.loads(raw.decode("utf-8"))
    except Exception as error:
        raise ValueError(f"Invalid JWT {segment_name}: {error}")


def parse_jwt(token):
    """Split and decode a JWT."""
    if not isinstance(token, str):
        raise ValueError("JWT must be a string.")

    parts = token.strip().split(".")

    if len(parts) != 3:
        raise ValueError("JWT must contain exactly 3 dot-separated parts.")

    header_b64, payload_b64, signature_b64 = parts

    if not header_b64 or not payload_b64:
        raise ValueError("JWT header and payload must not be empty.")

    header = decode_json_segment(header_b64, "header")
    payload = decode_json_segment(payload_b64, "payload")

    if not isinstance(header, dict):
        raise ValueError("JWT header must be a JSON object.")

    if not isinstance(payload, dict):
        raise ValueError("JWT payload must be a JSON object.")

    return {
        "header_b64": header_b64,
        "payload_b64": payload_b64,
        "signature_b64": signature_b64,
        "header": header,
        "payload": payload,
    }


def verify_hs256(token, secret):
    """
    Verify an HS256 JWT signature.
    Returns True only when the token is correctly signed using the supplied secret.
    """
    if not isinstance(secret, str) or not secret:
        raise ValueError("Secret must be a non-empty string.")

    parsed = parse_jwt(token)
    algorithm = parsed["header"].get("alg")

    # Never trust the algorithm solely because the token declares it.
    if algorithm != "HS256":
        return False

    signing_input = f'{parsed["header_b64"]}.{parsed["payload_b64"]}'.encode("utf-8")

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    expected_signature_b64 = base64url_encode(expected_signature)

    return hmac.compare_digest(
        expected_signature_b64,
        parsed["signature_b64"],
    )


def detect_security_issues(token):
    """
    Perform defensive JWT checks.
    These checks identify risky token characteristics; they do not exploit anything.
    """
    parsed = parse_jwt(token)
    header = parsed["header"]
    issues = []

    algorithm = header.get("alg")
    kid = header.get("kid")
    jwt_type = header.get("typ")

    if not algorithm:
        issues.append("Missing 'alg' header.")
    elif str(algorithm).lower() == "none":
        issues.append(
            "CRITICAL: 'alg: none' detected. Reject unsigned JWTs."
        )
    elif algorithm not in {"HS256", "HS384", "HS512", "RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}:
        issues.append(f"Unknown or unsupported algorithm: {algorithm!r}.")

    if algorithm and str(algorithm).startswith("HS") and header.get("x5c"):
        issues.append(
            "WARNING: HMAC algorithm used with certificate header data. "
            "Ensure RSA public keys are never accepted as HMAC secrets."
        )

    if algorithm and str(algorithm).startswith("HS") and header.get("jwk"):
        issues.append(
            "WARNING: HMAC algorithm with embedded JWK. Do not use attacker-supplied keys."
        )

    if kid is not None:
        if not isinstance(kid, str):
            issues.append("WARNING: 'kid' should be a string.")
        else:
            dangerous_kid_patterns = [
                "../",
                "..\\",
                "/etc/",
                "\\windows\\",
                "select ",
                "union ",
                " or ",
                "'",
                '"',
                ";",
                "--",
                "$(",
                "`",
            ]

            normalized_kid = kid.lower()

            if any(pattern in normalized_kid for pattern in dangerous_kid_patterns):
                issues.append(
                    "CRITICAL: Suspicious 'kid' value detected. "
                    "Use a fixed allowlist of key IDs; never use 'kid' as a file path or database query."
                )

            if len(kid) > 128:
                issues.append("WARNING: 'kid' is unusually long.")

    if jwt_type is not None and jwt_type != "JWT":
        issues.append(f"WARNING: Unexpected token type: {jwt_type!r}.")

    if not parsed["signature_b64"]:
        issues.append("CRITICAL: JWT signature is empty.")

    return parsed, issues


def main():
    print("JWT Forge Detector and Signature Validator")
    print("-" * 48)

    token = input("Paste JWT: ").strip()

    try:
        parsed, issues = detect_security_issues(token)

        print("\nDecoded header:")
        print(json.dumps(parsed["header"], indent=2))

        print("\nDecoded payload:")
        print(json.dumps(parsed["payload"], indent=2))

        print("\nSecurity checks:")

        if issues:
            for issue in issues:
                print(f"- {issue}")
        else:
            print("- No obvious structural security issues found.")

        algorithm = parsed["header"].get("alg")

        if algorithm == "HS256":
            secret = input("\nEnter HS256 secret for verification: ").strip()

            if verify_hs256(token, secret):
                print("\nSignature result: VALID")
            else:
                print("\nSignature result: INVALID")

        else:
            print(
                "\nSignature verification skipped: this script implements "
                "HS256 verification only."
            )

    except ValueError as error:
        print(f"\nInvalid token: {error}")
    except Exception as error:
        print(f"\nUnexpected error: {error}")


if __name__ == "__main__":
    main()