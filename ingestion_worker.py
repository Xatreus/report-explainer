"""Redis/RQ background ingestion helpers with batch embedding."""
from __future__ import annotations
import hashlib,os
from typing import Any

def enqueue_ingestion(file_name:str,content:bytes,tenant_id:str,*,queue_name:str="reports"):
 """Queue report bytes for asynchronous processing; requires Redis and RQ."""
 try:
  from redis import Redis
  from rq import Queue
 except ImportError as exc: raise RuntimeError("Install requirements-worker.txt.") from exc
 queue=Queue(queue_name,connection=Redis.from_url(os.environ["REDIS_URL"]),default_timeout=1800)
 return queue.enqueue("ingestion_worker.process_report",file_name,content,tenant_id,job_timeout=1800,result_ttl=86400)

def process_report(file_name:str,content:bytes,tenant_id:str)->dict[str,Any]:
 """Worker entry point for page-aware PDF ingestion."""
 from document_pipeline import chunk_page_records,extract_pdf_pages
 from postgres_store import PgVectorStore
 pages=extract_pdf_pages(content,ocr_if_empty=True); chunks=chunk_page_records(pages)
 full_text="\\n\\n".join(p["text"] for p in pages)
 if not full_text.strip(): raise ValueError("No text could be extracted, including OCR.")
 digest=hashlib.sha256(full_text.encode()).hexdigest(); doc_id=digest[:24]
 store=PgVectorStore(tenant_id=tenant_id)
 store.ingest_chunks(doc_id,file_name,digest,full_text,chunks,batch_size=int(os.getenv("EMBED_BATCH_SIZE","32")))
 store.audit("worker","report.ingested","report",doc_id,{"pages":len(pages),"chunks":len(chunks)})
 return {"document_id":doc_id,"pages":len(pages),"chunks":len(chunks)}
