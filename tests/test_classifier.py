from app.filters.signal_classifier import SignalClassifier, SignalType


def test_classify_industrial_reconversion():
    classifier = SignalClassifier()
    result = classifier.classify(
        title="Bebauungsplan I-B14a Industrie- und Gewerbegebiet",
        description="Wiedernutzbarmachung von Flächen, Revitalisierung und Konversion einer Industriebrache in Moabit.",
    )
    assert result.is_relevant is True
    assert result.primary_signal_type == SignalType.INDUSTRIAL_RECONVERSION
    assert result.confidence_score > 0.5


def test_classify_substation_alert():
    classifier = SignalClassifier()
    result = classifier.classify(
        title="Errichtung 110kV Umspannwerk Haselhorst",
        description="Der Übertragungsnetzbetreiber plant eine neue 110-kV Schaltanlage und Hochleistungstransformatoren.",
    )
    assert result.is_relevant is True
    assert result.primary_signal_type == SignalType.SUBSTATION_ALERT
    assert "umspannwerk" in [kw.lower() for kw in result.matched_keywords.get("high_power_substation_alert", [])]


def test_classify_datacenter_filing():
    classifier = SignalClassifier()
    result = classifier.classify(
        title="CleanTech Park - Neubau Rechenzentrum",
        description="Festsetzung eines Sondergebiets zur Errichtung eines Edge Data Center Campus mit 50 MW IT-Last.",
    )
    assert result.is_relevant is True
    assert result.primary_signal_type == SignalType.EDGE_DC_FILING


def test_filter_purely_residential():
    classifier = SignalClassifier()
    result = classifier.classify(
        title="Wohnquartier Am Schlosspark",
        description="Festsetzung eines reinen Wohngebiets mit 120 WE, Kindertagesstätte und Spielplatz.",
    )
    assert result.is_relevant is False
    assert result.primary_signal_type is None
