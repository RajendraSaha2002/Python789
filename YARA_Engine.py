import json
import re
from dataclasses import dataclass, field


@dataclass
class Pattern:
    identifier: str
    pattern_type: str
    value: bytes
    wide: bool = False
    nocase: bool = False


@dataclass
class Rule:
    name: str
    metadata: dict = field(default_factory=dict)
    patterns: list = field(default_factory=list)
    condition: str = "any of them"


class AhoCorasick:
    def __init__(self):
        self.goto = [{}]
        self.fail = [0]
        self.output = [[]]

    def add_pattern(self, pattern_bytes, pattern_info):
        state = 0

        for byte_value in pattern_bytes:
            if byte_value not in self.goto[state]:
                self.goto[state][byte_value] = len(self.goto)
                self.goto.append({})
                self.fail.append(0)
                self.output.append([])

            state = self.goto[state][byte_value]

        self.output[state].append(pattern_info)

    def build(self):
        queue = []

        for byte_value, next_state in self.goto[0].items():
            queue.append(next_state)
            self.fail[next_state] = 0

        queue_index = 0

        while queue_index < len(queue):
            state = queue[queue_index]
            queue_index += 1

            for byte_value, next_state in self.goto[state].items():
                queue.append(next_state)

                failure_state = self.fail[state]

                while (
                    failure_state != 0
                    and byte_value not in self.goto[failure_state]
                ):
                    failure_state = self.fail[failure_state]

                self.fail[next_state] = self.goto[
                    failure_state
                ].get(byte_value, 0)

                self.output[next_state].extend(
                    self.output[self.fail[next_state]]
                )

    def search(self, data):
        state = 0
        matches = []

        for position, byte_value in enumerate(data):
            while state != 0 and byte_value not in self.goto[state]:
                state = self.fail[state]

            state = self.goto[state].get(byte_value, 0)

            for pattern_info in self.output[state]:
                pattern_length = len(pattern_info["bytes"])

                matches.append(
                    {
                        "rule": pattern_info["rule"],
                        "identifier": pattern_info["identifier"],
                        "offset": position - pattern_length + 1,
                        "length": pattern_length,
                    }
                )

        return matches


