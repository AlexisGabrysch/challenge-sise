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
This is the OCR-extracted text from a resume, formatted in Markdown.  
The OCR was performed on two versions of the document:  
- **Original PDF** (captures normal text)
- **Processed PDF (Black & White)** (captures text that may be hidden due to background colors)

<BEGIN_PDF_OCR>
{ocr_text}
<END_PDF_OCR>

### Task:
Convert this into a well-structured JSON response following the exact schema below.  
Ensure all extracted information is accurate, well-formatted, and **free of redundancy**.  
If a field is missing or not found in the text, **leave it empty** but **do not fabricate data**.
determine their most appropriate title (e.g., 'Master’s Student in Data Science', 'AI Researcher', 'Professor', etc.).
If a specific title is not provided, infer the best possible one based on their education, experience, and skills. 
Ensure the title is professional, relevant to their field, and aligns with common industry terminology
For the summary, extract the most relevant professional summary or objective statement from the text. 
If none is available, generate a concise two-line summary that effectively highlights their expertise and career objectives.

### Expected JSON Structure:
{{
    "first_name": "Candidate's first name (if available)",
    "last_name": "Candidate's last name (if available)",
    "email": "Candidate's email (if available)",
    "phone": "Candidate's phone number (if available)",
    "address": "Full postal address (if available)",
    "title": "Professional title (e.g., 'Data Scientist', 'Software Engineer')",
    "summary": "Professional summary or objective",
    "driving_license": "Type of driving license (if mentioned, else empty)",
    "education": [
        {{
            "year": 2020,
            "school": "University/School Name",
            "degree": "Degree obtained",
            "details": "Additional details (e.g., specialization, honors) (if available)"
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
            "description": "Detailed description of the project (if available)",
            "technologies_used": ["Tech1", "Tech2"] (if mentioned)
        }}
    ],
    "hobbies": ["List of hobbies (if mentioned)"],
    "languages": {{
        "Language1": "Proficiency level (e.g., Beginner, Intermediate, Fluent)",
        "Language2": "Proficiency level"
    }},
    "skills": ["List of technical and soft skills (if mentioned)"],
    "certifications": ["List of certifications (if any)"]
}}

### Additional Instructions:
1. **Do not invent or infer any missing information.** Extract only what is explicitly found in the OCR text.  
2. **Avoid redundant entries.** If the same job, project, or skill appears multiple times, keep only one instance.  
3. **Ensure the extracted text is formatted cleanly** (no extra spaces, unnecessary characters, or formatting errors).  
4. **Use lists for multiple entries and maintain correct JSON formatting.**  
5. **The output must be strictly a JSON object with no extra commentary or explanations.**  
6. **If the same information appears in both OCR results (original and black & white), select the clearest version.**  
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