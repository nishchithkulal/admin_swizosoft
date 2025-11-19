from flask import Flask, render_template, request, send_file
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
import io, os, json, re, requests

app = Flask(__name__)

# ------------------ Paths ------------------
TEMPLATE_PATH = "offer_template/pdf_template.pdf"
GENERATED_PATH = "generated"
SERIAL_FILE = "offer_serial.json"
FONTS_DIR = "fonts"  # place Times New Roman TTFs here

# Configuration for admin app integration
ADMIN_APP_URL = os.getenv('ADMIN_APP_URL', 'http://localhost:5000')

# ------------------ Fonts ------------------
try:
    pdfmetrics.registerFont(TTFont("TNR", f"{FONTS_DIR}/Times New Roman.ttf"))
    pdfmetrics.registerFont(TTFont("TNRB", f"{FONTS_DIR}/Times New Roman Bold.ttf"))
    pdfmetrics.registerFont(TTFont("TNRI", f"{FONTS_DIR}/Times New Roman Italic.ttf"))
    BODY, BOLD, ITALIC = "TNR", "TNRB", "TNRI"
except:
    BODY, BOLD, ITALIC = "Times-Roman", "Times-Bold", "Times-Italic"

# ------------------ Layout ------------------
LEFT = 30
RIGHT = 30
LINE = 15
GAP = 12
TOP = 275
F_SIZE = 12

# ------------------ Helpers ------------------
def format_date(dt):
    d = dt.day
    suffix = "th" if 11 <= d <= 13 else {1:"st",2:"nd",3:"rd"}.get(d % 10, "th")
    return f"{d}{suffix} {dt.strftime('%b')} {dt.year}"

def get_monthwise_serial(month):
    if not os.path.exists(SERIAL_FILE):
        with open(SERIAL_FILE, "w") as f:
            json.dump({"month": "", "serial": 0}, f)

    with open(SERIAL_FILE, "r") as f:
        data = json.load(f)

    if data["month"] != month:
        data["month"] = month
        data["serial"] = 1
    else:
        data["serial"] += 1

    with open(SERIAL_FILE, "w") as f:
        json.dump(data, f)

    return f"{data['serial']:03}"

# ------------------ ROUTES ------------------
@app.route("/")
def home():
    return render_template("offer.html")

