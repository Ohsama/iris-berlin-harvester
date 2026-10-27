import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from app.config.paths import ProjectPaths
from app.config.settings import Settings
from app.scrapers.berlin_bplan_scraper import BerlinBplanScraper
from app.parsers.bplan_parser import BplanParser
from app.transformers.signal_transformer import SignalTransformer, TransformedSignal
from app.loaders.signal_loader import SignalLoader
from app.database.session import get_engine, init_db, get_session_factory

logger = logging.getLogger(__name__)


class HarvestRunner:
    """
    Main ETL orchestrator for IRIS-SIG-17 Berlin Bebauungspläne Harvester.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        paths: ProjectPaths | None = None,
    ):
        self.settings = settings or Settings()
        self.paths = paths or ProjectPaths()
        self.scraper = BerlinBplanScraper(settings=self.settings, paths=self.paths)
        self.parser = BplanParser()
        self.transformer = SignalTransformer()

    def run(self, save_to_db: bool = True) -> Dict[str, Any]:
        """
        Executes full harvester pipeline: Scrape -> Parse -> Classify/Transform -> Export -> Load.
        """
        logger.info("Starting IRIS-SIG-17 Harvester pipeline...")

        # 1. Scrape
        scraped_data = self.scraper.scrape()
        detail_pages = scraped_data["detail_pages"]
        source_status = scraped_data["source_status"]

        # 2. Parse & Transform
        transformed_signals: List[TransformedSignal] = []
        raw_records = []
        unresolved_locations = []

        for page in detail_pages:
            raw_rec = self.parser.parse_detail_page(page["html"], fallback_url=page["url"])
            raw_records.append(raw_rec)

            sig = self.transformer.transform(raw_rec)
            if sig:
                transformed_signals.append(sig)
                if not sig.easting_25832:
                    unresolved_locations.append({
                        "source_id": sig.source_id,
                        "location_status": sig.location_status,
                        "notes": sig.validation_notes,
                    })

        # 3. Export sample outputs (JSON and GeoJSON)
        self._export_outputs(transformed_signals)

        # 4. Optional Database Loading
        db_stats = {}
        if save_to_db:
            try:
                engine = get_engine(self.settings.database_url)
                init_db(engine, self.settings.database_schema)
                session_factory = get_session_factory(engine)

                with session_factory() as session:
                    loader = SignalLoader(session)
                    db_stats = loader.load(transformed_signals)
            except Exception as exc:
                logger.warning(
                    "Database ingestion skipped or failed (%s). "
                    "Outputs are successfully preserved in /output directory.",
                    exc,
                )
                db_stats = {"status": "skipped", "reason": str(exc)}

        summary = {
            "source_status": source_status,
            "raw_pages_evaluated": len(detail_pages),
            "signals_detected": len(transformed_signals),
            "signals_by_type": self._group_by_type(transformed_signals),
            "unresolved_locations_count": len(unresolved_locations),
            "database_stats": db_stats,
        }

        logger.info("Pipeline completed. Detected %d qualified signals.", len(transformed_signals))
        return summary

    def _group_by_type(self, signals: List[TransformedSignal]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for s in signals:
            counts[s.signal_type] = counts.get(s.signal_type, 0) + 1
        return counts

    def _export_outputs(self, signals: List[TransformedSignal]) -> None:
        """Exports JSON and GeoJSON deliverables to output/."""
        # 1. JSON
        json_path = self.paths.output / "sample_signals.json"
        data = [s.to_dict() for s in signals]
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Saved sample signals JSON to: %s", json_path)

        # 2. GeoJSON
        geojson_path = self.paths.output / "sample_signals.geojson"
        features = [s.to_geojson_feature() for s in signals if s.to_geojson_feature()]
        geojson_data = {
            "type": "FeatureCollection",
            "crs": {
                "type": "name",
                "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
            },
            "features": features,
        }
        geojson_path.write_text(json.dumps(geojson_data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Saved sample signals GeoJSON to: %s", geojson_path)
