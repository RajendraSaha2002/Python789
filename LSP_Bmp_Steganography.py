import struct
from pathlib import Path
from statistics import NormalDist


class BMPError(Exception):
    pass


class StegoError(Exception):
    pass


MASK64 = (1 << 64) - 1


def rotr(value, shift):
    return ((value >> shift) | (value << (64 - shift))) & MASK64


def ascon_permutation(state, rounds):
    """
    Ascon permutation used by the small authenticated-encryption routine below.
    State is five 64-bit integers.
    """
    start_round = 12 - rounds

    for round_number in range(start_round, 12):
        state[2] ^= ((0xF0 - round_number * 0x10) + round_number)

        x0, x1, x2, x3, x4 = state

        x0 ^= x4
        x4 ^= x3
        x2 ^= x1

        t0 = x0 ^ ((~x1) & x2)
        t1 = x1 ^ ((~x2) & x3)
        t2 = x2 ^ ((~x3) & x4)
        t3 = x3 ^ ((~x4) & x0)
        t4 = x4 ^ ((~x0) & x1)

        x0 = t0 & MASK64
        x1 = t1 & MASK64
        x2 = t2 & MASK64
        x3 = t3 & MASK64
        x4 = t4 & MASK64

        x1 ^= x0
        x0 ^= x4
        x3 ^= x2
        x2 = (~x2) & MASK64

        x0 ^= rotr(x0, 19) ^ rotr(x0, 28)
        x1 ^= rotr(x1, 61) ^ rotr(x1, 39)
        x2 ^= rotr(x2, 1) ^ rotr(x2, 6)
        x3 ^= rotr(x3, 10) ^ rotr(x3, 17)
        x4 ^= rotr(x4, 7) ^ rotr(x4, 41)

        state[0] = x0 & MASK64
        state[1] = x1 & MASK64
        state[2] = x2 & MASK64
        state[3] = x3 & MASK64
        state[4] = x4 & MASK64


def bytes_to_u64(data):
    return int.from_bytes(data, byteorder="big")


def u64_to_bytes(value):
    return value.to_bytes(8, byteorder="big")


def ascon_pad(data, rate=8):
    padding_size = rate - (len(data) % rate)
    return data + b"\x80" + (b"\x00" * (padding_size - 1))


def derive_key_from_password(password):
    """
    Simple deterministic password-to-key derivation for this educational tool.
    Use a strong password. This avoids external packages.
    """
    raw = password.encode("utf-8")

    if not raw:
        raise StegoError("Password cannot be empty.")

    state = [
        0x80400C0600000000,
        0x1234567890ABCDEF,
        0x0F1E2D3C4B5A6978,
        0x1122334455667788,
        0x8877665544332211,
    ]

    for index, byte_value in enumerate(raw):
        state[index % 5] ^= byte_value << ((index % 8) * 8)

        if index % 8 == 7:
            ascon_permutation(state, 12)

    ascon_permutation(state, 12)

    return u64_to_bytes(state[0]) + u64_to_bytes(state[1])


def create_nonce(password):
    raw = password.encode("utf-8")

    state = [
        0xA0400C0600000000,
        0xCAFEBABEDEADBEEF,
        0x0123456789ABCDEF,
        0xFEDCBA9876543210,
        0x55AA55AA55AA55AA,
    ]

    for index, byte_value in enumerate(raw):
        state[(index + 2) % 5] ^= byte_value << ((index % 8) * 8)

        if index % 8 == 7:
            ascon_permutation(state, 12)

    ascon_permutation(state, 12)

    return u64_to_bytes(state[3]) + u64_to_bytes(state[4])


def ascon_encrypt(plaintext, key, nonce):
    """
    Educational Ascon-128-style authenticated encryption.
    Returns ciphertext followed by a 16-byte authentication tag.
    """
    if len(key) != 16 or len(nonce) != 16:
        raise StegoError("ASCON key and nonce must both be 16 bytes.")

    key0 = bytes_to_u64(key[:8])
    key1 = bytes_to_u64(key[8:])
    nonce0 = bytes_to_u64(nonce[:8])
    nonce1 = bytes_to_u64(nonce[8:])

    state = [
        0x80400C0600000000,
        key0,
        key1,
        nonce0,
        nonce1,
    ]

    ascon_permutation(state, 12)
    state[3] ^= key0
    state[4] ^= key1

    ciphertext = bytearray()
    position = 0

    while position + 8 <= len(plaintext):
        block = plaintext[position:position + 8]
        state[0] ^= bytes_to_u64(block)
        ciphertext.extend(u64_to_bytes(state[0]))
        ascon_permutation(state, 6)
        position += 8

    final_block = plaintext[position:]
    padded_final_block = ascon_pad(final_block)
    state[0] ^= bytes_to_u64(padded_final_block[:8])
    ciphertext.extend(u64_to_bytes(state[0])[:len(final_block)])

    state[1] ^= key0
    state[2] ^= key1
    ascon_permutation(state, 12)
    state[3] ^= key0
    state[4] ^= key1

    tag = u64_to_bytes(state[3]) + u64_to_bytes(state[4])

    return bytes(ciphertext) + tag


