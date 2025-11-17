from flask import Flask, render_template, request, send_file
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os
import json
from datetime import datetime

app = Flask(__name__)

TEMPLATE_PATH = "certificate/certificate_template.pdf"
GENERATED_PATH = "generated"

# ---- SERIAL NUMBER FUNCTION (MONTH-WISE RESET) ----
def get_monthwise_serial(month):
    serial_file = "serial.json"

    # If serial.json doesn't exist, create it
    if not os.path.exists(serial_file):
        data = {"month": month, "serial": 0}
        with open(serial_file, "w") as f:
            json.dump(data, f)

    # Load file data
    with open(serial_file, "r") as f:
        data = json.load(f)

    # Reset serial if month changed
    if data["month"] != month:
        data["month"] = month
        data["serial"] = 1
    else:
        data["serial"] += 1

    # Save updated serial
    with open(serial_file, "w") as f:
        json.dump(data, f)

    # Return formatted like 001, 002, 003
    return f"{data['serial']:03}"


@app.route("/")
def form():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    name = request.form.get("name")

    # ---- DATE & SERIAL LOGIC ----
    now = datetime.now()
    year = now.year
    month = now.strftime("%b").upper()   # JAN, FEB, MAR...
    serial_no = get_monthwise_serial(month)

    # Certificate ID (display format)
    certificate_id = f"SZS_CERT_{year}_{month}_{serial_no}"

    # File-safe name for saving
    file_name = certificate_id.replace("/", "_") + ".pdf"
    output_file = f"{GENERATED_PATH}/{file_name}"

    # ---- PDF GENERATION SAME AS BEFORE ----
    existing_pdf = PdfReader(open(TEMPLATE_PATH, "rb"))
    page = existing_pdf.pages[0]

    media = page.mediabox
    width = float(media.width)
    height = float(media.height)

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(width, height))

    # FONT (Your existing settings)
    can.setFont("Times-Italic", 33)

    # Center name
    text_width = can.stringWidth(name, "Times-Italic", 33)
    x_position = (width - text_width) / 2
    y_position = height * 0.46   # adjust if needed

    can.drawString(x_position, y_position, name)


    # OPTIONAL: Print certificate ID on PDF bottom right
    # can.setFont("Helvetica", 12)
    # can.drawString(width - 200, 40, certificate_id)

    can.save()

    packet.seek(0)
    name_pdf = PdfReader(packet)

    writer = PdfWriter()
    page.merge_page(name_pdf.pages[0])
    writer.add_page(page)

    os.makedirs(GENERATED_PATH, exist_ok=True)
    with open(output_file, "wb") as f:
        writer.write(f)

    return send_file(output_file, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
