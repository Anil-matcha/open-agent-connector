import json
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.db.models import Connection, utcnow_str
from app.core.security import encrypt_secret, decrypt_secret
from app.providers.registry import registry
from app.core.ssrf import create_guarded_client

class ConnectionService:
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

        # Validate with provider
        client = await create_guarded_client()
        profile = {"account_id": "verified", "display_name": f"{provider.display_name} Account", "granted_scopes": []}
        try:
            profile = await provider.validate_credentials(values, client)
        except Exception as e:
            # If verification fails, raise descriptive error
            raise ValueError(f"Credential validation failed for {service}: {str(e)}")
        finally:
            await client.aclose()

        encrypted_val = encrypt_secret(json.dumps(values))
        granted_scopes_json = json.dumps(profile.get("granted_scopes", []))

        existing = await ConnectionService.get_connection(session, service, connection_name)
        if existing:
            existing.auth_type = auth_type
            existing.encrypted_value = encrypted_val
            existing.account_id = profile.get("account_id")
            existing.display_name = profile.get("display_name")
            existing.granted_scopes = granted_scopes_json
            existing.updated_at = utcnow_str()
            target_id = existing.id
        else:
            conn = Connection(
                service=service,
                connection_name=connection_name,
                auth_type=auth_type,
                encrypted_value=encrypted_val,
                account_id=profile.get("account_id"),
                display_name=profile.get("display_name"),
                granted_scopes=granted_scopes_json
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
            "displayName": profile.get("display_name")
        }

    @staticmethod
    async def delete_connection(
        session: AsyncSession,
        service: str,
        connection_name: str = "default"
    ) -> bool:
        existing = await ConnectionService.get_connection(session, service, connection_name)
        if not existing:
            return False
        await session.delete(existing)
        await session.commit()
        return True

    @staticmethod
    async def resolve_credentials(
        session: AsyncSession,
        service: str,
        connection_name: str = "default"
    ) -> Optional[Dict[str, Any]]:
        provider = registry.get_provider(service)
        if not provider:
            return None
        if "no_auth" in provider.auth_types:
            return {} # virtual connection

        conn = await ConnectionService.get_connection(session, service, connection_name)
        if not conn:
            return None
        decrypted_json = decrypt_secret(conn.encrypted_value)
        try:
            return json.loads(decrypted_json)
        except Exception:
            return {}
