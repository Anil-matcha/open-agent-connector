import json
import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.db.models import Connection, utcnow_str
from app.core.security import encrypt_secret, decrypt_secret, safe_error_message
from app.providers.registry import registry
from app.core.ssrf import create_guarded_client

class ConnectionService:
    @staticmethod
    async def get_connection_by_id(
        session: AsyncSession,
        connection_id: str
    ) -> Optional[Connection]:
        stmt = select(Connection).where(Connection.id == connection_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_connection(
        session: AsyncSession,
        service: str,
        connection_name: str = "default"
    ) -> Optional[Connection]:
        stmt = select(Connection).where(
            and_(Connection.service == service, Connection.connection_name == connection_name)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def resolve_connection(
        session: AsyncSession,
        id_or_service: str,
        connection_name: Optional[str] = None
    ) -> Optional[Connection]:
        """Lookup connection either by stable UUID id or by service + connection_name."""
        # Try primary key UUID lookup first
        try:
            uuid_obj = uuid.UUID(id_or_service)
            conn = await ConnectionService.get_connection_by_id(session, str(uuid_obj))
            if conn:
                return conn
        except (ValueError, AttributeError):
            pass

        # Fallback to (service, connection_name)
        return await ConnectionService.get_connection(
            session=session,
            service=id_or_service,
            connection_name=connection_name or "default"
        )

    @staticmethod
    async def list_connections(
        session: AsyncSession,
        service: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        stmt = select(Connection)
        if service:
            stmt = stmt.where(Connection.service == service)
        result = await session.execute(stmt)
        connections = result.scalars().all()
        
        output = []
        for c in connections:
            scopes = []
            try:
                scopes = json.loads(c.granted_scopes or "[]")
            except Exception:
                pass
            output.append({
                "id": c.id,
                "service": c.service,
                "connectionName": c.connection_name,
                "authType": c.auth_type,
                "accountId": c.account_id,
                "displayName": c.display_name,
                "grantedScopes": scopes,
                "status": c.status or "active",
                "statusMessage": c.status_message,
                "lastValidatedAt": c.last_validated_at,
                "expiresAt": c.expires_at,
                "createdAt": c.created_at,
                "updatedAt": c.updated_at
            })
        return output

    @staticmethod
    async def upsert_connection(
        session: AsyncSession,
        service: str,
        auth_type: str,
        values: Dict[str, Any],
        connection_name: str = "default"
    ) -> Dict[str, Any]:
        provider = registry.get_provider(service)
        if not provider:
            raise ValueError(f"Unknown provider service: '{service}'")

        # Validate with provider live
        client = await create_guarded_client()
        profile = {"account_id": "verified", "display_name": f"{provider.display_name} Account", "granted_scopes": []}
        try:
            profile = await provider.validate_credentials(values, client)
        except Exception as e:
            raise ValueError(f"Credential validation failed for {service}: {str(e)}")
        finally:
            await client.aclose()

        encrypted_val = encrypt_secret(json.dumps(values))
        granted_scopes_json = json.dumps(profile.get("granted_scopes", []))

        existing = await ConnectionService.get_connection(session, service, connection_name)
        now_ts = utcnow_str()
        if existing:
            existing.auth_type = auth_type
            existing.encrypted_value = encrypted_val
            existing.account_id = profile.get("account_id")
            existing.display_name = profile.get("display_name")
            existing.granted_scopes = granted_scopes_json
            existing.status = "active"
            existing.status_message = None
            existing.last_validated_at = now_ts
            existing.updated_at = now_ts
            target_id = existing.id
        else:
            conn = Connection(
                service=service,
                connection_name=connection_name,
                auth_type=auth_type,
                encrypted_value=encrypted_val,
                account_id=profile.get("account_id"),
                display_name=profile.get("display_name"),
                granted_scopes=granted_scopes_json,
                status="active",
                status_message=None,
                last_validated_at=now_ts
            )
            session.add(conn)
            await session.flush()
            target_id = conn.id

        await session.commit()
        return {
            "id": target_id,
            "service": service,
            "connectionName": connection_name,
            "authType": auth_type,
            "accountId": profile.get("account_id"),
            "displayName": profile.get("display_name"),
            "status": "active",
            "lastValidatedAt": now_ts
        }

    @staticmethod
    async def test_connection(
        session: AsyncSession,
        id_or_service: str,
        connection_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Test stored credentials against provider in real-time and update connection status."""
        conn = await ConnectionService.resolve_connection(session, id_or_service, connection_name)
        if not conn:
            raise ValueError(f"Connection '{id_or_service}' not found.")

        provider = registry.get_provider(conn.service)
        if not provider:
            raise ValueError(f"Provider '{conn.service}' is not registered.")

        if "no_auth" in provider.auth_types:
            conn.status = "active"
            conn.status_message = None
            conn.last_validated_at = utcnow_str()
            await session.commit()
            return {
                "success": True,
                "status": "active",
                "message": "Virtual connection is active.",
                "lastValidatedAt": conn.last_validated_at
            }

        try:
            creds = json.loads(decrypt_secret(conn.encrypted_value))
        except Exception:
            conn.status = "error"
            conn.status_message = "Stored credentials could not be decrypted."
            await session.commit()
            return {"success": False, "status": "error", "message": conn.status_message}

        client = await create_guarded_client()
        try:
            profile = await provider.validate_credentials(creds, client)
            conn.status = "active"
            conn.status_message = None
            conn.last_validated_at = utcnow_str()
            if profile.get("account_id"):
                conn.account_id = profile["account_id"]
            if profile.get("display_name"):
                conn.display_name = profile["display_name"]
            if "granted_scopes" in profile:
                conn.granted_scopes = json.dumps(profile["granted_scopes"])
            await session.commit()

            return {
                "success": True,
                "status": "active",
                "profile": profile,
                "lastValidatedAt": conn.last_validated_at
            }
        except Exception as e:
            conn.status = "error"
            conn.status_message = safe_error_message(e)
            await session.commit()
            return {
                "success": False,
                "status": "error",
                "message": conn.status_message
            }
        finally:
            await client.aclose()

    @staticmethod
    async def disconnect_connection(
        session: AsyncSession,
        id_or_service: str,
        connection_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Revoke a connection without permanently deleting the record."""
        conn = await ConnectionService.resolve_connection(session, id_or_service, connection_name)
        if not conn:
            raise ValueError(f"Connection '{id_or_service}' not found.")

        conn.status = "revoked"
        conn.status_message = "Revoked by administrator"
        conn.updated_at = utcnow_str()
        await session.commit()

        return {
            "id": conn.id,
            "service": conn.service,
            "connectionName": conn.connection_name,
            "status": "revoked"
        }

    @staticmethod
    async def reconnect_connection(
        session: AsyncSession,
        id_or_service: str,
        values: Dict[str, Any],
        connection_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update/rotate credentials on an existing connection, re-validating live."""
        conn = await ConnectionService.resolve_connection(session, id_or_service, connection_name)
        if not conn:
            raise ValueError(f"Connection '{id_or_service}' not found.")

        provider = registry.get_provider(conn.service)
        if not provider:
            raise ValueError(f"Provider '{conn.service}' not found.")

        client = await create_guarded_client()
        try:
            profile = await provider.validate_credentials(values, client)
        except Exception as e:
            raise ValueError(f"Credential validation failed during rotation: {str(e)}")
        finally:
            await client.aclose()

        now_ts = utcnow_str()
        conn.encrypted_value = encrypt_secret(json.dumps(values))
        conn.status = "active"
        conn.status_message = None
        conn.last_validated_at = now_ts
        conn.updated_at = now_ts
        if profile.get("account_id"):
            conn.account_id = profile["account_id"]
        if profile.get("display_name"):
            conn.display_name = profile["display_name"]
        if "granted_scopes" in profile:
            conn.granted_scopes = json.dumps(profile["granted_scopes"])

        await session.commit()
        return {
            "id": conn.id,
            "service": conn.service,
            "connectionName": conn.connection_name,
            "status": "active",
            "lastValidatedAt": now_ts
        }

    @staticmethod
    async def delete_connection(
        session: AsyncSession,
        id_or_service: str,
        connection_name: Optional[str] = None
    ) -> bool:
        """Permanently delete a connection from the database."""
        conn = await ConnectionService.resolve_connection(session, id_or_service, connection_name)
        if not conn:
            return False
        await session.delete(conn)
        await session.commit()
        return True

    @staticmethod
    async def resolve_credentials(
        session: AsyncSession,
        service: str,
        connection_name: str = "default"
    ) -> Optional[Dict[str, Any]]:
        """Resolve and decrypt credentials, enforcing lifecycle status and automatic OAuth token refresh."""
        provider = registry.get_provider(service)
        if not provider:
            return None
        if "no_auth" in provider.auth_types:
            return {} # virtual connection

        conn = await ConnectionService.get_connection(session, service, connection_name)
        if not conn:
            return None

        # Lifecycle checks
        if conn.status == "revoked":
            raise ValueError(
                f"Connection for '{service}' (alias: '{connection_name}') has been revoked. Please reconnect."
            )

        if conn.status == "expired":
            from app.services.oauth_service import OAuthService
            refreshed = await OAuthService.refresh_connection_if_needed(session, conn)
            if not refreshed:
                raise ValueError(
                    f"Connection for '{service}' (alias: '{connection_name}') has expired. Please re-authenticate."
                )

        # Proactive OAuth refresh check
        if conn.auth_type == "oauth2":
            from app.services.oauth_service import OAuthService
            await OAuthService.refresh_connection_if_needed(session, conn)

        decrypted_json = decrypt_secret(conn.encrypted_value)
        try:
            return json.loads(decrypted_json)
        except Exception:
            return {}
