import json
import time
from mistralai import Mistral
from config import API_KEY

def structure_cv_json(ocr_text: str) -> dict:
    """
    Convertit le texte OCR en JSON structuré en utilisant Mistral-8B.
    
    :param ocr_text: Texte brut OCR (Markdown)
    :return: Dictionnaire JSON structuré
    """
    client = Mistral(api_key=API_KEY)
    
    max_retries = 5
    retry_delay = 1

    for attempt in range(max_retries):
        try:
            chat_response = client.chat.complete(
                model="ministral-8b-latest",
                messages=[
                    {
                        "role": "user",
                        "content": f"This is pdf's OCR in markdown format :\n<BEGIN_PDF_OCR>\n{ocr_text}\n<END_PDF_OCR>\n"
                                   "Convert this into a sensible structured JSON response. "
                                   "The output should be strictly JSON with no extra commentary.",
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0
            )
            break
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise

    response_dict = json.loads(chat_response.choices[0].message.content)
    return response_dict
