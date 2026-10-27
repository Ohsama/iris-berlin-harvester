import re
from enum import Enum
from typing import Dict, List, Optional, Tuple


class SignalType(str, Enum):
    """Target signal types specified by IRIS-SIG-17 objective."""
    INDUSTRIAL_RECONVERSION = "urban_industrial_reconversion"
    SUBSTATION_ALERT = "high_power_substation_alert"
    EDGE_DC_FILING = "edge_dc_filing"


class SignalClassificationResult:
    """Outcome of signal classification."""

    def __init__(
        self,
        is_relevant: bool,
        primary_signal_type: Optional[SignalType] = None,
        confidence_score: float = 0.0,
        matched_keywords: Optional[Dict[str, List[str]]] = None,
        reasoning: str = "",
    ):
        self.is_relevant = is_relevant
        self.primary_signal_type = primary_signal_type
        self.confidence_score = confidence_score
        self.matched_keywords = matched_keywords or {}
        self.reasoning = reasoning

    def to_dict(self) -> Dict:
        return {
            "is_relevant": self.is_relevant,
            "primary_signal_type": self.primary_signal_type.value if self.primary_signal_type else None,
            "confidence_score": self.confidence_score,
            "matched_keywords": self.matched_keywords,
            "reasoning": self.reasoning,
        }


class SignalClassifier:
    """
    Evaluates Bebauungsplan texts against domain patterns for:
    1. Urban Industrial Reconversions
    2. High-power Substation Alerts
    3. Edge DC Filings
    """

    PATTERNS = {
        SignalType.EDGE_DC_FILING: [
            r"\brechenzentrum\b",
            r"\brechenzentren\b",
            r"\bdatacenter\b",
            r"\bdata\s*center\b",
            r"\bcloud[- ]infrastruktur\b",
            r"\bserverfarm\b",
            r"\bhyperscale\b",
            r"\bedge\s*computing\b",
            r"\bit[- ]last\b",
            r"\bso\s*datacenter\b",
        ],
        SignalType.SUBSTATION_ALERT: [
            r"\bumspannwerk\b",
            r"\bumspannwerke\b",
            r"\btransformator\b",
            r"\btrafostation\b",
            r"\b110\s*[-]?kv\b",
            r"\b220\s*[-]?kv\b",
            r"\b380\s*[-]?kv\b",
            r"\bhochspannung\b",
            r"\bhöchstspannung\b",
            r"\bübertragungsnetz\b",
            r"\bnetzanschluss\b",
            r"\bnetzverstärkung\b",
            r"\bschaltanlage\b",
            r"\benergieversorgungsanlage\b",
        ],
        SignalType.INDUSTRIAL_RECONVERSION: [
            r"\bkonversion\b",
            r"\bumstrukturierung\b",
            r"\bwiedernutzbarmachung\b",
            r"\brevitalisierung\b",
            r"\bindustriegebiet\b",
            r"\bgewerbegebiet\b",
            r"\bbrachfläche\b",
            r"\bindustriebrache\b",
            r"\bbrownfield\b",
            r"\bgewerbestandort\b",
            r"\bproduktionsstandort\b",
            r"\bgi/ge\b",
        ],
    }

    NEGATIVE_PATTERNS = [
        r"\breines\s*wohngebiet\b",
        r"\ballgemeines\s*wohngebiet\b",
        r"\bkindertagesstätte\b",
        r"\bspielplatz\b",
        r"\bkleingarten\b",
    ]

    def classify(self, title: str, description: str) -> SignalClassificationResult:
        """
        Scans title and description for positive and negative signal patterns.
        """
        combined_text = f"{title}\n{description}".lower()
        matched: Dict[str, List[str]] = {}
        type_scores: Dict[SignalType, int] = {}

        for sig_type, regex_list in self.PATTERNS.items():
            matches_for_type = []
            for pattern in regex_list:
                hits = re.findall(pattern, combined_text, flags=re.IGNORECASE)
                if hits:
                    matches_for_type.extend(hits)
            if matches_for_type:
                unique_hits = list(set(matches_for_type))
                matched[sig_type.value] = unique_hits
                # Title hits weighted x2
                title_hits = sum(1 for p in regex_list if re.search(p, title.lower()))
                type_scores[sig_type] = len(unique_hits) + (title_hits * 2)

        if not type_scores:
            # Check negative patterns
            neg_hits = [p for p in self.NEGATIVE_PATTERNS if re.search(p, combined_text)]
            reason = "Purely residential/non-industrial; excluded." if neg_hits else "No target signal keywords detected."
            return SignalClassificationResult(is_relevant=False, reasoning=reason)

        # Select highest-scoring category
        best_type = max(type_scores.items(), key=lambda x: x[1])[0]
        score = min(1.0, 0.4 + (type_scores[best_type] * 0.15))

        reason = f"Identified as {best_type.value} based on {len(matched[best_type.value])} indicators."
        return SignalClassificationResult(
            is_relevant=True,
            primary_signal_type=best_type,
            confidence_score=round(score, 2),
            matched_keywords=matched,
            reasoning=reason,
        )
