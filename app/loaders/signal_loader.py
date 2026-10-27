import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.database.repositories.signal_ingest_repository import SignalIngestRepository
from app.transformers.signal_transformer import TransformedSignal

logger = logging.getLogger(__name__)


class SignalLoader:
    """
    Idempotent loader for staging signal records into PostgreSQL.
    Identifies records by unique 'source_id'.
    Ensures safe, duplicate-free re-runs.
    """

    def __init__(self, session: Session):
        self.session = session
        self.repository = SignalIngestRepository(session)

    def _deduplicate(
        self,
        signals: List[TransformedSignal],
    ) -> Tuple[List[TransformedSignal], int]:
        """
        Deduplicates incoming batch by source_id.
        """
        unique: Dict[str, TransformedSignal] = {}
        duplicates_count = 0

        for sig in signals:
            if sig.source_id in unique:
                duplicates_count += 1
                logger.warning("Duplicate source_id in batch ignored: %s", sig.source_id)
                continue
            unique[sig.source_id] = sig

        return list(unique.values()), duplicates_count

    def load(self, signals: List[TransformedSignal]) -> Dict[str, Any]:
        """
        Executes idempotent loading into iris_staging.signal_ingest.
        """
        clean_signals, duplicates_skipped = self._deduplicate(signals)
        inserted = 0
        updated = 0

        for sig in clean_signals:
            _, is_new = self.repository.upsert(sig)
            if is_new:
                inserted += 1
            else:
                updated += 1

        self.session.commit()

        stats = {
            "total_submitted": len(signals),
            "unique_processed": len(clean_signals),
            "inserted": inserted,
            "updated": updated,
            "duplicates_skipped": duplicates_skipped,
            "total_in_staging": self.repository.count(),
        }

        logger.info(
            "Load complete: %d inserted, %d updated, %d duplicate(s) skipped.",
            inserted,
            updated,
            duplicates_skipped,
        )
        return stats
