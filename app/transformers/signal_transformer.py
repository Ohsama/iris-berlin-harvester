import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone

from app.parsers.bplan_parser import RawBplanRecord
from app.filters.signal_classifier import SignalClassifier, SignalType
from app.spatial.geo_resolver import GeoResolver, ResolvedLocation

logger = logging.getLogger(__name__)


class TransformedSignal:
    """Normalized signal record ready for staging database ingestion."""

    def __init__(
        self,
        source_id: str,
        title: str,
        signal_type: str,
        confidence_score: float,
        publication_date: Optional[str],
        source_url: str,
        district: Optional[str],
        description: str,
        raw_lat: Optional[float],
        raw_lon: Optional[float],
        easting_25832: Optional[float],
        northing_25832: Optional[float],
        geometry_wkt: Optional[str],
        location_status: str,
        matched_indicators: Dict[str, Any],
        validation_notes: List[str],
    ):
        self.source_id = source_id
        self.title = title
        self.signal_type = signal_type
        self.confidence_score = confidence_score
        self.publication_date = publication_date
        self.source_url = source_url
        self.district = district
        self.description = description
        self.raw_lat = raw_lat
        self.raw_lon = raw_lon
        self.easting_25832 = easting_25832
        self.northing_25832 = northing_25832
        self.geometry_wkt = geometry_wkt
        self.location_status = location_status
        self.matched_indicators = matched_indicators
        self.validation_notes = validation_notes
        self.ingested_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "signal_type": self.signal_type,
            "confidence_score": self.confidence_score,
            "publication_date": self.publication_date,
            "source_url": self.source_url,
            "district": self.district,
            "description": self.description,
            "raw_lat": self.raw_lat,
            "raw_lon": self.raw_lon,
            "easting_25832": self.easting_25832,
            "northing_25832": self.northing_25832,
            "geometry_wkt": self.geometry_wkt,
            "location_status": self.location_status,
            "matched_indicators": self.matched_indicators,
            "validation_notes": self.validation_notes,
            "ingested_at": self.ingested_at,
        }

    def to_geojson_feature(self) -> Optional[Dict[str, Any]]:
        """Exports WGS84 GeoJSON feature if coordinates are available."""
        if self.raw_lon is None or self.raw_lat is None:
            return None
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.raw_lon, self.raw_lat],
            },
            "properties": {
                "source_id": self.source_id,
                "title": self.title,
                "signal_type": self.signal_type,
                "confidence": self.confidence_score,
                "district": self.district,
                "publication_date": self.publication_date,
                "easting_25832": self.easting_25832,
                "northing_25832": self.northing_25832,
                "location_status": self.location_status,
            },
        }


class SignalTransformer:
    """
    Transforms raw parsed B-Plan records into normalized signals.
    Filters non-matching records and documents validation remarks.
    """

    def __init__(
        self,
        classifier: SignalClassifier | None = None,
        geo_resolver: GeoResolver | None = None,
    ):
        self.classifier = classifier or SignalClassifier()
        self.geo_resolver = geo_resolver or GeoResolver()

    def transform(self, raw_record: RawBplanRecord) -> Optional[TransformedSignal]:
        """
        Transforms a raw record into a TransformedSignal.
        Returns None if record does not match any target signal.
        """
        notes = list(raw_record.validation_errors)

        # 1. Classification
        classification = self.classifier.classify(
            title=raw_record.title,
            description=raw_record.description,
        )

        if not classification.is_relevant:
            logger.info("Record '%s' filtered out: %s", raw_record.source_id, classification.reasoning)
            return None

        # 2. Spatial resolution
        geo_result = self.geo_resolver.resolve(
            raw_lat=raw_record.raw_lat,
            raw_lon=raw_record.raw_lon,
            source_crs=raw_record.source_crs or "EPSG:4326",
        )

        if geo_result.error_message:
            notes.append(f"Spatial error: {geo_result.error_message}")

        return TransformedSignal(
            source_id=raw_record.source_id,
            title=raw_record.title,
            signal_type=classification.primary_signal_type.value,
            confidence_score=classification.confidence_score,
            publication_date=raw_record.publication_date.isoformat() if raw_record.publication_date else None,
            source_url=raw_record.source_url,
            district=raw_record.district,
            description=raw_record.description,
            raw_lat=geo_result.source_lat,
            raw_lon=geo_result.source_lon,
            easting_25832=geo_result.easting_25832,
            northing_25832=geo_result.northing_25832,
            geometry_wkt=geo_result.wkt,
            location_status=geo_result.status,
            matched_indicators=classification.matched_keywords,
            validation_notes=notes,
        )
