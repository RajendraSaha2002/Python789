import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Protocol limits and regular expressions
# ---------------------------------------------------------------------------

MAX_HEADER_BYTES = 64 * 1024
MAX_HEADERS = 200
MAX_CHUNK_LINE = 4096
MAX_CHUNKS = 10_000
MAX_CONTENT_LENGTH = 128 * 1024 * 1024

TOKEN_RE = re.compile(rb"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
REQUEST_LINE_RE = re.compile(
    rb"^(?P<method>[!#$%&'*+\-.^_`|~0-9A-Za-z]+) (?P<target>\S+) HTTP/(?P<major>[0-9])\.(?P<minor>[0-9])$"
)
CHUNK_SIZE_RE = re.compile(rb"^(?P<size>[0-9A-Fa-f]+)(?:;(?P<extensions>.*))?$")
DECIMAL_RE = re.compile(rb"^[0-9]+$")


# ---------------------------------------------------------------------------
# Errors, records, and parser policy definitions
# ---------------------------------------------------------------------------

class HTTPParseError(ValueError):
    """A structured parser failure that includes the byte location involved."""

    def __init__(self, message, offset=None):
        self.message = message
        self.offset = offset
        suffix = "" if offset is None else " at byte offset " + str(offset)
        super().__init__(message + suffix)


@dataclass(frozen=True)
class Header:
    """One parsed HTTP header field, retaining original and normalized names."""

    original_name: bytes
    normalized_name: bytes
    value: bytes
    line_offset: int

    def display(self):
        return self.original_name.decode("latin-1", "replace") + ": " + self.value.decode("latin-1", "replace")


@dataclass(frozen=True)
class HTTPRequestHead:
    """Request-line and headers occupying bytes [start, header_end)."""

    start: int
    header_end: int
    method: bytes
    target: bytes
    version: bytes
    headers: tuple

    def values(self, name):
        normalized = name.lower() if isinstance(name, bytes) else name.encode("ascii").lower()
        return [header.value for header in self.headers if header.normalized_name == normalized]

    def has(self, name):
        return bool(self.values(name))

    def display_request_line(self):
        return b" ".join((self.method, self.target, self.version)).decode("latin-1", "replace")


@dataclass(frozen=True)
class FramingDecision:
    """How one parser believes the request body is framed."""

    kind: str
    content_length: int = 0
    transfer_codings: tuple = ()
    reason: str = ""
    anomalies: tuple = ()


@dataclass(frozen=True)
class ParsedRequest:
    """A fully bounded request parse under one concrete policy."""

    head: HTTPRequestHead
    decision: FramingDecision
    body_start: int
    body_end: int
    request_end: int
    chunk_boundaries: tuple = ()
    trailers: tuple = ()

    @property
    def consumed(self):
        return self.request_end - self.head.start


@dataclass(frozen=True)
class ParserPolicy:
    """A deliberately explicit model of a proxy/server framing behavior.

    Policies model differences for diagnostic comparison; they are not a guide
    for deploying permissive HTTP parsers.  Production servers should use
    ``STRICT_POLICY`` and reject all ambiguous framing.
    """

    name: str
    precedence: str = "strict"       # strict, content-length, transfer-encoding
    duplicate_content_length: str = "reject"  # reject, first, last, identical
    duplicate_transfer_encoding: str = "reject"  # reject, combine, first, last
    trim_header_name: bool = False
    accept_obs_fold: bool = False
    accept_transfer_encoding: bool = True
    recognize_chunked_case_insensitively: bool = True


STRICT_POLICY = ParserPolicy("Strict RFC-oriented parser")
FRONT_CL_POLICY = ParserPolicy(
    "Simulated front end (Content-Length precedence)",
    precedence="content-length",
    duplicate_content_length="first",
    duplicate_transfer_encoding="first",
)
BACK_TE_POLICY = ParserPolicy(
    "Simulated back end (Transfer-Encoding precedence)",
    precedence="transfer-encoding",
    duplicate_content_length="last",
    duplicate_transfer_encoding="last",
)
FRONT_TE_POLICY = ParserPolicy(
    "Simulated front end (Transfer-Encoding precedence)",
    precedence="transfer-encoding",
    duplicate_content_length="first",
    duplicate_transfer_encoding="first",
)
BACK_CL_POLICY = ParserPolicy(
    "Simulated back end (Content-Length precedence)",
    precedence="content-length",
    duplicate_content_length="last",
    duplicate_transfer_encoding="last",
)


# ---------------------------------------------------------------------------
# Small safe byte helpers
# ---------------------------------------------------------------------------

def require_bytes(data, label="raw request"):
    """Return immutable bytes after validating the in-memory analysis input."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError(label + " must be bytes-like")
    return bytes(data)


def printable_preview(data, limit=120):
    """Show a compact escaped byte preview for reports without decoding as code."""
    data = require_bytes(data)
    pieces = []
    for byte in data[:limit]:
        if byte == 13:
            pieces.append("\\r")
        elif byte == 10:
            pieces.append("\\n")
        elif byte == 9:
            pieces.append("\\t")
        elif 32 <= byte <= 126:
            pieces.append(chr(byte))
        else:
            pieces.append("\\x%02x" % byte)
    return "".join(pieces) + ("..." if len(data) > limit else "")


def header_name_for_policy(raw_name, policy):
    """Normalize a header name exactly as the selected simulated parser does."""
    if policy.trim_header_name:
        raw_name = raw_name.strip(b" \t")
    if not TOKEN_RE.match(raw_name):
        raise HTTPParseError("invalid header field name: " + printable_preview(raw_name, 40))
    return raw_name.lower()


def split_header_values(values):
    """Split comma-separated header values while preserving empty entries."""
    pieces = []
    for value in values:
        pieces.extend(piece.strip(b" \t") for piece in value.split(b","))
    return pieces


# ---------------------------------------------------------------------------
# HTTP/1.1 head parsing
# ---------------------------------------------------------------------------

def find_header_end(data, start):
    """Locate CRLFCRLF and apply a finite header-size limit."""
    limit_end = min(len(data), start + MAX_HEADER_BYTES + 4)
    end = data.find(b"\r\n\r\n", start, limit_end)
    if end < 0:
        if len(data) - start > MAX_HEADER_BYTES:
            raise HTTPParseError("header section exceeds safe size limit", start)
        raise HTTPParseError("incomplete header section: missing CRLFCRLF", start)
    return end + 4


def parse_request_line(line, offset):
    """Parse METHOD SP target SP HTTP/version without accepting loose syntax."""
    match = REQUEST_LINE_RE.match(line)
    if not match:
        raise HTTPParseError("invalid HTTP/1.x request line", offset)
    if match.group("major") != b"1":
        raise HTTPParseError("only HTTP/1.x request lines are supported", offset)
    return (
        match.group("method"),
        match.group("target"),
        b"HTTP/" + match.group("major") + b"." + match.group("minor"),
    )


def parse_headers(header_block, base_offset, policy):
    """Parse CRLF-delimited headers, optionally modeling legacy obs-fold input."""
    lines = header_block.split(b"\r\n")
    if not lines or not lines[0]:
        raise HTTPParseError("missing HTTP request line", base_offset)
    method, target, version = parse_request_line(lines[0], base_offset)
    headers = []
    line_offset = base_offset + len(lines[0]) + 2
    previous = None
    for line in lines[1:]:
        if line == b"":
            line_offset += 2
            continue
        if line.startswith((b" ", b"\t")):
            if not policy.accept_obs_fold or previous is None:
                raise HTTPParseError("obsolete folded header line rejected", line_offset)
            merged = Header(previous.original_name, previous.normalized_name, previous.value + b" " + line.strip(), previous.line_offset)
            headers[-1] = merged
            previous = merged
            line_offset += len(line) + 2
            continue
        if b":" not in line:
            raise HTTPParseError("header line lacks colon", line_offset)
        raw_name, raw_value = line.split(b":", 1)
        normalized_name = header_name_for_policy(raw_name, policy)
        header = Header(raw_name, normalized_name, raw_value.strip(b" \t"), line_offset)
        headers.append(header)
        previous = header
        if len(headers) > MAX_HEADERS:
            raise HTTPParseError("too many headers", line_offset)
        line_offset += len(line) + 2
    return method, target, version, tuple(headers)


def parse_head(data, start, policy):
    """Parse only the request line and headers at a stream offset."""
    data = require_bytes(data)
    if start < 0 or start >= len(data):
        raise HTTPParseError("stream offset is outside supplied data", start)
    header_end = find_header_end(data, start)
    block = data[start:header_end - 4]
    method, target, version, headers = parse_headers(block, start, policy)
    return HTTPRequestHead(start, header_end, method, target, version, headers)


# ---------------------------------------------------------------------------
# Framing decision logic
# ---------------------------------------------------------------------------

def parse_content_length_values(head, policy):
    """Parse one or more Content-Length fields under a concrete duplicate rule."""
    raw_values = head.values(b"content-length")
    if not raw_values:
        return None, ()
    values = split_header_values(raw_values)
    if not values or any(not value or not DECIMAL_RE.match(value) for value in values):
        raise HTTPParseError("invalid Content-Length syntax", head.start)
    numbers = tuple(int(value) for value in values)
    if any(number > MAX_CONTENT_LENGTH for number in numbers):
        raise HTTPParseError("Content-Length exceeds safe analysis limit", head.start)
    anomalies = ()
    if len(numbers) > 1:
        anomalies = ("multiple Content-Length values: " + ", ".join(str(number) for number in numbers),)
        if policy.duplicate_content_length == "reject":
            raise HTTPParseError("multiple Content-Length values rejected", head.start)
        if policy.duplicate_content_length == "identical" and len(set(numbers)) != 1:
            raise HTTPParseError("conflicting Content-Length values rejected", head.start)
    if policy.duplicate_content_length == "last":
        return numbers[-1], anomalies
    return numbers[0], anomalies


def parse_transfer_codings(head, policy):
    """Parse Transfer-Encoding fields according to duplicate-header semantics."""
    raw_values = head.values(b"transfer-encoding")
    if not raw_values:
        return (), ()
    if not policy.accept_transfer_encoding:
        return (), ("Transfer-Encoding ignored by this simulated policy",)
    anomalies = []
    selected = raw_values
    if len(raw_values) > 1:
        anomalies.append("multiple Transfer-Encoding fields")
        if policy.duplicate_transfer_encoding == "reject":
            raise HTTPParseError("multiple Transfer-Encoding fields rejected", head.start)
        if policy.duplicate_transfer_encoding == "first":
            selected = raw_values[:1]
        elif policy.duplicate_transfer_encoding == "last":
            selected = raw_values[-1:]
    codings = tuple(piece.lower() for piece in split_header_values(selected))
    if not codings or any(not coding or not TOKEN_RE.match(coding) for coding in codings):
        raise HTTPParseError("invalid Transfer-Encoding syntax", head.start)
    if b"chunked" in codings and codings[-1] != b"chunked":
        raise HTTPParseError("chunked Transfer-Encoding is not final", head.start)
    return codings, tuple(anomalies)


def decide_framing(head, policy):
    """Apply framing precedence to the parsed headers and report ambiguities."""
    content_length, cl_anomalies = parse_content_length_values(head, policy)
    transfer_codings, te_anomalies = parse_transfer_codings(head, policy)
    has_chunked = b"chunked" in transfer_codings
    anomalies = cl_anomalies + te_anomalies
    has_te = bool(transfer_codings)

    if has_te and content_length is not None:
        anomalies += ("both Transfer-Encoding and Content-Length are present",)
        if policy.precedence == "strict":
            raise HTTPParseError("ambiguous TE plus Content-Length rejected", head.start)
    if has_te and not has_chunked:
        # This simulator does not attempt non-chunked transfer coding chains.
        if policy.precedence == "strict":
            raise HTTPParseError("Transfer-Encoding without final chunked rejected", head.start)
        anomalies += ("Transfer-Encoding exists but no usable final chunked coding",)

    if policy.precedence == "transfer-encoding" and has_chunked:
        return FramingDecision("chunked", transfer_codings=transfer_codings,
                               reason="policy gives final chunked Transfer-Encoding precedence", anomalies=anomalies)
    if policy.precedence == "content-length" and content_length is not None:
        return FramingDecision("content-length", content_length=content_length, transfer_codings=transfer_codings,
                               reason="policy gives Content-Length precedence", anomalies=anomalies)
    if policy.precedence == "strict":
        if has_chunked:
            return FramingDecision("chunked", transfer_codings=transfer_codings,
                                   reason="unambiguous final chunked Transfer-Encoding", anomalies=anomalies)
        if content_length is not None:
            return FramingDecision("content-length", content_length=content_length,
                                   reason="single accepted Content-Length", anomalies=anomalies)
    if content_length is not None:
        return FramingDecision("content-length", content_length=content_length, transfer_codings=transfer_codings,
                               reason="fallback Content-Length framing", anomalies=anomalies)
    return FramingDecision("none", reason="no request body framing header", anomalies=anomalies)


# ---------------------------------------------------------------------------
# Chunked-body parsing
# ---------------------------------------------------------------------------

def read_crlf_line(data, offset, maximum=MAX_CHUNK_LINE):
    """Return (line_without_CRLF, next_offset) with finite line limits."""
    end = data.find(b"\r\n", offset, min(len(data), offset + maximum + 2))
    if end < 0:
        raise HTTPParseError("missing CRLF or oversized chunk line", offset)
    return data[offset:end], end + 2


def parse_trailer_section(data, offset):
    """Parse zero or more trailer fields after the zero-size chunk."""
    trailers = []
    while True:
        line, offset = read_crlf_line(data, offset)
        if line == b"":
            return tuple(trailers), offset
        if b":" not in line:
            raise HTTPParseError("trailer line lacks colon", offset - len(line) - 2)
        raw_name, raw_value = line.split(b":", 1)
        if not TOKEN_RE.match(raw_name):
            raise HTTPParseError("invalid trailer field name", offset - len(line) - 2)
        trailers.append(Header(raw_name, raw_name.lower(), raw_value.strip(b" \t"), offset - len(line) - 2))
        if len(trailers) > MAX_HEADERS:
            raise HTTPParseError("too many trailer headers", offset)


def parse_chunked_body(data, body_start):
    """Parse chunk boundaries through trailers and return end offset and details."""
    offset = body_start
    chunks = []
    for _ in range(MAX_CHUNKS):
        size_line_start = offset
        size_line, offset = read_crlf_line(data, offset)
        match = CHUNK_SIZE_RE.match(size_line)
        if not match:
            raise HTTPParseError("invalid chunk-size line", size_line_start)
        size = int(match.group("size"), 16)
        if size > MAX_CONTENT_LENGTH:
            raise HTTPParseError("chunk size exceeds safe analysis limit", size_line_start)
        chunk_start = offset
        # The last-chunk is `0 CRLF trailer-section`; unlike a nonzero chunk,
        # it has no chunk-data CRLF before the trailer section begins.
        if size == 0:
            chunks.append((size_line_start, chunk_start, chunk_start, size))
            trailers, request_end = parse_trailer_section(data, offset)
            return request_end, tuple(chunks), trailers
        chunk_end = chunk_start + size
        if chunk_end + 2 > len(data):
            raise HTTPParseError("incomplete chunk data", chunk_start)
        if data[chunk_end:chunk_end + 2] != b"\r\n":
            raise HTTPParseError("chunk data is not terminated by CRLF", chunk_end)
        chunks.append((size_line_start, chunk_start, chunk_end, size))
        offset = chunk_end + 2
    raise HTTPParseError("too many chunks", body_start)


# ---------------------------------------------------------------------------
# Request and stream parsing
# ---------------------------------------------------------------------------

def parse_one_request(data, start, policy):
    """Parse one request at start under policy and calculate its exact endpoint."""
    data = require_bytes(data)
    head = parse_head(data, start, policy)
    decision = decide_framing(head, policy)
    body_start = head.header_end
    if decision.kind == "none":
        return ParsedRequest(head, decision, body_start, body_start, body_start)
    if decision.kind == "content-length":
        body_end = body_start + decision.content_length
        if body_end > len(data):
            raise HTTPParseError("incomplete Content-Length body", body_start)
        return ParsedRequest(head, decision, body_start, body_end, body_end)
    if decision.kind == "chunked":
        request_end, chunks, trailers = parse_chunked_body(data, body_start)
        return ParsedRequest(head, decision, body_start, request_end, request_end, chunks, trailers)
    raise HTTPParseError("internal unknown framing decision", body_start)


def parse_request_stream(data, policy, max_requests=8):
    """Parse sequential requests until input ends or a parser error is reached."""
    data = require_bytes(data)
    requests = []
    offset = 0
    error = None
    while offset < len(data) and len(requests) < max_requests:
        try:
            parsed = parse_one_request(data, offset, policy)
            requests.append(parsed)
            if parsed.request_end <= offset:
                raise HTTPParseError("parser made no forward progress", offset)
            offset = parsed.request_end
        except HTTPParseError as caught:
            error = caught
            break
    if len(requests) == max_requests and offset < len(data):
        error = HTTPParseError("stream parsing stopped at maximum request count", offset)
    return requests, offset, error


def request_summary(request):
    """Return a serializable summary of one parser's view of a request."""
    return {
        "request_line": request.head.display_request_line(),
        "start": request.head.start,
        "headers_end": request.head.header_end,
        "body_start": request.body_start,
        "body_end": request.body_end,
        "request_end": request.request_end,
        "consumed": request.consumed,
        "framing": request.decision.kind,
        "content_length": request.decision.content_length,
        "transfer_codings": list(request.decision.transfer_codings),
        "reason": request.decision.reason,
        "anomalies": list(request.decision.anomalies),
        "chunk_count": len(request.chunk_boundaries),
    }


# ---------------------------------------------------------------------------
# Front-end/back-end disagreement analysis
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BoundaryComparison:
    """A side-by-side result for two parser policies on one byte stream."""

    front_policy: ParserPolicy
    back_policy: ParserPolicy
    front_requests: tuple
    back_requests: tuple
    front_offset: int
    back_offset: int
    front_error: object
    back_error: object
    classification: str
    risk: str
    findings: tuple

    @property
    def disagreement(self):
        if self.front_error or self.back_error:
            return self.front_error != self.back_error or self.front_offset != self.back_offset
        return self.front_offset != self.back_offset or len(self.front_requests) != len(self.back_requests)


def classify_disagreement(front_requests, back_requests, front_error, back_error):
    """Classify a framing mismatch using first-request headers and decisions."""
    if not front_requests and not back_requests:
        return "parse failure (no complete request)"
    head = (front_requests or back_requests)[0].head
    has_cl = head.has(b"content-length")
    has_te = head.has(b"transfer-encoding")
    cl_values = head.values(b"content-length")
    te_values = head.values(b"transfer-encoding")
    if has_cl and len(split_header_values(cl_values)) > 1 and len(set(split_header_values(cl_values))) > 1:
        return "CL.CL"
    if has_te and len(te_values) > 1:
        return "TE.TE"
    if front_requests and back_requests:
        front_kind = front_requests[0].decision.kind
        back_kind = back_requests[0].decision.kind
        if front_kind == "content-length" and back_kind == "chunked":
            return "CL.TE"
        if front_kind == "chunked" and back_kind == "content-length":
            return "TE.CL"
        if (front_requests[0].request_end == back_requests[0].request_end and
                len(front_requests) == len(back_requests) and
                front_error is None and back_error is None):
            return "no ambiguity detected"
    if has_cl and has_te:
        return "TE/CL ambiguity"
    if front_error or back_error:
        return "parser acceptance mismatch"
    return "request boundary mismatch"


def risk_for_classification(classification, disagreement):
    """Use careful language: parser mismatch is a risk, not attack confirmation."""
    if not disagreement:
        return "No boundary disagreement under the selected simulated policies."
    if classification in ("CL.TE", "TE.CL", "TE.TE", "CL.CL"):
        return "High: selected policies disagree on HTTP request framing; reject this request at the edge."
    return "Medium: parser acceptance or boundary behavior differs; investigate and normalize/reject."


def compare_parsers(data, front_policy, back_policy):
    """Compare two offline policy parses and create an actionable diagnostic record."""
    data = require_bytes(data)
    front_requests, front_offset, front_error = parse_request_stream(data, front_policy)
    back_requests, back_offset, back_error = parse_request_stream(data, back_policy)
    classification = classify_disagreement(front_requests, back_requests, front_error, back_error)
    provisional = BoundaryComparison(
        front_policy, back_policy, tuple(front_requests), tuple(back_requests),
        front_offset, back_offset, front_error, back_error, classification, "", (),
    )
    findings = build_findings(data, provisional)
    risk = risk_for_classification(classification, provisional.disagreement)
    return BoundaryComparison(
        front_policy, back_policy, tuple(front_requests), tuple(back_requests),
        front_offset, back_offset, front_error, back_error, classification, risk, tuple(findings),
    )


def build_findings(data, comparison):
    """Describe exact byte-boundary consequences without sending any traffic."""
    findings = []
    if comparison.front_requests:
        first = comparison.front_requests[0]
        findings.extend(first.decision.anomalies)
        findings.append("Front end first request ends at byte %d (%s framing)." % (
            first.request_end, first.decision.kind
        ))
    if comparison.back_requests:
        first = comparison.back_requests[0]
        findings.extend(first.decision.anomalies)
        findings.append("Back end first request ends at byte %d (%s framing)." % (
            first.request_end, first.decision.kind
        ))
    if comparison.front_requests and comparison.back_requests:
        front_end = comparison.front_requests[0].request_end
        back_end = comparison.back_requests[0].request_end
        if front_end != back_end:
            low, high = sorted((front_end, back_end))
            findings.append("Disputed byte range [%d, %d): %s" % (
                low, high, printable_preview(data[low:high], 100)
            ))
    if comparison.front_error:
        findings.append("Front end parser error: " + str(comparison.front_error))
    if comparison.back_error:
        findings.append("Back end parser error: " + str(comparison.back_error))
    if not findings:
        findings.append("No framing anomaly was recorded by the selected policies.")
    return findings


def strict_validation(data):
    """Validate a single raw request using the secure, reject-on-ambiguity policy."""
    try:
        parsed = parse_one_request(data, 0, STRICT_POLICY)
        if parsed.request_end != len(data):
            return False, "strict parser accepted one request but trailing bytes remain at offset %d" % parsed.request_end
        return True, "strict parser accepted one unambiguous request"
    except HTTPParseError as error:
        return False, "strict parser rejected input: " + str(error)


# ---------------------------------------------------------------------------
# Text report rendering
# ---------------------------------------------------------------------------

def display_bytes(value):
    """Render arbitrary bytes/objects for concise report fields."""
    if isinstance(value, bytes):
        return value.decode("latin-1", "replace")
    return str(value)


def format_request_side(title, policy, requests, offset, error):
    """Render one parser side of a comparison in a stable human-readable form."""
    lines = [title + ": " + policy.name]
    lines.append("  Parsed requests: %d; stream offset: %d" % (len(requests), offset))
    for index, request in enumerate(requests, 1):
        summary = request_summary(request)
        lines.append("  Request %d: %s" % (index, summary["request_line"]))
        lines.append("    framing=%s, body=[%d,%d), request_end=%d" % (
            summary["framing"], summary["body_start"], summary["body_end"], summary["request_end"]
        ))
        if summary["transfer_codings"]:
            lines.append("    transfer codings: " + ", ".join(display_bytes(item) for item in summary["transfer_codings"]))
        if summary["anomalies"]:
            for anomaly in summary["anomalies"]:
                lines.append("    anomaly: " + anomaly)
    if error:
        lines.append("  Parser error: " + str(error))
    return lines


def format_comparison(data, comparison):
    """Create a full plain-text detector report for terminal or log output."""
    data = require_bytes(data)
    strict_ok, strict_message = strict_validation(data)
    lines = []
    lines.append("=" * 78)
    lines.append("OFFLINE HTTP/1.1 REQUEST-SMUGGLING DETECTOR")
    lines.append("=" * 78)
    lines.append("Input bytes: %d" % len(data))
    lines.append("Input preview: " + printable_preview(data, 220))
    lines.append("Classification: " + comparison.classification)
    lines.append("Risk: " + comparison.risk)
    lines.append("Strict validation: " + strict_message)
    lines.append("")
    lines.extend(format_request_side("FRONT-END VIEW", comparison.front_policy, comparison.front_requests,
                                     comparison.front_offset, comparison.front_error))
    lines.append("")
    lines.extend(format_request_side("BACK-END VIEW", comparison.back_policy, comparison.back_requests,
                                     comparison.back_offset, comparison.back_error))
    lines.append("")
    lines.append("Findings:")
    lines.extend("  - " + finding for finding in comparison.findings)
    lines.append("")
    lines.append("Defensive remediation:")
    lines.append("  - Reject requests containing both Transfer-Encoding and Content-Length.")
    lines.append("  - Reject conflicting or duplicate Content-Length and Transfer-Encoding fields.")
    lines.append("  - Normalize and validate HTTP/1.1 framing consistently at every hop.")
    lines.append("  - Disable HTTP/1.1 connection reuse on ambiguous/invalid requests.")
    lines.append("  - Use a single hardened proxy/parser implementation where possible.")
    lines.append("  - Treat this offline result as a configuration test, not proof of exploitation.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Safe inert test vectors
# ---------------------------------------------------------------------------

def request_head(content_length=None, transfer_encoding=None, extra_headers=()):
    """Construct a harmless request head for deterministic parser test vectors."""
    lines = [b"POST /training HTTP/1.1", b"Host: example.test"]
    if content_length is not None:
        if isinstance(content_length, (tuple, list)):
            lines.extend(b"Content-Length: " + str(item).encode("ascii") for item in content_length)
        else:
            lines.append(b"Content-Length: " + str(content_length).encode("ascii"))
    if transfer_encoding is not None:
        if isinstance(transfer_encoding, (tuple, list)):
            lines.extend(b"Transfer-Encoding: " + item for item in transfer_encoding)
        else:
            lines.append(b"Transfer-Encoding: " + transfer_encoding)
    lines.extend(extra_headers)
    return b"\r\n".join(lines) + b"\r\n\r\n"


SAFE_FOLLOWUP = b"GET /health HTTP/1.1\r\nHost: example.test\r\n\r\n"

# The following are inert parser fixtures.  They are not sent anywhere.
CL_TE_VECTOR = request_head(4, b"chunked") + b"0\r\n\r\n" + SAFE_FOLLOWUP
TE_CL_VECTOR = request_head(48, b"chunked") + b"0\r\n\r\n" + SAFE_FOLLOWUP
TE_TE_VECTOR = request_head(48, (b"chunked", b"identity")) + b"0\r\n\r\n" + SAFE_FOLLOWUP
CL_CL_VECTOR = request_head((4, 48), None) + b"ABCD" + SAFE_FOLLOWUP
CLEAN_VECTOR = request_head(5, None) + b"hello"


# ---------------------------------------------------------------------------
# Deterministic self-tests and demonstration
# ---------------------------------------------------------------------------

def run_self_tests():
    """Exercise parser details, all framing families, and strict rejections."""
    clean = parse_one_request(CLEAN_VECTOR, 0, STRICT_POLICY)
    assert clean.decision.kind == "content-length"
    assert clean.body_end == len(CLEAN_VECTOR)
    valid, _ = strict_validation(CLEAN_VECTOR)
    assert valid

    chunked = request_head(None, b"chunked") + b"3\r\nabc\r\n0\r\nX-Check: yes\r\n\r\n"
    parsed_chunked = parse_one_request(chunked, 0, STRICT_POLICY)
    assert parsed_chunked.decision.kind == "chunked"
    assert len(parsed_chunked.chunk_boundaries) == 2
    assert parsed_chunked.trailers[0].normalized_name == b"x-check"

    cl_te = compare_parsers(CL_TE_VECTOR, FRONT_CL_POLICY, BACK_TE_POLICY)
    assert cl_te.classification == "CL.TE"
    assert cl_te.disagreement

    te_cl = compare_parsers(TE_CL_VECTOR, FRONT_TE_POLICY, BACK_CL_POLICY)
    assert te_cl.classification == "TE.CL"
    assert te_cl.disagreement

    te_te = compare_parsers(TE_TE_VECTOR, FRONT_TE_POLICY, BACK_CL_POLICY)
    assert te_te.classification == "TE.TE"
    assert te_te.disagreement

    cl_cl = compare_parsers(CL_CL_VECTOR, FRONT_CL_POLICY, BACK_CL_POLICY)
    assert cl_cl.classification == "CL.CL"
    assert cl_cl.disagreement

    strict_ok, strict_reason = strict_validation(CL_TE_VECTOR)
    assert not strict_ok and "rejected" in strict_reason
    try:
        parse_one_request(b"GET / HTTP/1.1\r\nBad Header: x\r\n\r\n", 0, STRICT_POLICY)
    except HTTPParseError:
        pass
    else:
        raise AssertionError("strict parser should reject whitespace before colon")
    print("All HTTP parser and smuggling-detector self-tests passed.")


def run_demo():
    """Print detailed reports for clean and four inert ambiguity test vectors."""
    scenarios = (
        ("Clean Content-Length request", CLEAN_VECTOR, STRICT_POLICY, STRICT_POLICY),
        ("CL.TE disagreement", CL_TE_VECTOR, FRONT_CL_POLICY, BACK_TE_POLICY),
        ("TE.CL disagreement", TE_CL_VECTOR, FRONT_TE_POLICY, BACK_CL_POLICY),
        ("TE.TE disagreement", TE_TE_VECTOR, FRONT_TE_POLICY, BACK_CL_POLICY),
        ("CL.CL disagreement", CL_CL_VECTOR, FRONT_CL_POLICY, BACK_CL_POLICY),
    )
    for title, data, front, back in scenarios:
        print("\n" + "#" * 78)
        print("SCENARIO: " + title)
        print("#" * 78)
        print(format_comparison(data, compare_parsers(data, front, back)))


if __name__ == "__main__":
    run_self_tests()
    run_demo()
