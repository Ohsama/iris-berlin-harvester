import logging
from typing import Optional, Tuple
from pyproj import Transformer

logger = logging.getLogger(__name__)


class ResolvedLocation:
    """Represents the outcome of a spatial resolution."""

    def __init__(
        self,
        status: str,  # 'resolved', 'unresolved', 'invalid'
        source_lon: Optional[float] = None,
        source_lat: Optional[float] = None,
        easting_25832: Optional[float] = None,
        northing_25832: Optional[float] = None,
        wkt: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        self.status = status
        self.source_lon = source_lon
        self.source_lat = source_lat
        self.easting_25832 = easting_25832
        self.northing_25832 = northing_25832
        self.wkt = wkt
        self.error_message = error_message

    @property
    def is_resolved(self) -> bool:
        return self.status == "resolved" and self.easting_25832 is not None

    def to_dict(self):
        return {
            "status": self.status,
            "source_lon": self.source_lon,
            "source_lat": self.source_lat,
            "easting_25832": self.easting_25832,
            "northing_25832": self.northing_25832,
            "wkt": self.wkt,
            "error_message": self.error_message,
        }


class GeoResolver:
    """
    Transforms geographic coordinates from WGS84 (EPSG:4326) or source CRS into EPSG:25832 (ETRS89 / UTM 32N).
    Enforces strict coordinate validation:
    - Rejects non-numeric, corrupted, or out-of-bounds inputs.
    - Documents ambiguous or unresolved locations.
    - Produces valid EPSG:25832 Point geometries.
    """

    TARGET_CRS = "EPSG:25832"

    # Geographic boundary of Berlin metropolitan area in WGS84
    BERLIN_BOUNDS_WGS84 = {
        "min_lat": 52.2,
        "max_lat": 52.8,
        "min_lon": 12.9,
        "max_lon": 13.9,
    }

    def __init__(self):
        # always_xy=True ensures (lon, lat) ordering for EPSG:4326
        self.transformer_4326_to_25832 = Transformer.from_crs(
            "EPSG:4326",
            self.TARGET_CRS,
            always_xy=True,
        )

    def resolve(
        self,
        raw_lat: Optional[str | float],
        raw_lon: Optional[str | float],
        source_crs: str = "EPSG:4326",
    ) -> ResolvedLocation:
        """
        Resolves raw coordinate strings to EPSG:25832.
        """
        if not raw_lat or not raw_lon:
            return ResolvedLocation(
                status="unresolved",
                error_message="Coordinates missing from source.",
            )

        # 1. Parse floats
        try:
            lat = float(str(raw_lat).strip())
            lon = float(str(raw_lon).strip())
        except (ValueError, TypeError):
            msg = f"Invalid coordinate format: lat='{raw_lat}', lon='{raw_lon}'"
            logger.warning(msg)
            return ResolvedLocation(
                status="invalid",
                error_message=msg,
            )

        # 2. Validate bounds (WGS84)
        if source_crs.upper() in ["EPSG:4326", "WGS84"]:
            if not (
                self.BERLIN_BOUNDS_WGS84["min_lat"] <= lat <= self.BERLIN_BOUNDS_WGS84["max_lat"]
                and self.BERLIN_BOUNDS_WGS84["min_lon"] <= lon <= self.BERLIN_BOUNDS_WGS84["max_lon"]
            ):
                msg = f"Coordinates out of expected Berlin bounds: ({lat}, {lon})"
                logger.warning(msg)
                return ResolvedLocation(
                    status="invalid",
                    source_lat=lat,
                    source_lon=lon,
                    error_message=msg,
                )

            # 3. Transform to EPSG:25832
            try:
                easting, northing = self.transformer_4326_to_25832.transform(lon, lat)
                wkt = f"POINT({easting:.3f} {northing:.3f})"
                return ResolvedLocation(
                    status="resolved",
                    source_lat=lat,
                    source_lon=lon,
                    easting_25832=round(easting, 3),
                    northing_25832=round(northing, 3),
                    wkt=wkt,
                )
            except Exception as exc:
                msg = f"Coordinate transformation failed: {exc}"
                logger.error(msg)
                return ResolvedLocation(
                    status="invalid",
                    source_lat=lat,
                    source_lon=lon,
                    error_message=msg,
                )

        return ResolvedLocation(
            status="unresolved",
            source_lat=lat,
            source_lon=lon,
            error_message=f"Unsupported source CRS: {source_crs}",
        )
