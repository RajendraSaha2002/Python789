import base64
import string
from collections import Counter, deque


# ---------------------------------------------------------------------------
# Configuration and small data tables
# ---------------------------------------------------------------------------

PRINTABLE_BYTES = frozenset(range(32, 127)) | frozenset((9, 10, 13))
BASE64_ALPHABET = frozenset((string.ascii_letters + string.digits + "+/=").encode("ascii"))
COMMON_WORDS = (
    " the ", " and ", " this ", " that ", " with ", " from ", " for ",
    " is ", " are ", " to ", " of ", " in ", " on ", " at ", " by ",
    " a ", " an ", " config", " status", " mode", " user", " path", "http",
    "true", "false", "error", "message", "string", "data", "value", "key",
)
COMMON_BIGRAMS = (
    "th", "he", "in", "er", "an", "re", "on", "at", "en", "nd", "ti",
    "es", "or", "te", "of", "ed", "is", "it", "al", "ar", "st", "to",
    "nt", "ng", "se", "ha", "as", "ou", "io", "le", "ve", "co", "me",
)
SUSPICIOUS_WORDS = (
    "powershell", "cmd.exe", "wscript", "cscript", "rundll32", "regsvr32",
    "download", "payload", "socket", "injection", "credential", "password",
    "http://", "https://", "base64", "xor", "encrypt", "decrypt",
)
KNOWN_EXTENSIONS = (".exe", ".dll", ".bat", ".cmd", ".ps1", ".vbs", ".js")
MAX_INPUT_BYTES = 1_000_000
MAX_SEARCH_DEPTH = 5
DEFAULT_BEAM_WIDTH = 10
MAX_PREVIEW = 180


# ---------------------------------------------------------------------------
# General representation helpers
# ---------------------------------------------------------------------------

