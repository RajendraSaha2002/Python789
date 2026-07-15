import base64
import re
import unicodedata


ZERO_WIDTH_BITS = {
    "0": "\u200b",  # Zero Width Space
    "1": "\u200c",  # Zero Width Non-Joiner
}

ZERO_WIDTH_DECODE = {
    "\u200b": "0",
    "\u200c": "1",
}

VARIATION_BITS = {
    "0": "\ufe00",  # Variation Selector-1
    "1": "\ufe01",  # Variation Selector-2
}

VARIATION_DECODE = {
    "\ufe00": "0",
    "\ufe01": "1",
}

HOMOGLYPHS = {
    "a": "а",  # Cyrillic a
    "c": "с",  # Cyrillic c
    "e": "е",  # Cyrillic e
    "i": "і",  # Cyrillic i
    "j": "ј",  # Cyrillic j
    "o": "о",  # Cyrillic o
    "p": "р",  # Cyrillic p
    "s": "ѕ",  # Cyrillic s
    "x": "х",  # Cyrillic x
    "y": "у",  # Cyrillic y
    "A": "А",
    "B": "В",
    "C": "С",
    "E": "Е",
    "H": "Н",
    "I": "І",
    "K": "К",
    "M": "М",
    "O": "О",
    "P": "Р",
    "S": "Ѕ",
    "T": "Т",
    "X": "Х",
    "Y": "У",
}

KNOWN_HOMOGLYPHS = set(HOMOGLYPHS.values())


def text_to_bits(text):
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    bits = "".join(f"{ord(char):08b}" for char in encoded)
    length = f"{len(bits):032b}"
    return length + bits


def bits_to_text(bits):
    if len(bits) < 32:
        raise ValueError("Hidden payload is too short.")

    payload_length = int(bits[:32], 2)
    payload_bits = bits[32:32 + payload_length]

    if len(payload_bits) != payload_length:
        raise ValueError("Hidden payload is incomplete.")

    if payload_length % 8 != 0:
        raise ValueError("Hidden payload has invalid bit length.")

    encoded_text = "".join(
        chr(int(payload_bits[index:index + 8], 2))
        for index in range(0, payload_length, 8)
    )

    try:
        return base64.b64decode(encoded_text).decode("utf-8")
    except Exception as error:
        raise ValueError(
            f"Hidden payload could not be decoded: {error}"
        ) from error


def embed_invisible_text(cover_text, secret_text, mode):
    if not cover_text:
        raise ValueError("Cover text cannot be empty.")

    bits = text_to_bits(secret_text)

    if len(cover_text) < len(bits):
        raise ValueError(
            f"Cover text needs at least {len(bits)} characters. "
            f"It currently has {len(cover_text)}."
        )

    if mode == "zero_width":
        mapping = ZERO_WIDTH_BITS
    elif mode == "variation_selector":
        mapping = VARIATION_BITS
    else:
        raise ValueError("Unknown embedding mode.")

    output = []

    for index, character in enumerate(cover_text):
        output.append(character)

        if index < len(bits):
            output.append(mapping[bits[index]])

    return "".join(output)


def extract_invisible_text(stego_text, mode):
    if mode == "zero_width":
        decoding = ZERO_WIDTH_DECODE
    elif mode == "variation_selector":
        decoding = VARIATION_DECODE
    else:
        raise ValueError("Unknown extraction mode.")

    bits = "".join(
        decoding[character]
        for character in stego_text
        if character in decoding
    )

    return bits_to_text(bits)


def create_homoglyph_text(text):
    if not text:
        raise ValueError("Text cannot be empty.")

    return "".join(
        HOMOGLYPHS.get(character, character)
        for character in text
    )


def remove_invisible_characters(text):
    invisible_characters = (
        "\u200b"
        "\u200c"
        "\u200d"
        "\u2060"
        "\ufeff"
        "\ufe00"
        "\ufe01"
    )

    return "".join(
        character
        for character in text
        if character not in invisible_characters
    )