def ascon_decrypt(ciphertext_and_tag, key, nonce):
    """Decrypt and verify ciphertext created by ascon_encrypt()."""
    if len(ciphertext_and_tag) < 16:
        raise StegoError("Encrypted payload is too short.")

    ciphertext = ciphertext_and_tag[:-16]
    supplied_tag = ciphertext_and_tag[-16:]

    key0 = bytes_to_u64(key[:8])
    key1 = bytes_to_u64(key[8:])
    nonce0 = bytes_to_u64(nonce[:8])
    nonce1 = bytes_to_u64(nonce[8:])

    state = [
        0x80400C0600000000,
        key0,
        key1,
        nonce0,
        nonce1,
    ]

    ascon_permutation(state, 12)
    state[3] ^= key0
    state[4] ^= key1

    plaintext = bytearray()
    position = 0

    while position + 8 <= len(ciphertext):
        encrypted_block = ciphertext[position:position + 8]
        encrypted_value = bytes_to_u64(encrypted_block)

        plaintext_value = state[0] ^ encrypted_value
        plaintext.extend(u64_to_bytes(plaintext_value))

        state[0] = encrypted_value
        ascon_permutation(state, 6)
        position += 8

    final_ciphertext = ciphertext[position:]
    old_state_bytes = u64_to_bytes(state[0])

    final_plaintext = bytes(
        old_state_bytes[index] ^ final_ciphertext[index]
        for index in range(len(final_ciphertext))
    )

    plaintext.extend(final_plaintext)

    padded_plaintext = ascon_pad(final_plaintext)
    replacement = bytearray(old_state_bytes)

    for index in range(len(final_ciphertext)):
        replacement[index] = final_ciphertext[index]

    replacement[len(final_ciphertext)] ^= 0x80
    state[0] = bytes_to_u64(bytes(replacement))

    state[1] ^= key0
    state[2] ^= key1
    ascon_permutation(state, 12)
    state[3] ^= key0
    state[4] ^= key1

    expected_tag = u64_to_bytes(state[3]) + u64_to_bytes(state[4])

    if expected_tag != supplied_tag:
        raise StegoError(
            "Authentication failed: wrong password or modified hidden data."
        )

    return bytes(plaintext)


