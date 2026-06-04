import os 
from extract_text import extract_text
from text_preprocessing import text_preprocess
from model import model
import pandas as pd 

pdf_folder = 'pdfs'
results = []
for file in os.listdir(pdf_folder):
    try:
        if not file.endswith('.pdf'):
            print(f"{file}: Not PDF File")
            continue

        pdf_path = os.path.join(pdf_folder, file) 

        extracted_text = extract_text(pdf_path)  
        if not extracted_text:
            print('Empty PDF')
            continue

        clean_text = text_preprocess(extracted_text)
        prediction = model.predict([clean_text])[0]
        confidence = max(
            model.predict_proba([clean_text])[0]
        )
        if confidence < 0.70:
            prediction = "Unknown"

        results.append({
            "file_name": file,
            "category": prediction,
            "confidence": round(float(confidence), 3)
        })

    except Exception as e:

        results.append({
            "file_name": file,
            "category": "ERROR",
            "confidence": 0,
            "error": str(e)
        })
    
output = pd.DataFrame(results)
output.to_csv(
    "output.csv",
    index=False
)

print(output.head(5))

print("\nClassification Completed!")
