from unittest.mock import MagicMock, patch
import requests

from app.scrapers.berlin_bplan_scraper import BerlinBplanScraper
from app.config.settings import Settings


def test_scraper_loads_offline_fixtures(project_paths):
    settings = Settings(use_offline_fixtures=True)
    scraper = BerlinBplanScraper(settings=settings, paths=project_paths)
    data = scraper.scrape()

    assert "portal_html" in data
    assert len(data["detail_pages"]) >= 4
    assert data["source_status"]["mode"] == "offline_fixtures"


def test_scraper_handles_http_410_gone(project_paths):
    settings = Settings(use_offline_fixtures=False)
    mock_client = MagicMock()
    mock_response = MagicMock(status_code=410)
    mock_client.get.return_value = mock_response

    scraper = BerlinBplanScraper(settings=settings, paths=project_paths, http_client=mock_client)
    data = scraper.scrape()

    assert data["source_status"]["endpoint_status"] == 410
    assert len(data["detail_pages"]) > 0  # Fell back to tested fixtures
    assert any("410 Gone" in note for note in data["source_status"]["notes"])
