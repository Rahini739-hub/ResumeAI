from flask import Flask, render_template, request, redirect, url_for, session
from pypdf import PdfReader
import os
import re
import sys

app = Flask(__name__)

app.secret_key = "resumeai-secret-key-2026"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


SKILLS = [
    "Python", "Java", "C++", "C", "JavaScript", "HTML", "CSS",
    "SQL", "MySQL", "MongoDB", "Flask", "Django", "React",
    "Node.js", "Machine Learning", "Deep Learning",
    "Artificial Intelligence", "Data Science", "Data Analysis",
    "Power BI", "Tableau", "Excel", "Git", "GitHub", "AWS",
    "TensorFlow", "PyTorch", "Pandas", "NumPy", "OpenCV",
    "Scikit-learn", "Streamlit", "Matplotlib"
]


def detect_skills(text):
    text_lower = text.lower()
    detected = []

    for skill in SKILLS:
        pattern = r"(?<!\w)" + re.escape(skill.lower()) + r"(?!\w)"

        if re.search(pattern, text_lower):
            detected.append(skill)

    return detected


def job_match(resume_text, job_description):
    job_skills = detect_skills(job_description)
    resume_lower = resume_text.lower()

    matching_skills = []
    missing_skills = []

    for skill in job_skills:
        pattern = r"(?<!\w)" + re.escape(skill.lower()) + r"(?!\w)"

        if re.search(pattern, resume_lower):
            matching_skills.append(skill)
        else:
            missing_skills.append(skill)

    if job_skills:
        match_percentage = round(
            len(matching_skills) / len(job_skills) * 100
        )
    else:
        match_percentage = 0

    return {
        "match_percentage": match_percentage,
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
        "job_skills": job_skills
    }


def analyze_resume(text):
    text_lower = text.lower()
    detected_skills = detect_skills(text)

    education_patterns = [
        r"\bb\.?\s*tech\b",
        r"\bb\.?\s*e\b",
        r"\bbachelor\b",
        r"\bengineering\b",
        r"\bcomputer science\b",
        r"\binformation technology\b",
        r"\bartificial intelligence\b",
        r"\bdata science\b",
        r"\bm\.?\s*tech\b",
        r"\bm\.?\s*e\b",
        r"\bmaster\b",
        r"\bmba\b",
        r"\bdegree\b"
    ]

    education_found = []

    for pattern in education_patterns:
        matches = re.findall(pattern, text_lower)

        if matches:
            education_found.append(matches[0])

    education_found = list(dict.fromkeys(education_found))

    experience_patterns = [
        r"\b\d+\+?\s*years?\b",
        r"\binternship\b",
        r"\bintern\b",
        r"\bexperience\b",
        r"\bdeveloper\b",
        r"\bsoftware engineer\b"
    ]

    experience_found = []

    for pattern in experience_patterns:
        matches = re.findall(pattern, text_lower)

        if matches:
            experience_found.extend(matches)

    experience_found = list(dict.fromkeys(experience_found))

    sections = {
        "contact": False,
        "skills": False,
        "education": False,
        "experience": False,
        "projects": False,
        "certifications": False
    }

    if re.search(r"\b[\w\.-]+@[\w\.-]+\.\w+\b", text):
        sections["contact"] = True

    if "skill" in text_lower:
        sections["skills"] = True

    if "education" in text_lower:
        sections["education"] = True

    if "experience" in text_lower or "internship" in text_lower:
        sections["experience"] = True

    if "project" in text_lower:
        sections["projects"] = True

    if "certification" in text_lower or "certificate" in text_lower:
        sections["certifications"] = True

    score = 0

    score += min(len(detected_skills) * 3, 30)

    for value in sections.values():
        if value:
            score += 8

    if sections["contact"]:
        score += 5

    word_count = len(text.split())

    if word_count >= 300:
        score += 10

    if word_count >= 500:
        score += 5

    score = min(score, 100)

    suggestions = []

    if len(detected_skills) < 5:
        suggestions.append(
            "Add more relevant technical skills."
        )

    if not sections["projects"]:
        suggestions.append(
            "Add a Projects section."
        )

    if not sections["certifications"]:
        suggestions.append(
            "Consider adding relevant certifications."
        )

    if not sections["experience"]:
        suggestions.append(
            "Add internship or work experience if available."
        )

    if word_count < 300:
        suggestions.append(
            "Your resume appears short. Add more relevant details."
        )

    if not suggestions:
        suggestions.append(
            "Your resume contains the main sections expected by an ATS."
        )

    return {
        "score": score,
        "skills": detected_skills,
        "education": education_found,
        "experience": experience_found,
        "sections": sections,
        "word_count": word_count,
        "suggestions": suggestions
    }


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_resume():
    if "resume" not in request.files:
        return "No resume uploaded"

    file = request.files["resume"]

    if file.filename == "":
        return "No file selected"

    if not file.filename.lower().endswith(".pdf"):
        return "Please upload a PDF file"

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file.filename
    )

    file.save(file_path)

    session["resume_filename"] = file.filename

    return redirect(url_for("result_page"))


@app.route("/result")
def result_page():
    filename = session.get("resume_filename")

    if not filename:
        return redirect(url_for("home"))

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    if not os.path.exists(file_path):
        session.pop("resume_filename", None)
        return redirect(url_for("home"))

    try:
        reader = PdfReader(file_path)

        resume_text = ""

        for page in reader.pages:
            page_text = page.extract_text()

            if page_text:
                resume_text += page_text + "\n"

        resume_text = (
            resume_text
            .encode("utf-8", errors="replace")
            .decode("utf-8", errors="replace")
        )

    except Exception as e:
        return f"Error reading PDF: {e}"

    result = analyze_resume(resume_text)

    return render_template(
        "result.html",
        result=result,
        resume_text=resume_text
    )


@app.route("/job-match", methods=["POST"])
def job_matching():
    resume_text = request.form.get("resume_text", "")
    job_description = request.form.get("job_description", "")

    resume_text = (
        resume_text
        .encode("utf-8", errors="replace")
        .decode("utf-8", errors="replace")
    )

    job_description = (
        job_description
        .encode("utf-8", errors="replace")
        .decode("utf-8", errors="replace")
    )

    result = job_match(
        resume_text,
        job_description
    )

    return render_template(
        "job_match.html",
        result=result,
        job_description=job_description
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )