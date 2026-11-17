"""
Medication organizer, chronic refills analyzer, and timeline builder.
"""

import math
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from services.clinical.med_cleaner import (
    clean_brand_name,
    clean_ingredient,
    extract_med_dose,
)
from services.patient_mcp_client import (
    datetime_to_standard,
    normalize_freq,
    roc_to_datetime,
    to_standard_date,
)


class MedProcessor:
    """Processes outpatient prescriptions into therapeutic categories, active refills, and longitudinal timelines."""

    def _process_medications(
        self,
        raw_meds: List[Dict[str, Any]],
        consult_dt: Optional[datetime],
        lab_panel: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Organize medications into therapeutic classes, 慢箋 status, and safety checks."""
        active_meds = []
        completed_meds = []
        seen_keys = set()
        alerts = []

        egfr_val = lab_panel.get("key_metrics", {}).get("egfr", {}).get("value")
        is_esrd = (egfr_val is not None and egfr_val < 15.0)

        # Track 3-month refills
        refill_tracker = {}
        for m in raw_meds:
            code = (m.get("nhicode") or "").strip().upper()
            date = (m.get("date") or "").strip()
            k = (code, date)
            if k not in refill_tracker:
                refill_tracker[k] = {"count": 0, "single_days": int(m.get("days", 1) or 1)}
            refill_tracker[k]["count"] += 1

        for m in raw_meds:
            nhicode = (m.get("nhicode") or "").strip().upper()
            brand = (m.get("medication") or "").strip()
            raw_ing = (m.get("ingredient") or "").strip()
            ingredient = clean_ingredient(raw_ing, brand)
            atc5 = (m.get("ATC5") or "").strip()
            atc7 = (m.get("ATC7") or "").strip()
            method = normalize_freq(m.get("method"))
            presc_date = (m.get("date") or "").strip()
            days = int(m.get("days", 1) or 1)
            diag = (m.get("diag") or "").strip()

            unique_key = (nhicode, brand, presc_date, method)
            if unique_key in seen_keys:
                continue
            seen_keys.add(unique_key)

            start_dt = roc_to_datetime(presc_date)

            # Refill multiplier (慢箋 3 次調劑)
            ref_info = refill_tracker.get((nhicode, presc_date), {"count": 1, "single_days": days})
            ref_cnt = ref_info["count"]
            is_refill_3m = (ref_cnt >= 3 and days >= 28) or (days >= 80)
            total_days = days * ref_cnt if is_refill_3m else days

            end_dt = (start_dt + timedelta(days=max(total_days - 1, 0))) if start_dt else None
            is_active = (start_dt <= consult_dt <= end_dt) if (start_dt and end_dt and consult_dt) else False
            days_remaining = (end_dt - consult_dt).days if (consult_dt and end_dt and is_active) else 0

            # Therapeutic Classification
            category = self._classify_medication(brand, nhicode, ingredient)

            # Renal safety checks (evaluates both brand and generic ingredient)
            med_text_upper = f"{brand} {ingredient}".upper()
            contraindicated = False
            contra_reason = ""
            if is_esrd:
                if any(x in med_text_upper for x in ["METFORMIN", "JANUMET", "GLUCOPHAGE", "TRAJENTA DUO"]):
                    contraindicated = True
                    contra_reason = "ESRD/eGFR<15 嚴格禁忌雙胍類 (Metformin 乳酸中毒風險)"
                    alerts.append(f"⚠️ {brand} ({ingredient}): {contra_reason}")
                elif any(x in med_text_upper for x in ["DICLOFENAC", "IBUPROFEN", "NAPROXEN", "CELEBREX", "KETON", "KETOROLAC", "MEFENAMIC"]):
                    contraindicated = True
                    contra_reason = "嚴重腎功能障礙/ESRD 應避免全身性 NSAID"
                    alerts.append(f"⚠️ {brand} ({ingredient}): {contra_reason}")

            item = {
                "nhicode": nhicode,
                "medication": brand,
                "brand_name": clean_brand_name(brand),
                "brand_full": brand,
                "generic_name": ingredient,
                "ingredient": ingredient,
                "raw_ingredient": raw_ing,
                "atc5": atc5,
                "atc7": atc7,
                "dose": extract_med_dose(brand, raw_ing),
                "method": method,
                "presc_date": to_standard_date(presc_date),
                "days": days,
                "total_days": total_days,
                "is_chronic_refill": is_refill_3m,
                "start_date": datetime_to_standard(start_dt),
                "end_date": datetime_to_standard(end_dt),
                "is_active": is_active,
                "days_remaining": days_remaining,
                "category": category,
                "diagnosis": diag,
                "contraindicated": contraindicated,
                "contra_reason": contra_reason
            }

            if is_active:
                active_meds.append(item)
            else:
                completed_meds.append(item)

        # If no medications are active on consult_dt (e.g., queried with today's date against an earlier snapshot),
        # fall back to the patient's most recent prescription visit date so active regimen is still displayed.
        if not active_meds and completed_meds:
            valid_starts = [roc_to_datetime(m.get("start_date")) for m in completed_meds]
            valid_starts = [dt for dt in valid_starts if dt is not None]
            if valid_starts:
                latest_visit_dt = max(valid_starts)
                new_completed = []
                for m in completed_meds:
                    s_dt = roc_to_datetime(m.get("start_date"))
                    e_dt = roc_to_datetime(m.get("end_date"))
                    if s_dt and e_dt and (s_dt <= latest_visit_dt <= e_dt):
                        m["is_active"] = True
                        m["days_remaining"] = max((e_dt - latest_visit_dt).days, 0)
                        active_meds.append(m)
                    else:
                        new_completed.append(m)
                completed_meds = new_completed
                consult_dt = latest_visit_dt

        all_meds = active_meds + completed_meds
        timeline = self._build_medication_timeline(all_meds, consult_dt)

        return {
            "active_medications": active_meds,
            "completed_medications": completed_meds,
            "total_active": len(active_meds),
            "total_completed": len(completed_meds),
            "safety_alerts": alerts,
            "timeline": timeline
        }

    def _build_medication_timeline(
        self,
        all_meds: List[Dict[str, Any]],
        consult_dt: Optional[datetime]
    ) -> Dict[str, Any]:
        """
        Construct a longitudinal Medication Timeline Matrix:
        X-axis: Time / Dates (earliest on left, most current on the right).
        Dotted line at consult_dt (Current visit date) so drug remains (殘藥量) are visualized.
        Y-axis: Names of drugs with generic names, branded names, and doses.
        Shows overlaps of use of all drugs, prescription start and end dates.
        """
        drug_groups = {}
        for m in all_meds:
            gen = m.get("generic_name") or m.get("ingredient") or "Unknown"
            brand = m.get("brand_name") or m.get("medication") or ""
            key = (gen.lower().strip(), brand.lower().strip())

            if key not in drug_groups:
                drug_groups[key] = {
                    "generic_name": gen,
                    "brand_name": brand,
                    "brand_full": m.get("brand_full", brand),
                    "dose": m.get("dose") or extract_med_dose(m.get("brand_full", brand), m.get("raw_ingredient", "")),
                    "method": m.get("method", ""),
                    "category": m.get("category", "其他藥物"),
                    "is_active_now": False,
                    "current_remains": 0,
                    "episodes": []
                }

            d = drug_groups[key]
            if not d["dose"] and m.get("dose"):
                d["dose"] = m.get("dose")
            if not d["method"] and m.get("method"):
                d["method"] = m.get("method")

            s_dt = roc_to_datetime(m.get("start_date"))
            e_dt = roc_to_datetime(m.get("end_date"))

            remains = 0
            consumed = 0
            is_active = False
            if s_dt and e_dt and consult_dt:
                if s_dt <= consult_dt <= e_dt:
                    is_active = True
                    remains = (e_dt - consult_dt).days
                    consumed = (consult_dt - s_dt).days
                    d["is_active_now"] = True
                    d["current_remains"] = max(d["current_remains"], remains)
                elif consult_dt > e_dt:
                    consumed = (e_dt - s_dt).days
                    remains = 0
                elif consult_dt < s_dt:
                    remains = (e_dt - s_dt).days
                    consumed = 0

            d["episodes"].append({
                "start_date": m.get("start_date"),
                "end_date": m.get("end_date"),
                "days": m.get("days"),
                "total_days": m.get("total_days"),
                "is_chronic_refill": m.get("is_chronic_refill", False),
                "is_active": is_active,
                "remains": remains,
                "consumed": consumed,
                "dose": m.get("dose") or d["dose"],
                "method": m.get("method") or d["method"],
                "diagnosis": m.get("diagnosis", ""),
                "nhicode": m.get("nhicode", ""),
                "contraindicated": m.get("contraindicated", False),
                "contra_reason": m.get("contra_reason", "")
            })

        # Sort episodes per drug chronologically
        for d in drug_groups.values():
            d["episodes"].sort(key=lambda ep: ep["start_date"] or "")

        # Find min_date and max_date across all episodes
        all_starts = []
        all_ends = []
        for d in drug_groups.values():
            for ep in d["episodes"]:
                s = roc_to_datetime(ep["start_date"])
                e = roc_to_datetime(ep["end_date"])
                if s:
                    all_starts.append(s)
                if e:
                    all_ends.append(e)

        if consult_dt:
            all_starts.append(consult_dt)
            all_ends.append(consult_dt)

        min_dt = min(all_starts) if all_starts else (datetime.now() - timedelta(days=180))
        max_dt = max(all_ends) if all_ends else datetime.now()

        # Add 7 days padding after max_dt so drug remains have right margin
        padded_max_dt = max_dt + timedelta(days=7)

        # Sort drugs: Active medications first, then by latest episode start date descending
        sorted_drugs = sorted(
            drug_groups.values(),
            key=lambda d: (
                not d["is_active_now"],
                -max([roc_to_datetime(ep["start_date"]).timestamp() for ep in d["episodes"] if roc_to_datetime(ep["start_date"])] or [0])
            )
        )

        return {
            "clinic_date": datetime_to_standard(consult_dt) if consult_dt else "",
            "min_date": datetime_to_standard(min_dt),
            "max_date": datetime_to_standard(padded_max_dt),
            "total_days_span": max((padded_max_dt - min_dt).days, 1),
            "drugs": sorted_drugs,
            "total_drugs": len(sorted_drugs),
            "active_drugs_count": sum(1 for d in sorted_drugs if d["is_active_now"])
        }

    def _classify_medication(self, brand: str, nhicode: str, ingredient: str = "") -> str:
        """Categorize medication into clinical specialty group using brand and generic ingredient."""
        b = f"{brand} {ingredient}".upper()
        if any(x in b for x in ["EXNORTAN", "CONCOR", "NORVASC", "ISORMOL", "VALSARTAN", "AMLODIPINE", "BISO", "CADUET", "ISOSORBIDE", "CARVEDILOL", "LOSARTAN"]):
            return "心血管 / 降血壓 (Cardiovascular)"
        if any(x in b for x in ["REPAGLINIDE", "JANUMET", "METFORMIN", "DIAMICRON", "FORXIGA", "JARDIANCE", "GLIMEPIRIDE", "LINAGLIPTIN", "TRAJENTA", "INSULIN"]):
            return "新陳代謝 / 血糖 (Endocrine / DM)"
        if any(x in b for x in ["CALOWLIN", "CALCIUM ACETATE", "LOW-LIP", "FENOFIBRATE", "FOSRENOL", "SEVELAMER", "CIVIDOID", "HEPARINOID", "DARBEPOETIN", "NESP"]):
            return "腎臟 / 透析 / 降磷降血脂 (Renal & Dialysis)"
        if any(x in b for x in ["PLAVIX", "CLOPIDOGREL", "COFARIN", "WARFARIN", "BOKEY", "ASPIRIN", "ELIQUIS", "XARELTO", "APIXABAN", "RIVAROXABAN"]):
            return "抗血小板 / 抗凝血 (Antithrombotic)"
        if any(x in b for x in ["XANAX", "ALPRAZOLAM", "STILNOX", "SEROQUEL", "LEXAPRO", "ZOLPIDEM", "LORAZEPAM"]):
            return "精神 / 鎮靜安眠 (CNS & Sedatives)"
        if any(x in b for x in ["NEXIUM", "TAKECAB", "ULCER", "KASCOAL", "BOWEL", "FAMOTIDINE", "SENNAPUR", "SENNOSIDE"]):
            return "腸胃道 (Gastrointestinal)"
        return "一般 / 其他 (Others)"


    # Backwards-compatible aliases
    process_medications = _process_medications
    build_medication_timeline = _build_medication_timeline
    classify_medication = _classify_medication
