"""
Simple QR Code Generator
This script generates QR codes from text or URLs
"""

import qrcode
from PIL import Image
import os


def generate_qr_code():
    print("\n===== QR CODE GENERATOR =====")

    # Get the data to encode
    data = input("Enter text or URL to convert to QR code: ")
    if not data:
        print("Error: You must enter some text or URL!")
        return

    # Create a directory for saving if it doesn't exist
    if not os.path.exists('qr_codes'):
        os.makedirs('qr_codes')

    # Create filename
    filename = input("Enter filename (without extension) or press Enter for default: ")
    if not filename:
        filename = "my_qr_code"

    # Full path to save the file
    save_path = f"qr_codes/{filename}.png"

    try:
        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )

        # Add data to QR code
        qr.add_data(data)
        qr.make(fit=True)

        # Create image from QR code
        img = qr.make_image(fill_color="black", back_color="white")

        # Save the image
        img.save(save_path)
        print(f"SUCCESS: QR code saved to {save_path}")

        # Try to display the image
        print("Attempting to display the image...")
        try:
            Image.open(save_path).show()
            print("QR code displayed.")
        except Exception as e:
            print(f"NOTE: Could not automatically display the image: {e}")
            print(f"Please open {save_path} manually to view your QR code.")

    except Exception as e:
        print(f"ERROR: Failed to create QR code: {e}")


if __name__ == "__main__":
    print("Welcome to the QR Code Generator")
    print("--------------------------------")

    while True:
        generate_qr_code()

        choice = input("\nGenerate another QR code? (y/n): ")
        if choice.lower() != 'y':
            print("Thank you for using QR Code Generator!")
            break