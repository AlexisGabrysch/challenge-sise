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

pdf_response = client.ocr.process(document=DocumentURLChunk(document_url=signed_url.url),model="mistral-ocr-latest",include_image_base64=True,image_limit=0,
image_min_size=0)

response_dict = json.loads(pdf_response.json())
json_string = json.dumps(response_dict, indent=4)

print(json_string)