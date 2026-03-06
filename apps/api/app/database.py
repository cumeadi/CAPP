import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Read from env; fall back to SQLite so local dev works without a Postgres instance.
_raw_url = os.environ.get("DATABASE_URL", "sqlite:///./capp.db")

# This module uses the *synchronous* SQLAlchemy engine (create_engine / Session).
# asyncpg is an async-only driver and cannot be used here — swap it for psycopg2.
if "+asyncpg" in _raw_url:
    _raw_url = _raw_url.replace("+asyncpg", "+psycopg2")

SQL_ALCHEMY_DATABASE_URL = _raw_url

# check_same_thread is a SQLite-specific argument; omit it for any other engine.
_connect_args = {"check_same_thread": False} if SQL_ALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(SQL_ALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
