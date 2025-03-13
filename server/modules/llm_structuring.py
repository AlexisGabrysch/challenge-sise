import json
import time
from mistralai import Mistral
from .config import API_KEY

def structure_cv_json(ocr_text_original: str , ocr_text_baw: str) -> dict:
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

<BEGIN_Original PDF>
{ocr_text_original}
<END_Original PDF>

<BEGIN_Black & White PDF>
{ocr_text_baw}
<END_Black & White PDF>
### Task:
Convert this into a well-structured JSON response following the exemple schema key, value below.  
All keys must be present in the JSON response, even if the value is None.
If a field is missing or not found in the text (e.g., 'email', 'phone', 'address'), the value is None.
determine their most appropriate title (e.g., 'Master’s Student in Data Science', 'AI Researcher', 'Professor', etc.).
If a specific title is not provided, the value is None. 
For the summary, extract the most relevant professional summary or objective statement from the text in french. 

### Expected JSON Structure:
{{
    "first_name": Value,
    "last_name": Value,
    "email": Value,
    "phone": Value,
    "address": "Value,
    "title": Value,
    "summary": Value,
    "driving_license": Value,
    "education": [
        {{
            "year": Value,
            "school": Value,
            "degree": Value,
            "details": Value
        }}
    ],
    "work_experience": [
        {{
            "job_title": Value,
            "company": Value,
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
1. **Do not invent or infer any missing information.** Extract only what is explicitly found in on of the OCR text.  
2. **Ensure the extracted text is formatted cleanly** (no extra spaces, unnecessary characters, or formatting errors).  
3. **Use lists for multiple entries and maintain correct JSON formatting.**  
4. **The output must be strictly a JSON object with no extra commentary or explanations.**  
5. **If the same information appears in both OCR results (original and black & white), select the clearest version.**  
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