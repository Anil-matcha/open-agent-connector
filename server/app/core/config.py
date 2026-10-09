from pydantic_settings import BaseSettings
from pydantic import Field
import os
from pathlib import Path
import secrets

BASE_DIR = Path(__file__).resolve().parent.parent.parent

def _resolve_encryption_key() -> str:
    env_key = os.environ.get("CONNECTOR_ENCRYPTION_KEY") or os.environ.get("ENCRYPTION_KEY")
    if env_key and env_key.strip():
        return env_key.strip()
    key_file = BASE_DIR / "data" / ".secret.key"
    if key_file.exists():
        key_val = key_file.read_text(encoding="utf-8").strip()
        if key_val:
            return key_val
    new_key = secrets.token_urlsafe(32)
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_text(new_key, encoding="utf-8")
    return new_key

def _resolve_admin_token() -> str:
    env_token = os.environ.get("CONNECTOR_ADMIN_TOKEN") or os.environ.get("ADMIN_TOKEN")
    if env_token and env_token.strip():
        return env_token.strip()
    token_file = BASE_DIR / "data" / ".admin_token"
    if token_file.exists():
        val = token_file.read_text(encoding="utf-8").strip()
        if val:
            return val
    new_token = f"ch_admin_{secrets.token_urlsafe(32)}"
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(new_token, encoding="utf-8")
    return new_token

class Settings(BaseSettings):
    PROJECT_NAME: str = "ConnectorHub"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/v1"
    
    # Server host & port
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    PUBLIC_ORIGIN: str = "http://localhost:8000"
    
    # SQLite Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'connector.db'}"
    DATA_DIR: Path = BASE_DIR / "data"
    
    # Cryptographic AES-256-GCM encryption key
    ENCRYPTION_KEY: str = Field(
        default_factory=_resolve_encryption_key,
        description="Base64 or 32-char key for credential encryption"
    )
    ADMIN_TOKEN: str = Field(
        default_factory=_resolve_admin_token,
        description="Bearer token required for /api admin endpoints"
    )
    RUNTIME_TOKEN: str = Field(
        default="",
        description="Optional static Bearer token for /v1 and /mcp"
    )
    
    # SSRF Protection
    ALLOW_PRIVATE_NETWORK: bool = False
    
    class Config:
        env_prefix = "CONNECTOR_"
        env_file = ".env"
        extra = "ignore"

settings = Settings()
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
