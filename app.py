import time
from modules.pdf_preprocessing import remove_background_from_pdf
from modules.user_utils import register_user
from modules.cv_utils import add_cv_to_user
from modules.ocr_extraction import extract_text_from_pdf
from modules.llm_structuring import structure_cv_json

# 📌 Infos utilisateur + Fichier CV
USER_EMAIL = "alexiiiiis@email.com"
USER_PASSWORD = "alexiiiiis"
USER_NAME = "alexiiis"
PDF_PATH = "CV/CV_Alexis_DARDELET_stage_data_analyst.pdf"
CLEAN_PDF_PATH = "CV/CV_Alexis_DARDELET_stage_data_analyst-clean.pdf"

# 📌 Pipeline : Création utilisateur → Extraction OCR des 2 versions → Fusion → Attribution du CV
def process_user_and_cv(email, password, user_name, pdf_path):
    print(f"👤 Vérification ou création de l'utilisateur : {email}")

    # 📌 Vérifier si l'utilisateur existe, sinon le créer
    user_id = register_user(email, password, user_name)

    if not user_id:
        print("✅ L'utilisateur existe déjà, on continue avec l'ajout du CV.")

    print("🎨 Suppression des couleurs de fond du CV...")
    remove_background_from_pdf(pdf_path, CLEAN_PDF_PATH)

    print("📄 Extraction du texte OCR depuis le CV (Original)...")
    try:
        ocr_text_original = extract_text_from_pdf(pdf_path)
    except Exception as e:
        print(f"❌ Erreur OCR Original : {e}")
        ocr_text_original = ""

    # 📌 Attente pour éviter l'erreur 429
    time.sleep(2)

    print("📄 Extraction du texte OCR depuis le CV (Noir et Blanc)...")
    try:
        ocr_text_clean = extract_text_from_pdf(CLEAN_PDF_PATH)
    except Exception as e:
        print(f"❌ Erreur OCR Noir & Blanc : {e}")
        ocr_text_clean = ""

    # 📌 Fusion des deux OCRs
    combined_text = f"""
    --- OCR FROM ORIGINAL PDF ---
    {ocr_text_original}

    --- OCR FROM CLEANED PDF ---
    {ocr_text_clean}
    """

    print("🤖 Structuration du CV avec Mistral-8B...")
    structured_cv = structure_cv_json(combined_text)

    print(f"💾 Attribution du CV à {email} dans MongoDB Atlas...")
    success = add_cv_to_user(email, structured_cv)

    if success:
        print("🚀 CV attribué avec succès !")
    else:
        print("❌ Échec : utilisateur introuvable ou CV déjà existant.")

# 📌 Exécuter le script
if __name__ == "__main__":
    process_user_and_cv(USER_EMAIL, USER_PASSWORD, USER_NAME, PDF_PATH)
