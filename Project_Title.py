from fpdf import FPDF

# The list of project titles to be included in the PDF.
project_titles = [
    "1) GSM-Enabled Laser Tripwire Security System with NE555 and Arduino Nano",
    "2) Sentri-Guard : A GSM-Based Laser Security & Alert System",
    "3) Remote Security Monitoring System with Arduino, LDR & GSM Module"
]

# Create a new PDF object
pdf = FPDF()

# Add a page
pdf.add_page()

# Set font for the title
pdf.set_font("Arial", "B", 16)
pdf.cell(0, 10, "Project Titles", ln=True, align="C")
pdf.ln(10) # Add a line break for spacing

# Set font for the list items
pdf.set_font("Arial", "", 12)

# Loop through the list and add each title to the PDF
for title in project_titles:
    # Use multi_cell for titles that may wrap to multiple lines
    # 10 is the height of each line, 0 is for full width, True for a new line after the cell
    pdf.multi_cell(0, 10, title)
    pdf.ln(2) # Add a small break between titles

# Save the PDF file
output_filename = "project_titles.pdf"
pdf.output(output_filename)

print(f"PDF file '{output_filename}' created successfully.")
print("You can now download and view the generated PDF.")
