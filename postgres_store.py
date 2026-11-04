"""Optional tenant-scoped PostgreSQL + pgvector storage backend."""
from __future__ import annotations
import json,os
from typing import Any
from sqlalchemy import create_engine,text
from sqlalchemy.engine import Engine
from security import encrypt_text, decrypt_text

class PgVectorStore:
 def __init__(self,database_url:str|None=None,*,tenant_id:str,embedding_model:Any|None=None,dimensions:int=384):
  if not tenant_id: raise ValueError("tenant_id is required.")
  self.tenant_id=tenant_id; self.engine:Engine=create_engine(database_url or os.environ["DATABASE_URL"],pool_pre_ping=True)
  self.embedding_model=embedding_model; self.dimensions=dimensions; self.encryption_key=os.getenv('FERNET_KEY', '').strip(); self.initialize()
 def initialize(self):
  statements=[
   "CREATE EXTENSION IF NOT EXISTS vector",
   """CREATE TABLE IF NOT EXISTS report_documents (id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,file_name TEXT NOT NULL,sha256 TEXT NOT NULL,text_content TEXT NOT NULL,uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),analysis_json JSONB,UNIQUE(tenant_id,sha256),UNIQUE(id,tenant_id))""",
   f"""CREATE TABLE IF NOT EXISTS report_chunks (id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,document_id TEXT NOT NULL,chunk_index INTEGER NOT NULL,page_start INTEGER,page_end INTEGER,text_content TEXT NOT NULL,embedding vector({self.dimensions}) NOT NULL,FOREIGN KEY(document_id,tenant_id) REFERENCES report_documents(id,tenant_id) ON DELETE CASCADE)""",
   """CREATE TABLE IF NOT EXISTS audit_events (id BIGSERIAL PRIMARY KEY,tenant_id TEXT NOT NULL,actor_id TEXT NOT NULL,action TEXT NOT NULL,resource_type TEXT NOT NULL,resource_id TEXT NOT NULL DEFAULT '',metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
   "CREATE INDEX IF NOT EXISTS idx_report_docs_tenant ON report_documents(tenant_id)",
   "CREATE INDEX IF NOT EXISTS idx_report_chunks_tenant_doc ON report_chunks(tenant_id,document_id)",
   "CREATE INDEX IF NOT EXISTS idx_report_chunks_embedding ON report_chunks USING hnsw (embedding vector_cosine_ops)",
   "ALTER TABLE report_documents ENABLE ROW LEVEL SECURITY","ALTER TABLE report_chunks ENABLE ROW LEVEL SECURITY","ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY",
   "ALTER TABLE report_documents FORCE ROW LEVEL SECURITY","ALTER TABLE report_chunks FORCE ROW LEVEL SECURITY","ALTER TABLE audit_events FORCE ROW LEVEL SECURITY",
   """DO $$ BEGIN CREATE POLICY tenant_docs_policy ON report_documents USING (tenant_id=current_setting('app.tenant_id',true)) WITH CHECK (tenant_id=current_setting('app.tenant_id',true)); EXCEPTION WHEN duplicate_object THEN NULL; END $$""",
   """DO $$ BEGIN CREATE POLICY tenant_chunks_policy ON report_chunks USING (tenant_id=current_setting('app.tenant_id',true)) WITH CHECK (tenant_id=current_setting('app.tenant_id',true)); EXCEPTION WHEN duplicate_object THEN NULL; END $$""",
   """DO $$ BEGIN CREATE POLICY tenant_audit_policy ON audit_events USING (tenant_id=current_setting('app.tenant_id',true)) WITH CHECK (tenant_id=current_setting('app.tenant_id',true)); EXCEPTION WHEN duplicate_object THEN NULL; END $$"""]
  with self.engine.begin() as conn:
   for stmt in statements: conn.execute(text(stmt))
 def _embed(self,texts:list[str])->list[list[float]]:
  if self.embedding_model is None:
   from sentence_transformers import SentenceTransformer
   self.embedding_model=SentenceTransformer(os.getenv("EMBEDDING_MODEL","sentence-transformers/all-MiniLM-L6-v2"))
  values=self.embedding_model.encode(texts,normalize_embeddings=True)
  return values.tolist() if hasattr(values,"tolist") else values
 def ingest_chunks(self,document_id:str,file_name:str,sha256:str,full_text:str,chunks:list[dict[str,Any]],batch_size:int=32):
  with self.engine.begin() as conn:
   conn.execute(text("SELECT set_config('app.tenant_id',:tenant,true)"),{"tenant":self.tenant_id})
   conn.execute(text("INSERT INTO report_documents(id,tenant_id,file_name,sha256,text_content) VALUES (:id,:tenant,:name,:sha,:body) ON CONFLICT (tenant_id,sha256) DO NOTHING"),
   {"id":document_id,"tenant":self.tenant_id,"name":file_name,"sha":sha256,"body":encrypt_text(full_text,self.encryption_key) if self.encryption_key else full_text})
   for start in range(0,len(chunks),batch_size):
    batch=chunks[start:start+batch_size]; vectors=self._embed([x["text"] for x in batch])
    for idx,(chunk,vector) in enumerate(zip(batch,vectors),start):
     conn.execute(text("INSERT INTO report_chunks(id,tenant_id,document_id,chunk_index,page_start,page_end,text_content,embedding) VALUES (:id,:tenant,:doc,:idx,:pstart,:pend,:body,CAST(:embedding AS vector)) ON CONFLICT (id) DO NOTHING"),
     {"id":document_id+":S"+str(idx+1),"tenant":self.tenant_id,"doc":document_id,"idx":idx,"pstart":chunk.get("page_start"),"pend":chunk.get("page_end"),"body":encrypt_text(chunk["text"],self.encryption_key) if self.encryption_key else chunk["text"],"embedding":"["+",".join(map(str,vector))+"]"})
 def search(self,query:str,top_k:int=6)->list[dict[str,Any]]:
  vector=self._embed([query])[0]; literal="["+",".join(map(str,vector))+"]"
  with self.engine.begin() as conn:
   conn.execute(text("SELECT set_config('app.tenant_id',:tenant,true)"),{"tenant":self.tenant_id})
   rows=conn.execute(text("""SELECT c.id,c.document_id,d.file_name,c.text_content,c.page_start,c.page_end,1-(c.embedding <=> CAST(:vector AS vector)) AS score FROM report_chunks c JOIN report_documents d ON d.id=c.document_id AND d.tenant_id=c.tenant_id WHERE c.tenant_id=:tenant AND d.tenant_id=:tenant ORDER BY c.embedding <=> CAST(:vector AS vector) LIMIT :limit"""),
   {"tenant":self.tenant_id,"vector":literal,"limit":top_k}).mappings().all()
  results=[dict(row) for row in rows]
  if self.encryption_key:
   for row in results: row["text_content"]=decrypt_text(row["text_content"],self.encryption_key)
  return results
 def audit(self,actor_id:str,action:str,resource_type:str,resource_id:str="",metadata:dict[str,Any]|None=None):
  with self.engine.begin() as conn:
   conn.execute(text("SELECT set_config('app.tenant_id',:tenant,true)"),{"tenant":self.tenant_id})
   conn.execute(text("INSERT INTO audit_events(tenant_id,actor_id,action,resource_type,resource_id,metadata_json) VALUES (:tenant,:actor,:action,:rtype,:rid,CAST(:metadata AS jsonb))"),
   {"tenant":self.tenant_id,"actor":actor_id,"action":action,"rtype":resource_type,"rid":resource_id,"metadata":json.dumps(metadata or {})})
