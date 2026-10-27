from app.spatial.geo_resolver import GeoResolver


def test_resolve_valid_berlin_coordinates():
    resolver = GeoResolver()
    # Berlin Alexanderplatz approx: 52.5219, 13.4132
    res = resolver.resolve(raw_lat=52.5219, raw_lon=13.4132, source_crs="EPSG:4326")

    assert res.status == "resolved"
    assert res.is_resolved is True
    assert res.easting_25832 is not None
    assert res.northing_25832 is not None
    # UTM zone 32N coordinates for Berlin are roughly easting ~790,000m to 810,000m, northing ~5,820,000m to 5,840,000m
    assert 780000 < res.easting_25832 < 830000
    assert 5810000 < res.northing_25832 < 5850000
    assert "POINT(" in res.wkt


def test_resolve_corrupt_coordinates_rejected():
    resolver = GeoResolver()
    res = resolver.resolve(raw_lat="CORRUPT_LAT", raw_lon="13.4132")

    assert res.status == "invalid"
    assert res.is_resolved is False
    assert "Invalid coordinate format" in res.error_message


def test_resolve_out_of_bounds_rejected():
    resolver = GeoResolver()
    # Coordinates in Munich or international (e.g., lat: 48.1, lon: 11.5)
    res = resolver.resolve(raw_lat=48.1351, raw_lon=11.5820)

    assert res.status == "invalid"
    assert res.is_resolved is False
    assert "out of expected Berlin bounds" in res.error_message


def test_resolve_missing_coordinates():
    resolver = GeoResolver()
    res = resolver.resolve(raw_lat=None, raw_lon=None)

    assert res.status == "unresolved"
    assert res.is_resolved is False
    assert "missing" in res.error_message.lower()