def generate_offer_pdf(name, usn, college, email, role, duration, intern_type):
    """
    Generate offer letter PDF with given parameters.
    Returns: (pdf_file_path, reference_number) or (None, None) on failure
    """
    try:
        now = datetime.now()
        current_month = now.strftime("%b").upper()
        serial = get_monthwise_serial(current_month)
        ref_no = f"SZS/OFFR/{now.year}/{current_month}/{serial}"
        date_str = format_date(now)

        reader = PdfReader(open(TEMPLATE_PATH, "rb"))
        writer = PdfWriter()

        page = reader.pages[0]
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        max_width = width - LEFT - RIGHT

        buf = io.BytesIO()
        can = canvas.Canvas(buf, pagesize=(width, height))

        # ---------------- HEADER ----------------
        y = height - TOP
        can.setFont(BOLD, F_SIZE)
        can.drawString(LEFT, y, f"Ref. No.: {ref_no}")
        can.drawRightString(width - RIGHT, y, f"Date: {date_str}")

        # ---------------- TITLE ----------------
        y -= 40
        can.drawCentredString(width / 2, y, "INTERNSHIP OFFER LETTER")

        # ---------------- TO BLOCK ----------------
        y -= 50
        can.drawString(LEFT, y, "To,")
        y -= 20

        display_name = f"{name} ({usn})" if usn else name
        can.setFont(BODY, F_SIZE)
        can.drawString(LEFT, y, display_name); y -= 15
        can.drawString(LEFT, y, college); y -= 15
        can.drawString(LEFT, y, email); y -= 8

        can.setStrokeColorRGB(0.75, 0.75, 0.75)
        can.setLineWidth(1)
        can.line(LEFT, y, width - LEFT, y)
        y -= 25

        # ---------------- SUBJECT ----------------
        can.setFont(BOLD, F_SIZE)
        prefix = "Subject: Offer of Internship for the Role of "
        can.drawString(LEFT, y, prefix)
        can.drawString(LEFT + stringWidth(prefix, BOLD, F_SIZE), y, role)
        y -= 30

        # ---------------- SALUTATION ----------------
        can.setFont(BODY, F_SIZE)
        can.drawString(LEFT, y, f"Dear {name},")
        y -= 30

        # ---------------- BOLD & ITALIC RULES ----------------

        bold_position_company = re.compile(
            rf"{re.escape(role)}",
            re.IGNORECASE
        )

        bold_duration_trial = re.compile(
            rf"{re.escape(duration)}",
            re.IGNORECASE
        )

        bold_hands_on = re.compile(
            r"hands-on\s+project\s+experience",
            re.IGNORECASE
        )

        bold_swizo = re.compile(re.escape("Swizosoft (OPC) Private Limited"), re.IGNORECASE)
        bold_team = re.compile(re.escape("Team Swizosoft (OPC) Private Limited"), re.IGNORECASE)
        bold_industry = re.compile(r"industry-ready\s+skills", re.IGNORECASE)
        bold_role = re.compile(re.escape(role), re.IGNORECASE)
        bold_duration = re.compile(re.escape(duration), re.IGNORECASE)
        bold_intern_type = re.compile(re.escape(intern_type), re.IGNORECASE)
        bold_trial = re.compile(r"gain\s+hands-on\s+project", re.IGNORECASE)
        bold_company1 = re.compile(r"Swizosoft", re.IGNORECASE)
        bold_company2 = re.compile(r"\(OPC\)\s*Private\s+Limited", re.IGNORECASE)

        BOLD_PATTERNS = [
            bold_position_company,      # Most specific: "Role at Swizosoft (OPC) Private Limited"
            bold_duration_trial,      # Specific: "Duration for"
            bold_hands_on,              # Specific: "hands-on project experience"
            bold_industry,              # Specific: "industry-ready skills"
            bold_team,                  # "Team Swizosoft (OPC) Private Limited"
            bold_swizo,                 # "Swizosoft (OPC) Private Limited"
            bold_duration,              # Duration input
            bold_intern_type,           # Internship type
            bold_trial,                 # "gain hands-on project"
            bold_role, 
            bold_company1,              # "Swizosoft"
            bold_company2,              # "(OPC)"
        ]

        ITALIC_PHRASE = "real-time project execution"

        # ---------------- SEGMENT BUILDER ----------------
        def build_segments(words):
            txt = " ".join(words)
            segs = []
            pos = 0
            L = len(txt)

            while pos < L:
                earliest = None

                # italic
                idx = txt.lower().find(ITALIC_PHRASE.lower(), pos)
                if idx != -1:
                    earliest = (idx, idx+len(ITALIC_PHRASE), ITALIC)

                # bold
                for rx in BOLD_PATTERNS:
                    m = rx.search(txt, pos)
                    if m:
                        s,e = m.start(), m.end()
                        if earliest is None or s < earliest[0]:
                            earliest = (s,e,BOLD)

                if not earliest:
                    rest = txt[pos:].strip()
                    if rest:
                        for w in rest.split():
                            segs.append((w, BODY))
                    break

                s,e,font = earliest

                before = txt[pos:s].strip()
                if before:
                    for w in before.split():
                        segs.append((w,BODY))

                special = txt[s:e]
                for w in special.split():
                    segs.append((w,font))

                pos = e

            return segs

        # ---------------- JUSTIFIED DRAW ----------------
        def draw_justified(segs, yy):
            if len(segs) == 1:
                w,f = segs[0]
                can.setFont(f, F_SIZE)
                can.drawString(LEFT, yy, w)
                return

            total = sum(stringWidth(w,f,F_SIZE) for w,f in segs)
            rem = max_width - total
            gaps = len(segs) - 1
            gap = rem / gaps

            x = LEFT
            for i,(w,f) in enumerate(segs):
                can.setFont(f, F_SIZE)
                can.drawString(x, yy, w)
                x += stringWidth(w,f,F_SIZE)
                if i != len(segs)-1:
                    x += gap

        # ---------------- PARAGRAPH ENGINE ----------------
        def paragraph(text):
            nonlocal y
            text = text.replace("\r","")

            parts=[]
            for line in text.split("\n"):
                words = line.split()
                if words:
                    parts.extend(words)
                parts.append("\n")

            if parts[-1] == "\n":
                parts.pop()

            words = parts
            curr=[]

            while words:
                t = words.pop(0)

                if t == "\n":
                    if curr:
                        seg = build_segments(curr)
                        draw_justified(seg, y)
                        y -= LINE
                        curr=[]
                    else:
                        y -= LINE
                    continue

                test = curr + [t]
                test_line = " ".join(test)

                if stringWidth(test_line, BODY, F_SIZE) <= max_width:
                    curr = test
                    if not words:
                        can.setFont(BODY,F_SIZE)
                        can.drawString(LEFT,y," ".join(curr))
                        y -= LINE + GAP
                        return
                else:
                    seg = build_segments(curr)
                    draw_justified(seg, y)
                    y -= LINE
                    curr=[]
                    words.insert(0,t)

            y -= GAP

        # ---------------- PARAGRAPHS ----------------
        paragraph("Congratulations!")

        paragraph(
            f"We are pleased to offer you the position of {role} at Swizosoft (OPC) Private Limited for a period of {duration}."
        )
        
        paragraph(
            f"This internship is a {intern_type} designed to help students gain hands-on project\n"
            " experience and develop industry-ready skills in their respective domains. You will be assigned "
            "project-based tasks to work on from your own location, under the guidance of our mentors and "
            "coordinators."
        )

        paragraph(
            "Our goal is to ensure that you learn through real-time project execution rather than classroom "
            "sessions — allowing you to experience how actual software projects are managed in the IT industry."
        )

        paragraph(
            "We are not so excited to have you join Team Swizosoft (OPC) Private Limited, and we look forward to your "
            "active contribution, learning, and growth throughout this journey."
        )

        # ---------------- SIGNATURE ----------------
        y -= 10
        can.setFont(BOLD, F_SIZE)
        can.drawString(LEFT, y, "Mr. Aditya Madhukar Bhat")
        y -= 18
        can.drawString(LEFT, y, "Director, Swizosoft (OPC) Private Limited")

        # ---------------- MERGE PDF ----------------
        can.save()
        buf.seek(0)
        overlay = PdfReader(buf)
        page.merge_page(overlay.pages[0])

        writer.add_page(page)
        for i in range(1, len(reader.pages)):
            writer.add_page(reader.pages[i])

        os.makedirs(GENERATED_PATH, exist_ok=True)
        fname = ref_no.replace("/", "_") + ".pdf"
        out = os.path.join(GENERATED_PATH, fname)

        with open(out, "wb") as f:
            writer.write(f)

        return out, ref_no
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return None, None

