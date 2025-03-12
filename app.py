import json
import os
from modules.ocr_extraction import extract_text_from_pdf, extract_text_from_image
from modules.llm_structuring import structure_cv_json

# Définir le fichier PDF
pdf_path = r"CV\CV Maxence Liogier.jpg"

# Extraction OCR du texte depuis le PDF ou l'image
if pdf_path.endswith(".pdf"):
    ocr_text = extract_text_from_pdf(pdf_path)
elif pdf_path.endswith((".jpg", ".jpeg", ".png")):
    ocr_text = extract_text_from_image(pdf_path)
else:
    raise ValueError("Le fichier doit être un PDF ou une image (JPG, JPEG, PNG).")

if ocr_text:
    print("Texte OCR extrait.")

# Structuration JSON
structured_data = structure_cv_json(ocr_text)
print("Structuration JSON effectuée.")

# Sauvegarde en JSON
output_path = "output/parsed_cv.json"
os.makedirs("output", exist_ok=True)

with open(output_path, "w", encoding="utf-8") as json_file:
    json.dump(structured_data, json_file, ensure_ascii=False, indent=4)

print(f"Résultat sauvegardé sous {output_path}.")
