"""Database session factory."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import AsyncGenerator

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session


def get_db_url() -> str:
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "terraos")
    user = os.getenv("DB_USER", "terraos")
    password = os.getenv("DB_PASSWORD", "change_me")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(get_db_url(), pool_pre_ping=True)


def get_session() -> sessionmaker:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)