def analyze_unicode_text(text):
    findings = []
    character_details = []

    zero_width_counts = {
        "U+200B Zero Width Space": text.count("\u200b"),
        "U+200C Zero Width Non-Joiner": text.count("\u200c"),
        "U+200D Zero Width Joiner": text.count("\u200d"),
        "U+2060 Word Joiner": text.count("\u2060"),
        "U+FEFF Zero Width No-Break Space": text.count("\ufeff"),
    }

    variation_selector_count = sum(
        1
        for character in text
        if "\ufe00" <= character <= "\ufe0f"
    )

    homoglyph_count = 0

    for position, character in enumerate(text):
        if character in KNOWN_HOMOGLYPHS:
            homoglyph_count += 1

        category = unicodedata.category(character)

        if (
            character in ZERO_WIDTH_DECODE
            or character in VARIATION_DECODE
            or character in KNOWN_HOMOGLYPHS
        ):
            character_details.append(
                {
                    "position": position,
                    "character": character,
                    "unicode": f"U+{ord(character):04X}",
                    "name": unicodedata.name(
                        character,
                        "UNKNOWN",
                    ),
                    "category": category,
                }
            )

    if any(zero_width_counts.values()):
        findings.append(
            "Zero-width Unicode characters detected."
        )

    if variation_selector_count:
        findings.append(
            "Variation selector characters detected."
        )

    if homoglyph_count:
        findings.append(
            "Potential Cyrillic/Greek homoglyph characters detected."
        )

    if not findings:
        findings.append(
            "No obvious Unicode steganography indicators found."
        )

    return {
        "text_length": len(text),
        "zero_width_counts": zero_width_counts,
        "variation_selector_count": variation_selector_count,
        "homoglyph_count": homoglyph_count,
        "findings": findings,
        "suspicious_characters": character_details,
        "visible_normalized_text": remove_invisible_characters(text),
    }


def print_analysis(report):
    print("\n" + "=" * 72)
    print("UNICODE STEGANOGRAPHY ANALYSIS REPORT")
    print("=" * 72)
    print(f"Total characters: {report['text_length']}")

    print("\nZero-width character counts:")

    for name, count in report["zero_width_counts"].items():
        print(f"  {name}: {count}")

    print(
        "\nVariation selectors: "
        f"{report['variation_selector_count']}"
    )

    print(
        "Potential homoglyphs: "
        f"{report['homoglyph_count']}"
    )

    print("\nFindings:")

    for finding in report["findings"]:
        print(f"  - {finding}")

    print("\nSuspicious characters:")

    if report["suspicious_characters"]:
        for item in report["suspicious_characters"][:30]:
            print(
                f"  Position {item['position']}: "
                f"{item['unicode']} | {item['name']}"
            )

        if len(report["suspicious_characters"]) > 30:
            print("  ... additional suspicious characters omitted.")
    else:
        print("  None")

    print("\nVisible text after removing invisible characters:")
    print(report["visible_normalized_text"])


def main():
    print("Unicode Whitespace and Zero-Width Steganography")
    print("=" * 72)
    print("1 - Embed secret using zero-width characters")
    print("2 - Extract zero-width hidden text")
    print("3 - Embed secret using variation selectors")
    print("4 - Extract variation-selector hidden text")
    print("5 - Create homoglyph text")
    print("6 - Detect Unicode steganography")

    choice = input("\nChoose an option (1-6): ").strip()

    try:
        if choice == "1":
            cover = input("Cover text: ")
            secret = input("Secret message: ")

            result = embed_invisible_text(
                cover,
                secret,
                "zero_width",
            )

            print("\nStego text created.")
            print("Copy this text exactly:")
            print(result)

        elif choice == "2":
            stego = input("Paste zero-width stego text: ")

            secret = extract_invisible_text(
                stego,
                "zero_width",
            )

            print("\nExtracted hidden message:")
            print(secret)

        elif choice == "3":
            cover = input("Cover text: ")
            secret = input("Secret message: ")

            result = embed_invisible_text(
                cover,
                secret,
                "variation_selector",
            )

            print("\nStego text created.")
            print("Copy this text exactly:")
            print(result)

        elif choice == "4":
            stego = input("Paste variation-selector stego text: ")

            secret = extract_invisible_text(
                stego,
                "variation_selector",
            )

            print("\nExtracted hidden message:")
            print(secret)

        elif choice == "5":
            text = input("Text to convert to homoglyph form: ")
            result = create_homoglyph_text(text)

            print("\nHomoglyph text:")
            print(result)

        elif choice == "6":
            text = input("Paste text to analyse: ")
            report = analyze_unicode_text(text)
            print_analysis(report)

        else:
            print("Error: choose a number from 1 to 6.")

    except ValueError as error:
        print(f"Error: {error}")

    except KeyboardInterrupt:
        print("\nOperation cancelled.")

    except Exception as error:
        print(f"Unexpected error: {error}")


if __name__ == "__main__":
    main()