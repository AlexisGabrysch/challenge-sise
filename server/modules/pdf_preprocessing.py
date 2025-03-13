import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image
from io import BytesIO

def remove_background_from_pdf(pdf_path: str, output_path: str):
    """
    Convertit un PDF couleur en noir et blanc et enlève le fond coloré.
    """
    doc = fitz.open(pdf_path)
    new_doc = fitz.open()

    for page_num in range(len(doc)):
        page = doc[page_num]

        # 📌 Convertir la page en image (résolution augmentée)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # 📌 Convertir en niveaux de gris (noir et blanc)
        gray = img.convert("L")

        # 📌 Convertir l’image PIL en tableau numpy
        img_np = np.array(gray)

        # 📌 Appliquer un seuillage adaptatif pour enlever les fonds colorés
        binary = cv2.adaptiveThreshold(
            img_np, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # 📌 Convertir numpy array en image PIL
        processed_img = Image.fromarray(binary)

        # 📌 Convertir l’image PIL en bytes
        img_bytes = BytesIO()
        processed_img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        # 📌 Ajouter la page nettoyée dans le nouveau PDF
        new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(new_page.rect, stream=img_bytes.getvalue())

    # 📌 Sauvegarder le PDF nettoyé
    new_doc.save(output_path)
    new_doc.close()
    doc.close()

    print(f"✅ Fond du PDF nettoyé et enregistré dans {output_path}")
