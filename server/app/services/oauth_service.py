import asyncio
import base64
import hashlib
import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.models import OAuthState, OAuthClientConfig, Connection, utcnow_str
from app.core.security import encrypt_secret, decrypt_secret, safe_error_message
from app.core.ssrf import create_guarded_client, execute_guarded_request
from app.core.config import settings
from app.providers.registry import registry

# Built-in OAuth provider endpoints and default scopes
OAUTH_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "github": {
        "display_name": "GitHub",
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "default_scopes": ["repo", "read:user"],
    },
    "slack": {
        "display_name": "Slack",
        "authorize_url": "https://slack.com/oauth/v2/authorize",
        "token_url": "https://slack.com/api/oauth.v2.access",
        "default_scopes": ["chat:write", "channels:read"],
    }
}

class OAuthService:
    # In-memory per-connection locks to guarantee single-flight refresh operations
    _refresh_locks: Dict[str, asyncio.Lock] = {}

    @classmethod
    def _get_lock(cls, connection_id: str) -> asyncio.Lock:
        if connection_id not in cls._refresh_locks:
            cls._refresh_locks[connection_id] = asyncio.Lock()
        return cls._refresh_locks[connection_id]

    @staticmethod
    def create_pkce_pair() -> Tuple[str, str]:
        """Generate RFC 7636 PKCE code_verifier and code_challenge (S256)."""
        code_verifier = secrets.token_urlsafe(64)
        hashed = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = base64.urlsafe_b64encode(hashed).decode("ascii").rstrip("=")
        return code_verifier, code_challenge

    @staticmethod
    async def get_client_config(session: AsyncSession, service: str) -> Optional[Dict[str, str]]:
        """Retrieve stored encrypted OAuth client credentials, falling back to environment settings."""
        stmt = select(OAuthClientConfig).where(OAuthClientConfig.service == service)
        res = (await session.execute(stmt)).scalar_one_or_none()
        if res and res.encrypted_value:
            try:
                decrypted = decrypt_secret(res.encrypted_value)
                return json.loads(decrypted)
            except Exception:
                pass
        
        # Fallback to environment variables if defined
        env_client_id = getattr(settings, f"{service.upper()}_CLIENT_ID", None)
        env_client_secret = getattr(settings, f"{service.upper()}_CLIENT_SECRET", None)
        if env_client_id and env_client_secret:
            return {
                "client_id": env_client_id,
                "client_secret": env_client_secret
            }
        return None

    @staticmethod
    async def set_client_config(session: AsyncSession, service: str, client_id: str, client_secret: str) -> None:
        """Store OAuth client credentials encrypted with AES-256-GCM."""
        payload = json.dumps({"client_id": client_id, "client_secret": client_secret})
        encrypted_val = encrypt_secret(payload)
        
        stmt = select(OAuthClientConfig).where(OAuthClientConfig.service == service)
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.encrypted_value = encrypted_val
            existing.updated_at = utcnow_str()
        else:
            new_conf = OAuthClientConfig(
                service=service,
                encrypted_value=encrypted_val
            )
            session.add(new_conf)
        await session.commit()

    @staticmethod
    async def create_authorization_url(
        session: AsyncSession,
        service: str,
        connection_name: str = "default",
        redirect_uri: Optional[str] = None,
        custom_scopes: Optional[list] = None
    ) -> Dict[str, Any]:
        """Generate PKCE state, record expiring transaction state, and build authorization URL."""
        provider_meta = OAUTH_PROVIDERS.get(service)
        if not provider_meta:
            raise ValueError(f"OAuth is not supported for service '{service}'.")

        config = await OAuthService.get_client_config(session, service)
        if not config or not config.get("client_id"):
            raise ValueError(f"OAuth client credentials have not been configured for '{service}'.")

        client_id = config["client_id"]
        code_verifier, code_challenge = OAuthService.create_pkce_pair()
        state = secrets.token_urlsafe(32)
        expires_at = (datetime.utcnow() + timedelta(minutes=10)).isoformat() + "Z"

        # Record expiring transaction state
        oauth_state = OAuthState(
            state=state,
            service=service,
            connection_name=connection_name,
            code_verifier=code_verifier,
            return_uri=redirect_uri,
            created_at=utcnow_str(),
            expires_at=expires_at
        )
        session.add(oauth_state)
        await session.commit()

        scopes = custom_scopes or provider_meta.get("default_scopes", [])
        scope_str = " ".join(scopes) if service != "github" else ",".join(scopes)

        params = {
            "client_id": client_id,
            "response_type": "code",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }
        if scope_str:
            params["scope"] = scope_str
        if redirect_uri:
            params["redirect_uri"] = redirect_uri

        auth_url = f"{provider_meta['authorize_url']}?{urlencode(params)}"
        return {
            "authorization_url": auth_url,
            "state": state,
            "service": service,
            "connectionName": connection_name,
            "expiresAt": expires_at
        }

    @staticmethod
    async def exchange_code(
        session: AsyncSession,
        service: str,
        code: str,
        state: str
    ) -> Dict[str, Any]:
        """Atomically validate one-time state, exchange code with PKCE, and persist encrypted credentials."""
        stmt = select(OAuthState).where(
            and_(OAuthState.state == state, OAuthState.service == service)
        )
        res = (await session.execute(stmt)).scalar_one_or_none()
        if not res:
            raise ValueError("Invalid or expired OAuth state parameter.")

        # Check state expiration (10 min lifetime)
        now_str = utcnow_str()
        if res.expires_at and res.expires_at < now_str:
            await session.delete(res)
            await session.commit()
            raise ValueError("OAuth transaction state has expired. Please restart the authorization flow.")

        connection_name = res.connection_name
        code_verifier = res.code_verifier
        redirect_uri = res.return_uri

        # Atomically delete one-time state to prevent replay attacks
        await session.delete(res)
        await session.commit()

        # Retrieve client config
        config = await OAuthService.get_client_config(session, service)
        if not config:
            raise ValueError(f"OAuth configuration missing for service '{service}'.")

        provider_meta = OAUTH_PROVIDERS.get(service)
        if not provider_meta:
            raise ValueError(f"Unknown OAuth provider: '{service}'.")

        token_url = provider_meta["token_url"]
        
        # Prepare token exchange payload
        token_payload = {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "code": code,
            "grant_type": "authorization_code"
        }
        if code_verifier:
            token_payload["code_verifier"] = code_verifier
        if redirect_uri:
            token_payload["redirect_uri"] = redirect_uri

        client = await create_guarded_client()
        try:
            resp = await execute_guarded_request(
                client=client,
                method="POST",
                url=token_url,
                data=token_payload,
                headers={"Accept": "application/json"}
            )
            if resp.status_code != 200:
                raise ValueError(f"OAuth token exchange rejected by provider (status {resp.status_code}): {resp.text}")

            try:
                token_data = resp.json()
            except Exception:
                # Some providers return URL-encoded form data
                from urllib.parse import parse_qs
                parsed = parse_qs(resp.text)
                token_data = {k: v[0] for k, v in parsed.items()}

            if "error" in token_data:
                raise ValueError(f"Provider returned OAuth error: {token_data.get('error_description') or token_data['error']}")

            access_token = token_data.get("access_token")
            if not access_token:
                raise ValueError("No access_token returned by provider.")

            refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in")
            expires_at = None
            if expires_in:
                expires_at = (datetime.utcnow() + timedelta(seconds=int(expires_in))).isoformat() + "Z"

            # Validate live with provider registry
            provider = registry.get_provider(service)
            if not provider:
                raise ValueError(f"Provider registry entry missing for '{service}'.")

            profile = await provider.validate_credentials({"accessToken": access_token}, client)

            # Build credential record
            credential_dict = {
                "accessToken": access_token,
                "refreshToken": refresh_token,
                "tokenType": token_data.get("token_type", "Bearer"),
                "scope": token_data.get("scope", "")
            }
            encrypted_val = encrypt_secret(json.dumps(credential_dict))
            granted_scopes_json = json.dumps(profile.get("granted_scopes", []))

            # Upsert into connection model
            conn_stmt = select(Connection).where(
                and_(Connection.service == service, Connection.connection_name == connection_name)
            )
            existing_conn = (await session.execute(conn_stmt)).scalar_one_or_none()
            if existing_conn:
                existing_conn.auth_type = "oauth2"
                existing_conn.encrypted_value = encrypted_val
                existing_conn.account_id = profile.get("account_id")
                existing_conn.display_name = profile.get("display_name")
                existing_conn.granted_scopes = granted_scopes_json
                existing_conn.status = "active"
                existing_conn.status_message = None
                existing_conn.last_validated_at = utcnow_str()
                existing_conn.expires_at = expires_at
                existing_conn.updated_at = utcnow_str()
                conn_id = existing_conn.id
            else:
                new_conn = Connection(
                    service=service,
                    connection_name=connection_name,
                    auth_type="oauth2",
                    encrypted_value=encrypted_val,
                    account_id=profile.get("account_id"),
                    display_name=profile.get("display_name"),
                    granted_scopes=granted_scopes_json,
                    status="active",
                    status_message=None,
                    last_validated_at=utcnow_str(),
                    expires_at=expires_at
                )
                session.add(new_conn)
                await session.flush()
                conn_id = new_conn.id

            await session.commit()

            return {
                "id": conn_id,
                "service": service,
                "connectionName": connection_name,
                "authType": "oauth2",
                "accountId": profile.get("account_id"),
                "displayName": profile.get("display_name"),
                "status": "active",
                "lastValidatedAt": utcnow_str(),
                "expiresAt": expires_at
            }
        finally:
            await client.aclose()

    @staticmethod
    async def refresh_connection_if_needed(session: AsyncSession, connection: Connection) -> bool:
        """Concurrency-safe OAuth token refresh using connection lock. Returns True if active/refreshed, False if expired."""
        if connection.auth_type != "oauth2":
            return True

        # Decrypt credential
        try:
            creds = json.loads(decrypt_secret(connection.encrypted_value))
        except Exception:
            return False

        refresh_token = creds.get("refreshToken")
        expires_at = connection.expires_at

        # If token does not expire or has > 60s remaining, no refresh needed
        if expires_at:
            try:
                exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if datetime.now(exp_dt.tzinfo) + timedelta(seconds=60) < exp_dt:
                    return True
            except Exception:
                pass

        # If no refresh token is stored, token is permanently expired
        if not refresh_token:
            if expires_at and expires_at < utcnow_str():
                connection.status = "expired"
                connection.status_message = "Access token expired and no refresh token is available. Re-authentication required."
                await session.commit()
                return False
            return True

        # Acquire lock to ensure only one refresh request runs for this connection
        lock = OAuthService._get_lock(connection.id)
        async with lock:
            # Re-read connection inside lock to check if another worker already refreshed it
            await session.refresh(connection)
            try:
                re_creds = json.loads(decrypt_secret(connection.encrypted_value))
                if connection.expires_at:
                    exp_dt = datetime.fromisoformat(connection.expires_at.replace("Z", "+00:00"))
                    if datetime.now(exp_dt.tzinfo) + timedelta(seconds=60) < exp_dt:
                        return True
            except Exception:
                pass

            config = await OAuthService.get_client_config(session, connection.service)
            provider_meta = OAUTH_PROVIDERS.get(connection.service)
            if not config or not provider_meta:
                connection.status = "expired"
                connection.status_message = "OAuth configuration unavailable for automatic refresh."
                await session.commit()
                return False

            client = await create_guarded_client()
            try:
                refresh_payload = {
                    "client_id": config["client_id"],
                    "client_secret": config["client_secret"],
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                }
                resp = await execute_guarded_request(
                    client=client,
                    method="POST",
                    url=provider_meta["token_url"],
                    data=refresh_payload,
                    headers={"Accept": "application/json"}
                )

                if resp.status_code in (400, 401):
                    connection.status = "expired"
                    connection.status_message = "Refresh token expired or revoked. Please reconnect account."
                    await session.commit()
                    return False
                
                if resp.status_code != 200:
                    connection.status = "error"
                    connection.status_message = f"Token refresh failed upstream with status {resp.status_code}"
                    await session.commit()
                    return False

                token_data = resp.json()
                new_access_token = token_data.get("access_token")
                if not new_access_token:
                    return False

                # Update credentials
                creds["accessToken"] = new_access_token
                if "refresh_token" in token_data:
                    creds["refreshToken"] = token_data["refresh_token"]

                expires_in = token_data.get("expires_in")
                new_expires_at = None
                if expires_in:
                    new_expires_at = (datetime.utcnow() + timedelta(seconds=int(expires_in))).isoformat() + "Z"

                connection.encrypted_value = encrypt_secret(json.dumps(creds))
                connection.status = "active"
                connection.status_message = None
                connection.last_validated_at = utcnow_str()
                connection.expires_at = new_expires_at
                connection.updated_at = utcnow_str()
                await session.commit()
                return True
            except Exception as e:
                connection.status = "error"
                connection.status_message = safe_error_message(e)
                await session.commit()
                return False
            finally:
                await client.aclose()
