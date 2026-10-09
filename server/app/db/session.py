from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False}
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

from sqlalchemy import text

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Verify and migrate runtime_tokens columns
        res = await conn.execute(text("PRAGMA table_info(runtime_tokens)"))
        existing_cols = {row[1] for row in res.fetchall()}
        if existing_cols:
            if "is_active" not in existing_cols:
                await conn.execute(text("ALTER TABLE runtime_tokens ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"))
            if "revoked_at" not in existing_cols:
                await conn.execute(text("ALTER TABLE runtime_tokens ADD COLUMN revoked_at TEXT"))

        # Verify and migrate action_idempotency columns
        res_idemp = await conn.execute(text("PRAGMA table_info(action_idempotency)"))
        existing_idemp_cols = {row[1] for row in res_idemp.fetchall()}
        if existing_idemp_cols and "payload_hash" not in existing_idemp_cols:
            await conn.execute(text("ALTER TABLE action_idempotency ADD COLUMN payload_hash TEXT"))

        # Verify and migrate connections columns
        res_conn = await conn.execute(text("PRAGMA table_info(connections)"))
        existing_conn_cols = {row[1] for row in res_conn.fetchall()}
        if existing_conn_cols:
            if "status" not in existing_conn_cols:
                await conn.execute(text("ALTER TABLE connections ADD COLUMN status VARCHAR(32) NOT NULL DEFAULT 'active'"))
            if "status_message" not in existing_conn_cols:
                await conn.execute(text("ALTER TABLE connections ADD COLUMN status_message TEXT"))
            if "last_validated_at" not in existing_conn_cols:
                await conn.execute(text("ALTER TABLE connections ADD COLUMN last_validated_at VARCHAR(32)"))
            if "expires_at" not in existing_conn_cols:
                await conn.execute(text("ALTER TABLE connections ADD COLUMN expires_at VARCHAR(32)"))

        # Verify and migrate oauth_states columns
        res_oauth = await conn.execute(text("PRAGMA table_info(oauth_states)"))
        existing_oauth_cols = {row[1] for row in res_oauth.fetchall()}
        if existing_oauth_cols:
            if "expires_at" not in existing_oauth_cols:
                await conn.execute(text("ALTER TABLE oauth_states ADD COLUMN expires_at VARCHAR(32)"))


