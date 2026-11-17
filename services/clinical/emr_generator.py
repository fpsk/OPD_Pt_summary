"""
1-Click Outpatient EMR Pre-Consultation SOAP Note Generator.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from services.patient_mcp_client import to_standard_date


class EmrNoteGenerator:
    """Synthesizes structured pre-consultation SOAP progress notes for hospital EMR."""

    def _generate_emr_note(
        self,
        p_id: str,
        clinic_date: str,
        badges: List[Dict[str, str]],
        surgeries: List[Any],
        diag_summary: Dict[str, Any],
        labs: Dict[str, Any],
        reports: List[Dict[str, Any]],
        meds: Dict[str, Any]
    ) -> str:
        """Format standardized EMR progress pre-consultation note with separated chronic/acute diagnoses."""
        badge_strs = [b["label"] for b in badges]
        lines = [
            "=== 門診病歷預覽摘要 (OPD Consultation Summary) ===",
            f"病患識別: {p_id} | 門診日期: {to_standard_date(clinic_date)}",
            f"臨床主要標記: {', '.join(badge_strs) if badge_strs else '無特定重大標記'}",
            "",
            "[1. Problem List & Surgical History (問題清單與術史)]",
        ]

        # Chronic Diagnoses Grouped
        chronic_list = diag_summary.get("chronic_list", []) if isinstance(diag_summary, dict) else []
        lines.append("• 慢性長期追蹤 (Chronic Conditions):")
        if chronic_list:
            for c in chronic_list[:8]:
                lines.append(f"  - {c.get('name')} ({c.get('code')})")
        else:
            lines.append("  - 無特定慢性病紀錄")

        # Acute Diagnoses with Recorded Dates
        acute_list = diag_summary.get("acute_list", []) if isinstance(diag_summary, dict) else []
        lines.append("• 近期急性疾患 (Acute Diagnoses - 含記錄日期):")
        if acute_list:
            for a in acute_list[:8]:
                lines.append(f"  - [{a.get('date', '近期')}] {a.get('name')} ({a.get('code')})")
        else:
            lines.append("  - 近期無急性問題紀錄")

        if surgeries:
            lines.append("• 手術與介入處置史 (含執行日期):")
            for s in surgeries[:6]:
                if isinstance(s, dict):
                    d_str = s.get('date', '歷史')
                    name_str = s.get('name', '')
                    det_str = f" - {s.get('detail')}" if s.get('detail') else ""
                    lines.append(f"  - [{d_str}] {name_str}{det_str}")
                else:
                    lines.append(f"  - {s}")

        lines.append("")
        lines.append("[2. Objective Findings (客觀檢驗與影像摘要)]")
        km = labs.get("key_metrics", {})
        lab_parts = []
        if "creatinine" in km:
            lab_parts.append(f"Cr: {km['creatinine']['value']} mg/dL")
        if "egfr" in km:
            lab_parts.append(f"eGFR: {km['egfr']['value']} mL/min")
        if "bun" in km:
            lab_parts.append(f"BUN: {km['bun']['value']} mg/dL")
        if "hb" in km:
            lab_parts.append(f"Hb: {km['hb']['value']} g/dL")
        if "glucose" in km:
            lab_parts.append(f"Glucose: {km['glucose']['value']} mg/dL")

        if lab_parts:
            lines.append("• 最近數據: " + ", ".join(lab_parts))

        # Radiology & Imaging: Highlight CT / MRI scans and latest clinical reports
        ct_mri_reports = [r for r in reports if r.get("is_ct") or r.get("is_mri")]
        other_reports = [r for r in reports if not (r.get("is_ct") or r.get("is_mri"))]

        if ct_mri_reports:
            lines.append("• 電腦斷層與磁振造影 (CT / MRI Studies):")
            for rep in ct_mri_reports[:4]:
                d_str = rep.get("date", "")
                study = rep.get("study_name") or rep.get("modality", "CT/MRI")
                imp = rep.get("sections", {}).get("impression", "")
                lesion_items = []
                for m in rep.get("measurements", []):
                    lbl = m.get("full_label") or (f"{m.get('lesion_name')}: {m.get('dimension')}" if m.get('lesion_name') else m.get('dimension'))
                    if lbl and lbl not in lesion_items:
                        lesion_items.append(lbl)
                meas_str = f" [病灶發現: {', '.join(lesion_items[:4])}]" if lesion_items else ""
                lines.append(f"  - [{d_str}] {study}{meas_str}")
                if imp:
                    lines.append(f"    結論: {imp[:120]}")

        if other_reports:
            lines.append("• 其他近期重要影像與檢查 (內視鏡/X光/超音波):")
            for rep in other_reports[:4]:
                d_str = rep.get("date", "")
                study = rep.get("study_name") or rep.get("modality", "")
                lesion_items = []
                for m in rep.get("measurements", []):
                    lbl = m.get("full_label") or (f"{m.get('lesion_name')}: {m.get('dimension')}" if m.get('lesion_name') else m.get('dimension'))
                    if lbl and lbl not in lesion_items:
                        lesion_items.append(lbl)
                meas_str = f" [病灶/處置發現: {', '.join(lesion_items[:3])}]" if lesion_items else ""
                imp = rep.get("sections", {}).get("impression", "")
                lines.append(f"  - [{d_str}] {study}{meas_str}")
                if imp and len(imp) > 3:
                    lines.append(f"    摘要: {imp[:100]}")

        lines.append("")
        lines.append(f"[3. Active Medications ({meds.get('total_active', 0)} 項現行用藥)]")
        for m in meds.get("active_medications", [])[:12]:
            ref_badge = "[慢箋]" if m.get("is_chronic_refill") else ""
            brand = m.get('brand_name') or m.get('medication')
            generic = m.get('generic_name') or m.get('ingredient')
            gen_str = f" [成分: {generic}]" if generic and generic.upper() not in brand.upper() else ""
            lines.append(f"• {brand}{gen_str} ({m.get('method')}) {ref_badge} (預計服至: {m.get('end_date')}, 餘 {m.get('days_remaining')} 天)")

        if meds.get("safety_alerts"):
            lines.append("")
            lines.append("[4. Clinical Safety Alerts (臨床用藥警示)]")
            for a in meds.get("safety_alerts"):
                lines.append(f"• {a}")

        return "\n".join(lines)

    # Backwards-compatible alias
    generate_emr_note = _generate_emr_note
