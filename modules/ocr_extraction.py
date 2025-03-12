from mistralai import Mistral
from mistralai import DocumentURLChunk
from pathlib import Path
from config import API_KEY

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Envoie un PDF à Mistral OCR et récupère le texte en format Markdown.
    
    :param pdf_path: Chemin du fichier PDF
    :return: Texte extrait en Markdown
    """
    client = Mistral(api_key=API_KEY)
    pdf_file = Path(pdf_path)

    # Upload du PDF
    uploaded_pdf = client.files.upload(
        file={
            "file_name": pdf_file.stem,
            "content": pdf_file.read_bytes(),
        },
         purpose="ocr"
    )

    # Générer URL signée
    signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id, expiry=1)

    # Appel OCR
    pdf_response = client.ocr.process(
        document=DocumentURLChunk(document_url=signed_url.url),
        model="mistral-ocr-latest",
        include_image_base64=True
    )

    # Récupérer tout le texte Markdown
    all_markdown_content = "\n\n".join(page.markdown for page in pdf_response.pages)
    
    return all_markdown_content
