import qrcode
from barcode import EAN13, Code128
from barcode.writer import ImageWriter
from PIL import Image

def generate_qr_code():
    """Generates a QR code from user input and saves it as an image."""
    data = input("Enter the text or URL to encode in the QR code: ")
    if not data:
        print("Error: Data cannot be empty.")
        return

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # Create an image from the QR Code instance
    img = qr.make_image(fill_color="black", back_color="white")

    # Save the image
    filename = "qr_code.png"
    img.save(filename)
    print(f"Successfully generated QR code and saved it as '{filename}'")
    # Open the image
    Image.open(filename).show()


def generate_barcode():
    """Generates a barcode from user input and saves it as an image."""
    print("Select Barcode Type:")
    print("1. EAN-13 (12 digits, e.g., for products)")
    print("2. Code 128 (alphanumeric, versatile)")
    barcode_type = input("Enter choice (1 or 2): ")

    if barcode_type == '1':
        data = input("Enter 12 digits for the EAN-13 barcode: ")
        if not data.isdigit() or len(data) != 12:
            print("Error: EAN-13 requires exactly 12 digits.")
            return
        barcode_class = EAN13
    elif barcode_type == '2':
        data = input("Enter the data for the Code 128 barcode: ")
        if not data:
            print("Error: Data cannot be empty.")
            return
        barcode_class = Code128
    else:
        print("Invalid choice. Please try again.")
        return

    # Generate barcode and save it as a PNG file
    filename = "barcode.png"
    # The ImageWriter is used to save the barcode as an image
    with open(filename, 'wb') as f:
        barcode_class(data, writer=ImageWriter()).write(f)

    print(f"Successfully generated barcode and saved it as '{filename}'")
    # Open the image
    Image.open(filename).show()


def main():
    """Main function to run the generator tool."""
    while True:
        print("\n--- Barcode and QR Code Generator ---")
        print("1. Generate QR Code")
        print("2. Generate Barcode")
        print("3. Exit")
        choice = input("Enter your choice (1, 2, or 3): ")

        if choice == '1':
            generate_qr_code()
        elif choice == '2':
            generate_barcode()
        elif choice == '3':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


if __name__ == "__main__":
    main()