import json
import time
from mistralai import Mistral
from .config import API_KEY

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
                        "content": f'''
    This is the OCR-extracted text from a resume, formatted in Markdown:
    <BEGIN_PDF_OCR>
    {ocr_text}
    <END_PDF_OCR>

    Convert this into a well-structured JSON response following the exact schema below.  
    Extract as much relevant information as possible from the resume.  
    If any information is missing, leave the field empty but keep the structure intact.

    ### Expected JSON Structure:
    {{
        "first_name": "Candidate's first name",
        "last_name": "Candidate's last name",
        "email": "Candidate's email",
        "phone": "Candidate's phone number",
        "address": "Full postal address",
        "driving_license": "Type of driving license (if mentioned, else empty)",
        "education": [
            {{
                "year": 2020,
                "school": "University/School Name",
                "degree": "Degree obtained",
                "details": "Additional details (e.g., specialization, honors)"
            }}
        ],
        "work_experience": [
            {{
                "job_title": "Job title",
                "company": "Company name",
                "duration": "Start - End date",
                "description": "Key responsibilities and achievements"
            }}
        ],
        "projects": [
            {{
                "title": "Project title",
                "type": "Academic | Volunteering | Association | Other",
                "description": "Detailed description of the project",
                "technologies_used": ["Tech1", "Tech2"] (if mentioned)
            }}
        ],
        "hobbies": ["List of hobbies"],
        "languages": {{
            "Language1": "Proficiency level (e.g., Beginner, Intermediate, Fluent)",
            "Language2": "Proficiency level"
        }},
        "skills": ["List of technical and soft skills"],
        "certifications": ["List of certifications, if any"]
    }}

    ### Additional Instructions:
    1. **Extract all available information from the CV and match it to the correct fields.**  
    2. **Group all project-related experiences under `projects`, whether academic, volunteering, or associative.**  
    3. **Ensure that all extracted content is well-formatted and precise.**  
    4. **If a field is not available, leave it empty but maintain the structure.**  
    5. **Use lists for multiple entries and avoid duplicates.**  

    The output **must** be a valid JSON object **with no extra commentary or explanations**.
    '''
,
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
