import os
import json
import re
import pandas as pd
import pdfplumber

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

# TRAIN MODEL

data = pd.read_csv("train_data.csv")

model = Pipeline([
    ("tfidf", TfidfVectorizer(stop_words="english")),
    ("nb", MultinomialNB())
])

model.fit(data["text"], data["category"])


# TEXT PREPROCESSING

def preprocess(text):
    text = text.lower()

    text = re.sub(r'[^a-zA-Z\s]', ' ', text)

    text = re.sub(r'\s+', ' ', text)

    return text.strip()


# PDF TEXT EXTRACTION

def extract_text(pdf_path):

    try:
        with pdfplumber.open(pdf_path) as pdf:

            text = ""

            for page in pdf.pages:
                page_text = page.extract_text()

                if page_text:
                    text += page_text + " "

        if not text.strip():
            raise ValueError("PDF contains no readable text")

        return text

    except Exception as e:
        raise Exception(str(e))


# CLASSIFY PDFs

pdf_folder = "pdfs"

results = []

for file in os.listdir(pdf_folder):

    if not file.endswith(".pdf"):
        continue

    pdf_path = os.path.join(pdf_folder, file)

    try:

        text = extract_text(pdf_path)

        clean_text = preprocess(text)

        prediction = model.predict([clean_text])[0]

        confidence = max(model.predict_proba([clean_text])[0])

        results.append({
            "file_name": file,
            "category": prediction,
            "confidence": round(float(confidence), 3)
        })

        print(f"{file} -> {prediction}")

    except Exception as e:

        results.append({
            "file_name": file,
            "category": "ERROR",
            "confidence": 0,
            "error": str(e)
        })

        print(f"{file} -> ERROR")


# SAVE OUTPUT

pd.DataFrame(results).to_csv(
    "output.csv",
    index=False
)

with open("output.json", "w") as f:
    json.dump(results, f, indent=4)

print("\nClassification Completed!")

