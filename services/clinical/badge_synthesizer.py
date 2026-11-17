"""
Clinical risk and status badge synthesizer (ESRD, Dialysis, CKD, HTN, DM, CAD, Cirrhosis).
"""

from typing import Any, Dict, List, Optional, Set


class BadgeSynthesizer:
    """Synthesizes high-priority clinical condition and risk badges for header profile."""

    def _synthesize_clinical_badges(
        self,
        labs: Dict[str, Any],
        surgeries: set,
        conditions: set,
        meds: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Synthesize high-priority clinical tags."""
        badges = []
        all_text = " ".join(list(surgeries) + list(conditions)).lower()

        # ESRD / Dialysis
        egfr = labs.get("key_metrics", {}).get("egfr", {}).get("value")
        if (egfr is not None and egfr < 15) or "hemodialysis" in all_text or "esrd" in all_text or "uremia" in all_text:
            badges.append({"label": "ESRD 血液透析 (H/D)", "color": "danger"})
        elif egfr is not None and egfr < 60:
            badges.append({"label": f"CKD (eGFR {egfr})", "color": "warning"})

        # CAD / CABG
        if "cabg" in all_text or "coronary" in all_text:
            badges.append({"label": "CAD s/p CABG", "color": "primary"})

        # AV Fistula
        if any(x in all_text for x in ["av fistula", "fistula creation", "fistulogram", "動靜脈瘻管"]):
            badges.append({"label": "AV Fistula s/p PTA", "color": "info"})

        # Musculoskeletal / TAME / Osteoarthritis
        if "tame" in all_text or "micro-embolization" in all_text:
            badges.append({"label": "踝關節炎 s/p TAME 微栓塞處置", "color": "primary"})
        elif any(x in all_text for x in ["osteoarthritis", "骨關節炎"]):
            badges.append({"label": "退化性骨關節炎 (OA)", "color": "secondary"})

        # Diabetes
        glucose = labs.get("key_metrics", {}).get("glucose", {}).get("value")
        if (glucose and glucose > 180) or "diabetes" in all_text or "dm" in all_text:
            badges.append({"label": "Type 2 DM", "color": "warning"})

        # Hypertension
        if "hypertension" in all_text or "htn" in all_text:
            badges.append({"label": "Hypertension", "color": "secondary"})

        # Anemia
        hb = labs.get("key_metrics", {}).get("hb", {}).get("value")
        if (hb and hb < 10.0) or "anemia" in all_text:
            badges.append({"label": "Anemia", "color": "secondary"})

        # Liver Fibrosis & Chronic Viral Hepatitis
        fib4_data = labs.get("liver_assessment", {}).get("fib4")
        if fib4_data and fib4_data.get("value") is not None:
            val = fib4_data["value"]
            status = fib4_data.get("status")
            badge_color = "success" if status == "low_risk" else ("danger" if status == "high_risk" else "warning")
            badges.append({"label": f"FIB-4: {val:.2f} ({fib4_data.get('status_label', '')})", "color": badge_color})

        if any(x in all_text for x in ["b18.1", "b18.0", "b型肝炎", "hepatitis b"]):
            badges.append({"label": "慢性 B 型肝炎 (HBV)", "color": "info"})
        if any(x in all_text for x in ["b18.2", "c型肝炎", "hepatitis c"]):
            badges.append({"label": "慢性 C 型肝炎 (HCV)", "color": "info"})
        if any(x in all_text for x in ["k74", "肝硬化", "cirrhosis"]):
            badges.append({"label": "肝硬化 (Cirrhosis)", "color": "danger"})

        return badges


    # Backwards-compatible alias
    synthesize_clinical_badges = _synthesize_clinical_badges
