import logging
import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class RawBplanRecord:
    """Structured representation of a parsed HTML B-Plan record before transformation."""

    def __init__(
        self,
        source_id: str,
        title: str,
        district: Optional[str],
        publication_date: Optional[date],
        raw_publication_date: Optional[str],
        description: str,
        source_url: str,
        raw_lat: Optional[str] = None,
        raw_lon: Optional[str] = None,
        source_crs: Optional[str] = "EPSG:4326",
        validation_errors: Optional[List[str]] = None,
    ):
        self.source_id = source_id
        self.title = title
        self.district = district
        self.publication_date = publication_date
        self.raw_publication_date = raw_publication_date
        self.description = description
        self.source_url = source_url
        self.raw_lat = raw_lat
        self.raw_lon = raw_lon
        self.source_crs = source_crs
        self.validation_errors = validation_errors or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "district": self.district,
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "raw_publication_date": self.raw_publication_date,
            "description": self.description,
            "source_url": self.source_url,
            "raw_lat": self.raw_lat,
            "raw_lon": self.raw_lon,
            "source_crs": self.source_crs,
            "validation_errors": self.validation_errors,
        }


class BplanParser:
    """
    Parses HTML documents from the Berlin Bebauungsplan portal into structured domain records.
    """

    DATE_FORMATS = [
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
    ]

    def parse_portal_list(self, html: str) -> List[Dict[str, str]]:
        """
        Parses portal overview HTML table and extracts summary list items.
        """
        soup = BeautifulSoup(html, "html.parser")
        records = []
        rows = soup.find_all("tr", class_="bplan-row")

        for row in rows:
            plan_id_el = row.find(class_="plan-id")
            district_el = row.find(class_="district")
            title_el = row.find(class_="title")
            pub_date_el = row.find(class_="pub-date")
            link_el = row.find("a", class_="detail-link")

            plan_id = plan_id_el.get_text(strip=True) if plan_id_el else row.get("data-id", "UNKNOWN")
            district = district_el.get_text(strip=True) if district_el else None
            title = title_el.get_text(strip=True) if title_el else ""
            pub_date_raw = pub_date_el.get_text(strip=True) if pub_date_el else None
            href = link_el.get("href") if link_el else ""

            records.append({
                "plan_id": plan_id,
                "district": district,
                "title": title,
                "raw_date": pub_date_raw,
                "href": href,
            })

        return records

    def parse_detail_page(self, html: str, fallback_url: str = "") -> RawBplanRecord:
        """
        Parses an individual Bebauungsplan detail HTML page.
        """
        soup = BeautifulSoup(html, "html.parser")
        errors = []

        # 1. Source ID
        id_el = soup.find(id="source_identifier")
        source_id = id_el.get_text(strip=True) if id_el else ""
        if not source_id:
            header_ref = soup.find(class_="plan-reference")
            source_id = header_ref.get_text(strip=True) if header_ref else "UNKNOWN_PLAN"

        # 2. Title
        title_el = soup.find(class_="plan-title") or soup.find("h1")
        title = title_el.get_text(strip=True) if title_el else ""

        # 3. District
        district_el = soup.find(id="district")
        district = district_el.get_text(strip=True) if district_el else None

        # 4. Publication date
        date_el = soup.find(id="publication_date")
        raw_date = date_el.get_text(strip=True) if date_el else None
        pub_date = self._parse_date(raw_date)
        if raw_date and not pub_date:
            errors.append(f"Invalid publication date format: '{raw_date}'")

        # 5. Description / Planning justification
        desc_el = soup.find("section", class_="description") or soup.find("article")
        description = desc_el.get_text(" ", strip=True) if desc_el else ""

        # 6. Source URL
        url_el = soup.find("a", id="source_url")
        source_url = url_el.get("href") if url_el else fallback_url

        # 7. Coordinates & CRS
        coord_el = soup.find(id="coordinates")
        raw_lat = None
        raw_lon = None
        source_crs = "EPSG:4326"

        if coord_el:
            raw_lat = coord_el.get("data-lat")
            raw_lon = coord_el.get("data-lon")
            source_crs = coord_el.get("data-crs", "EPSG:4326")

            # Fallback regex extraction from text if attributes missing
            if not raw_lat or not raw_lon:
                text = coord_el.get_text()
                match = re.search(r"Breitengrad:\s*([0-9\.\-]+).*Längengrad:\s*([0-9\.\-]+)", text)
                if match:
                    raw_lat, raw_lon = match.group(1), match.group(2)

        return RawBplanRecord(
            source_id=source_id,
            title=title,
            district=district,
            publication_date=pub_date,
            raw_publication_date=raw_date,
            description=description,
            source_url=source_url,
            raw_lat=raw_lat,
            raw_lon=raw_lon,
            source_crs=source_crs,
            validation_errors=errors,
        )

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        if not date_str:
            return None
        date_str = date_str.strip()
        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return None
