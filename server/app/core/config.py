from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os
from pathlib import Path
import secrets
from typing import Optional

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
    model_config = SettingsConfigDict(env_prefix="CONNECTOR_", env_file=".env", extra="ignore")

    PROJECT_NAME: str = "ConnectorHub"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/v1"
    
    # Server host & port
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    PUBLIC_ORIGIN: str = Field(
        default=os.environ.get("CONNECTOR_PUBLIC_ORIGIN") or os.environ.get("PUBLIC_ORIGIN") or "https://connector.suparagent.ai",
        description="Public origin used for OAuth callbacks and reverse proxy"
    )
    HOSTED_ORIGIN: str = "https://connector.suparagent.ai"
    HOSTED_DOMAIN: str = "connector.suparagent.ai"
    
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
    
    # Set CONNECTOR_EXPOSE_LOCAL_TOKEN=false on any network-facing deployment.
    EXPOSE_LOCAL_TOKEN: bool = True

    # SSRF Protection
    ALLOW_PRIVATE_NETWORK: bool = False

    # Public Access Gate for Open Web Console
    ALLOW_PUBLIC_ACCESS: bool = Field(
        default=os.environ.get("CONNECTOR_ALLOW_PUBLIC_ACCESS", os.environ.get("ALLOW_PUBLIC_ACCESS", "true")).lower() in ("true", "1", "yes"),
        description="Allow public access to connect providers, manage tokens, and execute actions without an admin token."
    )

    # Origins (besides PUBLIC_ORIGIN) allowed as post-OAuth return URLs, comma separated.
    ALLOWED_RETURN_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- Optional user accounts (email + password, cookie sessions) ---
    # disabled | invite (needs ACCOUNTS_INVITE_CODES) | open (needs an email backend)
    ACCOUNTS_SIGNUP_MODE: str = "disabled"
    ACCOUNTS_INVITE_CODES: str = ""            # comma-separated one-line invite codes
    ACCOUNTS_EMAIL_BACKEND: str = "none"       # none | ses | smtp | console (console logs codes: development only)
    ACCOUNTS_EMAIL_FROM: str = ""              # e.g. "ConnectorHub <support@example.com>"; must be a verified sender
    # Amazon SES API. Leave the keys empty to use the machine's IAM role / default AWS credentials.
    ACCOUNTS_SES_REGION: str = "us-east-1"
    ACCOUNTS_SES_ACCESS_KEY: str = ""
    ACCOUNTS_SES_SECRET_KEY: str = ""
    ACCOUNTS_BLOCKED_EMAIL_DOMAINS: str = ""   # comma-separated, in addition to reserved test domains
    ACCOUNTS_SESSION_DAYS: int = 30
    ACCOUNTS_COOKIE_SECURE: Optional[bool] = None  # default: true when PUBLIC_ORIGIN is https
    ACCOUNTS_SMTP_HOST: str = ""
    ACCOUNTS_SMTP_PORT: int = 587
    ACCOUNTS_SMTP_USER: str = ""
    ACCOUNTS_SMTP_PASSWORD: str = ""
    ACCOUNTS_SMTP_FROM: str = ""
    ACCOUNTS_SMTP_STARTTLS: bool = True

    # MCP Authentication Gate (Fail-Closed by default)
    ALLOW_ANONYMOUS_MCP: bool = Field(
        default=False,
        description="Explicit opt-in to allow unauthenticated MCP access (restricted to loopback)"
    )

settings = Settings()
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
