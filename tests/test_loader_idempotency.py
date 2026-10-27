from app.loaders.signal_loader import SignalLoader
from app.transformers.signal_transformer import TransformedSignal
from app.database.repositories.signal_ingest_repository import SignalIngestRepository


def create_sample_signal(source_id: str, title: str, signal_type: str = "edge_dc_filing") -> TransformedSignal:
    return TransformedSignal(
        source_id=source_id,
        title=title,
        signal_type=signal_type,
        confidence_score=0.85,
        publication_date="2026-10-15",
        source_url=f"https://berlin.de/test/{source_id}",
        district="Marzahn",
        description="Edge DC testing filing.",
        raw_lat=52.55,
        raw_lon=13.53,
        easting_25832=806450.0,
        northing_25832=5831200.0,
        geometry_wkt="POINT(806450.0 5831200.0)",
        location_status="resolved",
        matched_indicators={"edge_dc": ["datacenter"]},
        validation_notes=[],
    )


def test_loader_idempotency_and_no_duplicates(db_session):
    loader = SignalLoader(db_session)
    repo = SignalIngestRepository(db_session)

    # Initial batch of 2 records
    signals = [
        create_sample_signal("SIG-001", "Filing One"),
        create_sample_signal("SIG-002", "Filing Two"),
    ]

    # --- Run 1: First Ingestion ---
    stats_1 = loader.load(signals)
    assert stats_1["inserted"] == 2
    assert stats_1["updated"] == 0
    assert stats_1["duplicates_skipped"] == 0
    assert repo.count() == 2

    # Verify records stored correctly
    rec1 = repo.get_by_source_id("SIG-001")
    assert rec1 is not None
    assert rec1.title == "Filing One"

    # --- Run 2: Exact Same Ingestion (Re-run) ---
    stats_2 = loader.load(signals)
    assert stats_2["inserted"] == 0
    assert stats_2["updated"] == 2
    assert stats_2["duplicates_skipped"] == 0
    assert repo.count() == 2  # CRITICAL: Count remains 2! Zero duplicates created.

    # --- Run 3: Ingestion with an in-batch duplicate and one update ---
    updated_signal_1 = create_sample_signal("SIG-001", "Filing One - Updated Title")
    duplicate_signal_1 = create_sample_signal("SIG-001", "Duplicate Copy of One")
    new_signal_3 = create_sample_signal("SIG-003", "Filing Three")

    batch_3 = [updated_signal_1, duplicate_signal_1, new_signal_3]
    stats_3 = loader.load(batch_3)

    assert stats_3["inserted"] == 1  # SIG-003
    assert stats_3["updated"] == 1   # SIG-001 updated
    assert stats_3["duplicates_skipped"] == 1  # duplicate_signal_1 skipped
    assert repo.count() == 3

    # Check updated record reflected changes
    rec1_updated = repo.get_by_source_id("SIG-001")
    assert rec1_updated.title == "Filing One - Updated Title"
