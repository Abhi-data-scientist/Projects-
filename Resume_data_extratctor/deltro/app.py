import os
import re
import pandas as pd
from pypdf import PdfReader


# -----------------------------
# PDF Text Extraction
# -----------------------------
def extract_text_from_pdf(pdf_path):
    text = ""

    try:
        reader = PdfReader(pdf_path)

        for page in reader.pages:
            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")

    return text


# -----------------------------
# Name Extraction
# -----------------------------
def extract_name(text):

    lines = text.split("\n")

    for line in lines[:10]:

        candidate = line.strip()

        if not candidate:
            continue

        if "@" in candidate:
            continue

        if "linkedin" in candidate.lower():
            continue

        if re.search(r"\d", candidate):
            continue

        words = candidate.split()

        if 2 <= len(words) <= 4:
            return candidate

    return ""


# -----------------------------
# Email
# -----------------------------
def extract_email(text):

    pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"

    match = re.search(pattern, text)

    return match.group() if match else ""


# -----------------------------
# Phone
# -----------------------------
def extract_phone(text):

    pattern = r"(\+?\d[\d\s\-]{8,15})"

    match = re.search(pattern, text)

    return match.group().strip() if match else ""


# -----------------------------
# LinkedIn
# -----------------------------
def extract_linkedin(text):

    pattern = r"(https?:\/\/)?(www\.)?linkedin\.com\/[A-Za-z0-9\/\-\_\.]+"

    match = re.search(pattern, text, re.IGNORECASE)

    return match.group() if match else ""


# -----------------------------
# Department
# -----------------------------
def extract_department(text):

    pattern = r"department\s*[:\-]\s*(.+)"

    match = re.search(pattern, text, re.IGNORECASE)

    return match.group(1).strip() if match else ""


# -----------------------------
# Experience
# -----------------------------
def extract_experience(text):

    pattern = r"(\d+\+?\s*(?:years|year|yrs|yr))"

    match = re.search(pattern, text, re.IGNORECASE)

    return match.group(1) if match else ""


# -----------------------------
# Skills Section Extraction
# -----------------------------
def extract_skills(text):

    lines = text.split("\n")

    start_idx = -1

    headings = [
        "experience",
        "education",
        "project",
        "projects",
        "certification",
        "certifications",
        "achievement",
        "achievements"
    ]

    for i, line in enumerate(lines):

        if "skills" in line.lower():
            start_idx = i + 1
            break

    if start_idx == -1:
        return ""

    skills_lines = []

    for line in lines[start_idx:]:

        clean = line.strip()

        if not clean:
            continue

        lower = clean.lower()

        if any(h in lower for h in headings):
            break

        skills_lines.append(clean)

    return " | ".join(skills_lines)


# -----------------------------
# Main Parser
# -----------------------------
def parse_resume(pdf_path):

    text = extract_text_from_pdf(pdf_path)

    return {
        "name": extract_name(text),
        "contact": extract_phone(text),
        "email": extract_email(text),
        "linkedin": extract_linkedin(text),
        "experience": extract_experience(text),
        "department": extract_department(text),
        "skills": extract_skills(text)
    }


# -----------------------------
# Folder Processing
# -----------------------------
folder_path = "resumes"   # change folder path

all_data = []

for file in os.listdir(folder_path):

    if file.lower().endswith(".pdf"):

        pdf_path = os.path.join(folder_path, file)

        row = parse_resume(pdf_path)

        row["file_name"] = file

        all_data.append(row)

        print(f"Processed -> {file}")


# -----------------------------
# CSV Export
# -----------------------------
df = pd.DataFrame(all_data)

df.to_csv("resume_dataset.csv", index=False)

print("\nCSV Saved Successfully")
print(df.head())