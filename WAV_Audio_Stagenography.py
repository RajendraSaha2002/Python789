import math
import struct
import wave
from pathlib import Path


class WAVStegoError(Exception):
    pass


PHASE_BLOCK_SIZE = 1024
LENGTH_BITS = 16


def read_wav_samples(path):
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(f"WAV file not found: {path}")

    try:
        with wave.open(str(path), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            frame_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()
            compression = wav_file.getcomptype()
            raw_data = wav_file.readframes(frame_count)

    except wave.Error as error:
        raise WAVStegoError(f"Invalid WAV file: {error}") from error

    if compression != "NONE":
        raise WAVStegoError("Only uncompressed PCM WAV files are supported.")

    if sample_width != 2:
        raise WAVStegoError(
            "Only 16-bit PCM WAV files are supported."
        )

    if channels < 1:
        raise WAVStegoError("Invalid WAV channel count.")

    sample_count = len(raw_data) // 2
    samples = list(struct.unpack(f"<{sample_count}h", raw_data))

    return {
        "channels": channels,
        "sample_width": sample_width,
        "frame_rate": frame_rate,
        "frame_count": frame_count,
        "samples": samples,
    }


def write_wav_samples(path, wav_info):
    path = Path(path)

    samples = wav_info["samples"]
    raw_data = struct.pack(f"<{len(samples)}h", *samples)

    try:
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(wav_info["channels"])
            wav_file.setsampwidth(wav_info["sample_width"])
            wav_file.setframerate(wav_info["frame_rate"])
            wav_file.writeframes(raw_data)

    except wave.Error as error:
        raise WAVStegoError(f"Could not write WAV file: {error}") from error


def bytes_to_bits(data):
    bits = []

    for byte_value in data:
        for shift in range(7, -1, -1):
            bits.append((byte_value >> shift) & 1)

    return bits


def bits_to_bytes(bits):
    output = bytearray()

    for index in range(0, len(bits), 8):
        value = 0

        for bit in bits[index:index + 8]:
            value = (value << 1) | bit

        output.append(value)

    return bytes(output)


def create_payload(message):
    message_bytes = message.encode("utf-8")

    if len(message_bytes) > 65535:
        raise WAVStegoError("Message is too large.")

    return struct.pack(">H", len(message_bytes)) + message_bytes


def parse_payload(payload):
    if len(payload) < 2:
        raise WAVStegoError("Hidden payload is missing.")

    message_length = struct.unpack(">H", payload[:2])[0]
    message_bytes = payload[2:2 + message_length]

    if len(message_bytes) != message_length:
        raise WAVStegoError("Hidden payload is incomplete.")

    return message_bytes.decode("utf-8", errors="replace")


def embed_lsb(input_path, output_path, message):
    wav_info = read_wav_samples(input_path)
    payload = create_payload(message)
    bits = bytes_to_bits(payload)

    if len(bits) > len(wav_info["samples"]):
        capacity = len(wav_info["samples"]) // 8 - 2

        raise WAVStegoError(
            f"Message is too large. Maximum LSB message size: "
            f"{max(capacity, 0)} bytes."
        )

    samples = wav_info["samples"][:]

    for index, bit in enumerate(bits):
        unsigned_sample = samples[index] & 0xFFFF
        unsigned_sample = (unsigned_sample & 0xFFFE) | bit

        if unsigned_sample >= 32768:
            samples[index] = unsigned_sample - 65536
        else:
            samples[index] = unsigned_sample

    wav_info["samples"] = samples
    write_wav_samples(output_path, wav_info)

    return {
        "output_file": str(Path(output_path).resolve()),
        "message_size": len(message.encode("utf-8")),
        "capacity_bytes": len(wav_info["samples"]) // 8 - 2,
    }


def extract_lsb(input_path):
    wav_info = read_wav_samples(input_path)
    samples = wav_info["samples"]

    if len(samples) < 16:
        raise WAVStegoError("WAV file is too small.")

    length_bits = [
        sample & 1
        for sample in samples[:16]
    ]

    message_length = struct.unpack(
        ">H",
        bits_to_bytes(length_bits),
    )[0]

    total_bits = (message_length + 2) * 8

    if total_bits > len(samples):
        raise WAVStegoError(
            "No valid LSB message found or WAV file is not a stego file."
        )

    bits = [
        sample & 1
        for sample in samples[:total_bits]
    ]

    payload = bits_to_bytes(bits)

    return parse_payload(payload)


def dft(samples):
    """
    Direct Discrete Fourier Transform.
    Slow but uses only the Python standard library.
    """
    size = len(samples)
    spectrum = []

    for frequency in range(size):
        real = 0.0
        imaginary = 0.0

        for index, value in enumerate(samples):
            angle = -2.0 * math.pi * frequency * index / size
            real += value * math.cos(angle)
            imaginary += value * math.sin(angle)

        spectrum.append(complex(real, imaginary))

    return spectrum


def inverse_dft(spectrum):
    """Direct inverse Discrete Fourier Transform."""
    size = len(spectrum)
    samples = []

    for index in range(size):
        value = 0.0

        for frequency, coefficient in enumerate(spectrum):
            angle = 2.0 * math.pi * frequency * index / size
            value += (
                coefficient.real * math.cos(angle)
                - coefficient.imag * math.sin(angle)
            )

        samples.append(value / size)

    return samples


def clamp_16bit(value):
    value = int(round(value))

    if value > 32767:
        return 32767

    if value < -32768:
        return -32768

    return value


def get_first_channel_samples(wav_info, count):
    channels = wav_info["channels"]
    samples = wav_info["samples"]

    return [
        samples[index * channels]
        for index in range(count)
    ]


def replace_first_channel_samples(wav_info, new_values):
    channels = wav_info["channels"]

    for index, value in enumerate(new_values):
        wav_info["samples"][index * channels] = clamp_16bit(value)


def embed_phase(input_path, output_path, message):
    wav_info = read_wav_samples(input_path)
    channels = wav_info["channels"]
    available_frames = wav_info["frame_count"]

    if available_frames < PHASE_BLOCK_SIZE:
        raise WAVStegoError(
            f"WAV requires at least {PHASE_BLOCK_SIZE} audio frames "
            f"for phase coding."
        )

    payload = create_payload(message)
    bits = bytes_to_bits(payload)

    maximum_bits = (PHASE_BLOCK_SIZE // 2) - 1

    if len(bits) > maximum_bits:
        maximum_bytes = (maximum_bits // 8) - 2

        raise WAVStegoError(
            f"Phase coding supports up to {maximum_bytes} message bytes "
            f"with the current block size."
        )

    first_channel = get_first_channel_samples(
        wav_info,
        PHASE_BLOCK_SIZE,
    )

    spectrum = dft(first_channel)

    for index, bit in enumerate(bits):
        frequency = index + 1
        magnitude = abs(spectrum[frequency])

        if magnitude < 10:
            magnitude = 10

        phase = 0.0 if bit == 0 else math.pi

        real = magnitude * math.cos(phase)
        imaginary = magnitude * math.sin(phase)

        spectrum[frequency] = complex(real, imaginary)
        spectrum[-frequency] = complex(real, -imaginary)

    modified_samples = inverse_dft(spectrum)
    replace_first_channel_samples(wav_info, modified_samples)

    write_wav_samples(output_path, wav_info)

    return {
        "output_file": str(Path(output_path).resolve()),
        "message_size": len(message.encode("utf-8")),
        "capacity_bytes": (maximum_bits // 8) - 2,
        "channels": channels,
    }


def extract_phase(input_path):
    wav_info = read_wav_samples(input_path)

    if wav_info["frame_count"] < PHASE_BLOCK_SIZE:
        raise WAVStegoError("WAV file is too short for phase extraction.")

    first_channel = get_first_channel_samples(
        wav_info,
        PHASE_BLOCK_SIZE,
    )

    spectrum = dft(first_channel)
    bits = []

    for frequency in range(1, LENGTH_BITS + 1):
        phase = math.atan2(
            spectrum[frequency].imag,
            spectrum[frequency].real,
        )

        bit = 1 if abs(phase) > (math.pi / 2) else 0
        bits.append(bit)

    message_length = struct.unpack(
        ">H",
        bits_to_bytes(bits),
    )[0]

    total_bits = (message_length + 2) * 8
    maximum_bits = (PHASE_BLOCK_SIZE // 2) - 1

    if total_bits > maximum_bits:
        raise WAVStegoError(
            "No valid phase-coded message found in this WAV file."
        )

    bits = []

    for frequency in range(1, total_bits + 1):
        phase = math.atan2(
            spectrum[frequency].imag,
            spectrum[frequency].real,
        )

        bit = 1 if abs(phase) > (math.pi / 2) else 0
        bits.append(bit)

    return parse_payload(bits_to_bytes(bits))


def sample_pair_analysis(input_path):
    wav_info = read_wav_samples(input_path)
    samples = wav_info["samples"]

    even_lsb_zero = 0
    even_lsb_one = 0
    odd_lsb_zero = 0
    odd_lsb_one = 0

    pair_difference_zero = 0
    pair_difference_one = 0

    for index in range(0, len(samples) - 1, 2):
        first = samples[index]
        second = samples[index + 1]

        if first % 2 == 0:
            even_lsb_zero += 1
        else:
            even_lsb_one += 1

        if second % 2 == 0:
            odd_lsb_zero += 1
        else:
            odd_lsb_one += 1

        difference = abs(first - second)

        if difference % 2 == 0:
            pair_difference_zero += 1
        else:
            pair_difference_one += 1

    total_samples = len(samples)
    zero_lsb_count = even_lsb_zero + odd_lsb_zero
    one_lsb_count = even_lsb_one + odd_lsb_one

    lsb_balance = (
        min(zero_lsb_count, one_lsb_count)
        / max(zero_lsb_count, one_lsb_count)
        if max(zero_lsb_count, one_lsb_count) > 0
        else 0.0
    )

    difference_balance = (
        min(pair_difference_zero, pair_difference_one)
        / max(pair_difference_zero, pair_difference_one)
        if max(pair_difference_zero, pair_difference_one) > 0
        else 0.0
    )

    suspicion_score = (
        (lsb_balance * 70)
        + (difference_balance * 30)
    )

    if suspicion_score >= 90:
        confidence = "HIGH"
        conclusion = (
            "LSB distribution is highly balanced. "
            "Possible LSB embedding detected."
        )
    elif suspicion_score >= 75:
        confidence = "MEDIUM"
        conclusion = (
            "Some sample-pair characteristics may indicate LSB embedding."
        )
    else:
        confidence = "LOW"
        conclusion = (
            "No strong LSB steganography indicator was found."
        )

    return {
        "file": str(Path(input_path).resolve()),
        "channels": wav_info["channels"],
        "sample_rate": wav_info["frame_rate"],
        "frames": wav_info["frame_count"],
        "total_samples": total_samples,
        "lsb_zero_count": zero_lsb_count,
        "lsb_one_count": one_lsb_count,
        "lsb_balance": round(lsb_balance, 6),
        "pair_difference_even": pair_difference_zero,
        "pair_difference_odd": pair_difference_one,
        "pair_difference_balance": round(difference_balance, 6),
        "suspicion_score": round(suspicion_score, 2),
        "confidence": confidence,
        "conclusion": conclusion,
    }


def print_spa_report(report):
    print("\n" + "=" * 72)
    print("WAV SAMPLE PAIR ANALYSIS REPORT")
    print("=" * 72)
    print(f"File: {report['file']}")
    print(f"Channels: {report['channels']}")
    print(f"Sample rate: {report['sample_rate']} Hz")
    print(f"Audio frames: {report['frames']}")
    print(f"Total samples: {report['total_samples']}")
    print(f"\nLSB zero count: {report['lsb_zero_count']}")
    print(f"LSB one count: {report['lsb_one_count']}")
    print(f"LSB balance: {report['lsb_balance']}")
    print(
        "Pair difference balance: "
        f"{report['pair_difference_balance']}"
    )
    print(f"Suspicion score: {report['suspicion_score']} / 100")
    print(f"Confidence: {report['confidence']}")
    print(f"Conclusion: {report['conclusion']}")
    print(
        "\nNote: Sample Pair Analysis is heuristic and cannot prove "
        "that hidden data exists."
    )


def main():
    print("=" * 72)
    print("WAV Audio Steganography: LSB, Phase Coding, and SPA Detection")
    print("=" * 72)
    print("Only uncompressed 16-bit PCM WAV files are supported.\n")
    print("1 - Embed text with LSB substitution")
    print("2 - Extract LSB hidden text")
    print("3 - Embed text with phase coding")
    print("4 - Extract phase-coded hidden text")
    print("5 - Run Sample Pair Analysis detector")

    choice = input("\nChoose an option (1-5): ").strip()

    try:
        if choice == "1":
            input_path = input("Input WAV path: ").strip()
            output_path = input(
                "Output WAV path [lsb_stego.wav]: "
            ).strip()

            if not output_path:
                output_path = "lsb_stego.wav"

            message = input("Secret message: ")

            result = embed_lsb(
                input_path,
                output_path,
                message,
            )

            print("\nLSB message embedded successfully.")
            print(f"Output file: {result['output_file']}")
            print(f"Message size: {result['message_size']} bytes")
            print(f"LSB capacity: {result['capacity_bytes']} bytes")

        elif choice == "2":
            input_path = input("LSB stego WAV path: ").strip()
            message = extract_lsb(input_path)

            print("\nExtracted LSB message:")
            print(message)

        elif choice == "3":
            input_path = input("Input WAV path: ").strip()
            output_path = input(
                "Output WAV path [phase_stego.wav]: "
            ).strip()

            if not output_path:
                output_path = "phase_stego.wav"

            message = input("Secret message: ")

            result = embed_phase(
                input_path,
                output_path,
                message,
            )

            print("\nPhase-coded message embedded successfully.")
            print(f"Output file: {result['output_file']}")
            print(f"Message size: {result['message_size']} bytes")
            print(f"Phase capacity: {result['capacity_bytes']} bytes")

        elif choice == "4":
            input_path = input("Phase stego WAV path: ").strip()
            message = extract_phase(input_path)

            print("\nExtracted phase-coded message:")
            print(message)

        elif choice == "5":
            input_path = input("WAV path to analyse: ").strip()
            report = sample_pair_analysis(input_path)
            print_spa_report(report)

        else:
            print("Error: choose a number from 1 to 5.")

    except FileNotFoundError as error:
        print(f"File error: {error}")

    except PermissionError:
        print("Permission error: cannot read or write this file.")

    except (WAVStegoError, ValueError) as error:
        print(f"Error: {error}")

    except KeyboardInterrupt:
        print("\nOperation cancelled.")

    except Exception as error:
        print(f"Unexpected error: {error}")


if __name__ == "__main__":
    main()