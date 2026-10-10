"""Database engine, async session factory, and transaction management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base class for all SQLAlchemy domain models."""

    pass


def create_engine_instance(url: str, echo: bool = False) -> AsyncEngine:
    """Create async engine with appropriate dialect arguments."""
    connect_args = {}
    if "sqlite" in url:
        connect_args = {"check_same_thread": False}

    return create_async_engine(
        url,
        echo=echo,
        future=True,
        connect_args=connect_args,
    )


# Primary application async engine and sessionmaker
engine: AsyncEngine = create_engine_instance(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@asynccontextmanager
async def transaction_scope(
    session_factory: async_sessionmaker[AsyncSession] = AsyncSessionLocal,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional scope around a series of operations."""
    async with session_factory() as session:
        async with session.begin():
            try:
                yield session
            except Exception:
                await session.rollback()
                raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
