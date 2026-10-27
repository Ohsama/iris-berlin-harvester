import logging
from typing import Optional, List, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.database.models.signal_ingest import SignalIngest
from app.transformers.signal_transformer import TransformedSignal

logger = logging.getLogger(__name__)


class SignalIngestRepository:
    """Repository for querying and persisting SignalIngest records."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_source_id(self, source_id: str) -> Optional[SignalIngest]:
        """Fetch signal record by unique source identifier."""
        stmt = select(SignalIngest).where(SignalIngest.source_id == source_id)
        return self.session.scalars(stmt).first()

    def upsert(self, signal: TransformedSignal) -> Tuple[SignalIngest, bool]:
        """
        Idempotent upsert: Inserts if source_id is new; updates attributes if existing.
        Returns: (SignalIngest instance, is_created: bool)
        """
        from datetime import date
        existing = self.get_by_source_id(signal.source_id)

        pub_date = None
        if signal.publication_date:
            try:
                pub_date = date.fromisoformat(signal.publication_date)
            except ValueError:
                pub_date = None

        metadata = {
            "confidence_score": signal.confidence_score,
            "matched_indicators": signal.matched_indicators,
            "validation_notes": signal.validation_notes,
            "raw_lat": signal.raw_lat,
            "raw_lon": signal.raw_lon,
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
        }

        if existing:
            # Update existing record
            existing.title = signal.title
            existing.signal_type = signal.signal_type
            existing.confidence_score = signal.confidence_score
            existing.publication_date = pub_date
            existing.source_url = signal.source_url
            existing.district = signal.district
            existing.description = signal.description
            existing.easting_25832 = signal.easting_25832
            existing.northing_25832 = signal.northing_25832
            existing.geometry_wkt = signal.geometry_wkt
            existing.location_status = signal.location_status
            existing.metadata_json = metadata
            return existing, False

        # Create new record
        new_record = SignalIngest(
            source_id=signal.source_id,
            title=signal.title,
            signal_type=signal.signal_type,
            confidence_score=signal.confidence_score,
            publication_date=pub_date,
            source_url=signal.source_url,
            district=signal.district,
            description=signal.description,
            easting_25832=signal.easting_25832,
            northing_25832=signal.northing_25832,
            geometry_wkt=signal.geometry_wkt,
            location_status=signal.location_status,
            metadata_json=metadata,
        )
        self.session.add(new_record)
        return new_record, True

    def count(self) -> int:
        """Count total records in staging table."""
        stmt = select(func.count(SignalIngest.id))
        return self.session.scalar(stmt) or 0

    def list_all(self) -> List[SignalIngest]:
        """Retrieve all ingested signals."""
        stmt = select(SignalIngest).order_by(SignalIngest.created_at.desc())
        return list(self.session.scalars(stmt).all())
