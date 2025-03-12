import json
import os
from modules.ocr_extraction import extract_text_from_pdf
from modules.llm_structuring import structure_cv_json

# Définir le fichier PDF
pdf_path = "data/CV-JOMAA.pdf"

# Extraction OCR
ocr_text = extract_text_from_pdf(pdf_path)
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
