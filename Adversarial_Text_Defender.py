import unicodedata
import re
from collections import Counter


# Defensive mapping for common look-alike Unicode characters.
CONFUSABLES = {
    "а": "a", "А": "A",  # Cyrillic
    "е": "e", "Е": "E",
    "о": "o", "О": "O",
    "р": "p", "Р": "P",
    "с": "c", "С": "C",
    "х": "x", "Х": "X",
    "у": "y", "У": "Y",
    "і": "i", "І": "I",
    "ј": "j", "Ј": "J",
    "ѕ": "s", "Ѕ": "S",
    "ԁ": "d",
    "ԛ": "q",
    "ԝ": "w",
}

# Includes zero-width and directional Unicode characters.
INVISIBLE_PATTERN = re.compile(
    r"[\u200B-\u200F\u2060\u2061\u2062\u2063\u2064\u2066-\u2069\uFEFF]"
)

# Small, controlled synonym table for demonstration.
SYNONYMS = {
    "buy": "purchase",
    "free": "complimentary",
    "cheap": "affordable",
    "money": "cash",
    "offer": "proposal",
    "deal": "arrangement",
    "urgent": "important",
    "winner": "recipient",
    "click": "select",
}


def normalize_text(text):
    """Normalize Unicode and lowercase text for defensive comparison."""
    if not isinstance(text, str):
        raise ValueError("Text must be a string.")

    text = unicodedata.normalize("NFKC", text)
    text = INVISIBLE_PATTERN.sub("", text)
    text = "".join(CONFUSABLES.get(char, char) for char in text)
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def keyword_filter(text, blocked_keywords):
    """
    Basic keyword filter.
    Returns matched keywords after defensive normalization.
    """
    normalized = normalize_text(text)
    matches = []

    for keyword in blocked_keywords:
        normalized_keyword = normalize_text(keyword)

        if normalized_keyword in normalized:
            matches.append(keyword)

    return matches


def insert_zero_width_characters(text):
    """Insert zero-width spaces between characters for test data."""
    return "\u200B".join(text)


def replace_with_homoglyphs(text):
    """Replace selected Latin letters with visually similar Cyrillic letters."""
    replacement_map = {
        "a": "а",
        "e": "е",
        "o": "о",
        "p": "р",
        "c": "с",
        "x": "х",
        "y": "у",
        "i": "і",
        "j": "ј",
        "s": "ѕ",
    }

    result = []

    for char in text:
        lower_char = char.lower()

        if lower_char in replacement_map:
            replacement = replacement_map[lower_char]

            if char.isupper():
                replacement = replacement.upper()

            result.append(replacement)
        else:
            result.append(char)

    return "".join(result)


def synonym_swap(text):
    """Replace selected whole words using the controlled synonym map."""
    def replace_word(match):
        word = match.group(0)
        replacement = SYNONYMS.get(word.lower())

        if replacement is None:
            return word

        if word[0].isupper():
            return replacement.capitalize()

        return replacement

    return re.sub(r"\b[A-Za-z]+\b", replace_word, text)


def simple_paraphrase(text):
    """
    Demonstration-only sentence paraphrase.
    Uses constrained substitutions, not an external language model.
    """
    replacements = [
        (r"\bplease buy\b", "please consider purchasing"),
        (r"\bclick here\b", "select this link"),
        (r"\bfree offer\b", "complimentary proposal"),
        (r"\bact now\b", "respond promptly"),
        (r"\byou are a winner\b", "you have been selected"),
    ]

    result = text

    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result


def character_ngrams(text, n=3):
    """Return a Counter of normalized character n-grams."""
    normalized = normalize_text(text)
    normalized = re.sub(r"\s+", " ", normalized)

    if len(normalized) < n:
        return Counter()

    return Counter(
        normalized[index:index + n]
        for index in range(len(normalized) - n + 1)
    )


def ngram_similarity(first_text, second_text, n=3):
    """
    Calculate Dice similarity between character n-gram sets.
    A value near 1.0 means texts are highly similar.
    """
    first_ngrams = set(character_ngrams(first_text, n))
    second_ngrams = set(character_ngrams(second_text, n))

    if not first_ngrams and not second_ngrams:
        return 1.0

    if not first_ngrams or not second_ngrams:
        return 0.0

    overlap = len(first_ngrams.intersection(second_ngrams))
    return (2 * overlap) / (len(first_ngrams) + len(second_ngrams))


def analyze_variant(original, variant, blocked_keywords):
    """Analyze whether a variant is detected before and after normalization."""
    raw_matches = [
        keyword
        for keyword in blocked_keywords
        if keyword.lower() in variant.lower()
    ]

    defended_matches = keyword_filter(variant, blocked_keywords)
    similarity = ngram_similarity(original, variant)

    return {
        "raw_matches": raw_matches,
        "defended_matches": defended_matches,
        "similarity": similarity,
        "normalized_variant": normalize_text(variant),
    }


def print_result(name, original, variant, blocked_keywords):
    """Print test results clearly."""
    result = analyze_variant(original, variant, blocked_keywords)

    print("\n" + "=" * 70)
    print(f"Test: {name}")
    print("=" * 70)
    print(f"Variant: {variant}")
    print(f"Raw keyword filter matches: {result['raw_matches']}")
    print(f"Defended filter matches: {result['defended_matches']}")
    print(f"N-gram similarity: {result['similarity']:.3f}")
    print(f"Normalized form: {result['normalized_variant']}")


def main():
    print("Adversarial Text Attack Generator and Defender")
    print("-" * 70)

    original = input(
        "Enter text to test "
        "(example: 'Click here for a free offer'): "
    ).strip()

    if not original:
        print("Error: text cannot be empty.")
        return

    blocked_keywords = [
        "click here",
        "free offer",
        "buy",
        "urgent",
        "winner",
    ]

    variants = {
        "Original text": original,
        "Zero-width character insertion": insert_zero_width_characters(original),
        "Homoglyph substitution": replace_with_homoglyphs(original),
        "Word-level synonym swap": synonym_swap(original),
        "Controlled sentence paraphrase": simple_paraphrase(original),
    }

    print("\nBlocked keywords:", ", ".join(blocked_keywords))

    for name, variant in variants.items():
        print_result(name, original, variant, blocked_keywords)

    print("\n" + "=" * 70)
    print("Defensive recommendation")
    print("=" * 70)
    print(
        "Normalize input with Unicode NFKC, remove invisible characters, "
        "map confusables, then apply keyword and similarity checks."
    )


if __name__ == "__main__":
    main()