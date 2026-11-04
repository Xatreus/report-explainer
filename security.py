"""Security primitives for password hashing, signed sessions, RBAC and encryption."""
from __future__ import annotations
import base64, hashlib, hmac, json, secrets, time
from typing import Any

ROLE_PERMISSIONS = {
 "viewer": {"reports:read", "search:run"},
 "analyst": {"reports:read", "search:run", "reports:ingest", "reports:compare"},
 "admin": {"reports:read", "search:run", "reports:ingest", "reports:compare", "reports:delete", "users:manage", "audit:read"},
}
def _b64(data: bytes) -> str: return base64.urlsafe_b64encode(data).decode().rstrip("=")
def _unb64(value: str) -> bytes: return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
def hash_password(password: str, salt: bytes | None = None) -> str:
 if len(password) < 12: raise ValueError("Password must contain at least 12 characters.")
 salt=salt or secrets.token_bytes(16); digest=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,600_000)
 return "pbkdf2_sha256$600000$"+_b64(salt)+"$"+_b64(digest)
def verify_password(password: str, encoded: str) -> bool:
 try:
  algorithm,iterations,salt,expected=encoded.split("$",3)
  if algorithm!="pbkdf2_sha256": return False
  actual=hashlib.pbkdf2_hmac("sha256",password.encode(),_unb64(salt),int(iterations))
  return hmac.compare_digest(actual,_unb64(expected))
 except (ValueError,TypeError): return False
def issue_session_token(subject:str,tenant_id:str,role:str,secret:str,ttl_seconds:int=3600)->str:
 if role not in ROLE_PERMISSIONS or not secret or ttl_seconds<=0: raise ValueError("Known role, secret and positive TTL required.")
 payload={"sub":subject,"tenant":tenant_id,"role":role,"exp":int(time.time())+ttl_seconds}
 body=_b64(json.dumps(payload,sort_keys=True,separators=(",",":")).encode())
 sig=_b64(hmac.new(secret.encode(),body.encode(),hashlib.sha256).digest())
 return body+"."+sig
def verify_session_token(token:str,secret:str)->dict[str,Any]:
 try:
  body,sig=token.split(".",1); expected=_b64(hmac.new(secret.encode(),body.encode(),hashlib.sha256).digest())
  if not hmac.compare_digest(sig,expected): raise ValueError("Invalid session signature.")
  payload=json.loads(_unb64(body))
  if int(payload["exp"])<=int(time.time()): raise ValueError("Session expired.")
  if payload.get("role") not in ROLE_PERMISSIONS: raise ValueError("Invalid session role.")
  return payload
 except (KeyError,TypeError,json.JSONDecodeError) as exc: raise ValueError("Invalid session token.") from exc
def authorize(principal:dict[str,Any],permission:str)->None:
 if permission not in ROLE_PERMISSIONS.get(principal.get("role"),set()): raise PermissionError("Insufficient role permissions.")
def encrypt_text(plaintext:str,key:str)->str:
 from cryptography.fernet import Fernet
 return Fernet(key.encode()).encrypt(plaintext.encode()).decode()
def decrypt_text(ciphertext:str,key:str)->str:
 from cryptography.fernet import Fernet,InvalidToken
 try: return Fernet(key.encode()).decrypt(ciphertext.encode()).decode()
 except InvalidToken as exc: raise ValueError("Unable to decrypt content; check encryption key.") from exc
def audit_event(connection:Any,*,tenant_id:str,actor_id:str,action:str,resource_type:str,resource_id:str="",metadata:dict[str,Any]|None=None)->None:
 connection.execute("""INSERT INTO audit_events
 (tenant_id,actor_id,action,resource_type,resource_id,metadata_json,created_at)
 VALUES (:tenant_id,:actor_id,:action,:resource_type,:resource_id,:metadata_json,CURRENT_TIMESTAMP)""",
 {"tenant_id":tenant_id,"actor_id":actor_id,"action":action,"resource_type":resource_type,
  "resource_id":resource_id,"metadata_json":json.dumps(metadata or {},ensure_ascii=False)})
