import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.config.settings import Settings
from app.database.base import Base

logger = logging.getLogger(__name__)


def get_engine(database_url: str | None = None):
    """Creates SQLAlchemy Engine."""
    settings = Settings()
    url = database_url or settings.database_url

    if url.startswith("sqlite"):
        engine = create_engine(url, echo=False)
        from sqlalchemy import event

        # Register lightweight Spatialite mock functions for SQLite testing
        dummy_hex = "0101000020e064000000000000000000000000000000000000"

        @event.listens_for(engine, "connect")
        def _sqlite_connect(conn, record):
            conn.create_function("GeomFromEWKT", 1, lambda x: x)
            conn.create_function("AsEWKB", 1, lambda x: dummy_hex if x is not None else None)
            conn.create_function("RecoverGeometryColumn", 5, lambda a, b, c, d, e: 1)
    else:
        engine = create_engine(
            url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            echo=False,
        )
    return engine


def init_db(engine, schema: str = "iris_staging") -> None:
    """
    Initializes database tables and creates schema if PostgreSQL.
    """
    dialect = engine.dialect.name
    if dialect == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema};"))
            logger.info("Schema '%s' and PostGIS extension verified.", schema)
        Base.metadata.create_all(bind=engine)
    else:
        # For SQLite testing without requiring spatialite binary
        try:
            from geoalchemy2.admin.dialects import sqlite as geo_sqlite
            geo_sqlite.after_create = lambda table, bind, **kw: None
        except Exception:
            pass

        # SQLite does not support schemas, create tables without schema namespace
        for table in Base.metadata.tables.values():
            table.schema = None
        Base.metadata.create_all(bind=engine)


def get_session_factory(engine) -> sessionmaker[Session]:
    """Returns configured Session factory."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
