from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import normalize_database_url


class Base(DeclarativeBase):
    pass


def build_engine(database_url: str) -> Engine:
    url = make_url(normalize_database_url(database_url))
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=0,
        connect_args={
            "connect_timeout": 10,
            "sslmode": url.query.get("sslmode", "require"),
            # Compatible with Supavisor transaction pooling too.
            "prepare_threshold": None,
        },
    )


def make_session_dependency(engine: Engine):
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    return get_session