@app.route("/generate-offer", methods=["POST"])
def generate_offer():

    # Input
    name = request.form.get("candidate", "").strip()
    usn = request.form.get("usn", "").strip()
    college = request.form.get("college", "").strip()
    email = request.form.get("email", "").strip()
    role = request.form.get("role", "").strip()
    duration = request.form.get("month", "").strip()
    intern_type = request.form.get("intern_type", "").strip()

    pdf_path, ref_no = generate_offer_pdf(name, usn, college, email, role, duration, intern_type)
    
    if pdf_path and os.path.exists(pdf_path):
        return send_file(pdf_path, as_attachment=True)
    else:
        return "Failed to generate offer letter", 500

@app.route("/api/generate-offer", methods=["POST"])
def api_generate_offer():
    """API endpoint to generate offer letter automatically from admin app"""
    try:
        data = request.get_json()
        
        # Extract parameters
        name = data.get("candidate", data.get("name", "")).strip()
        usn = data.get("usn", "").strip()
        college = data.get("college", "").strip()
        email = data.get("email", "").strip()
        role = data.get("role", "").strip()
        duration = data.get("month", data.get("duration", "3 months")).strip()
        intern_type = data.get("intern_type", data.get("internship_type", "")).strip()

        if not all([name, usn, college, email, role, intern_type]):
            return {
                'success': False,
                'error': 'Missing required fields: name, usn, college, email, role, internship_type'
            }, 400

        pdf_path, ref_no = generate_offer_pdf(name, usn, college, email, role, duration, intern_type)
        
        if not pdf_path or not os.path.exists(pdf_path):
            return {'success': False, 'error': 'Failed to generate PDF'}, 500

        # Read the PDF file and convert to base64 for response
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
        
        import base64
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
        
        return {
            'success': True,
            'message': 'Offer letter generated successfully',
            'reference_number': ref_no,
            'filename': os.path.basename(pdf_path),
            'pdf_data': pdf_base64
        }, 200

    except Exception as e:
        print(f"API error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }, 500

# ------------------ RUN APP ------------------
if __name__ == "__main__":
    app.run(debug=True)
