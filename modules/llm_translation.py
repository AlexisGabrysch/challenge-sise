from http import client
import json
import time

from mistralai import Mistral

from config import API_KEY

client = Mistral(api_key=API_KEY)

def translate_cv_json(cv_json: dict) -> dict:
    """
    Traduit le JSON structuré en français ou en anglais.

    :param cv_json: Dictionnaire JSON structuré
    :return: Deux JSONs (un en français, un en anglais)
    """
    max_retries = 5
    retry_delay = 1

    for attempt in range(max_retries):
        try:
            translation_response = client.chat.complete(
                model="ministral-8b-latest",
                messages=[
                    {
                        "role": "user",
                        "content": f'''
Translate the following JSON into English if it is in French, or into French if it is in English.
The structure of the JSON must be **kept intact**.
You should only add one "original_language" field to the JSON which takes "fr" or "en".

<BEGIN_JSON>
{json.dumps(cv_json, indent=4)}
<END_JSON>
'''
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0
            )
            translated_dict = json.loads(translation_response.choices[0].message.content)
            break
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise

    original_language = translated_dict.get("original_language", "unknown")

    if original_language == "fr":
        print("✅ Le CV original était en français.")
        return cv_json, translated_dict  # cv_fr = original, cv_en = traduit
    elif original_language == "en":
        print("✅ Le CV original était en anglais.")
        return translated_dict, cv_json  # cv_fr = traduit, cv_en = original
    else:
        print("⚠️ Langue non détectée correctement, enregistrement par défaut.")
        return cv_json, translated_dict  # On garde une structure par défaut