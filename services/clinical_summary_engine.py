"""
Clinical Summary Engine for OPD Pre-view & Review.
Synthesizes Patient Conditions, Objective Findings, and Current Medications
into structured clinical views and EMR pre-consultation notes.
"""

from typing import Any, Dict, List, Optional, Set

import config
from services.clinical import (
    BadgeSynthesizer,
    ConditionProcessor,
    EmrNoteGenerator,
    LabProcessor,
    MedProcessor,
    classify_lab_group,
    clean_brand_name,
    clean_display_reference_range,
    clean_ingredient,
    clean_lab_item_name,
    extract_med_dose,
    parse_reference_range,
    trim_display_zeros,
)
from services.patient_mcp_client import (
    SNAPSHOT_DATES,
    PatientMcpClient,
    calculate_age_from_birthdate,
    extract_demographics_from_dict,
    roc_to_datetime,
    to_roc_date,
    to_standard_date,
)
from services.report_nlp_engine import ReportNlpEngine


class ClinicalSummaryEngine:
    """Core synthesis engine for Outpatient Department clinical summaries."""

    def __init__(self):
        self.mcp_client = PatientMcpClient()
        self.nlp_engine = ReportNlpEngine()
        self.lab_processor = LabProcessor()
        self.med_processor = MedProcessor()
        self.condition_processor = ConditionProcessor()
        self.badge_synthesizer = BadgeSynthesizer()
        self.emr_generator = EmrNoteGenerator()

    # Backwards-compatible method delegates
    def _is_pathology_report(self, record: Dict[str, Any]) -> bool:
        return self.condition_processor.is_pathology_report(record)

    def _process_laboratory_tests(self, raw_labs: List[Dict[str, Any]], patient_age: Optional[float] = None, patient_gender: Optional[str] = None) -> Dict[str, Any]:
        return self.lab_processor.process_laboratory_tests(raw_labs, patient_age, patient_gender)

    def _build_lab_flowsheet(self, entries: List[Dict[str, Any]], patient_age: Optional[float] = None, patient_gender: Optional[str] = None) -> Dict[str, Any]:
        return self.lab_processor.build_lab_flowsheet(entries, patient_age, patient_gender)

    def _calculate_liver_scores(self, *args, **kwargs) -> Dict[str, Any]:
        return self.lab_processor.calculate_liver_scores(*args, **kwargs)

    def _process_medications(self, raw_meds: List[Dict[str, Any]], consult_dt: Optional[Any], lab_panel: Dict[str, Any]) -> Dict[str, Any]:
        return self.med_processor.process_medications(raw_meds, consult_dt, lab_panel)

    def _build_medication_timeline(self, meds_records: List[Dict[str, Any]], consult_dt: Optional[Any]) -> Dict[str, Any]:
        return self.med_processor.build_medication_timeline(meds_records, consult_dt)

    def _classify_medication(self, brand: str, nhicode: str, ingredient: str = "") -> str:
        return self.med_processor.classify_medication(brand, nhicode, ingredient)

    def _synthesize_clinical_badges(self, lab_panel: Dict[str, Any], surgical_history_set: Set[str], all_condition_names: Set[str], med_summary: Dict[str, Any]) -> List[Dict[str, str]]:
        return self.badge_synthesizer.synthesize_clinical_badges(lab_panel, surgical_history_set, all_condition_names, med_summary)

    def _process_diagnoses(self, raw_imgs: List[Dict[str, Any]], raw_meds: List[Dict[str, Any]], raw_labs: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.condition_processor.process_diagnoses(raw_imgs, raw_meds, raw_labs)

    def _process_surgical_and_interventions(self, raw_imgs: List[Dict[str, Any]], pathology_records: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        return self.condition_processor.process_surgical_and_interventions(raw_imgs, pathology_records)

    def _generate_emr_note(self, *args, **kwargs) -> str:
        return self.emr_generator.generate_emr_note(*args, **kwargs)

    def generate_patient_summary(
        self,
        patient_id: str,
        clinic_date: str = "1150721",
        daterange: int = getattr(config, 'DEFAULT_DATERANGE', 1095),
        chart_no: Optional[str] = None,
        birth_date: Optional[str] = None,
        age: Optional[Any] = None,
        name: Optional[str] = None,
        gender: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate complete OPD summary bundle for a patient.
        """
        p_id = (patient_id or "").strip().upper()
        c_date = (clinic_date or "1150721").strip()
        consult_dt = roc_to_datetime(c_date)
        standard_clinic_date = to_standard_date(c_date)

        # 1. Fetch raw data from Hospital Gateway (passes to_roc_date internally)
        meds_res = self.mcp_client.get_medications(p_id, c_date, daterange)
        labs_res = self.mcp_client.get_lab_tests(p_id, c_date, daterange)
        imgs_res = self.mcp_client.get_image_summary(p_id, c_date)

        raw_meds = meds_res.get("latestMed", []) if isinstance(meds_res, dict) else []
        raw_labs = labs_res.get("latestLab", []) if isinstance(labs_res, dict) else []
        raw_imgs = imgs_res.get("imageSummary", []) if isinstance(imgs_res, dict) else []

        # If the requested date returned no records (e.g. launched with today's date), check patient's roster clinic_date and known hospital snapshot dates
        if not raw_meds and not raw_labs and not raw_imgs:
            candidate_dates = self.mcp_client.roster.candidate_dates(p_id, extra=SNAPSHOT_DATES)
            for fallback_date in candidate_dates:
                if fallback_date == c_date:
                    continue
                f_meds_res = self.mcp_client.get_medications(p_id, fallback_date, daterange)
                f_labs_res = self.mcp_client.get_lab_tests(p_id, fallback_date, daterange)
                f_imgs_res = self.mcp_client.get_image_summary(p_id, fallback_date)
                f_meds = f_meds_res.get("latestMed", []) if isinstance(f_meds_res, dict) else []
                f_labs = f_labs_res.get("latestLab", []) if isinstance(f_labs_res, dict) else []
                f_imgs = f_imgs_res.get("imageSummary", []) if isinstance(f_imgs_res, dict) else []
                if f_meds or f_labs or f_imgs:
                    meds_res, labs_res, imgs_res = f_meds_res, f_labs_res, f_imgs_res
                    raw_meds, raw_labs, raw_imgs = f_meds, f_labs, f_imgs
                    break

        # Check API status
        msg_code = meds_res.get("messageCode", "000")
        if msg_code == "001" and not raw_meds and not raw_labs and not raw_imgs:
            return {
                "status": "not_found",
                "patient_id": p_id,
                "clinic_date": c_date,
                "message": f"查無病患紀錄 (代碼 {msg_code})。請確認身分證號碼或回溯門診日期。"
            }

        # Extract any demographic metadata embedded in the gateway responses or passed via API
        gw_demo: Dict[str, Any] = {}
        for res_obj in (meds_res, labs_res, imgs_res):
            if isinstance(res_obj, dict):
                for k, v in extract_demographics_from_dict(res_obj, reference_date=c_date).items():
                    if k not in gw_demo and v not in (None, ""):
                        gw_demo[k] = v

        eff_chart_no = chart_no if chart_no not in (None, "") else gw_demo.get("chart_no")
        eff_birth_date = birth_date if birth_date not in (None, "") else gw_demo.get("birth_date")
        eff_age = age if age not in (None, "") else gw_demo.get("age")
        eff_name = name if name not in (None, "") else gw_demo.get("name")
        eff_gender = gender if gender not in (None, "") else gw_demo.get("gender")

        if any(v not in (None, "") for v in (eff_chart_no, eff_birth_date, eff_age, eff_name, eff_gender)):
            self.mcp_client.update_patient_demographics(
                p_id,
                chart_no=eff_chart_no,
                birth_date=eff_birth_date,
                age=eff_age,
                name=eff_name,
                gender=eff_gender,
                reference_date=c_date
            )

        # Demographics from Roster + Runtime Push Cache (with ROC birthdate -> age conversion)
        demo = self.mcp_client.get_patient_demographics(p_id, reference_date=c_date)
        pt_age: Optional[float] = None
        if demo.get("birth_date"):
            calc_age = calculate_age_from_birthdate(demo.get("birth_date"), reference_date=c_date)
            if calc_age is not None:
                pt_age = float(calc_age)
        if pt_age is None and demo.get("age"):
            try:
                val = float(demo.get("age"))
                if 0 < val <= 130:
                    pt_age = val
            except Exception:
                pt_age = None

        pt_gender = demo.get("gender", "") if isinstance(demo, dict) else ""
        if not pt_gender and len(p_id) >= 2:
            if p_id[1] == "1":
                pt_gender = "男"
            elif p_id[1] == "2":
                pt_gender = "女"

        # Separate surgical pathology narrative reports from routine numerical laboratory tests
        pure_labs = []
        pathology_records = []
        for l in raw_labs:
            if self.condition_processor.is_pathology_report(l):
                pathology_records.append(l)
            else:
                pure_labs.append(l)

        # 2. Extract and Process Laboratory Tests & Trends (pathology removed from lab table)
        lab_panel = self.lab_processor.process_laboratory_tests(pure_labs, patient_age=pt_age, patient_gender=pt_gender)

        # 3. Extract and Process Narrative Reports (Radiology, Procedures, and Surgical Pathology)
        processed_reports = []
        for record in raw_imgs:
            parsed = self.nlp_engine.parse_imaging_record(record)
            processed_reports.append(parsed)

        for prec in pathology_records:
            parsed_path = self.nlp_engine.parse_pathology_record(prec)
            processed_reports.append(parsed_path)

        # Sort all diagnostic narrative reports chronologically descending (newest first)
        processed_reports.sort(key=lambda r: r.get("date", "") or "", reverse=True)

        # 4. Extract Surgical Procedures and PTA Interventions with Execution Dates
        surgical_procedures = self.condition_processor.process_surgical_and_interventions(raw_imgs, pathology_records)
        surgical_history_set = set([p.get("name", "") for p in surgical_procedures])

        # 5. Extract and Process Medications & 慢箋 (Chronic Refills)
        med_summary = self.med_processor.process_medications(raw_meds, consult_dt, lab_panel)

        # 6. Extract & Categorize Diagnoses into Chronic and Acute (with recorded dates)
        diag_summary = self.condition_processor.process_diagnoses(raw_imgs, raw_meds, raw_labs)

        # 7. Synthesize Chronic Clinical Badges & Risk Profile
        all_condition_names = set([d["name"] for d in diag_summary["chronic_list"] + diag_summary["acute_list"]])
        clinical_badges = self.badge_synthesizer.synthesize_clinical_badges(lab_panel, surgical_history_set, all_condition_names, med_summary)

        # 8. Generate 1-Click EMR Pre-Consultation SOAP Note
        emr_note = self.emr_generator.generate_emr_note(
            p_id, c_date, clinical_badges, surgical_procedures,
            diag_summary, lab_panel, processed_reports, med_summary
        )

        egfr_val = lab_panel.get("key_metrics", {}).get("egfr", {}).get("value")
        cr_val = lab_panel.get("key_metrics", {}).get("creatinine", {}).get("value")
        display_age = str(int(round(pt_age))) if pt_age is not None else (str(demo.get("age", "")).strip() or "--")

        return {
            "status": "success",
            "patient_id": p_id,
            "clinic_date": to_roc_date(c_date),
            "standard_date": standard_clinic_date,
            "profile": {
                "id_no": p_id,
                "name": demo.get("name") or f"門診病患 ({p_id})",
                "gender": pt_gender or demo.get("gender", "") or "--",
                "age": display_age,
                "birth_date": demo.get("birth_date") or "",
                "chart_no": demo.get("chart_no") or "MCP-CLOUD",
                "badges": clinical_badges,
                "egfr": egfr_val,
                "creatinine": cr_val,
                "hb": lab_panel.get("key_metrics", {}).get("hb", {}).get("value"),
                "glucose": lab_panel.get("key_metrics", {}).get("glucose", {}).get("value")
            },
            "conditions": {
                "chronic_diagnoses": diag_summary["chronic_list"],
                "acute_diagnoses": diag_summary["acute_list"],
                "chronic_count": len(diag_summary["chronic_list"]),
                "acute_count": len(diag_summary["acute_list"]),
                "surgical_procedures": surgical_procedures
            },
            "findings": {
                "lab_panel": lab_panel,
                "radiology_reports": processed_reports,
                "total_reports": len(processed_reports)
            },
            "medications": med_summary,
            "emr_preconsult_note": emr_note
        }


__all__ = [
    "ClinicalSummaryEngine",
    "clean_lab_item_name",
    "parse_reference_range",
    "trim_display_zeros",
    "clean_display_reference_range",
    "classify_lab_group",
    "clean_ingredient",
    "clean_brand_name",
    "extract_med_dose",
]
