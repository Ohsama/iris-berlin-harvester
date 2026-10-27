from __future__ import annotations
from uuid import uuid4
from datetime import date
from typing import Optional, Dict, Any

from sqlalchemy import (
    String,
    Float,
    Text,
    Date,
    Index,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geometry

from app.database.base import BaseEntity


class SignalIngest(BaseEntity):
    """
    SQLAlchemy Model for 'iris_staging.signal_ingest'.
    
    Destination table for ingested Bebauungsplan signals.
    Supports PostGIS 3.4 Point geometries in EPSG:25832.
    """

    __tablename__ = "signal_ingest"

    __table_args__ = (
        Index("idx_signal_ingest_source_id", "source_id"),
        Index("idx_signal_ingest_signal_type", "signal_type"),
        Index("idx_signal_ingest_district", "district"),
        Index("idx_signal_ingest_pub_date", "publication_date"),
        UniqueConstraint("source_id", name="uq_signal_ingest_source_id"),
        {"schema": "iris_staging"},
    )

    # 1. Primary Key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # 2. External Source Identity (for idempotency)
    source_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    # 3. Attributes
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    signal_type: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    publication_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    district: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 4. Spatial Attributes (EPSG:25832)
    easting_25832: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    northing_25832: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    geometry_wkt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location_status: Mapped[str] = mapped_column(String(32), default="unresolved")

    # Optional PostGIS geometry column for PostgreSQL environments
    geom = mapped_column(
        Geometry(geometry_type="POINT", srid=25832, spatial_index=False),
        nullable=True,
    )

    # 5. Metadata & Audit JSON
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