class YaraInspiredScanner:
    def __init__(self):
        self.rules = []

    @staticmethod
    def parse_hex_pattern(value):
        cleaned = value.strip().replace(" ", "")

        if not cleaned:
            raise ValueError("Hex pattern cannot be empty.")

        if "??" in cleaned:
            raise ValueError(
                "Wildcard hex bytes are not supported in this basic scanner."
            )

        if len(cleaned) % 2 != 0:
            raise ValueError("Hex pattern must contain complete byte pairs.")

        try:
            return bytes.fromhex(cleaned)
        except ValueError as error:
            raise ValueError(f"Invalid hex pattern: {error}") from error

    @staticmethod
    def parse_string_pattern(value):
        try:
            decoded = bytes(value, "utf-8").decode("unicode_escape")
            return decoded.encode("utf-8")
        except UnicodeDecodeError:
            return value.encode("utf-8")

    @staticmethod
    def make_wide_pattern(value):
        return value.decode("utf-8", errors="replace").encode("utf-16le")

    def parse_rules(self, rule_text):
        self.rules = []

        rule_blocks = re.findall(
            r"rule\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{(.*?)\}",
            rule_text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if not rule_blocks:
            raise ValueError("No valid rule blocks were found.")

        for rule_name, body in rule_blocks:
            metadata = self.parse_metadata(body)
            patterns = self.parse_strings(body)
            condition = self.parse_condition(body)

            if not patterns:
                raise ValueError(
                    f"Rule '{rule_name}' contains no supported patterns."
                )

            self.rules.append(
                Rule(
                    name=rule_name,
                    metadata=metadata,
                    patterns=patterns,
                    condition=condition,
                )
            )

        return self.rules

    @staticmethod
    def extract_section(body, section_name):
        match = re.search(
            rf"{section_name}\s*:(.*?)(?=\n\s*(?:meta|strings|condition)\s*:|\Z)",
            body,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if match:
            return match.group(1)

        return ""

    def parse_metadata(self, body):
        metadata_text = self.extract_section(body, "meta")
        metadata = {}

        for line in metadata_text.splitlines():
            line = line.strip()

            if not line or line.startswith("//"):
                continue

            match = re.match(
                r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\"(.*?)\"",
                line,
            )

            if match:
                metadata[match.group(1)] = match.group(2)
                continue

            match = re.match(
                r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)",
                line,
            )

            if match:
                metadata[match.group(1)] = match.group(2).strip()

        return metadata

    def parse_strings(self, body):
        strings_text = self.extract_section(body, "strings")
        patterns = []

        for line in strings_text.splitlines():
            line = line.strip()

            if not line or line.startswith("//"):
                continue

            hex_match = re.match(
                r"\$([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{([^}]+)\}",
                line,
                flags=re.IGNORECASE,
            )

            if hex_match:
                identifier = "$" + hex_match.group(1)
                pattern_data = self.parse_hex_pattern(hex_match.group(2))

                patterns.append(
                    Pattern(
                        identifier=identifier,
                        pattern_type="hex",
                        value=pattern_data,
                    )
                )
                continue

            string_match = re.match(
                r'\$([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"(.*?)"(.*)$',
                line,
                flags=re.IGNORECASE,
            )

            if string_match:
                identifier = "$" + string_match.group(1)
                string_value = string_match.group(2)
                modifiers = string_match.group(3).lower()

                patterns.append(
                    Pattern(
                        identifier=identifier,
                        pattern_type="string",
                        value=self.parse_string_pattern(string_value),
                        wide="wide" in modifiers,
                        nocase="nocase" in modifiers,
                    )
                )

        return patterns

    def parse_condition(self, body):
        condition_text = self.extract_section(body, "condition")
        condition = " ".join(condition_text.split())

        if not condition:
            return "any of them"

        return condition

    def build_automaton(self):
        automaton = AhoCorasick()

        for rule in self.rules:
            for pattern in rule.patterns:
                values_to_add = []

                if pattern.nocase:
                    values_to_add.append(pattern.value.lower())
                    values_to_add.append(pattern.value.upper())
                else:
                    values_to_add.append(pattern.value)

                if pattern.wide:
                    wide_values = []

                    for value in values_to_add:
                        wide_values.append(self.make_wide_pattern(value))

                    values_to_add = wide_values

                for pattern_bytes in values_to_add:
                    automaton.add_pattern(
                        pattern_bytes,
                        {
                            "rule": rule.name,
                            "identifier": pattern.identifier,
                            "bytes": pattern_bytes,
                        },
                    )

        automaton.build()
        return automaton

    @staticmethod
    def find_nocase_matches(data, pattern):
        data_lower = data.lower()
        pattern_lower = pattern.value.lower()
        matches = []
        offset = 0

        while True:
            position = data_lower.find(pattern_lower, offset)

            if position == -1:
                break

            matches.append(position)
            offset = position + 1

        return matches

    @staticmethod
    def find_exact_matches(data, pattern_bytes):
        matches = []
        offset = 0

        while True:
            position = data.find(pattern_bytes, offset)

            if position == -1:
                break

            matches.append(position)
            offset = position + 1

        return matches

    def find_pattern_matches(self, data, pattern):
        if pattern.wide:
            target = self.make_wide_pattern(pattern.value)

            if pattern.nocase:
                return self.find_nocase_matches(data, Pattern(
                    identifier=pattern.identifier,
                    pattern_type=pattern.pattern_type,
                    value=target,
                ))

            return self.find_exact_matches(data, target)

        if pattern.nocase:
            return self.find_nocase_matches(data, pattern)

        return self.find_exact_matches(data, pattern.value)

    def evaluate_condition(self, condition, pattern_matches, all_identifiers):
        normalized = condition.lower().strip()

        if normalized == "any of them":
            return any(pattern_matches.get(identifier, []) for identifier in all_identifiers)

        if normalized == "all of them":
            return all(pattern_matches.get(identifier, []) for identifier in all_identifiers)

        if normalized == "none of them":
            return not any(
                pattern_matches.get(identifier, [])
                for identifier in all_identifiers
            )

        expression = condition

        def replace_count(match):
            identifier = "$" + match.group(1)
            return str(len(pattern_matches.get(identifier, [])))

        expression = re.sub(
            r"#([A-Za-z_][A-Za-z0-9_]*)",
            replace_count,
            expression,
        )

        def replace_identifier(match):
            identifier = "$" + match.group(1)
            return str(bool(pattern_matches.get(identifier, [])))

        expression = re.sub(
            r"\$([A-Za-z_][A-Za-z0-9_]*)",
            replace_identifier,
            expression,
        )

        expression = re.sub(
            r"\bAND\b",
            "and",
            expression,
            flags=re.IGNORECASE,
        )
        expression = re.sub(
            r"\bOR\b",
            "or",
            expression,
            flags=re.IGNORECASE,
        )
        expression = re.sub(
            r"\bNOT\b",
            "not",
            expression,
            flags=re.IGNORECASE,
        )

        if not re.fullmatch(
            r"[\s0-9TrueFalsandornot<>=!().]+",
            expression,
        ):
            return False

        try:
            return bool(eval(expression, {"__builtins__": {}}, {}))
        except (SyntaxError, NameError, TypeError):
            return False

    def scan_data(self, data, source_name="memory"):
        if not self.rules:
            raise RuntimeError("Load rules before scanning data.")

        findings = []

        for rule in self.rules:
            pattern_matches = {}

            for pattern in rule.patterns:
                pattern_matches[pattern.identifier] = self.find_pattern_matches(
                    data,
                    pattern,
                )

            identifiers = [pattern.identifier for pattern in rule.patterns]

            if self.evaluate_condition(
                rule.condition,
                pattern_matches,
                identifiers,
            ):
                matched_patterns = []

                for identifier, offsets in pattern_matches.items():
                    if offsets:
                        matched_patterns.append(
                            {
                                "identifier": identifier,
                                "count": len(offsets),
                                "offsets": offsets[:20],
                            }
                        )

                findings.append(
                    {
                        "rule": rule.name,
                        "source": source_name,
                        "metadata": rule.metadata,
                        "condition": rule.condition,
                        "matched_patterns": matched_patterns,
                    }
                )

        return findings


def create_sarif_report(findings):
    results = []

    for finding in findings:
        message = finding["metadata"].get(
            "description",
            f"YARA-inspired rule matched: {finding['rule']}",
        )

        results.append(
            {
                "ruleId": finding["rule"],
                "level": "warning",
                "message": {
                    "text": message,
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": finding["source"],
                            }
                        }
                    }
                ],
                "properties": {
                    "metadata": finding["metadata"],
                    "matchedPatterns": finding["matched_patterns"],
                },
            }
        )

    return {
        "$schema": (
            "https://json.schemastore.org/sarif-2.1.0.json"
        ),
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "YARA-Inspired Python Scanner",
                        "version": "1.0",
                    }
                },
                "results": results,
            }
        ],
    }


