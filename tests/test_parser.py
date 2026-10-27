from datetime import date
from app.parsers.bplan_parser import BplanParser


def test_parse_portal_list(sample_html_fixtures):
    parser = BplanParser()
    rows = parser.parse_portal_list(sample_html_fixtures["list"])

    assert len(rows) == 5
    assert rows[0]["plan_id"] == "I-B14a"
    assert rows[0]["district"] == "Mitte"
    assert "Moabit" in rows[0]["title"]


def test_parse_detail_industrial(sample_html_fixtures):
    parser = BplanParser()
    record = parser.parse_detail_page(sample_html_fixtures["industrial"], fallback_url="https://test.de/1")

    assert record.source_id == "I-B14a"
    assert "Mitte" in record.district
    assert record.publication_date == date(2026, 9, 15)
    assert float(record.raw_lat) == 52.53120
    assert float(record.raw_lon) == 13.33640
    assert "Konversion" in record.description or "Neuordnung" in record.description
    assert len(record.validation_errors) == 0


def test_parse_detail_malformed(sample_html_fixtures):
    parser = BplanParser()
    record = parser.parse_detail_page(sample_html_fixtures["malformed"], fallback_url="https://test.de/err")

    assert record.source_id == "NK-ERR-99"
    assert record.publication_date is None
    assert any("Invalid publication date" in err for err in record.validation_errors)
    assert record.raw_lat == "CORRUPT_LAT"
