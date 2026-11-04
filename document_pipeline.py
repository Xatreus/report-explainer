"""Page-aware PDF extraction with optional OCR fallback."""
from __future__ import annotations
from io import BytesIO
from typing import Any
from report_utils import normalize_text

def extract_pdf_pages(data:bytes,*,ocr_if_empty:bool=True,language:str="eng",min_text_characters:int=24)->list[dict[str,Any]]:
 """Extract selectable text page-by-page; OCR sparse pages when optional tools exist."""
 from pypdf import PdfReader
 reader=PdfReader(BytesIO(data)); pages=[]
 for number,page in enumerate(reader.pages,1):
  text=normalize_text(page.extract_text() or ""); source="text"
  if ocr_if_empty and len(text)<min_text_characters:
   try:
    from pdf2image import convert_from_bytes
    import pytesseract
    image=convert_from_bytes(data,first_page=number,last_page=number)[0]
    ocr=normalize_text(pytesseract.image_to_string(image,lang=language))
    if len(ocr)>len(text): text,source=ocr,"ocr"
   except (ImportError,OSError): pass
  pages.append({"page":number,"text":text,"extraction":source})
 return pages

def chunk_page_records(pages:list[dict[str,Any]],*,max_words:int=220,overlap:int=40)->list[dict[str,Any]]:
 """Chunk pages without losing page provenance."""
 if max_words<1 or overlap<0 or overlap>=max_words: raise ValueError("Require max_words >= 1 and 0 <= overlap < max_words.")
 chunks=[]; step=max_words-overlap
 for page in pages:
  words=normalize_text(str(page.get("text",""))).split()
  for start in range(0,len(words),step):
   body=" ".join(words[start:start+max_words])
   if not body: continue
   chunks.append({"id":"S"+str(len(chunks)+1),"text":body,"page_start":int(page["page"]),
                  "page_end":int(page["page"]),"extraction":page.get("extraction","text")})
   if start+max_words>=len(words): break
 return chunks