def print_findings(findings):
    print("\n" + "=" * 70)
    print("SCAN RESULTS")
    print("=" * 70)

    if not findings:
        print("No rules matched.")
        return

    for finding in findings:
        print(f"\nRule matched: {finding['rule']}")
        print(f"Source: {finding['source']}")

        if finding["metadata"]:
            print("Metadata:")

            for key, value in finding["metadata"].items():
                print(f"  {key}: {value}")

        print("Matched patterns:")

        for pattern in finding["matched_patterns"]:
            offsets = ", ".join(
                f"0x{offset:X}"
                for offset in pattern["offsets"]
            )

            print(
                f"  {pattern['identifier']} | "
                f"count: {pattern['count']} | "
                f"offsets: {offsets}"
            )


SAMPLE_RULES = r'''
rule Suspicious_Download_Command
{
    meta:
        author = "Security Analyst"
        description = "Detects suspicious download command text"
        severity = "medium"

    strings:
        $download = "download_payload" nocase
        $command = "powershell" nocase
        $hex_marker = { 4D 5A }

    condition:
        $download and $command
}

rule Wide_Executable_Path
{
    meta:
        author = "Security Analyst"
        description = "Detects a UTF-16LE executable path"
        severity = "low"

    strings:
        $path = "C:\\Temp\\example.exe" wide

    condition:
        $path
}

rule Repeated_Marker
{
    meta:
        description = "Detects repeated marker values"
        severity = "low"

    strings:
        $marker = "DEMO_MARKER"

    condition:
        #marker >= 2
}
'''

SIMULATED_SAMPLE = (
    b"MZ"
    b"\x90\x00\x03\x00"
    b"This is simulated test data. "
    b"powershell -command download_payload "
    b"C:\x00\\\x00T\x00e\x00m\x00p\x00\\\x00"
    b"e\x00x\x00a\x00m\x00p\x00l\x00e\x00.\x00e\x00x\x00e\x00"
    b" DEMO_MARKER "
    b" benign text "
    b" DEMO_MARKER "
)


def main():
    print("YARA-Inspired Rule Engine with Aho-Corasick")
    print("=" * 70)
    print("1 - Scan included simulated byte array")
    print("2 - Scan a file")
    print("3 - Enter custom rules and scan simulated byte array")

    choice = input("\nChoose an option (1, 2, or 3): ").strip()

    rule_text = SAMPLE_RULES
    source_name = "simulated_malware_bytes"
    scan_data = SIMULATED_SAMPLE

    if choice == "2":
        file_path = input("Enter full file path: ").strip().strip('"')

        if not file_path:
            print("Error: no file path entered.")
            return

        try:
            with open(file_path, "rb") as file_handle:
                scan_data = file_handle.read()

            source_name = file_path

        except FileNotFoundError:
            print("Error: file not found.")
            return

        except PermissionError:
            print("Error: permission denied.")
            return

        except OSError as error:
            print(f"File error: {error}")
            return

    elif choice == "3":
        print("\nEnter rules. Type END on its own line when finished.")
        print("Example condition: $name and $other")
        print("Example condition: any of them")
        print("Example condition: #marker >= 2\n")

        lines = []

        while True:
            line = input()

            if line.strip() == "END":
                break

            lines.append(line)

        rule_text = "\n".join(lines)

        if not rule_text.strip():
            print("Error: no rule text entered.")
            return

    elif choice != "1":
        print("Error: choose 1, 2, or 3.")
        return

    try:
        scanner = YaraInspiredScanner()
        scanner.parse_rules(rule_text)

        findings = scanner.scan_data(
            scan_data,
            source_name=source_name,
        )

        print_findings(findings)

        sarif = create_sarif_report(findings)
        output_path = "scan_findings.sarif.json"

        with open(output_path, "w", encoding="utf-8") as file_handle:
            json.dump(sarif, file_handle, indent=2)

        print(f"\nSARIF report saved as: {output_path}")

    except ValueError as error:
        print(f"Rule parsing error: {error}")

    except RuntimeError as error:
        print(f"Scanner error: {error}")

    except OSError as error:
        print(f"Report writing error: {error}")

    except Exception as error:
        print(f"Unexpected error: {error}")


if __name__ == "__main__":
    main()