from modules.user_utils import register_user
from modules.cv_utils import add_cv_to_user
from modules.ocr_extraction import extract_text_from_pdf
from modules.llm_structuring import structure_cv_json

# 📌 Infos utilisateur + Fichier CV
USER_EMAIL = "test@email.com"
USER_PASSWORD = "test123"
USER_NAME = "test"
PDF_PATH = "data/CV-JOMAA.pdf"

# 📌 Pipeline : Création utilisateur → Extraction du CV → Attribution du CV
def process_user_and_cv(email, password, user_name, pdf_path):
    print(f"👤 Vérification ou création de l'utilisateur : {email}")
    
    # 📌 Vérifier si l'utilisateur existe, sinon le créer
    user_id = register_user(email, password,user_name)

    if not user_id:
        print("✅ L'utilisateur existe déjà, on continue avec l'ajout du CV.")

    print("📄 Extraction du texte OCR depuis le CV...")
    ocr_text = extract_text_from_pdf(pdf_path)

    print("🤖 Structuration du CV avec Mistral-8B...")
    structured_cv = structure_cv_json(ocr_text)

    print(f"💾 Attribution du CV à {email} dans MongoDB Atlas...")
    success = add_cv_to_user(email, structured_cv)

    if success:
        print("🚀 CV attribué avec succès !")
    else:
        print("❌ Échec : utilisateur introuvable ou CV déjà existant.")

# 📌 Exécuter le script
if __name__ == "__main__":
    process_user_and_cv(USER_EMAIL, USER_PASSWORD, USER_NAME, PDF_PATH)
