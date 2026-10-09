from sqlalchemy import Column, String, Integer, Float, Boolean, Text, Index
from app.db.session import Base
from datetime import datetime
import uuid

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utcnow_str() -> str:
    return datetime.utcnow().isoformat() + "Z"

class Connection(Base):
    __tablename__ = "connections"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    service = Column(String(64), nullable=False, index=True)
    connection_name = Column(String(64), nullable=False, default="default")
    auth_type = Column(String(32), nullable=False)
    encrypted_value = Column(Text, nullable=False, default="")
    account_id = Column(String(128), nullable=True)
    display_name = Column(String(128), nullable=True)
    granted_scopes = Column(Text, nullable=True) # JSON list
    status = Column(String(32), nullable=False, default="active") # "active", "expired", "revoked", "error"
    status_message = Column(Text, nullable=True)
    last_validated_at = Column(String(32), nullable=True)
    expires_at = Column(String(32), nullable=True)
    created_at = Column(String(32), default=utcnow_str)
    updated_at = Column(String(32), default=utcnow_str, onupdate=utcnow_str)

    __table_args__ = (
        Index("idx_service_connection", "service", "connection_name", unique=True),
    )

class OAuthClientConfig(Base):
    __tablename__ = "oauth_client_configs"
    
    service = Column(String(64), primary_key=True)
    encrypted_value = Column(Text, nullable=False)
    updated_at = Column(String(32), default=utcnow_str, onupdate=utcnow_str)

class OAuthState(Base):
    __tablename__ = "oauth_states"
    
    state = Column(String(64), primary_key=True)
    service = Column(String(64), nullable=False)
    connection_name = Column(String(64), nullable=False, default="default")
    code_verifier = Column(String(128), nullable=True)
    return_uri = Column(String(512), nullable=True)
    created_at = Column(String(32), default=utcnow_str)
    expires_at = Column(String(32), nullable=False)

class RuntimeToken(Base):
    __tablename__ = "runtime_tokens"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(64), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    allowed_actions = Column(Text, nullable=False, default="[]")       # JSON array of wildcard patterns
    blocked_actions = Column(Text, nullable=False, default="[]")       # JSON array
    allowed_proxies = Column(Text, nullable=False, default="[]")       # JSON array
    allowed_connections = Column(Text, nullable=False, default="[]")   # JSON array of connection IDs
    is_active = Column(Boolean, nullable=False, default=True)
    revoked_at = Column(String(32), nullable=True)
    created_at = Column(String(32), default=utcnow_str)
    last_used_at = Column(String(32), nullable=True)

class RunLog(Base):
    __tablename__ = "runs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    action_id = Column(String(128), nullable=False, index=True)
    service = Column(String(64), nullable=False, index=True)
    caller = Column(String(16), nullable=False, default="http") # "http", "mcp", "web"
    connection_id = Column(String(36), nullable=True)
    ok = Column(Boolean, nullable=False, default=True)
    status_code = Column(Integer, nullable=False, default=200)
    duration_ms = Column(Float, nullable=False, default=0.0)
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(String(32), default=utcnow_str)
    completed_at = Column(String(32), default=utcnow_str)

class IdempotencyRecord(Base):
    __tablename__ = "action_idempotency"
    
    key_hash = Column(String(64), primary_key=True) # Hash of idempotency_key + principal + action + connection
    payload_hash = Column(String(64), nullable=True) # Hash of normalized input data for conflict detection
    action_id = Column(String(128), nullable=False)
    status = Column(String(32), nullable=False) # "in_progress", "completed", "failed"
    response_status = Column(Integer, nullable=True)
    response_payload = Column(Text, nullable=True) # Encrypted JSON
    created_at = Column(String(32), default=utcnow_str)
    expires_at = Column(String(32), nullable=False)
