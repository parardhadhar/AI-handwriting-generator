import os
import random
import cv2
import numpy as np
import pytesseract
from flask import Flask, request, render_template, send_file
from pdf2image import convert_from_path
from PIL import Image, ImageDraw, ImageFont
from fpdf import FPDF

app = Flask(__name__)

# Ensure uploads folder exists
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Set Tesseract path (update if installed elsewhere)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Folder to store extracted handwriting characters
CHARACTER_OUTPUT_DIR = "handwriting_samples"
os.makedirs(CHARACTER_OUTPUT_DIR, exist_ok=True)

# Available pen colors (blue, black, dark blue)
PEN_COLORS = [(0, 0, 0), (0, 0, 139), (25, 25, 112)]  

def extract_text_from_pdf(pdf_path):
    """Extract text from a multi-page PDF using OCR."""
    images = convert_from_path(pdf_path, dpi=300)  
    text_pages = []
    custom_config = r"--oem 3 --psm 6"

    for img in images:
        extracted_text = pytesseract.image_to_string(img, config=custom_config)
        text_pages.append(extracted_text.strip())

    return text_pages  

def extract_handwriting_chars(image_path):
    """Extracts individual handwritten characters from an image"""
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    _, thresh = cv2.threshold(img, 150, 255, cv2.THRESH_BINARY_INV)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    char_images = []
    for i, contour in enumerate(contours):
        x, y, w, h = cv2.boundingRect(contour)
        if w > 5 and h > 10:  
            char_img = img[y:y+h, x:x+w]
            char_img = cv2.resize(char_img, (50, 50))  
            char_path = os.path.join(CHARACTER_OUTPUT_DIR, f"char_{i}.png")
            cv2.imwrite(char_path, char_img)
            char_images.append(char_path)

    return char_images

def generate_handwriting_pdf(text_pages, output_pdf_path):
    """Convert extracted text into a handwritten-style PDF with ruled lines."""
    pdf = FPDF()
    font_path = "handwriting_font.ttf"  

    try:
        pdf.add_font("Handwriting", "", font_path, uni=True)
    except:
        return "Font file not found. Please add a handwriting font (e.g., 'handwriting_font.ttf')."

    pdf.set_auto_page_break(auto=True, margin=15)

    for text in text_pages:
        pdf.add_page()
        pdf.set_font("Handwriting", size=16)

        pdf.set_draw_color(150, 150, 150)  
        margin_left = 20
        margin_right = 190

        for y in range(30, 280, 10):  
            pdf.line(margin_left, y, margin_right, y)

        y_position = 35
        for line in text.split("\n"):
            if line.strip():
                x_offset = random.randint(-2, 2)  
                color = random.choice(PEN_COLORS)  
                pdf.set_text_color(*color)
                pdf.text(margin_left + x_offset, y_position, line)
                y_position += 10  

    pdf.output(output_pdf_path)
    return output_pdf_path

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "handwriting_sample" in request.files:
            file = request.files["handwriting_sample"]
            if file:
                sample_path = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(sample_path)
                extracted_chars = extract_handwriting_chars(sample_path)
                return f"Extracted {len(extracted_chars)} characters from handwriting sample."

        elif "file" in request.files:
            file = request.files["file"]
            if not file:
                return "No file uploaded", 400

            file_extension = file.filename.split(".")[-1].lower()

            if file_extension == "pdf":
                pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
                file.save(pdf_path)  
                text_pages = extract_text_from_pdf(pdf_path)

                if not any(text_pages):
                    return "No text found in the PDF.", 400

                output_pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], "handwritten_output.pdf")
                generate_handwriting_pdf(text_pages, output_pdf_path)
                return send_file(output_pdf_path, as_attachment=True)

            else:
                return "Unsupported file type", 400

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