def require_bytes(data, name="data"):
    """Validate an in-memory bytes-like value and return immutable bytes."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError(name + " must be bytes, bytearray, or memoryview")
    value = bytes(data)
    if len(value) > MAX_INPUT_BYTES:
        raise ValueError(name + " exceeds the safe analysis limit of " + str(MAX_INPUT_BYTES) + " bytes")
    return value


def visible_text(data, limit=MAX_PREVIEW):
    """Render bytes as a readable escaped preview without treating them as code."""
    data = require_bytes(data)
    clipped = data[:limit]
    pieces = []
    for byte in clipped:
        if byte == 10:
            pieces.append("\\n")
        elif byte == 13:
            pieces.append("\\r")
        elif byte == 9:
            pieces.append("\\t")
        elif 32 <= byte <= 126:
            pieces.append(chr(byte))
        else:
            pieces.append("\\x%02x" % byte)
    suffix = "..." if len(data) > limit else ""
    return "".join(pieces) + suffix


def ascii_lower(data):
    """ASCII-only lowercase conversion, preserving non-ASCII bytes exactly."""
    output = bytearray()
    for byte in data:
        output.append(byte + 32 if 65 <= byte <= 90 else byte)
    return bytes(output)


def is_probably_text(data, threshold=0.90):
    """Return whether the fraction of printable/control whitespace is high."""
    data = require_bytes(data)
    if not data:
        return True
    return printable_ratio(data) >= threshold


def printable_ratio(data):
    """Return a number in [0, 1] estimating how much of data is visible text."""
    data = require_bytes(data)
    if not data:
        return 1.0
    return sum(byte in PRINTABLE_BYTES for byte in data) / len(data)


def byte_histogram(data):
    """Return a Counter mapping byte values to their frequency."""
    return Counter(require_bytes(data))


def top_bytes(data, count=8):
    """Return the most common raw bytes as displayable (hex, frequency) pairs."""
    if count < 1:
        raise ValueError("count must be positive")
    return [("%02x" % byte, frequency) for byte, frequency in byte_histogram(data).most_common(count)]


# ---------------------------------------------------------------------------
# Entropy analysis with a self-contained log2 approximation
# ---------------------------------------------------------------------------

def log2_approx(value):
    """Approximate base-2 logarithm using only arithmetic (no math import).

    The result is sufficiently accurate for classifying text-like, encoded, and
    random-looking buffers; it is not intended for scientific measurement.
    """
    if value <= 0.0:
        raise ValueError("log2 is defined here only for positive values")
    exponent = 0
    while value >= 2.0:
        value /= 2.0
        exponent += 1
    while value < 1.0:
        value *= 2.0
        exponent -= 1
    fractional = 0.0
    weight = 0.5
    # Binary logarithm by repeatedly squaring the normalized mantissa.
    for _ in range(20):
        value *= value
        if value >= 2.0:
            value /= 2.0
            fractional += weight
        weight *= 0.5
    return exponent + fractional


def shannon_entropy(data):
    """Estimate Shannon entropy in bits/byte for a byte sequence."""
    data = require_bytes(data)
    if not data:
        return 0.0
    total = len(data)
    entropy = 0.0
    for frequency in byte_histogram(data).values():
        probability = frequency / total
        entropy -= probability * log2_approx(probability)
    return entropy


def entropy_band(entropy):
    """Convert an entropy measurement into a cautious descriptive category."""
    if entropy < 3.0:
        return "very low: repetitive or highly structured"
    if entropy < 4.5:
        return "low: likely plain text or a simple structured encoding"
    if entropy < 5.7:
        return "moderate: mixed text/encoded data"
    if entropy < 7.2:
        return "high: compressed, encoded, encrypted, or obfuscated-looking"
    return "very high: random-looking; often compressed or encrypted"


def base64_character_ratio(data):
    """Measure the fraction of non-whitespace bytes allowed in Base64 text."""
    data = require_bytes(data)
    meaningful = bytes(byte for byte in data if byte not in (9, 10, 13, 32))
    if not meaningful:
        return 0.0
    return sum(byte in BASE64_ALPHABET for byte in meaningful) / len(meaningful)


def layer_hints(data):
    """Return non-conclusive clues about likely active obfuscation layers."""
    data = require_bytes(data)
    entropy = shannon_entropy(data)
    hints = []
    if looks_like_base64(data):
        hints.append("Base64 alphabet/padding pattern detected")
    if is_probably_text(data):
        hints.append("mostly printable text")
    else:
        hints.append("contains substantial non-printable data")
    if entropy >= 6.8:
        hints.append("high entropy may indicate XOR, compression, encryption, or binary data")
    elif entropy <= 4.5:
        hints.append("low entropy is compatible with ordinary text or simple encoding")
    if len(data) >= 2 and len(data) % 2 == 0 and swap_pair_bytes(data) != data:
        swapped = swap_pair_bytes(data)
        if printable_ratio(swapped) > printable_ratio(data) + 0.25:
            hints.append("adjacent-byte swapping substantially improves text-likeness")
    return hints


# ---------------------------------------------------------------------------
# Individual reversible layers
# ---------------------------------------------------------------------------

def xor_single_byte(data, key):
    """Apply a one-byte XOR key. The same function reverses the operation."""
    data = require_bytes(data)
    if not isinstance(key, int) or not 0 <= key <= 255:
        raise ValueError("XOR key must be an integer from 0 through 255")
    return bytes(byte ^ key for byte in data)


def rot13_bytes(data):
    """Apply ROT13 to ASCII letters; non-letter bytes are untouched."""
    data = require_bytes(data)
    output = bytearray()
    for byte in data:
        if 65 <= byte <= 90:
            output.append(65 + ((byte - 65 + 13) % 26))
        elif 97 <= byte <= 122:
            output.append(97 + ((byte - 97 + 13) % 26))
        else:
            output.append(byte)
    return bytes(output)


def swap_pair_bytes(data):
    """Swap adjacent bytes. For odd lengths, leave the final byte untouched."""
    data = require_bytes(data)
    output = bytearray(data)
    for index in range(0, len(output) - 1, 2):
        output[index], output[index + 1] = output[index + 1], output[index]
    return bytes(output)


def normalize_base64(data):
    """Remove ASCII whitespace and restore missing Base64 padding if needed."""
    data = require_bytes(data)
    compact = bytes(byte for byte in data if byte not in (9, 10, 13, 32))
    return compact + b"=" * ((-len(compact)) % 4)


def looks_like_base64(data):
    """Conservatively test whether data is plausible standard Base64 text."""
    data = require_bytes(data)
    compact = bytes(byte for byte in data if byte not in (9, 10, 13, 32))
    if len(compact) < 4 or base64_character_ratio(compact) < 1.0:
        return False
    if b"=" in compact[:-2]:
        return False
    try:
        base64.b64decode(normalize_base64(compact), validate=True)
        return True
    except ValueError:
        return False


def decode_base64(data):
    """Strictly decode a standard Base64 layer; reject malformed input."""
    data = require_bytes(data)
    compact = bytes(byte for byte in data if byte not in (9, 10, 13, 32))
    if not looks_like_base64(compact):
        raise ValueError("data is not valid standard Base64")
    return base64.b64decode(normalize_base64(compact), validate=True)


def reconstruct_stack_string(fragments, reverse_push_order=True, separator=b""):
    """Safely reconstruct a stack-built string from an iterable of byte fragments.

    In many disassembly views, pushes are listed in execution order but strings
    emerge in reverse order due to stack LIFO behavior. Set reverse_push_order
    accordingly; no code or instruction bytes are interpreted or executed.
    """
    if not isinstance(separator, (bytes, bytearray, memoryview)):
        raise TypeError("separator must be bytes-like")
    clean = [require_bytes(fragment, "stack fragment") for fragment in fragments]
    if reverse_push_order:
        clean.reverse()
    return bytes(separator).join(clean)


def unpack_little_endian_dwords(values, trim_nuls=True):
    """Turn immediate 32-bit stack values into their little-endian byte chunks."""
    chunks = []
    for value in values:
        if not isinstance(value, int) or not 0 <= value <= 0xFFFFFFFF:
            raise ValueError("each dword must be an unsigned 32-bit integer")
        chunk = value.to_bytes(4, "little")
        chunks.append(chunk.rstrip(b"\x00") if trim_nuls else chunk)
    return reconstruct_stack_string(chunks, reverse_push_order=True)


# ---------------------------------------------------------------------------
# English-frequency scoring and single-byte XOR search
# ---------------------------------------------------------------------------

def character_class_score(data):
    """Score plausible human-readable bytes while penalizing control bytes."""
    data = require_bytes(data)
    if not data:
        return -20.0
    score = 0.0
    for byte in data:
        if byte in (9, 10, 13):
            score += 0.4
        elif 32 <= byte <= 126:
            score += 1.0
        elif byte < 32 or byte == 127:
            score -= 4.5
        else:
            score -= 2.0
    return score / len(data)


def english_frequency_score(data):
    """Rank likely English-like text; heuristic only, not a language detector."""
    data = require_bytes(data)
    if not data:
        return -100.0
    text = ascii_lower(data).decode("latin-1", errors="ignore")
    score = character_class_score(data) * 12.0
    letters = sum(character in string.ascii_lowercase for character in text)
    spaces = text.count(" ")
    digits = sum(character.isdigit() for character in text)
    score += 2.0 * letters / len(text)
    score += 1.5 * min(spaces, max(1, len(text) // 5)) / max(1, len(text) // 5)
    score += 0.3 * digits / len(text)
    for word in COMMON_WORDS:
        score += 4.5 * text.count(word)
    for bigram in COMMON_BIGRAMS:
        score += 0.40 * text.count(bigram)
    score -= 2.0 * (text.count("@@") + text.count("~~") + text.count("\x00"))
    return score


class XorCandidate:
    """A ranked outcome from an exhaustive single-byte XOR key search."""

    def __init__(self, key, plaintext, score):
        self.key = key
        self.plaintext = plaintext
        self.score = score

    def summary(self):
        return {
            "key_decimal": self.key,
            "key_hex": "0x%02X" % self.key,
            "score": round(self.score, 3),
            "preview": visible_text(self.plaintext),
            "entropy": round(shannon_entropy(self.plaintext), 3),
            "printable_ratio": round(printable_ratio(self.plaintext), 3),
        }


def score_xor_candidate(plaintext):
    """Combine readable-text and plausible-next-layer evidence for XOR ranking."""
    score = english_frequency_score(plaintext)
    if looks_like_base64(plaintext):
        score += 20.0
    if plaintext.startswith((b"http://", b"https://", b"{" , b"[", b"<")):
        score += 5.0
    return score


def brute_force_single_byte_xor(data, limit=12):
    """Try all 256 keys and return the highest ranked candidate objects."""
    data = require_bytes(data)
    if not isinstance(limit, int) or limit < 1 or limit > 256:
        raise ValueError("limit must be an integer in [1, 256]")
    candidates = []
    for key in range(256):
        plaintext = xor_single_byte(data, key)
        candidates.append(XorCandidate(key, plaintext, score_xor_candidate(plaintext)))
    candidates.sort(key=lambda item: (-item.score, item.key))
    return candidates[:limit]


# ---------------------------------------------------------------------------
# Multi-layer search
# ---------------------------------------------------------------------------

class Layer:
    """One reversible transform used on a candidate during the search."""

    def __init__(self, name, detail=""):
        self.name = name
        self.detail = detail

    def label(self):
        return self.name if not self.detail else self.name + " (" + self.detail + ")"


class AnalysisCandidate:
    """A state in the bounded breadth-first deobfuscation search."""

    def __init__(self, data, layers=(), score=None):
        self.data = require_bytes(data)
        self.layers = tuple(layers)
        self.score = score if score is not None else candidate_score(self.data)

    def path(self):
        return " -> ".join(layer.label() for layer in self.layers) or "original input"

    def summary(self):
        return {
            "path": self.path(),
            "score": round(self.score, 3),
            "length": len(self.data),
            "entropy": round(shannon_entropy(self.data), 3),
            "entropy_band": entropy_band(shannon_entropy(self.data)),
            "printable_ratio": round(printable_ratio(self.data), 3),
            "preview": visible_text(self.data),
        }


def candidate_score(data):
    """Score a search state while favouring readable output and recognized layers."""
    data = require_bytes(data)
    score = english_frequency_score(data)
    entropy = shannon_entropy(data)
    if 3.0 <= entropy <= 5.8:
        score += 2.0
    if looks_like_base64(data):
        score += 8.0
    lower = ascii_lower(data)
    for term in SUSPICIOUS_WORDS:
        if term.encode("ascii") in lower:
            score += 1.0
    return score


def likely_transforms(candidate, xor_per_state=5):
    """Generate bounded, safe reverse-transform possibilities for a candidate."""
    data = candidate.data
    produced = []
    if looks_like_base64(data):
        try:
            decoded = decode_base64(data)
            produced.append(AnalysisCandidate(decoded, candidate.layers + (Layer("Base64 decode"),)))
        except ValueError:
            pass

    # ROT13 is self-inverse and useful only for visibly textual data.
    rotated = rot13_bytes(data)
    if rotated != data and printable_ratio(rotated) >= 0.75:
        produced.append(AnalysisCandidate(rotated, candidate.layers + (Layer("ROT13"),)))

    swapped = swap_pair_bytes(data)
    if swapped != data:
        produced.append(AnalysisCandidate(swapped, candidate.layers + (Layer("adjacent-byte swap"),)))

    # Do not retain all 256 expansions at every search level; keep the best
    # frequency-ranked options to prevent combinatorial growth.
    for xor_result in brute_force_single_byte_xor(data, limit=xor_per_state):
        if xor_result.key != 0:
            produced.append(AnalysisCandidate(
                xor_result.plaintext,
                candidate.layers + (Layer("single-byte XOR", "key=0x%02X" % xor_result.key),),
                xor_result.score,
            ))
    return produced


def analyse_bytes(data, max_depth=MAX_SEARCH_DEPTH, beam_width=DEFAULT_BEAM_WIDTH):
    """Perform a bounded beam search over reversible deobfuscation layers.

    Returns a dictionary containing entropy/histogram facts, layer hints, XOR
    candidates, and the best final multi-layer candidates.  It never executes
    the recovered content.
    """
    data = require_bytes(data)
    if not isinstance(max_depth, int) or not 0 <= max_depth <= 10:
        raise ValueError("max_depth must be an integer from 0 through 10")
    if not isinstance(beam_width, int) or not 1 <= beam_width <= 32:
        raise ValueError("beam_width must be an integer from 1 through 32")

    original = AnalysisCandidate(data)
    frontier = [original]
    all_candidates = [original]
    seen = {data}
    for _ in range(max_depth):
        next_frontier = []
        for candidate in frontier:
            for next_candidate in likely_transforms(candidate):
                # A byte value can be produced via many reversible paths. Keep
                # only the first to make the report deterministic and bounded.
                if next_candidate.data not in seen:
                    seen.add(next_candidate.data)
                    next_frontier.append(next_candidate)
                    all_candidates.append(next_candidate)
        next_frontier.sort(key=lambda item: (-item.score, len(item.layers), item.path()))
        frontier = next_frontier[:beam_width]
        if not frontier:
            break

    all_candidates.sort(key=lambda item: (-item.score, len(item.layers), item.path()))
    return {
        "input_length": len(data),
        "input_entropy": shannon_entropy(data),
        "input_entropy_band": entropy_band(shannon_entropy(data)),
        "input_printable_ratio": printable_ratio(data),
        "input_preview": visible_text(data),
        "top_bytes": top_bytes(data),
        "layer_hints": layer_hints(data),
        "xor_candidates": [item.summary() for item in brute_force_single_byte_xor(data, limit=8)],
        "best_candidates": [item.summary() for item in all_candidates[:beam_width]],
        "states_considered": len(all_candidates),
    }


# ---------------------------------------------------------------------------
# Stack-string analysis
# ---------------------------------------------------------------------------

def analyse_stack(fragments, reverse_push_order=True, separator=b"", **search_options):
    """Reconstruct stack fragments then run the same safe multi-layer analysis."""
    # Materialise once: callers may pass a generator, which cannot be replayed
    # to count fragments after reconstruction.
    fragments = list(fragments)
    reconstructed = reconstruct_stack_string(fragments, reverse_push_order, separator)
    report = analyse_bytes(reconstructed, **search_options)
    report["stack_reconstruction"] = {
        "fragment_count": len(fragments),
        "reverse_push_order": reverse_push_order,
        "reconstructed_preview": visible_text(reconstructed),
    }
    return report


# ---------------------------------------------------------------------------
# Human-readable report rendering
# ---------------------------------------------------------------------------

def format_key_values(mapping, indent="  "):
    """Format a mapping as simple deterministic text lines."""
    lines = []
    for key in sorted(mapping):
        lines.append(indent + str(key) + ": " + str(mapping[key]))
    return lines


def format_candidate(candidate, number):
    """Render one candidate summary for terminal-safe copy/paste output."""
    lines = ["  [%d] %s" % (number, candidate["path"])]
    lines.append("      score=%s  entropy=%s  printable=%s" % (
        candidate["score"], candidate["entropy"], candidate["printable_ratio"]
    ))
    lines.append("      preview: " + candidate["preview"])
    return lines


def format_analysis(report):
    """Convert an analyse_bytes result into a detailed plain-text report."""
    lines = []
    lines.append("=" * 76)
    lines.append("SAFE MULTI-LAYER STRING DEOBFUSCATION REPORT")
    lines.append("=" * 76)
    lines.append("Input length: %d bytes" % report["input_length"])
    lines.append("Input entropy: %.3f bits/byte (%s)" % (
        report["input_entropy"], report["input_entropy_band"]
    ))
    lines.append("Input printable ratio: %.3f" % report["input_printable_ratio"])
    lines.append("Input preview: " + report["input_preview"])
    lines.append("Most common bytes: " + ", ".join(key + "=" + str(value) for key, value in report["top_bytes"]))
    lines.append("")
    lines.append("Layer hints:")
    lines.extend("  - " + hint for hint in report["layer_hints"])
    lines.append("")
    lines.append("Top single-byte XOR candidates:")
    for index, candidate in enumerate(report["xor_candidates"], 1):
        lines.append("  [%d] key=%s (%s), score=%s" % (
            index, candidate["key_hex"], candidate["key_decimal"], candidate["score"]
        ))
        lines.append("      preview: " + candidate["preview"])
    lines.append("")
    lines.append("Best multi-layer candidates (states considered: %d):" % report["states_considered"])
    for index, candidate in enumerate(report["best_candidates"], 1):
        lines.extend(format_candidate(candidate, index))
    lines.append("")
    lines.append("Interpretation note: scoring identifies likely readable data; it is not proof")
    lines.append("of intent, provenance, or maliciousness. Recovered content is never executed.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Harmless sample data and self-tests
# ---------------------------------------------------------------------------

def make_layered_sample(plaintext, xor_key=0x5A):
    """Build XOR(Base64(ROT13(plaintext))) for a repeatable harmless demo."""
    plaintext = require_bytes(plaintext, "plaintext")
    return xor_single_byte(base64.b64encode(rot13_bytes(plaintext)), xor_key)


def make_byte_swapped_sample(plaintext):
    """Build an adjacent-byte-swapped harmless sample (the transform is inverse)."""
    return swap_pair_bytes(require_bytes(plaintext, "plaintext"))


HARMLESS_SAMPLE_TEXT = (
    b"this is a harmless training configuration string; mode=analysis; status=ok"
)
HARMLESS_LAYERED_SAMPLE = make_layered_sample(HARMLESS_SAMPLE_TEXT)
HARMLESS_SWAPPED_SAMPLE = make_byte_swapped_sample(b"stack strings are reconstructed safely")
HARMLESS_STACK_DWORDS = (0x73756F69, 0x20736920, 0x6B636174, 0x7473202D)


def run_self_tests():
    """Test every core transform and a complete three-layer recovery path."""
    original = b"Hello, Safe Analysis 123!"
    assert xor_single_byte(xor_single_byte(original, 0xA7), 0xA7) == original
    assert rot13_bytes(rot13_bytes(original)) == original
    assert swap_pair_bytes(swap_pair_bytes(original)) == original
    encoded = base64.b64encode(original)
    assert looks_like_base64(encoded)
    assert decode_base64(encoded) == original
    assert not looks_like_base64(b"not-base64!!!")
    assert reconstruct_stack_string((b"world", b"hello ")) == b"hello world"
    assert unpack_little_endian_dwords((0x6C6C6568, 0x0000006F)) == b"ohell"
    assert shannon_entropy(b"AAAAAAAA") < shannon_entropy(bytes(range(64)))

    layered = make_layered_sample(b"this is a harmless layered english test string", 0x5A)
    report = analyse_bytes(layered, max_depth=4, beam_width=12)
    previews = [candidate["preview"] for candidate in report["best_candidates"]]
    assert any("harmless layered english test string" in preview for preview in previews)
    candidates = brute_force_single_byte_xor(xor_single_byte(b"this is readable", 0x22), limit=4)
    assert any(candidate.key == 0x22 for candidate in candidates)
    print("All safe deobfuscator self-tests passed.")


def run_demo():
    """Analyse several built-in harmless byte arrays and print complete reports."""
    samples = (
        ("Three-layer XOR -> Base64 -> ROT13", HARMLESS_LAYERED_SAMPLE),
        ("Adjacent-byte swap", HARMLESS_SWAPPED_SAMPLE),
        ("Stack dword reconstruction", unpack_little_endian_dwords(HARMLESS_STACK_DWORDS)),
    )
    for title, sample in samples:
        print("\n" + "#" * 76)
        print("SAMPLE: " + title)
        print("#" * 76)
        print(format_analysis(analyse_bytes(sample)))


if __name__ == "__main__":
    run_self_tests()
    run_demo()
