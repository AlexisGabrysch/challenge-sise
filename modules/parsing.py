from mistralai import Mistral
import os
import json
from mistralai import DocumentURLChunk , ImageURLChunk, TextChunk
from pathlib import Path


api_key = os.environ["MISTRAL_API_KEY"]

client = Mistral(api_key=api_key)

pdf_file = Path("data/CV-JOMAA.pdf")

uploaded_pdf = client.files.upload(
    file={
        "file_name": pdf_file.stem,
        "content": pdf_file.read_bytes(),
    },
    purpose="ocr"
)  
signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id,expiry=1)

pdf_response = client.ocr.process(document=DocumentURLChunk(document_url=signed_url.url),model="mistral-ocr-latest",include_image_base64=True)

all_markdown_content = "\n\n".join(page.markdown for page in pdf_response.pages)

import time

max_retries = 5
retry_delay = 1

for attempt in range(max_retries):
    try:
        chat_response = client.chat.complete(
            model="ministral-8b-latest",
            messages=[
                {
                    "role": "user",
                    "content": "This is pdf's OCR in markdown format :\n<BEGIN_PDF_OCR>\n" + all_markdown_content + "\n<END_PDF_OCR>\n convert this into a sensible structured json response. The output should be strictly json with no extra commentary",
                },
            ],
            response_format={"type": "json_object"},
            temperature=0
        )
        break
    except models.SDKError as e:
        if e.status_code == 429 and attempt < max_retries - 1:
            time.sleep(retry_delay)
            retry_delay *= 2
        else:
            raise

response_dict = json.loads(chat_response.choices[0].message.content)
json_string = json.dumps(response_dict, indent=4)
print(json_string)