class BMPImage:
    def __init__(self, path):
        self.path = Path(path)

        if not self.path.is_file():
            raise FileNotFoundError(f"BMP file not found: {self.path}")

        self.data = bytearray(self.path.read_bytes())
        self.pixel_offsets = []
        self.width = 0
        self.height = 0
        self.bits_per_pixel = 0
        self.pixel_data_offset = 0

        self.parse()

    def parse(self):
        if len(self.data) < 54:
            raise BMPError("File is too small to be a valid BMP.")

        if self.data[:2] != b"BM":
            raise BMPError("Not a BMP file: missing BM signature.")

        self.pixel_data_offset = struct.unpack_from("<I", self.data, 10)[0]
        dib_size = struct.unpack_from("<I", self.data, 14)[0]

        if dib_size < 40:
            raise BMPError("Unsupported BMP DIB header.")

        self.width = struct.unpack_from("<i", self.data, 18)[0]
        signed_height = struct.unpack_from("<i", self.data, 22)[0]
        planes = struct.unpack_from("<H", self.data, 26)[0]
        self.bits_per_pixel = struct.unpack_from("<H", self.data, 28)[0]
        compression = struct.unpack_from("<I", self.data, 30)[0]

        if self.width <= 0 or signed_height == 0:
            raise BMPError("Invalid BMP image dimensions.")

        if planes != 1:
            raise BMPError("Unsupported BMP plane count.")

        if self.bits_per_pixel not in (24, 32):
            raise BMPError("Only 24-bit and 32-bit BMP files are supported.")

        if compression != 0:
            raise BMPError("Compressed BMP files are not supported.")

        self.height = abs(signed_height)

        bytes_per_pixel = self.bits_per_pixel // 8
        row_stride = ((self.width * bytes_per_pixel + 3) // 4) * 4

        pixel_data_end = self.pixel_data_offset + row_stride * self.height

        if pixel_data_end > len(self.data):
            raise BMPError("BMP pixel data is incomplete.")

        for row in range(self.height):
            row_start = self.pixel_data_offset + row * row_stride

            for column in range(self.width):
                pixel_start = row_start + column * bytes_per_pixel

                # BMP channel order is Blue, Green, Red, Alpha.
                # Use only B, G, R; Alpha is not modified.
                self.pixel_offsets.extend(
                    [
                        pixel_start,
                        pixel_start + 1,
                        pixel_start + 2,
                    ]
                )

    @property
    def capacity_bits(self):
        return len(self.pixel_offsets)

    @property
    def capacity_bytes(self):
        return self.capacity_bits // 8

    def save(self, output_path):
        Path(output_path).write_bytes(self.data)


def bytes_to_bits(data):
    bits = []

    for byte_value in data:
        for shift in range(7, -1, -1):
            bits.append((byte_value >> shift) & 1)

    return bits


def bits_to_bytes(bits):
    result = bytearray()

    for start in range(0, len(bits), 8):
        value = 0

        for bit in bits[start:start + 8]:
            value = (value << 1) | bit

        result.append(value)

    return bytes(result)


def embed_message(input_path, output_path, password, message):
    image = BMPImage(input_path)

    key = derive_key_from_password(password)
    nonce = create_nonce(password)

    encrypted = ascon_encrypt(
        message.encode("utf-8"),
        key,
        nonce,
    )

    payload = struct.pack(">I", len(encrypted)) + encrypted
    payload_bits = bytes_to_bits(payload)

    if len(payload_bits) > image.capacity_bits:
        raise StegoError(
            f"Message is too large. BMP capacity: "
            f"{image.capacity_bytes} bytes."
        )

    for index, bit in enumerate(payload_bits):
        pixel_offset = image.pixel_offsets[index]
        image.data[pixel_offset] = (
            image.data[pixel_offset] & 0xFE
        ) | bit

    image.save(output_path)

    return {
        "output_file": str(Path(output_path).resolve()),
        "message_bytes": len(message.encode("utf-8")),
        "encrypted_payload_bytes": len(payload),
        "bmp_capacity_bytes": image.capacity_bytes,
    }


def extract_message(image_path, password):
    image = BMPImage(image_path)

    if image.capacity_bits < 32:
        raise StegoError("BMP image does not have enough data capacity.")

    length_bits = [
        image.data[offset] & 1
        for offset in image.pixel_offsets[:32]
    ]

    encrypted_length = struct.unpack(">I", bits_to_bytes(length_bits))[0]

    if encrypted_length < 16:
        raise StegoError("No valid hidden encrypted payload was found.")

    total_bits_needed = (4 + encrypted_length) * 8

    if total_bits_needed > image.capacity_bits:
        raise StegoError(
            "Hidden payload length is invalid for this BMP image."
        )

    payload_bits = [
        image.data[offset] & 1
        for offset in image.pixel_offsets[32:total_bits_needed]
    ]

    encrypted = bits_to_bytes(payload_bits)
    key = derive_key_from_password(password)
    nonce = create_nonce(password)

    message = ascon_decrypt(encrypted, key, nonce)

    return message.decode("utf-8", errors="replace")


def chi_square_channel_test(values):
    """
    Basic pair-of-values chi-square LSB analysis.
    Lower chi-square values can indicate more evenly distributed LSBs.
    """
    histogram = [0] * 256

    for value in values:
        histogram[value] += 1

    chi_square = 0.0
    degrees_of_freedom = 0

    for value in range(0, 256, 2):
        first = histogram[value]
        second = histogram[value + 1]
        total = first + second

        if total > 0:
            expected = total / 2
            chi_square += (
                ((first - expected) ** 2) / expected
                + ((second - expected) ** 2) / expected
            )
            degrees_of_freedom += 1

    if degrees_of_freedom <= 0:
        return {
            "chi_square": 0.0,
            "degrees_of_freedom": 0,
            "p_value_approximation": 0.0,
        }

    # Wilson-Hilferty approximation of chi-square survival probability.
    normal = NormalDist()
    transformed = (
        (chi_square / degrees_of_freedom) ** (1 / 3)
        - (1 - 2 / (9 * degrees_of_freedom))
    ) / math_sqrt(2 / (9 * degrees_of_freedom))

    p_value = 1 - normal.cdf(transformed)

    return {
        "chi_square": round(chi_square, 4),
        "degrees_of_freedom": degrees_of_freedom,
        "p_value_approximation": round(p_value, 6),
    }


def math_sqrt(value):
    """Small square-root helper without adding another import."""
    if value <= 0:
        return 0.0

    estimate = value

    for _ in range(20):
        estimate = (estimate + value / estimate) / 2

    return estimate


def detect_lsb(image_path):
    image = BMPImage(image_path)

    blue_values = []
    green_values = []
    red_values = []

    for index in range(0, len(image.pixel_offsets), 3):
        blue_values.append(image.data[image.pixel_offsets[index]])
        green_values.append(image.data[image.pixel_offsets[index + 1]])
        red_values.append(image.data[image.pixel_offsets[index + 2]])

    channels = {
        "blue": chi_square_channel_test(blue_values),
        "green": chi_square_channel_test(green_values),
        "red": chi_square_channel_test(red_values),
    }

    p_values = [
        channel["p_value_approximation"]
        for channel in channels.values()
    ]

    average_p = sum(p_values) / len(p_values)

    if average_p >= 0.80:
        confidence = "HIGH"
        conclusion = (
            "LSB values are unusually balanced; hidden data is plausible."
        )
    elif average_p >= 0.50:
        confidence = "MEDIUM"
        conclusion = (
            "Some LSB balance is present; further inspection is recommended."
        )
    else:
        confidence = "LOW"
        conclusion = (
            "No strong statistical indication of LSB embedding was found."
        )

    return {
        "file": str(Path(image_path).resolve()),
        "image_width": image.width,
        "image_height": image.height,
        "bits_per_pixel": image.bits_per_pixel,
        "capacity_bytes": image.capacity_bytes,
        "channels": channels,
        "average_p_value": round(average_p, 6),
        "confidence": confidence,
        "conclusion": conclusion,
    }


def print_detector_report(report):
    print("\n" + "=" * 70)
    print("LSB CHI-SQUARE DETECTION REPORT")
    print("=" * 70)
    print(f"File: {report['file']}")
    print(
        f"Image: {report['image_width']} x {report['image_height']} "
        f"({report['bits_per_pixel']}-bit)"
    )
    print(f"LSB capacity: {report['capacity_bytes']} bytes")

    print("\nChannel statistics:")

    for channel_name, result in report["channels"].items():
        print(
            f"  {channel_name.title():<6} "
            f"Chi-square: {result['chi_square']:<10} "
            f"P-value: {result['p_value_approximation']}"
        )

    print(f"\nAverage p-value: {report['average_p_value']}")
    print(f"Confidence: {report['confidence']}")
    print(f"Conclusion: {report['conclusion']}")
    print(
        "\nNote: chi-square analysis is heuristic only; it cannot prove "
        "that hidden content exists."
    )


def main():
    print("LSB BMP Steganography Embedder and Detector")
    print("=" * 70)
    print("1 - Embed encrypted text in a BMP")
    print("2 - Extract encrypted text from a BMP")
    print("3 - Run chi-square LSB detector")

    choice = input("\nChoose an option (1, 2, or 3): ").strip()

    try:
        if choice == "1":
            input_path = input("Input 24-bit/32-bit BMP path: ").strip()
            output_path = input(
                "Output BMP path [stego_output.bmp]: "
            ).strip()

            if not output_path:
                output_path = "stego_output.bmp"

            password = input("Password: ").strip()
            message = input("Secret message: ")

            result = embed_message(
                input_path,
                output_path,
                password,
                message,
            )

            print("\nMessage embedded successfully.")
            print(f"Output BMP: {result['output_file']}")
            print(f"Message size: {result['message_bytes']} bytes")
            print(
                f"Used capacity: {result['encrypted_payload_bytes']} "
                f"of {result['bmp_capacity_bytes']} bytes"
            )

        elif choice == "2":
            image_path = input("Stego BMP path: ").strip()
            password = input("Password: ").strip()

            message = extract_message(image_path, password)

            print("\nExtracted message:")
            print("-" * 70)
            print(message)

        elif choice == "3":
            image_path = input("BMP path to analyse: ").strip()
            report = detect_lsb(image_path)
            print_detector_report(report)

        else:
            print("Error: choose 1, 2, or 3.")

    except FileNotFoundError as error:
        print(f"File error: {error}")

    except PermissionError:
        print("Permission error: unable to read or write the selected file.")

    except (BMPError, StegoError, ValueError) as error:
        print(f"Error: {error}")

    except OSError as error:
        print(f"File system error: {error}")

    except KeyboardInterrupt:
        print("\nOperation cancelled.")


if __name__ == "__main__":
    main()