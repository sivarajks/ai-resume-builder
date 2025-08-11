import os
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import openai
from io import BytesIO
from datetime import datetime
from markupsafe import Markup

# PDF and DOCX libraries
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from docx import Document
from docx.shared import Pt

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "change-me")

openai.api_key = os.getenv("OPENAI_API_KEY")  # must be set in environment

SYSTEM_INSTRUCTION = (
    "You are a helpful assistant that writes clear, concise, professional resume content. "
    "Return sections labeled: Summary, Experience, Skills, Education, Additional (optional). "
    "Use short bullet points under Experience focused on achievements."
)

def build_prompt(form):
    name = form.get("name", "").strip()
    title = form.get("job_title", "").strip()
    summary_input = form.get("summary", "").strip()
    skills = form.get("skills", "").strip()
    experience = form.get("experience", "").strip()
    education = form.get("education", "").strip()
    extra = form.get("extra", "").strip()

    prompt = f"""
Create an ATS-friendly resume content for the following candidate.

Name: {name}
Target job title: {title}

User-provided summary/objective:
{summary_input}

Skills (comma or newline separated):
{skills}

Work experience (one job per line, include company, years, role, short achievements):
{experience}

Education:
{education}

Extra (certifications, projects, languages):
{extra}

Produce:
- A short professional summary paragraph.
- Experience section with 3-5 bullet points per role focusing on accomplishments (use numbers where possible).
- Skills as a concise comma-separated line.
- Education lines.

Return plain text with clear section headers: Summary, Experience, Skills, Education.
"""
    return prompt

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        form = request.form
        if not form.get("name") or not form.get("job_title"):
            flash("Please enter at least name and target job title.")
            return redirect(url_for("index"))

        prompt = build_prompt(form)
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": SYSTEM_INSTRUCTION},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=800
            )
        except Exception as e:
            flash(f"OpenAI API error: {e}")
            return redirect(url_for("index"))

        resume_text = response.choices[0].message["content"].strip()
        data = {
            "name": form.get("name"),
            "job_title": form.get("job_title"),
            "resume_text": resume_text,
            "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        }
        return render_template("result.html", **data)

    return render_template("index.html")

def generate_pdf_bytes(name, job_title, resume_text):
    """Create an ATS-friendly PDF in memory using ReportLab."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER,
                            leftMargin=72, rightMargin=72, topMargin=72, bottomMargin=72)
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    normal.fontName = "Helvetica"
    normal.fontSize = 11
    normal.leading = 14

    story = []

    # Header: name and job title
    name_style = ParagraphStyle('name', parent=normal, fontSize=18, leading=22, spaceAfter=6, alignment=TA_LEFT)
    title_style = ParagraphStyle('title', parent=normal, fontSize=12, leading=14, textColor='gray', spaceAfter=12)
    story.append(Paragraph(f"<b>{name}</b>", name_style))
    story.append(Paragraph(job_title, title_style))
    story.append(Spacer(1, 6))

    # Resume body: the resume_text is plain text with section headers.
    # We'll split by lines and convert headers to bold paragraphs.
    lines = resume_text.splitlines()
    for line in lines:
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1,6))
            continue
        # Detect section headers (Summary, Experience, Skills, Education)
        if stripped.lower().endswith(":") or stripped.lower() in ("summary", "experience", "skills", "education", "additional"):
            story.append(Paragraph(f"<b>{stripped.rstrip(':')}</b>", normal))
            story.append(Spacer(1,4))
            continue
        # Bullet lines (starting with - or •)
        if stripped.startswith("-") or stripped.startswith("•"):
            bullet = stripped.lstrip("-• ").strip()
            story.append(Paragraph(f"• {bullet}", normal))
        else:
            # regular paragraph
            story.append(Paragraph(stripped, normal))

    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_docx_bytes(name, job_title, resume_text):
    """Create a simple .docx file in memory using python-docx."""
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Helvetica'
    font.size = Pt(11)

    # Header
    doc.add_heading(name, level=1)
    p = doc.add_paragraph(job_title)
    p.runs[0].italic = True
    doc.add_paragraph("")

    # Add sections by parsing resume_text
    lines = resume_text.splitlines()
    current_section = None
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # headers
        if stripped.lower().endswith(":") or stripped.lower() in ("summary", "experience", "skills", "education", "additional"):
            current_section = stripped.rstrip(':')
            doc.add_heading(current_section, level=2)
            continue
        # bullets
        if stripped.startswith("-") or stripped.startswith("•"):
            bullet = stripped.lstrip("-• ").strip()
            doc.add_paragraph(bullet, style='List Bullet')
        else:
            doc.add_paragraph(stripped)

    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

@app.route("/download-pdf", methods=["POST"])
def download_pdf():
    name = request.form.get("name", "Applicant")
    job_title = request.form.get("job_title", "")
    resume_text = request.form.get("resume_text", "")
    pdf_io = generate_pdf_bytes(name, job_title, resume_text)
    filename = f"{name.replace(' ', '_')}_Resume.pdf"
    return send_file(pdf_io, mimetype="application/pdf", as_attachment=True, download_name=filename)

@app.route("/download-docx", methods=["POST"])
def download_docx():
    name = request.form.get("name", "Applicant")
    job_title = request.form.get("job_title", "")
    resume_text = request.form.get("resume_text", "")
    docx_io = generate_docx_bytes(name, job_title, resume_text)
    filename = f"{name.replace(' ', '_')}_Resume.docx"
    return send_file(docx_io, mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                     as_attachment=True, download_name=filename)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
