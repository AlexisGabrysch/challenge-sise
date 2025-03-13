import time
from modules.pdf_preprocessing import remove_background_from_pdf
from modules.user_utils import register_user
from modules.cv_utils import add_cv_to_user
from modules.ocr_extraction import extract_text_and_first_image_from_pdf, extract_text_from_pdf
from modules.llm_structuring import structure_cv_json

# 📌 Infos utilisateur + Fichier CV
USER_EMAIL = "guillaume@email.com"
USER_PASSWORD = "guillaume123"
USER_NAME = "guillaume"
PDF_PATH = "CV/cv-guillaume.pdf"
CLEAN_PDF_PATH = "CV/cv-guillaume-clean.pdf"

# 📌 Pipeline : Création utilisateur → Extraction OCR (Texte + Images) → Structuration → Attribution du CV
def process_user_and_cv(email, password, user_name, pdf_path):
    print(f"👤 Vérification ou création de l'utilisateur : {email}")

    # 📌 Vérifier si l'utilisateur existe, sinon le créer
    user_id = register_user(email, password, user_name)

    if not user_id:
        print("✅ L'utilisateur existe déjà, on continue avec l'ajout du CV.")

    print("🎨 Suppression des couleurs de fond du CV...")
    remove_background_from_pdf(pdf_path, CLEAN_PDF_PATH)

    print("📄 Extraction du texte et de la première image OCR depuis le CV (Original)...")
    try:
        ocr_result_original = extract_text_and_first_image_from_pdf(pdf_path, email)  # ✅ Texte + 1ère image seulement
        ocr_text_original = ocr_result_original["markdown"]
        first_image = ocr_result_original["image"]  # 📌 Une seule image ou None
    except Exception as e:
        print(f"❌ Erreur OCR Original : {e}")
        ocr_text_original = ""
        first_image = None

    # 📌 Attente pour éviter l'erreur 429
    time.sleep(2)

    print("📄 Extraction du texte OCR depuis le CV (Noir et Blanc) (Sans Images)...")
    try:
        ocr_text_clean = extract_text_from_pdf(CLEAN_PDF_PATH)  # ✅ Texte seulement, pas d'images
    except Exception as e:
        print(f"❌ Erreur OCR Noir & Blanc : {e}")
        ocr_text_clean = ""

    # 📌 Fusion des deux OCRs (Texte uniquement)
    combined_text = f"""
    --- OCR FROM ORIGINAL PDF ---
    {ocr_text_original}

    --- OCR FROM CLEANED PDF ---
    {ocr_text_clean}
    """

    print("🤖 Structuration du CV avec Mistral-8B...")
    structured_cv = structure_cv_json(combined_text)  # On envoie **uniquement le texte** au LLM

    print(f"💾 Enregistrement du CV et de la première image dans MongoDB Atlas...")
    structured_cv["image"] = first_image  # On stocke **uniquement la première image trouvée**

    success = add_cv_to_user(email, structured_cv)

    if success:
        print("🚀 CV et image enregistrés avec succès !")
    else:
        print("❌ Échec : utilisateur introuvable ou CV déjà existant.")

# 📌 Exécuter le script
if __name__ == "__main__":
    process_user_and_cv(USER_EMAIL, USER_PASSWORD, USER_NAME, PDF_PATH)