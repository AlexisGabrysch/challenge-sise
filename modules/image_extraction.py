from pdf2image import convert_from_path
import cv2
import numpy as np
import os

def extract_photo_from_pdf(pdf_path):
    images = convert_from_path(pdf_path)
    
    if not images:
        return None
    
    first_page = np.array(images[0])
    cv_image = cv2.cvtColor(first_page, cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w > 100 and h > 100:  # Exclure les petits logos
            photo = cv_image[y:y+h, x:x+w]
            output_path = os.path.join("static", "photo_extrait.png")
            cv2.imwrite(output_path, photo)
            return output_path
    
    return None


# Extraction de la photo
photo_path = extract_photo_from_pdf("data/CV-JOMAA.pdf")

print(photo_path)
