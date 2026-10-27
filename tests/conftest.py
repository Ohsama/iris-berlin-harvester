import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.database.session import init_db
from app.config.paths import ProjectPaths
from app.parsers.bplan_parser import RawBplanRecord


@pytest.fixture
def project_paths():
    return ProjectPaths()


@pytest.fixture
def sample_html_fixtures(project_paths):
    fixtures_dir = project_paths.fixtures
    return {
        "list": (fixtures_dir / "bplan_portal_list.html").read_text(encoding="utf-8"),
        "industrial": (fixtures_dir / "bplan_detail_industrial.html").read_text(encoding="utf-8"),
        "substation": (fixtures_dir / "bplan_detail_substation.html").read_text(encoding="utf-8"),
        "datacenter": (fixtures_dir / "bplan_detail_datacenter.html").read_text(encoding="utf-8"),
        "residential": (fixtures_dir / "bplan_detail_residential_ignored.html").read_text(encoding="utf-8"),
        "malformed": (fixtures_dir / "bplan_detail_malformed.html").read_text(encoding="utf-8"),
    }


@pytest.fixture
def db_session():
    """In-memory SQLite session with schema adaptation for unit testing."""
    from app.database.session import get_engine, init_db, get_session_factory
    engine = get_engine("sqlite:///:memory:")
    init_db(engine, schema="iris_staging")
    Session = get_session_factory(engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
