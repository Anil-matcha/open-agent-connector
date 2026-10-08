import os
import base64
import hashlib
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.config import settings

def _get_key_bytes() -> bytes:
    raw = settings.ENCRYPTION_KEY.strip()
    try:
        decoded = base64.urlsafe_b64decode(raw)
        if len(decoded) == 32:
            return decoded
    except Exception:
        pass
    # Deterministic 32-byte key from string
    return hashlib.sha256(raw.encode("utf-8")).digest()

def encrypt_secret(plain_text: str) -> str:
    """Encrypt a plaintext secret using AES-256-GCM returning base64(nonce + ciphertext + tag)"""
    if not plain_text:
        return ""
    key = _get_key_bytes()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    cipher_bytes = aesgcm.encrypt(nonce, plain_text.encode("utf-8"), None)
    return base64.b64encode(nonce + cipher_bytes).decode("ascii")

def decrypt_secret(cipher_text_b64: str) -> str:
    """Decrypt a base64 encoded ciphertext using AES-256-GCM"""
    if not cipher_text_b64:
        return ""
    try:
        data = base64.b64decode(cipher_text_b64)
        if len(data) < 28:
            raise ValueError("Ciphertext payload is too short")
        nonce = data[:12]
        cipher_bytes = data[12:]
        key = _get_key_bytes()
        aesgcm = AESGCM(key)
        plain_bytes = aesgcm.decrypt(nonce, cipher_bytes, None)
        return plain_bytes.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Secret decryption failed: {str(e)}")

def hash_token(raw_token: str) -> str:
    """Deterministic SHA-256 hash for bearer tokens"""
    return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()
