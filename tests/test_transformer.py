from app.parsers.bplan_parser import BplanParser
from app.transformers.signal_transformer import SignalTransformer


def test_transformer_filters_and_normalizes(sample_html_fixtures):
    parser = BplanParser()
    transformer = SignalTransformer()

    # 1. Industrial -> Qualified
    ind_rec = parser.parse_detail_page(sample_html_fixtures["industrial"], fallback_url="https://test.de/1")
    sig1 = transformer.transform(ind_rec)
    assert sig1 is not None
    assert sig1.signal_type == "urban_industrial_reconversion"
    assert sig1.easting_25832 is not None
    assert sig1.location_status == "resolved"

    # 2. Substation -> Qualified
    sub_rec = parser.parse_detail_page(sample_html_fixtures["substation"], fallback_url="https://test.de/2")
    sig2 = transformer.transform(sub_rec)
    assert sig2 is not None
    assert sig2.signal_type == "high_power_substation_alert"

    # 3. Datacenter -> Qualified
    dc_rec = parser.parse_detail_page(sample_html_fixtures["datacenter"], fallback_url="https://test.de/3")
    sig3 = transformer.transform(dc_rec)
    assert sig3 is not None
    assert sig3.signal_type == "edge_dc_filing"

    # 4. Residential -> Filtered out (None)
    res_rec = parser.parse_detail_page(sample_html_fixtures["residential"], fallback_url="https://test.de/4")
    sig4 = transformer.transform(res_rec)
    assert sig4 is None

    # 5. Malformed -> Captured with errors visible (not silently dropped or crashed)
    mal_rec = parser.parse_detail_page(sample_html_fixtures["malformed"], fallback_url="https://test.de/5")
    sig5 = transformer.transform(mal_rec)
    assert sig5 is not None
    assert sig5.location_status == "invalid"
    assert len(sig5.validation_notes) > 0


def test_geojson_export(sample_html_fixtures):
    parser = BplanParser()
    transformer = SignalTransformer()
    dc_rec = parser.parse_detail_page(sample_html_fixtures["datacenter"], fallback_url="https://test.de/3")
    sig = transformer.transform(dc_rec)

    feature = sig.to_geojson_feature()
    assert feature is not None
    assert feature["type"] == "Feature"
    assert feature["geometry"]["type"] == "Point"
    assert len(feature["geometry"]["coordinates"]) == 2
    assert feature["properties"]["signal_type"] == "edge_dc_filing"
