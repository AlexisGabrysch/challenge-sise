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
                       "content": f'''
This is the OCR-extracted text from a resume, formatted in Markdown.  
The OCR was performed on two versions of the document:  
- **Original PDF** (captures standard text)  
- **Processed PDF (Black & White)** (extracts hidden text due to background colors)  

<BEGIN_PDF_OCR>
{ocr_text}
<END_PDF_OCR>

### Task:
Convert this into a **clean, structured JSON** following the schema below.  
Extract only the information **explicitly available**—**do not infer or generate missing data**.  
If a field is missing, leave it empty but keep the structure intact.

If a professional **title** is not explicitly mentioned, infer it based on education, experience, and skills, using industry-standard terms.  
If a **summary** is missing, generate a concise 2-line summary highlighting expertise and career goals **in the same language (French or English) as the input**.

### Expected JSON Structure:
{{
    "first_name": "Candidate's first name",
    "last_name": "Candidate's last name",
    "email": "Candidate's email",
    "phone": "Candidate's phone number",
    "address": "Full postal address",
    "title": "Professional title (e.g., 'Data Scientist', 'Software Engineer')",
    "summary": "Professional summary or objective",
    "driving_license": "Type of driving license (if mentioned, else empty)",
    "education": [
        {{"year": 2020, "school": "University Name", "degree": "Degree", "details": "Optional details"}}
    ],
    "work_experience": [
        {{"job_title": "Title", "company": "Company", "duration": "Start - End", "description": "Responsibilities"}}
    ],
    "projects": [
        {{"title": "Project title", "type": "Academic | Volunteer | Other", "description": "Details", "technologies_used": ["Tech1", "Tech2"]}}
    ],
    "hobbies": ["List of hobbies"],
    "languages": {{"Language1": "Proficiency", "Language2": "Proficiency"}},
    "skills": ["List of skills"],
    "certifications": ["List of certifications"]
}}

### Additional Instructions:
1. **Do not add or infer data**—use only what is explicitly found.  
2. **Eliminate redundant entries** (keep unique mentions of jobs, projects, or skills).  
3. **Ensure correct formatting**—no extra spaces or unnecessary characters.  
4. **Output must be a strict JSON object with no additional text or explanations.**  
5. **If both OCR versions contain similar content, select the clearest version.**
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
