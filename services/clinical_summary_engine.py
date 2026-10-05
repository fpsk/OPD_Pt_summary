"""
Clinical Summary Engine for OPD Pre-view & Review.
Synthesizes Patient Conditions, Objective Findings, and Current Medications
into structured clinical views and EMR pre-consultation notes.
"""

import re
import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

import config
from services.patient_mcp_client import (
    PatientMcpClient,
    roc_to_datetime,
    datetime_to_standard,
    to_standard_date,
    normalize_freq
)
from services.report_nlp_engine import ReportNlpEngine


def clean_lab_item_name(item: str, order: str) -> str:
    """Standardize and resolve garbled lab test names into clean Medical English names."""
    item_s = (item or "").strip()
    order_s = (order or "").strip()
    order_parts = order_s.split('||')
    panel_desc = order_parts[1].strip() if len(order_parts) > 1 else order_s
    sub_desc = order_parts[2].strip() if len(order_parts) > 2 else item_s

    panel_lower = panel_desc.lower()
    sub_lower = (sub_desc or item_s).lower()
    combined = f"{item_s} {panel_desc} {sub_desc}".lower()

    # Liver Function
    if ";(s-got/ast)" in panel_lower or re.search(r'\b(ast|got)\b', sub_lower) or "草酸麩酸" in combined:
        return "AST / GOT"
    if ";(s-gpt/alt)" in panel_lower or re.search(r'\b(alt|gpt)\b', sub_lower) or "丙酮酸轉氨" in combined:
        return "ALT / GPT"
    if "alk-p" in panel_lower or "alp" in panel_lower or "鹼性磷酸" in combined or "alkaline phosphatase" in combined:
        return "Alk-P (ALP)"
    if "r-gt" in panel_lower or "ggt" in panel_lower or "麩胺醯" in combined:
        return "r-GT (GGT)"
    if "bilirubin" in panel_lower or "bilirubin" in sub_lower or "膽紅素" in combined:
        if "direct" in panel_lower or "direct" in sub_lower or "直接" in combined:
            return "Direct Bilirubin"
        return "Total Bilirubin"
    if "albumin" in panel_lower or "albumin" in sub_lower or "白蛋白" in combined:
        if "micro" not in combined and "urine" not in combined and "尿" not in combined:
            return "Albumin"
    if "total protein" in combined or "總蛋白" in combined:
        if "urine" not in combined and "尿" not in combined and "ascitic" not in combined and "random" not in combined:
            return "Total Protein"
        elif "urine" in combined or "尿" in combined:
            return "Urine Total Protein"
    if "afp" in panel_lower or "afp" in sub_lower or "胎兒蛋白" in combined:
        return "AFP (Alpha-Fetoprotein)"
    if "ammonia" in panel_lower or "血氨" in combined:
        return "Ammonia"

    # Renal Function
    if "egfr-ckd-epi" in panel_lower or "egfr" in sub_lower or "腎絲球" in combined:
        return "eGFR"
    if "creatinine (b)" in panel_lower or (re.search(r'\b(cre|crtn|creatinine)\b', sub_lower) and "urine" not in combined and "24hr" not in combined) or "肌酸酐" in combined:
        if "urine" not in combined and "24hr" not in combined and "尿" not in combined and "screening" not in sub_lower:
            return "Creatinine"
    if "creatinine (u)" in panel_lower or "24hrs urine" in combined or ("creatinine" in combined and ("urine" in combined or "尿" in combined)):
        return "Urine Creatinine"
    if "bun" in combined or "尿素氮" in combined:
        if "洗後" in combined or "後" in combined:
            return "BUN (Post-dialysis)"
        return "BUN"
    if "uric acid" in combined or "尿酸" in combined or re.search(r'\bua\b', combined):
        return "Uric Acid"
    if "microalbumin" in panel_lower or "微白蛋白" in combined:
        return "Microalbumin"

    # Hematology & Coagulation
    if ";(platelet count)" in panel_lower or "platelet" in sub_lower or re.search(r'\bplt\b', sub_lower) or "血小板" in combined:
        return "Platelet"
    if "wbc" in sub_lower or "白血球" in combined:
        return "WBC"
    if "rbc" in sub_lower or "紅血球" in combined:
        return "RBC"
    if "mcv" in sub_lower:
        return "MCV"
    if "mchc" in sub_lower:
        return "MCHC"
    if "mch" in sub_lower:
        return "MCH"
    if "rdw-cv" in sub_lower:
        return "RDW-CV"
    if "rdw-sd" in sub_lower:
        return "RDW-SD"
    if "hematocrit" in sub_lower or "hct" in sub_lower or sub_lower == "ht" or "血球比容" in combined:
        return "Hematocrit (Hct)"
    if ("hemoglobin" in sub_lower or re.search(r'\bhb\b', sub_lower) or "血色素" in combined) and not any(x in combined for x in ["hba1c", "a1c"]):
        return "Hemoglobin (Hb)"
    if "lymphocyte" in combined or "淋巴球" in combined:
        return "Lymphocyte %"
    if re.search(r'\baptt\b|pttp\b|aptt control', combined):
        if "control" in combined:
            return "aPTT Control"
        return "aPTT"
    if re.search(r'\bpt\b|prothrombin time', combined) or "凝血酶原" in combined:
        return "PT (Prothrombin Time)"
    if re.search(r'\binr\b', combined):
        return "INR"
    if "fibrinogen" in combined or "纖維蛋白原" in combined:
        return "Fibrinogen"
    if "d-dimer" in combined or "d 雙合體" in combined:
        return "D-Dimer"
    if "fdp" in combined or "降解產物" in combined:
        return "FDP"
    if "abo" in combined or "blood grouping" in combined:
        return "ABO Blood Group"
    if "rh" in combined:
        return "Rh Type"
    if "crossmatching" in combined or "交叉配合" in combined:
        return "Crossmatch"
    if "antibody screening" in combined or "不規則抗體" in combined:
        return "Antibody Screen"

    # Metabolic
    if "glucose-ante cibum" in panel_lower or "glucose ac" in sub_lower or "glu-ac" in sub_lower or "飯前血糖" in combined:
        return "Glucose AC"
    if "glucose" in combined or "血糖" in combined:
        return "Glucose"
    if "hba1c" in panel_lower or "hba1c" in sub_lower or "糖化" in combined or "醣化" in combined:
        return "HbA1c"
    if "hdl-c" in panel_lower or "hdl" in sub_lower:
        return "HDL-C"
    if "ldl-c" in panel_lower or "ldl" in sub_lower:
        return "LDL-C"
    if "cholestero1, total" in panel_lower or "cholesterol, total" in panel_lower or ("chol" in sub_lower and "total" in combined):
        return "Total Cholesterol"
    if "triglyceride" in panel_lower or "tg" in sub_lower or "三酸甘油" in combined:
        return "Triglyceride"
    if re.search(r'\b(sodium|鈉)\b', combined) or sub_lower == "na":
        return "Sodium (Na)"
    if re.search(r'\b(potassium|鉀)\b', combined) or sub_lower == "k":
        return "Potassium (K)"
    if re.search(r'\b(chloride|氯)\b', combined) or sub_lower == "cl":
        return "Chloride (Cl)"
    if re.search(r'\b(calcium|鈣)\b', combined) or sub_lower in ["ca", "ca (b)"]:
        return "Calcium (Ca)"
    if re.search(r'\b(phosphorus|phosphate|磷)\b', combined) or sub_lower == "p":
        return "Phosphorus (P)"
    if re.search(r'\b(magnesium|鎂)\b', combined) or sub_lower == "mg":
        return "Magnesium (Mg)"

    # Immunological
    if "c.r.p" in combined or "c-reactive" in combined or sub_lower == "crp" or "ｃ反應性蛋白" in combined:
        return "CRP"
    if "dna quantitative" in panel_lower or "hbv dna" in combined:
        return "HBV DNA (Quantitative)"
    if "hcv ab" in panel_lower or "hcv" in sub_lower or "c型肝炎" in combined:
        return "HCV Ab"
    if "hbsag" in combined or "b型肝炎表面抗原" in combined:
        return "HBsAg"
    if "anti-hbs" in combined:
        return "Anti-HBs"
    if "hbeag" in combined or "b型肝炎 e 抗原" in combined:
        return "HBeAg"
    if "anti-hbe" in combined:
        return "Anti-HBe"
    if "anti-hbc" in combined:
        return "Anti-HBc"
    if "c3" in combined and "c4" in combined:
        return "C3 / C4"
    if "anti-cell ab" in combined or re.search(r'\bana\b', combined):
        return "ANA (Anti-Cell Ab)"
    if "免疫球蛋白 e" in combined or "ige" in combined:
        return "IgE"
    if "免疫球蛋白a" in combined or "iga" in combined:
        return "IgA"

    # Other functions
    if "troponin i" in combined or "心肌旋轉蛋白" in combined:
        return "Troponin I"
    if "ck-mb" in combined:
        return "CK-MB"
    if re.search(r'\b(cpk|ck)\b', combined):
        return "CPK / CK"
    if "nt-probnp" in combined:
        return "NT-proBNP"
    if "tsh" in combined:
        return "TSH"
    if "free t4" in combined or "游離甲狀腺素" in combined:
        return "Free T4"
    if "pth-i" in combined or "副甲狀腺素" in combined:
        return "Intact PTH"
    if "stool occult blood" in combined or "糞便潛血" in combined or "occult blood" in combined:
        return "Stool Occult Blood"
    if "ferritin" in combined or "鐵蛋白" in combined:
        return "Ferritin"
    if re.search(r'\b(fe|iron)\b', combined) or "血清鐵" in combined:
        return "Serum Iron (Fe)"
    if "tibc" in combined or "總鐵結合能" in combined:
        return "TIBC"

    # If item still has unprintable characters, try extracting from order ;( ... )
    if '\ufffd' in item_s or len(item_s) == 0 or '?' in item_s:
        m = re.search(r';\(([^)]+)\)', order_s)
        if m:
            cand = m.group(1).strip()
            if cand:
                return cand

    return item_s if item_s else (order_s or "Unknown Lab")


def parse_reference_range(ref_str: str, gender: str = "") -> Tuple[Optional[float], Optional[float]]:
    """
    Parse a reference range string into (low_limit, high_limit).
    Handles:
      - Bracketed pair: '[65][175]', '[17.3][74.1]', '[0][10]'
      - Standard range: '65-175', '17.3~74.1', '0.2 - 1.2', '[(125 - 220)...]'
      - Upper limit only: '< 150', '＜140', '≦8.78', '<= 200', '[< 200 mg/dL][]'
      - Lower limit only: '> 10', '＞10', '≧10', '>= 10'
      - Gender specific subparts: 'M; 4.4-7.6, F; 2.3-6.6'
    """
    if not ref_str:
        return None, None
    s = ref_str.strip()

    # Check for gender specific sub-part if present, e.g. M; 4.4-7.6 or F; 2.3-6.6
    if gender:
        g = gender.upper()
        if g.startswith('M') or '男' in g:
            m_gen = re.search(r'[M男][~;:\s]+([0-9.]+\s*[-~至–]\s*[0-9.]+)', s, re.I)
            if m_gen:
                s = m_gen.group(1)
        elif g.startswith('F') or '女' in g:
            m_gen = re.search(r'[F女][~;:\s]+([0-9.]+\s*[-~至–]\s*[0-9.]+)', s, re.I)
            if m_gen:
                s = m_gen.group(1)

    # 1. Bracketed pair: [65][175] or [17.3][74.1] or [0][10]
    m1 = re.search(r'\[\s*([0-9]+(?:\.[0-9]+)?)\s*\]\s*\[\s*([0-9]+(?:\.[0-9]+)?)\s*\]', s)
    if m1:
        try:
            return float(m1.group(1)), float(m1.group(2))
        except Exception:
            pass

    # 2. Standard range with separator: 0.2-1.2 or 125 - 220 or 1000 -3400
    m2 = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(?:-|~|至|–)\s*([0-9]+(?:\.[0-9]+)?)', s)
    if m2:
        try:
            return float(m2.group(1)), float(m2.group(2))
        except Exception:
            pass

    # 3. Upper limit only: < 150, ＜140, ≦8.78, <= 200
    m3 = re.search(r'(?:<|<=|＜|≦)\s*([0-9]+(?:\.[0-9]+)?)', s)
    if m3:
        try:
            return None, float(m3.group(1))
        except Exception:
            pass

    # 4. Lower limit only: > 10, ＞10, ≧10, >= 10
    m4 = re.search(r'(?:>|>=|＞|≧)\s*([0-9]+(?:\.[0-9]+)?)', s)
    if m4:
        try:
            return float(m4.group(1)), None
        except Exception:
            pass

    return None, None


def classify_lab_group(item_name: str, raw_item: str = "", order: str = "") -> str:
    """
    Classify a laboratory analyte into one of the 6 physiological systems:
    1. 'liver': Liver function, enzymes, synthesis & viral hepatitis fibrosis
    2. 'hematological': Complete blood count (CBC), differential, coagulation & blood bank
    3. 'renal': Renal filtration, urea, uric acid & urinalysis protein/creatinine
    4. 'metabolic': Glucose, HbA1c, lipids, electrolytes & acid-base
    5. 'immunological': Inflammatory markers, hepatitis serology & autoimmune antibodies
    6. 'others': Endocrine/thyroid, cardiac biomarkers, routine UA/stool & microbiology
    """
    comb = f"{item_name} {raw_item} {order}".lower()
    is_aptt = bool(re.search(r'\baptt\b|ptt\b', comb))
    is_urine_alb = ('micro' in comb) or ('urine' in comb) or ('尿' in comb)

    # 1. Liver
    if not is_aptt and (
        any(k in comb for k in [
            'got', 'ast', '草酸', 'gpt', 'alt', '丙酮酸', 'r-gt', 'ggt', '麩胺醯',
            'alk-p', 'alp', '鹼性磷酸', 'alkaline phosphatase',
            'bilirubin', '膽紅素', 'ammonia', '血氨', 'afp', '胎兒蛋白',
            'fib-4', 'fib4', 'apri', 'pivka', 'dcp'
        ])
        or re.search(r'\binr\b', comb)
        or (re.search(r'\bpt\b', comb) and not any(x in comb for x in ['gpt', 'platelet', 'aptt', 'ptt', 'opt']))
        or (('albumin' in comb or '白蛋白' in comb) and not is_urine_alb)
        or (any(k in comb for k in ['total protein', '總蛋白']) and not ('urine' in comb or '尿' in comb or 'ascitic' in comb))
    ):
        return 'liver'

    # 2. Hematological
    if (
        is_aptt
        or any(k in comb for k in [
            'wbc', '白血球', 'rbc', '紅血球', 'platelet', '血小板', 'plt', 'hct', '血球比容',
            'hematocrit', 'mcv', 'mch', 'mchc', 'rdw', 'mpv', 'differential', 'seg', 'band',
            'lymphocyte', 'monocyte', 'eosinophil', 'basophil', 'blast', 'atypical lymph',
            'fibrinogen', 'd-dimer', 'fdp', 'bleeding time', 'clotting time',
            'blood grouping', 'crossmatching', 'abo', 'rh factor', 'antibody screening', '輸血',
            'a-cell', 'b-cell', 'anti-a', 'anti-b', 'anti-d', 'crossmatch'
        ])
        or ((re.search(r'\bhb\b', comb) or 'hemoglobin' in comb or '血紅素' in comb or '血色素' in comb)
            and not any(x in comb for x in ['hba1c', 'a1c', '糖化', '醣化']))
    ):
        return 'hematological'

    # 3. Renal
    if (
        any(k in comb for k in [
            'egfr', '腎絲球', 'creatinine', '肌酸酐', 'bun', '尿素氮', 'uric acid', '尿酸',
            'microalbumin', '微白蛋白', 'uacr', 'upcr', 'ccr'
        ])
        or re.search(r'\bua\b', comb)
        or (('urine' in comb or '尿' in comb) and any(k in comb for k in ['protein', 'albumin', 'creatinine', 'tp']))
    ):
        return 'renal'

    # 4. Immunological (Checked before metabolic so CRP is not captured by single-letter metabolic checks)
    if (
        any(k in comb for k in [
            'crp', 'c-reactive', 'c.r.p', 'esr', '紅血球沉降', 'procalcitonin', 'pct',
            'hbsag', 'anti-hbs', 'hbeag', 'anti-hbe', 'anti-hbc', 'hbv', 'hcv',
            'b型肝炎', 'c型肝炎', 'c肝', 'b肝', 'hiv', 'vdrl', 'rpr', 'tppa', 'syphilis', '梅毒',
            'anti-cell', 'rf', 'rheumatoid', 'anti-ccp', 'c3', 'c4', 'complement',
            'iga', 'igg', 'igm', 'ige', 'immunoglobulin', '免疫球蛋白', 'anca', 'dsdna', 'anti-dna',
            'autoantibody', '抗體', 'widal', 'weils', 'cryoglobulin'
        ])
        or re.search(r'\bana\b', comb)
    ):
        return 'immunological'

    # 5. Metabolic
    if (
        any(k in comb for k in [
            'glucose', '血糖', 'glu', 'fpg', 'hba1c', 'a1c', '糖化血色素', '醣化血色素',
            'cholesterol', '膽固醇', 'chol', 'triglyceride', 'tg', '三酸甘油脂', '三酸甘油',
            'hdl', 'ldl', 'vldl', 'lipid', 'sodium', 'potassium', 'chloride', 'calcium',
            'phosphorus', 'phosphate', 'magnesium', 'bicarbonate', 'hco3', 'co2',
            'osmolality', '滲透壓', 'ketone', '酮體', 'lactic', 'lactate', '乳酸',
            'pco2', 'po2', 'o2sat', 'b.e.b'
        ])
        or re.search(r'\b(na|k|cl|ca|mg|ph)\b', comb)
        or any(k in comb for k in ['鈉', '鉀', '氯', '鈣', '磷', '鎂'])
    ):
        return 'metabolic'

    return 'others'



def clean_ingredient(raw_ing: str, brand: str = "") -> str:
    """Normalize active generic ingredient and fallback if missing."""
    ing = (raw_ing or "").strip()
    if not ing and brand:
        # Try extracting from parentheses if brand has (HEPARINOID) or (ISOSORBIDE)
        m = re.search(r'\(([A-Za-z0-9\s\+\-\/\.\=\%]+)\)', brand)
        if m:
            cand = m.group(1).strip()
            if len(cand) >= 3 and not any(c in cand for c in ["TAB", "CAP", "GEL", "PO", "IV", "SC", "鋁箔", "膠箔"]):
                ing = cand.title()
    if not ing:
        return ""
    # Standardize full-width or half-width semicolons to ' + ' for combination products
    ing = ing.replace("；", " + ").replace(";", " + ")
    ing = re.sub(r'\s+', ' ', ing).strip()
    return ing


def clean_brand_name(brand: str) -> str:
    """Clean packaging tags like (鋁箔/膠箔) from brand name for cleaner display."""
    if not brand:
        return ""
    cleaned = re.sub(r'\s*\((?:鋁箔|膠箔|鋁箔\/膠箔|三\/一|健保|公立|自費)[^)]*\)', '', brand)
    return cleaned.strip() or brand


def extract_med_dose(brand: str, raw_ing: str = "") -> str:
    """Extract standard dose / strength string (e.g. 5mg, 5/80mg, 667mg, 0.5mg, 40mcg, 10%)."""
    text = f"{brand} {raw_ing}".strip()
    if not text:
        return ""
    m1 = re.search(r'(\d+(?:\.\d+)?\s*[\/\+]\s*\d+(?:\.\d+)?\s*(?:mg|g|mcg|ug|ml|iu|u|%))\b', text, re.I)
    if m1:
        return m1.group(1).replace(" ", "")
    m2 = re.search(r'(\d+(?:\.\d+)?\s*(?:mg(?:\/(?:ml|gm|g))?|mcg(?:\/ml)?|ug|g(?:\/ml)?|ml|iu|u|%))\b', text, re.I)
    if m2:
        return m2.group(1).strip()
    m3 = re.search(r'\b(concor|bisoprolol)\s+(\d+(?:\.\d+)?)\b', text, re.I)
    if m3:
        return f"{m3.group(2)}mg"
    m4 = re.search(r'\b(?:tab|cap|tablet|capsule)s?\s+(\d+(?:\.\d+)?)\b', text, re.I)
    if m4:
        return f"{m4.group(1)}mg"
    return ""


class ClinicalSummaryEngine:
    """Core synthesis engine for Outpatient Department clinical summaries."""

    def __init__(self):
        self.mcp_client = PatientMcpClient()
        self.nlp_engine = ReportNlpEngine()

    def generate_patient_summary(
        self,
        patient_id: str,
        clinic_date: str = "2026/09/01",
        daterange: int = getattr(config, 'DEFAULT_DATERANGE', 1095)
    ) -> Dict[str, Any]:
        """
        Generate complete OPD summary bundle for a patient.
        """
        p_id = (patient_id or "").strip()
        c_date = (clinic_date or "2026/09/01").strip()
        consult_dt = roc_to_datetime(c_date)
        standard_clinic_date = to_standard_date(c_date)

        # 1. Fetch raw data from Hospital Gateway (passes to_roc_date internally)
        meds_res = self.mcp_client.get_medications(p_id, c_date, daterange)
        labs_res = self.mcp_client.get_lab_tests(p_id, c_date, daterange)
        imgs_res = self.mcp_client.get_image_summary(p_id, c_date)

        raw_meds = meds_res.get("latestMed", []) if isinstance(meds_res, dict) else []
        raw_labs = labs_res.get("latestLab", []) if isinstance(labs_res, dict) else []
        raw_imgs = imgs_res.get("imageSummary", []) if isinstance(imgs_res, dict) else []

        # Check API status
        msg_code = meds_res.get("messageCode", "000")
        if msg_code == "001" and not raw_meds and not raw_labs and not raw_imgs:
            return {
                "status": "not_found",
                "patient_id": p_id,
                "clinic_date": c_date,
                "message": f"查無病患紀錄 (代碼 {msg_code})。請確認身分證號碼或回溯門診日期。"
            }

        # Demographics from Roster / Master DB
        demo = self.mcp_client.get_patient_demographics(p_id)
        pt_age = None
        try:
            pt_age = float(demo.get("age", 0)) if demo.get("age") else None
        except Exception:
            pt_age = None
        pt_gender = demo.get("gender", "") if isinstance(demo, dict) else ""

        # Separate surgical pathology narrative reports from routine numerical laboratory tests
        pure_labs = []
        pathology_records = []
        for l in raw_labs:
            if self._is_pathology_report(l):
                pathology_records.append(l)
            else:
                pure_labs.append(l)

        # 2. Extract and Process Laboratory Tests & Trends (pathology removed from lab table)
        lab_panel = self._process_laboratory_tests(pure_labs, patient_age=pt_age, patient_gender=pt_gender)

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
        surgical_procedures = self._process_surgical_and_interventions(raw_imgs, pathology_records)
        surgical_history_set = set([p.get("name", "") for p in surgical_procedures])

        # 5. Extract and Process Medications & 慢箋 (Chronic Refills)
        med_summary = self._process_medications(raw_meds, consult_dt, lab_panel)

        # 6. Extract & Categorize Diagnoses into Chronic and Acute (with recorded dates)
        diag_summary = self._process_diagnoses(raw_imgs, raw_meds, raw_labs)

        # 7. Synthesize Chronic Clinical Badges & Risk Profile
        all_condition_names = set([d["name"] for d in diag_summary["chronic_list"] + diag_summary["acute_list"]])
        clinical_badges = self._synthesize_clinical_badges(lab_panel, surgical_history_set, all_condition_names, med_summary)

        # 8. Generate 1-Click EMR Pre-Consultation SOAP Note
        emr_note = self._generate_emr_note(
            p_id, c_date, clinical_badges, surgical_procedures,
            diag_summary, lab_panel, processed_reports, med_summary
        )

        return {
            "status": "success",
            "patient_id": p_id,
            "clinic_date": standard_clinic_date,
            "profile": {
                "id_no": p_id,
                "name": demo.get("name", ""),
                "gender": demo.get("gender", ""),
                "age": demo.get("age", ""),
                "chart_no": demo.get("chart_no", ""),
                "badges": clinical_badges,
                "egfr": lab_panel.get("key_metrics", {}).get("egfr", {}).get("value"),
                "creatinine": lab_panel.get("key_metrics", {}).get("creatinine", {}).get("value"),
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

    def _is_pathology_report(self, record: Dict[str, Any]) -> bool:
        """Identify if a laboratory record is a narrative surgical pathology report."""
        item = str(record.get("item", "")).lower()
        order = str(record.get("order", "")).lower()
        val = str(record.get("val", "")).strip()

        # NHI codes for pathology (25001C - 25025C)
        if any(c in order for c in ["25001", "25002", "25003", "25004", "25005", "25024", "25025"]):
            return True
        if any(k in item or k in order for k in ["pathology", "外科病理", "病理組織", "細胞病理", "cytology"]):
            return True
        if len(val) > 100 and any(k in val.lower() for k in [
            "microscopically", "specimen submitted", "tissue fragment", "tubular adenoma", 
            "pathological diagnosis", "病理組織", "病理診斷", "病理中心"
        ]):
            return True
        return False

    def _process_laboratory_tests(self, raw_labs: List[Dict[str, Any]], patient_age: Optional[float] = None, patient_gender: Optional[str] = None) -> Dict[str, Any]:
        """Group lab parameters across 6 physiological systems, calculate liver scores, and construct longitudinal flowsheet."""
        grouped = {
            "all": [],
            "liver": [],
            "hematological": [],
            "renal": [],
            "metabolic": [],
            "immunological": [],
            "others": [],
            "cbc": [],      # Backward-compatibility alias
            "biochem": []   # Backward-compatibility alias
        }
        key_metrics = {}

        # Track latest liver metrics for FIB-4 & APRI
        latest_ast = None
        latest_alt = None
        latest_plt = None
        latest_alb = None
        latest_tbil = None
        latest_alkp = None
        latest_ggt = None
        latest_inr = None
        latest_afp = None

        for l in raw_labs:
            item = str(l.get("item", "")).strip()
            order = str(l.get("order", "")).strip()
            val_str = str(l.get("val", "")).strip()
            unit = str(l.get("unit", "")).strip()
            ref = str(l.get("ref", "")).strip()
            date = to_standard_date(str(l.get("date", "")).strip())

            # Ignore non-lab survey items
            if any(k == item for k in ["抽菸", "戒菸服務"]):
                continue

            # Parse numeric value
            val_num = None
            m = re.search(r'([0-9]+(?:\.[0-9]+)?)', val_str)
            if m:
                try:
                    val_num = float(m.group(1))
                except Exception:
                    pass

            cleaned_name = clean_lab_item_name(item, order)
            c_name_lower = cleaned_name.lower()

            entry = {
                "item": cleaned_name,
                "raw_item": item,
                "order": order,
                "value_str": val_str,
                "value_num": val_num,
                "unit": unit,
                "ref": ref,
                "date": date,
                "abnormal": False,
                "status_tag": "normal",
                "comment": ""
            }

            # 1. AST / GOT
            if ("got" in c_name_lower or "ast" in c_name_lower) and val_num is not None:
                if not latest_ast or date >= latest_ast["date"]:
                    latest_ast = {"val": val_num, "unit": unit or "U/L", "date": date}
                if val_num > 120.0:
                    entry["abnormal"] = True
                    entry["status_tag"] = "critical_high"
                    entry["comment"] = "AST 顯著升高 (>3x)"
                elif val_num > 40.0:
                    entry["abnormal"] = True
                    entry["status_tag"] = "high"

            # 2. ALT / GPT
            if ("gpt" in c_name_lower or "alt" in c_name_lower) and val_num is not None:
                if not latest_alt or date >= latest_alt["date"]:
                    latest_alt = {"val": val_num, "unit": unit or "U/L", "date": date}
                if val_num > 120.0:
                    entry["abnormal"] = True
                    entry["status_tag"] = "critical_high"
                    entry["comment"] = "ALT 顯著升高 (>3x)"
                elif val_num > 40.0:
                    entry["abnormal"] = True
                    entry["status_tag"] = "high"

            # 3. Platelet
            if "platelet" in c_name_lower and val_num is not None:
                if not latest_plt or date >= latest_plt["date"]:
                    latest_plt = {"val": val_num, "unit": unit or "10^3/uL", "date": date}
                if val_num < 100.0:
                    entry["abnormal"] = True
                    entry["status_tag"] = "critical_low"
                    entry["comment"] = "血小板顯著低下"
                elif val_num < 150.0:
                    entry["abnormal"] = True
                    entry["status_tag"] = "low"
                    entry["comment"] = "血小板偏低"
                elif val_num > 450.0:
                    entry["abnormal"] = True
                    entry["status_tag"] = "high"

            # 4. Albumin
            if "albumin" in c_name_lower and "micro" not in c_name_lower and "urine" not in c_name_lower and val_num is not None:
                if not latest_alb or date >= latest_alb["date"]:
                    latest_alb = {"val": val_num, "unit": unit or "g/dL", "date": date}
                if val_num < 2.8:
                    entry["abnormal"] = True
                    entry["status_tag"] = "critical_low"
                    entry["comment"] = "嚴重低白蛋白"
                elif val_num < 3.5:
                    entry["abnormal"] = True
                    entry["status_tag"] = "low"

            # 5. Bilirubin
            if "bilirubin" in c_name_lower and val_num is not None:
                if "direct" not in c_name_lower:
                    if not latest_tbil or date >= latest_tbil["date"]:
                        latest_tbil = {"val": val_num, "unit": unit or "mg/dL", "date": date}
                    if val_num > 2.0:
                        entry["abnormal"] = True
                        entry["status_tag"] = "critical_high"
                        entry["comment"] = "黃疸"
                    elif val_num > 1.2:
                        entry["abnormal"] = True
                        entry["status_tag"] = "high"
                elif "direct" in c_name_lower and val_num > 0.3:
                    entry["abnormal"] = True
                    entry["status_tag"] = "high"

            # 6. Alk-P
            if ("alk-p" in c_name_lower or "alp" in c_name_lower) and val_num is not None:
                if not latest_alkp or date >= latest_alkp["date"]:
                    latest_alkp = {"val": val_num, "unit": unit or "U/L", "date": date}
                if val_num > 130.0:
                    entry["abnormal"] = True
                    entry["status_tag"] = "high"

            # 7. r-GT
            if ("r-gt" in c_name_lower or "ggt" in c_name_lower) and val_num is not None:
                if not latest_ggt or date >= latest_ggt["date"]:
                    latest_ggt = {"val": val_num, "unit": unit or "U/L", "date": date}
                if val_num > 50.0:
                    entry["abnormal"] = True
                    entry["status_tag"] = "high"

            # 8. PT / INR
            if (re.search(r'\binr\b|\bpt\b', c_name_lower) or "prothrombin" in c_name_lower) and "gpt" not in c_name_lower and val_num is not None:
                if not latest_inr or date >= latest_inr["date"]:
                    latest_inr = {"val": val_num, "unit": unit or "", "date": date}
                if val_num > 1.3:
                    entry["abnormal"] = True
                    entry["status_tag"] = "high"
                    entry["comment"] = "凝血時間延長"

            # 9. AFP
            if "afp" in c_name_lower and val_str:
                if not latest_afp or date >= latest_afp["date"]:
                    latest_afp = {"val": val_str, "unit": unit or "ng/mL", "date": date}
                if val_num is not None and val_num > 20.0:
                    entry["abnormal"] = True
                    entry["status_tag"] = "critical_high" if val_num > 400.0 else "high"

            # 10. eGFR & Renal Metrics
            if "egfr" in c_name_lower or "腎絲球" in c_name_lower:
                if "egfr" not in key_metrics and val_num is not None:
                    key_metrics["egfr"] = {"value": val_num, "unit": "mL/min", "date": date}
                if val_num is not None:
                    if val_num < 15:
                        entry["abnormal"] = True
                        entry["status_tag"] = "critical_low"
                        entry["comment"] = "ESRD / Stage 5 CKD"
                    elif val_num < 30:
                        entry["abnormal"] = True
                        entry["status_tag"] = "severe_low"
                        entry["comment"] = "Stage 4 CKD"
                    elif val_num < 60:
                        entry["abnormal"] = True
                        entry["status_tag"] = "low"
                        entry["comment"] = "Stage 3 CKD"

            if "creatinine" in c_name_lower and "urine" not in c_name_lower and "egfr" not in c_name_lower:
                if "creatinine" not in key_metrics and val_num is not None:
                    key_metrics["creatinine"] = {"value": val_num, "unit": unit or "mg/dL", "date": date}
                if val_num is not None and val_num > 1.3:
                    entry["abnormal"] = True
                    entry["status_tag"] = "critical_high" if val_num > 4.0 else "high"

            if "bun" in c_name_lower and "post" not in c_name_lower:
                if "bun" not in key_metrics and val_num is not None:
                    key_metrics["bun"] = {"value": val_num, "unit": unit or "mg/dL", "date": date}
                if val_num is not None and val_num > 25.0:
                    entry["abnormal"] = True
                    entry["status_tag"] = "critical_high" if val_num > 50.0 else "high"

            if "uric acid" in c_name_lower and val_num is not None and val_num > 7.0:
                entry["abnormal"] = True
                entry["status_tag"] = "high"

            # 11. Hemoglobin & CBC
            if (re.search(r'\bhb\b|hemoglobin', c_name_lower)) and not any(x in c_name_lower for x in ["hba1c", "a1c"]):
                if "hb" not in key_metrics and val_num is not None:
                    key_metrics["hb"] = {"value": val_num, "unit": unit or "g/dL", "date": date}
                if val_num is not None and val_num < 10.0:
                    entry["abnormal"] = True
                    entry["status_tag"] = "critical_low" if val_num < 8.0 else "low"
                    entry["comment"] = "Anemia"

            if "wbc" in c_name_lower and val_num is not None:
                if val_num > 10.0:
                    entry["abnormal"] = True
                    entry["status_tag"] = "high"
                elif val_num < 4.0:
                    entry["abnormal"] = True
                    entry["status_tag"] = "low"

            # 12. Metabolic (Glucose, HbA1c, Lipids, Electrolytes)
            if "glucose" in c_name_lower or "glu" in c_name_lower:
                if "glucose" not in key_metrics and val_num is not None:
                    key_metrics["glucose"] = {"value": val_num, "unit": unit or "mg/dL", "date": date}
                if val_num is not None:
                    if val_num > 200.0:
                        entry["abnormal"] = True
                        entry["status_tag"] = "critical_high"
                    elif val_num > 140.0:
                        entry["abnormal"] = True
                        entry["status_tag"] = "high"
                    elif val_num < 70.0:
                        entry["abnormal"] = True
                        entry["status_tag"] = "critical_low"

            if "hba1c" in c_name_lower and val_num is not None:
                if val_num > 9.0:
                    entry["abnormal"] = True
                    entry["status_tag"] = "critical_high"
                elif val_num > 7.0:
                    entry["abnormal"] = True
                    entry["status_tag"] = "high"

            if ("cholesterol" in c_name_lower or "ldl" in c_name_lower) and val_num is not None:
                if val_num > 200.0:
                    entry["abnormal"] = True
                    entry["status_tag"] = "high"

            if "triglyceride" in c_name_lower and val_num is not None and val_num > 150.0:
                entry["abnormal"] = True
                entry["status_tag"] = "high"

            if ("potassium" in c_name_lower or c_name_lower == "k") and val_num is not None:
                if val_num > 5.1:
                    entry["abnormal"] = True
                    entry["status_tag"] = "critical_high" if val_num > 6.0 else "high"
                    entry["comment"] = "高血鉀"
                elif val_num < 3.5:
                    entry["abnormal"] = True
                    entry["status_tag"] = "low"
                    entry["comment"] = "低血鉀"

            if ("sodium" in c_name_lower or c_name_lower == "na") and val_num is not None:
                if val_num < 135.0:
                    entry["abnormal"] = True
                    entry["status_tag"] = "low"
                    entry["comment"] = "低血鈉"
                elif val_num > 145.0:
                    entry["abnormal"] = True
                    entry["status_tag"] = "high"

            # 13. Immunological (CRP)
            if "crp" in c_name_lower and val_num is not None:
                if val_num > 3.0:
                    entry["abnormal"] = True
                    entry["status_tag"] = "critical_high"
                    entry["comment"] = "顯著發炎反應"
                elif val_num > 0.5:
                    entry["abnormal"] = True
                    entry["status_tag"] = "high"

            # 14. Universal Reference Range Check for ANY lab item (flags out-of-range abnormal data)
            if entry["status_tag"] == "normal" and not entry["abnormal"]:
                v_lower = val_str.lower()
                if any(k in v_lower for k in ["陽性", "positive", "reactive", "(+)", "1+", "2+", "3+", "4+"]) and not any(k in v_lower for k in ["non-reactive", "negative", "陰性", "(-)"]):
                    entry["abnormal"] = True
                    entry["status_tag"] = "high"
                elif val_num is not None and ref:
                    low_lim, high_lim = parse_reference_range(ref, str(patient_gender or ""))
                    if high_lim is not None and val_num > high_lim:
                        entry["abnormal"] = True
                        if high_lim > 0 and val_num >= high_lim * 2.0:
                            entry["status_tag"] = "critical_high"
                        else:
                            entry["status_tag"] = "high"
                    elif low_lim is not None and val_num < low_lim:
                        entry["abnormal"] = True
                        if low_lim > 0 and val_num <= low_lim * 0.5:
                            entry["status_tag"] = "critical_low"
                        else:
                            entry["status_tag"] = "low"

            # Classify into one of 6 physiological systems
            cat = classify_lab_group(cleaned_name, item, order)
            if cat in grouped:
                grouped[cat].append(entry)
            else:
                grouped["others"].append(entry)

            # Compatibility aliases
            if cat == "hematological":
                grouped["cbc"].append(entry)
            elif cat == "metabolic":
                grouped["biochem"].append(entry)

            grouped["all"].append(entry)

        # Calculate Liver Assessment (FIB-4, APRI, AST/ALT ratio)
        liver_assessment = self._calculate_liver_scores(
            latest_ast, latest_alt, latest_plt, latest_alb,
            latest_tbil, latest_alkp, latest_ggt, latest_inr, latest_afp,
            patient_age
        )

        # Build Longitudinal Flowsheet Matrix (X: Time/Dates, Y: Analytes grouped by 6 systems)
        flowsheet = self._build_lab_flowsheet(grouped["all"], patient_age=patient_age)

        return {
            "grouped": grouped,
            "key_metrics": key_metrics,
            "liver_assessment": liver_assessment,
            "flowsheet": flowsheet,
            "total_labs": len(raw_labs)
        }

    def _build_lab_flowsheet(
        self,
        entries: List[Dict[str, Any]],
        patient_age: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Construct a longitudinal Flowsheet Matrix:
        X-axis: Time / Dates (sorted descending)
        Y-axis: Laboratory Analytes grouped into 6 Physiological Systems
                (Liver, Hematological, Renal, Metabolic, Immunological, Other functions)
        """
        # 1. Distinct dates sorted chronologically ascending (earliest on left, newest report at the right edge)
        all_dates = sorted(list(set(e["date"] for e in entries if e.get("date"))), reverse=False)

        # 2. Group items by physiological category
        cat_items_map: Dict[str, Dict[str, Dict[str, Any]]] = {
            "liver": {},
            "hematological": {},
            "renal": {},
            "metabolic": {},
            "immunological": {},
            "others": {}
        }

        # Track AST, ALT, PLT per date for longitudinal Liver Fibrosis calculation
        ast_by_date: Dict[str, float] = {}
        alt_by_date: Dict[str, float] = {}
        plt_by_date: Dict[str, float] = {}

        for e in entries:
            it_name = e.get("item") or "Unknown"
            raw_it = e.get("raw_item") or ""
            ord_str = e.get("order") or ""
            d = e.get("date")
            val_num = e.get("value_num")

            cat_id = classify_lab_group(it_name, raw_it, ord_str)
            if cat_id not in cat_items_map:
                cat_id = "others"

            # Track liver biomarkers for calculated fibrosis rows
            it_lower = it_name.lower()
            if ("ast" in it_lower or "got" in it_lower) and val_num is not None:
                ast_by_date[d] = val_num
            elif ("alt" in it_lower or "gpt" in it_lower) and val_num is not None:
                alt_by_date[d] = val_num
            elif "platelet" in it_lower and val_num is not None:
                plt_by_date[d] = val_num

            if it_name not in cat_items_map[cat_id]:
                cat_items_map[cat_id][it_name] = {
                    "item": it_name,
                    "unit": e.get("unit") or "",
                    "ref": e.get("ref") or "",
                    "category": cat_id,
                    "values": {}
                }
            elif not cat_items_map[cat_id][it_name]["unit"] and e.get("unit"):
                cat_items_map[cat_id][it_name]["unit"] = e.get("unit")
            elif not cat_items_map[cat_id][it_name]["ref"] and e.get("ref"):
                cat_items_map[cat_id][it_name]["ref"] = e.get("ref")

            if d:
                curr = cat_items_map[cat_id][it_name]["values"].get(d)
                if not curr or (e.get("abnormal") and not curr.get("abnormal")):
                    cat_items_map[cat_id][it_name]["values"][d] = {
                        "val": e.get("value_str") or "-",
                        "val_num": e.get("value_num"),
                        "abnormal": e.get("abnormal", False),
                        "status_tag": e.get("status_tag", "normal"),
                        "comment": e.get("comment", "")
                    }

        # 3. Add Calculated Longitudinal Liver Fibrosis Rows to 'liver' category
        fib4_values = {}
        apri_values = {}
        ratio_values = {}

        age_val = float(patient_age) if (patient_age and patient_age > 0) else 60.0

        for d in all_dates:
            ast = ast_by_date.get(d)
            alt = alt_by_date.get(d)
            plt = plt_by_date.get(d)

            # FIB-4 Index: (Age * AST) / (PLT * sqrt(ALT))
            if ast and alt and plt and ast > 0 and alt > 0 and plt > 0:
                try:
                    f4 = round((age_val * ast) / (plt * math.sqrt(alt)), 2)
                    is_abn = f4 > 2.0 if age_val >= 65 else f4 > 1.30
                    crit = f4 > 2.67
                    fib4_values[d] = {
                        "val": str(f4),
                        "val_num": f4,
                        "abnormal": is_abn,
                        "status_tag": "critical_high" if crit else ("high" if is_abn else "normal"),
                        "comment": "顯著纖維化風險 (>2.67)" if crit else ("可能纖維化" if is_abn else "低風險")
                    }
                except Exception:
                    pass

            # APRI Score: ((AST / 40) / PLT) * 100
            if ast and plt and ast > 0 and plt > 0:
                try:
                    ap = round(((ast / 40.0) / plt) * 100.0, 2)
                    is_abn = ap > 0.5
                    crit = ap > 1.0
                    apri_values[d] = {
                        "val": str(ap),
                        "val_num": ap,
                        "abnormal": is_abn,
                        "status_tag": "critical_high" if crit else ("high" if is_abn else "normal"),
                        "comment": "高風險 (>1.0)" if crit else ("中風險 (>0.5)" if is_abn else "正常")
                    }
                except Exception:
                    pass

            # AST / ALT Ratio
            if ast and alt and alt > 0:
                try:
                    r = round(ast / alt, 2)
                    is_abn = r > 1.0
                    ratio_values[d] = {
                        "val": str(r),
                        "val_num": r,
                        "abnormal": is_abn,
                        "status_tag": "high" if r > 2.0 else ("warning" if is_abn else "normal"),
                        "comment": ">2.0" if r > 2.0 else (">1.0" if is_abn else "<=1.0")
                    }
                except Exception:
                    pass

        if fib4_values:
            cat_items_map["liver"]["FIB-4 Index (Score)"] = {
                "item": "FIB-4 Index (Score)",
                "unit": "index",
                "ref": "< 2.0 (Age 65+)" if age_val >= 65 else "< 1.30",
                "category": "liver",
                "is_calculated": True,
                "values": fib4_values
            }
        if apri_values:
            cat_items_map["liver"]["APRI Score (AST / PLT)"] = {
                "item": "APRI Score (AST / PLT)",
                "unit": "score",
                "ref": "< 0.50",
                "category": "liver",
                "is_calculated": True,
                "values": apri_values
            }
        if ratio_values:
            cat_items_map["liver"]["AST / ALT Ratio"] = {
                "item": "AST / ALT Ratio",
                "unit": "ratio",
                "ref": "< 1.00",
                "category": "liver",
                "is_calculated": True,
                "values": ratio_values
            }

        # 4. Clinical Priority Sorting maps per category
        PRIORITY = {
            "liver": [
                "ast / got", "alt / gpt", "total bilirubin", "direct bilirubin",
                "albumin", "total protein", "alk-p (alp)", "r-gt (ggt)",
                "pt (prothrombin time)", "inr", "afp (alpha-fetoprotein)", "ammonia",
                "fib-4 index (score)", "apri score (ast / plt)", "ast / alt ratio"
            ],
            "hematological": [
                "wbc", "rbc", "hemoglobin (hb)", "hematocrit (hct)", "platelet",
                "mcv", "mch", "mchc", "rdw-cv", "rdw-sd",
                "aptt", "aptt control", "pt (prothrombin time)", "inr",
                "fibrinogen", "d-dimer", "fdp", "abo blood group", "rh type"
            ],
            "renal": [
                "egfr", "creatinine", "bun", "bun (post-dialysis)", "uric acid",
                "microalbumin", "urine creatinine", "urine total protein"
            ],
            "metabolic": [
                "glucose ac", "glucose", "hba1c", "total cholesterol", "triglyceride",
                "hdl-c", "ldl-c", "sodium (na)", "potassium (k)", "chloride (cl)",
                "calcium (ca)", "phosphorus (p)", "magnesium (mg)"
            ],
            "immunological": [
                "crp", "esr", "hbsag", "anti-hbs", "hbeag", "anti-hbe", "anti-hbc",
                "hbv dna (quantitative)", "hcv ab", "ana (anti-cell ab)", "c3 / c4", "ige", "iga"
            ],
            "others": [
                "tsh", "free t4", "troponin i", "ck-mb", "cpk / ck", "nt-probnp",
                "stool occult blood", "ferritin", "serum iron (fe)", "tibc"
            ]
        }

        CAT_META = [
            ("liver", "Liver (肝膽功能)"),
            ("hematological", "Hematological (血液常規與凝血)"),
            ("renal", "Renal (腎臟功能)"),
            ("metabolic", "Metabolic (生化代謝與電解質)"),
            ("immunological", "Immunological (免疫發炎與肝炎標記)"),
            ("others", "Other functions (其他功能與常規檢驗)")
        ]

        categories_list = []
        for cat_id, cat_title in CAT_META:
            items_dict = cat_items_map.get(cat_id, {})
            if not items_dict:
                continue

            pri_list = PRIORITY.get(cat_id, [])
            pri_map = {name.lower(): idx for idx, name in enumerate(pri_list)}

            def item_sort_key(it_obj):
                name = it_obj["item"]
                # Calculated items go right after primary liver enzymes
                if it_obj.get("is_calculated"):
                    return (100, name)
                for k, rank in pri_map.items():
                    if k in name.lower():
                        return (rank, name)
                return (500, name)

            sorted_items = sorted(list(items_dict.values()), key=item_sort_key)
            categories_list.append({
                "id": cat_id,
                "name": cat_title,
                "items": sorted_items,
                "item_count": len(sorted_items)
            })

        def to_short_date(d_str: str) -> str:
            if not d_str:
                return ""
            s = str(d_str).strip().replace("-", "/")
            return re.sub(r'^20(\d{2})/', r'\1/', s)

        return {
            "dates": all_dates,
            "short_dates": [to_short_date(d) for d in all_dates],
            "total_dates": len(all_dates),
            "categories": categories_list,
            "total_categories": len(categories_list)
        }

    def _calculate_liver_scores(
        self,
        ast_data: Optional[Dict[str, Any]],
        alt_data: Optional[Dict[str, Any]],
        plt_data: Optional[Dict[str, Any]],
        alb_data: Optional[Dict[str, Any]],
        tbil_data: Optional[Dict[str, Any]],
        alkp_data: Optional[Dict[str, Any]],
        ggt_data: Optional[Dict[str, Any]],
        inr_data: Optional[Dict[str, Any]],
        afp_data: Optional[Dict[str, Any]],
        age: Optional[float]
    ) -> Dict[str, Any]:
        """
        Calculate FIB-4 Index, APRI Score, and AST/ALT ratio with age-stratified thresholds.
        """
        res = {
            "has_scores": False,
            "age_used": age,
            "ast": ast_data,
            "alt": alt_data,
            "platelet": plt_data,
            "albumin": alb_data,
            "total_bilirubin": tbil_data,
            "alk_p": alkp_data,
            "r_gt": ggt_data,
            "inr": inr_data,
            "afp": afp_data,
            "fib4": None,
            "apri": None,
            "ast_alt_ratio": None
        }

        ast_val = ast_data.get("val") if ast_data else None
        alt_val = alt_data.get("val") if alt_data else None
        plt_val = plt_data.get("val") if plt_data else None

        # 1. AST / ALT Ratio (De Ritis)
        if ast_val and alt_val and alt_val > 0:
            ratio = round(ast_val / alt_val, 2)
            if ratio > 2.0:
                ratio_badge = "danger"
                ratio_desc = "AST/ALT > 2.0 (提示酒精性肝炎或進行性纖維化/硬化)"
            elif ratio > 1.0:
                ratio_badge = "warning"
                ratio_desc = "AST/ALT > 1.0 (慢性肝病進展或進行性纖維化警訊)"
            else:
                ratio_badge = "info"
                ratio_desc = "AST/ALT <= 1.0 (常見於早期脂肪肝或代謝異常)"
            res["ast_alt_ratio"] = {
                "value": ratio,
                "badge_color": ratio_badge,
                "interpretation": ratio_desc
            }
            res["has_scores"] = True

        # 2. APRI Score: (AST / ULN=40) / (Platelet 10^9/L) * 100
        if ast_val and plt_val and plt_val > 0:
            apri_val = round(((ast_val / 40.0) / plt_val) * 100.0, 2)
            if apri_val > 1.0:
                apri_status = "high_risk"
                apri_color = "danger"
                apri_label = "高風險 (F4)"
                apri_desc = "APRI > 1.0 (高度提示肝硬化 F4，建議積極專科評估)"
            elif apri_val >= 0.5:
                apri_status = "intermediate"
                apri_color = "warning"
                apri_label = "中度風險 (F2+)"
                apri_desc = "APRI 0.5 - 1.0 (提示顯著肝纖維化 F2+，需定期追蹤)"
            else:
                apri_status = "low_risk"
                apri_color = "success"
                apri_label = "低風險 (F0-F1)"
                apri_desc = "APRI < 0.5 (排除顯著纖維化，陰性預測值高)"
            res["apri"] = {
                "value": apri_val,
                "status": apri_status,
                "status_label": apri_label,
                "badge_color": apri_color,
                "cutoff_rule": "< 0.5 (低風險) / > 1.0 (高風險)",
                "interpretation": apri_desc
            }
            res["has_scores"] = True

        # 3. FIB-4 Index: (Age * AST) / (PLT * sqrt(ALT))
        calc_age = age if (age and age > 0) else 65.0
        if ast_val and alt_val and plt_val and alt_val > 0 and plt_val > 0:
            fib4_val = round((calc_age * ast_val) / (plt_val * math.sqrt(alt_val)), 2)
            is_senior = calc_age >= 65.0
            low_cutoff = 2.0 if is_senior else 1.30

            if fib4_val > 2.67:
                fib_status = "high_risk"
                fib_color = "danger"
                fib_label = "高風險 (F3-F4)"
                fib_desc = "FIB-4 > 2.67 (高度懷疑顯著纖維化或早期肝硬化，建議轉介肝膽專科)"
            elif fib4_val >= low_cutoff:
                fib_status = "intermediate"
                fib_color = "warning"
                fib_label = "灰色地帶 (中間風險)"
                fib_desc = f"FIB-4 {low_cutoff} - 2.67 (不確定區間，建議進一步安排 FibroScan 評估)"
            else:
                fib_status = "low_risk"
                fib_color = "success"
                fib_label = "低風險 (F0-F1)"
                fib_desc = f"FIB-4 < {low_cutoff} ({'年齡>=65歲校正門檻' if is_senior else '標準門檻'}，排除進行性纖維化)"

            res["fib4"] = {
                "value": fib4_val,
                "age_used": calc_age,
                "is_age_adjusted": is_senior,
                "status": fib_status,
                "status_label": fib_label,
                "badge_color": fib_color,
                "cutoff_rule": f"< {low_cutoff} (低風險) / > 2.67 (高風險)",
                "interpretation": fib_desc
            }
            res["has_scores"] = True

        return res

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

    def _process_diagnoses(
        self,
        raw_imgs: List[Dict[str, Any]],
        raw_meds: List[Dict[str, Any]],
        raw_labs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract and partition diagnoses into Chronic and Acute categories.
        For Acute diagnoses, associates and returns the recorded date (民國年月日).
        """
        def norm_date(d):
            return to_standard_date(d)

        def clean_icd_code(c):
            if not c: return ''
            return re.sub(r'[^A-Z0-9]', '', str(c).upper())

        # Canonical names for clean presentation
        CANONICAL_NAMES = {
            "N18": "末期腎疾病 / 慢性腎衰竭 (End stage renal disease)",
            "E11": "第二型糖尿病 (Type 2 diabetes mellitus)",
            "I10": "本態性高血壓 (Essential hypertension)",
            "I50": "心臟衰竭 (Heart failure)",
            "I35": "非風濕性主動脈瓣疾患 (Aortic valve disorder)",
            "K76": "脂肪肝 (Fatty liver)",
            "D64": "貧血 (Anemia, unspecified)",
            "J18": "肺炎 (Pneumonia, unspecified organism)",
            "R50": "發燒 (Fever, unspecified)",
            "R06": "呼吸困難/異常 (Abnormalities of breathing)",
            "R07": "胸痛 (Chest pain, unspecified)",
            "R19": "排便習慣改變 (Change in bowel habit)",
            "L30": "皮膚炎/濕疹 (Dermatitis)",
            "L50": "蕁麻疹 (Urticaria)",
            "B35": "皮癬 (Tinea / Fungal infection)"
        }

        def clean_hospital_name(h_str):
            if not h_str:
                return ""
            parts = str(h_str).split('|')
            name = parts[0].strip()
            return name

        all_diags = {}

        EXAM_PROCEDURE_PATTERN = re.compile(
            r'\b(view|merchant|caldwell|waters|skull|kub|radiography|plain\s*film)\b|'
            r'\bchest\s*(?:p-?a|ap)\b|'
            r'\b(?:knee|wrist|ankle|foot|hand|elbow|shoulder|hip|femur|tibia|spine|c-spine|t-spine|l-spine)\s*l[\'’]?t\b|'
            r'\b(?:knee|wrist|ankle|foot|hand|elbow|shoulder|hip|femur|tibia|spine|c-spine|t-spine|l-spine)\s*r[\'’]?t\b|'
            r'\b(?:ap|lat|lateral|oblique|supine|erect|decubitus)\b|'
            r'\b(?:2nd|no\.\s*\d+)\b|'
            r'\b(?:ekg|ecg|sono|sonography|ultrasound|fiberoscopy|colonoscopy|endoscopy)\b|'
            r'(站立|臥|心電圖|鏡檢查|檢查項目|檢查名|檢查)',
            re.IGNORECASE
        )

        def is_valid_icd_diagnosis(code_str: str, name_str: str) -> bool:
            """Ensure entry is a clinical diagnosis and not an X-ray view, procedure, or order code."""
            if not name_str or name_str.strip() in ['-', '無']:
                return False
            name_clean = name_str.strip()
            c_raw = (code_str or '').strip()
            c_upper = c_raw.upper().replace('檢查名:', '').replace('檢查項目:', '').strip()

            # 1. Reject if name contains radiology, projection, examination, or order terms
            if EXAM_PROCEDURE_PATTERN.search(name_clean):
                return False

            # 2. Reject if code starts with digits or hospital Chinese prefixes
            if re.match(r'^\d', c_upper) or any(c_upper.startswith(p) for p in ['檢查', 'ORDER', 'PROC']):
                return False

            # 3. Reject hospital radiology order codes (e.g. X52K1003, X45W1001, X3C1008)
            if re.match(r'^X\d{1,2}[A-Z]', c_upper) or re.match(r'^X[0-9A-Z]{4,}', c_upper):
                return False

            # 4. Format check: Valid ICD-10 diagnostic codes start with [A-Z], followed by 2 digits
            if '.' in c_upper:
                if not re.match(r'^[A-Z]\d{2}\.[0-9A-Z]{1,4}$', c_upper):
                    return False
            else:
                if not re.match(r'^[A-Z]\d{2}([0-9A-Z]{1,4})?$', c_upper):
                    return False
                # If no dot, 4th character in clinical diagnostic ICD is a digit, not a procedure letter
                if len(c_upper) >= 4 and c_upper[3].isalpha():
                    return False
                # Max length for unpunctuated ICD-10-CM is 7 characters (Category + Etiology + Manifestation/Laterality)
                if len(c_upper) > 7:
                    return False

            # 5. Reject administrative encounter Z-codes (Z00-Z29, Z76: routine exam, vaccination, repeat script)
            if re.match(r'^Z(?:0[0-9]|1[0-9]|2[0-9]|76)', c_upper) or any(k in name_clean for k in ['接種', '疫苗', '健康檢查', '開立慢箋']):
                return False

            return True

        def add_diag_entry(name, code, date, hosp=None):
            if not is_valid_icd_diagnosis(code, name):
                return

            c_code = clean_icd_code(code)
            prefix_3 = c_code[:3] if len(c_code) >= 3 else ''

            canon_key = prefix_3 if prefix_3 in CANONICAL_NAMES else (c_code or name.strip().lower())
            canon_name = CANONICAL_NAMES.get(prefix_3, name.strip())

            # Acute vs Chronic Classification
            is_acute = False
            cat = "其他慢性追蹤"

            acute_prefixes = ['J18', 'J12', 'J13', 'J14', 'J15', 'J16', 'J17', 'R50', 'R07', 'R06', 'R10', 'R19', 'L50', 'L30', 'B35', 'J20', 'I21', 'N39']
            acute_keywords = ['PNEUMONIA', '肺炎', 'FEVER', '發燒', 'CHEST PAIN', '胸痛', 'BREATHING', 'DYSPNEA', '呼吸', 
                              'BOWEL HABIT', '排便習慣', 'ABDOMINAL PAIN', '腹痛', 'URTICARIA', '蕁麻疹', 'DERMATITIS', 
                              '皮膚炎', 'ECZEMA', 'TINEA', '皮癬', 'UTI', 'BRONCHITIS', '支氣管炎', 'ACUTE', '急性']

            text_check = f"{name} {code}".upper()
            if prefix_3 in acute_prefixes or any(k in text_check for k in acute_keywords):
                is_acute = True
                if prefix_3 in ['J18', 'J12', 'J20'] or any(k in text_check for k in ['PNEUMONIA', '肺炎', 'BRONCHITIS']):
                    cat = "胸腔/呼吸感染"
                elif prefix_3 in ['L50', 'L30', 'B35'] or any(k in text_check for k in ['蕁麻疹', '皮膚炎', '皮癬']):
                    cat = "皮膚/過敏免疫"
                elif prefix_3 in ['R07', 'R06'] or any(k in text_check for k in ['胸痛', '呼吸']):
                    cat = "急症/心肺症狀"
                elif prefix_3 in ['R50'] or '發燒' in text_check:
                    cat = "急性發燒/感染"
                elif prefix_3 in ['R19', 'R10'] or any(k in text_check for k in ['排便', '腹痛']):
                    cat = "腸胃急症/症狀"
                else:
                    cat = "近期急性問題"
            else:
                if prefix_3 in ['N18'] or any(k in text_check for k in ['ESRD', 'RENAL', 'KIDNEY', 'UREMIA', '透析', '末期腎']):
                    cat = "腎臟疾患 (Nephrology / ESRD)"
                elif prefix_3 in ['E11', 'E10', 'E78'] or any(k in text_check for k in ['DIABETES', 'DM', '糖尿病']):
                    cat = "代謝與內分泌 (Metabolic & Endocrine)"
                elif prefix_3 in ['I10', 'I50', 'I25', 'I35'] or any(k in text_check for k in ['HYPERTENSION', 'HTN', '高血壓', 'HEART FAILURE', 'CHF', 'CAD', 'AORTIC', '主動脈']):
                    cat = "心血管疾患 (Cardiovascular)"
                elif prefix_3 in ['K76'] or any(k in text_check for k in ['FATTY', '脂肪肝', 'CIRRHOSIS', '肝硬化']):
                    cat = "肝膽腸胃 (Hepatology & GI)"
                elif prefix_3 in ['D64'] or '貧血' in text_check:
                    cat = "血液疾患 (Hematology)"
                else:
                    cat = "一般慢性追蹤 (General Chronic)"

            d_clean = norm_date(date)
            h_clean = clean_hospital_name(hosp)

            if canon_key not in all_diags:
                all_diags[canon_key] = {
                    "name": canon_name,
                    "raw_name": name.strip(),
                    "code": code or prefix_3,
                    "dates": set(),
                    "hospitals": set(),
                    "records": [],
                    "type": "acute" if is_acute else "chronic",
                    "category": cat
                }
            if d_clean:
                all_diags[canon_key]["dates"].add(d_clean)
            if h_clean:
                all_diags[canon_key]["hospitals"].add(h_clean)
            if d_clean or h_clean:
                all_diags[canon_key]["records"].append({
                    "date": d_clean or "",
                    "hospital": h_clean or ""
                })

        # 1. Harvest from Imaging Impressions
        for img in raw_imgs:
            d = img.get('date')
            hosp = img.get('hospital', '')
            for line in img.get('summary', '').split('\n'):
                line_s = line.strip()
                if '_' in line_s and not line_s.startswith('檢查項目'):
                    parts = line_s.split('_', 1)
                    code = parts[0].strip()
                    name = parts[1].strip() if len(parts) > 1 else ''
                    add_diag_entry(name, code, d, hosp)

        # 2. Harvest from Prescription Medication Diagnoses
        for m in raw_meds:
            d = m.get('date')
            diag = m.get('diag')
            hosp = m.get('hospital', '') or m.get('presHospital', '')
            if diag:
                parts = diag.split('|', 1)
                name = parts[0].strip()
                code = parts[1].strip() if len(parts) > 1 else ''
                add_diag_entry(name, code, d, hosp)

        # Split and format
        acute_list = [v for v in all_diags.values() if v['type'] == 'acute']
        chronic_list = [v for v in all_diags.values() if v['type'] == 'chronic']

        # Format acute: latest date + latest hospital + sort descending
        for a in acute_list:
            recs = a.get('records', [])
            recs.sort(key=lambda r: r.get('date', ''), reverse=True)
            latest_h = ""
            for r in recs:
                if r.get('hospital'):
                    latest_h = r['hospital']
                    break
            dates_sorted = sorted(list(a['dates']), reverse=True)
            a['latest_date'] = dates_sorted[0] if dates_sorted else '近期'
            a['date'] = a['latest_date'] # Primary field for acute diagnosis
            a['all_dates'] = dates_sorted
            a['dates'] = dates_sorted # Replace set with JSON-serializable list
            a['hospital'] = latest_h
            a['institute'] = latest_h
            a['hospitals'] = sorted(list(a['hospitals']))
            a.pop('records', None)
        acute_list.sort(key=lambda x: x['latest_date'], reverse=True)

        # Format chronic: latest date + latest hospital + sort by specialty
        cat_priority = {
            "腎臟疾患 (Nephrology / ESRD)": 1,
            "代謝與內分泌 (Metabolic & Endocrine)": 2,
            "心血管疾患 (Cardiovascular)": 3,
            "肝膽腸胃 (Hepatology & GI)": 4,
            "血液疾患 (Hematology)": 5,
            "一般慢性追蹤 (General Chronic)": 6
        }
        for c in chronic_list:
            recs = c.get('records', [])
            recs.sort(key=lambda r: r.get('date', ''), reverse=True)
            latest_h = ""
            for r in recs:
                if r.get('hospital'):
                    latest_h = r['hospital']
                    break
            dates_sorted = sorted(list(c['dates']), reverse=True)
            c['latest_date'] = dates_sorted[0] if dates_sorted else '長期'
            c['date'] = c['latest_date']
            c['all_dates'] = dates_sorted
            c['dates'] = dates_sorted # Replace set with JSON-serializable list
            c['hospital'] = latest_h
            c['institute'] = latest_h
            c['hospitals'] = sorted(list(c['hospitals']))
            c.pop('records', None)

        def get_chronic_sort_key(item):
            prio = cat_priority.get(item.get('category'), 99)
            latest_d = item.get('latest_date', '')
            return (prio, latest_d if latest_d != '-' else '0000/00/00')

        chronic_list.sort(key=get_chronic_sort_key)

        return {
            "chronic_list": chronic_list,
            "acute_list": acute_list
        }

    def _process_surgical_and_interventions(self, raw_imgs: List[Dict[str, Any]], pathology_records: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Extract surgical, endoscopic, and interventional procedures (especially PTA)
        along with their exact time/date of execution.
        """
        def norm_date(d):
            return to_standard_date(d)

        procedures = []
        seen = set()

        # Pass 1: Extract all directly executed procedure reports (PTA 33074B, Colonoscopy 28017C, etc.)
        for img in raw_imgs:
            d = norm_date(img.get('date', ''))
            raw = img.get('summary', '') or ''
            code = str(img.get('NHICode', '')).strip().upper()
            hosp_clean = str(img.get('hospital', '')).split('|')[0].strip() or '院內處置'

            # TAME / TAE (Transcatheter Arterial Micro-Embolization, NHI 33075B)
            if code == '33075B' or 'tame' in raw.lower() or 'micro-embolization' in raw.lower() or 'radioembolization' in raw.lower():
                key = ('TAME', d)
                if key not in seen:
                    seen.add(key)
                    site_m = re.search(r'\{Transcatheter Arterial Micro-Embolization \(TAME\),\s*([^}]+)\}', raw, re.I)
                    site_txt = site_m.group(1).strip() if site_m else 'left ankle'
                    course_m = re.search(r's/p\s+(\d+(?:st|nd|rd|th)?\s+course\s+TAME|TAME)', raw, re.I)
                    course_txt = f" ({course_m.group(1)})" if course_m else ""
                    procedures.append({
                        'date': d or '近期',
                        'name': f'Transcatheter Arterial Micro-Embolization (TAME, 經皮微動脈栓塞術) - {site_txt}{course_txt}',
                        'detail': f'使用 imipenem/cilastatin 栓塞異常新生血管以緩解關節炎頑固性疼痛 ({site_txt})',
                        'category': '血管微栓塞處置 (TAME)',
                        'hospital': hosp_clean,
                        'institute': hosp_clean,
                        'sort_date': d or '0000/00/00'
                    })

            # Sonoguided Joint Injection (HA-PRP 19007C)
            if 'prp' in raw.lower() or 'sonoguided ha' in raw.lower() or 'ha-prp' in raw.lower():
                key = ('PRP', d)
                if key not in seen:
                    seen.add(key)
                    procedures.append({
                        'date': d or '近期',
                        'name': 'Sonoguided HA-PRP injection (超音波導引玻尿酸/PRP關節注射處置)',
                        'detail': '左踝重度骨關節炎超音波導引玻尿酸與高濃度血小板血漿 (PRP) 關節腔注射',
                        'category': '超音波介入治療',
                        'hospital': hosp_clean,
                        'institute': hosp_clean,
                        'sort_date': d or '0000/00/00'
                    })

            # PTA & Thrombectomy Reports (NHI 33074B or direct AV fistula PTA execution report)
            if (code == '33074B' or any(k in raw.lower() for k in ['fistulogram', 'av fistula', 'fistula thrombectomy'])) and not any(k in raw.lower() for k in ['tame', 'micro-embolization']) and not raw.strip().startswith('s/p'):
                balloons = re.findall(r'([A-Za-z0-9]+\s+[0-9]+\*[0-9]+(?:\.[0-9]+)?mm\s+balloon)', raw, re.IGNORECASE)
                atm = re.findall(r'(\d+\s*ATM)', raw, re.IGNORECASE)
                sheaths = re.findall(r'(\d+\s*Fr\s+introducer|\d+\s*Fr\s+sheath)', raw, re.IGNORECASE)

                details = []
                if balloons:
                    details.append(balloons[0])
                if atm:
                    details.append(atm[0])
                if sheaths:
                    details.append(sheaths[0])

                access_m = re.search(r'(?:via|approach|access)\s+([^\.\,\n;]+)', raw, re.IGNORECASE)
                if details:
                    detail_txt = ', '.join(details)
                elif access_m:
                    detail_txt = access_m.group(0).strip()
                else:
                    detail_txt = '經皮血管成形術介入處置 (PTA intervention)'
                if 'total occlusion' in raw.lower():
                    detail_txt += ' (全阻塞疏通/Total occlusion recannulated)'
                elif 'stenosis' in raw.lower():
                    detail_txt += ' (狹窄氣球擴張/Stenosis dilated)'

                key = ('PTA', d)
                if key not in seen:
                    seen.add(key)
                    procedures.append({
                        'date': d or '近期',
                        'name': 'AV fistula Thrombectomy + PTA (動靜脈瘻管血栓清除暨氣球擴張術)',
                        'detail': detail_txt,
                        'category': 'PTA 介入處置',
                        'hospital': hosp_clean,
                        'institute': hosp_clean,
                        'sort_date': d or '0000/00/00'
                    })

            # Endoscopic procedures (Colonoscopy 28017C)
            if code == '28017C' or 'colon fiberoscopy' in raw.lower():
                polyps = 'Colon polyps (大腸多發息肉)' if 'polyp' in raw.lower() else 'Colonoscopy'
                key = ('Colonoscopy', d)
                if key not in seen:
                    seen.add(key)
                    procedures.append({
                        'date': d or '近期',
                        'name': f'Colon fiberoscopy (大腸鏡檢查) - {polyps}',
                        'detail': '直腸/乙狀結腸/脾彎/橫結腸多發息肉，建議停用抗凝血劑後排程切除',
                        'category': '內視鏡處置',
                        'hospital': hosp_clean,
                        'institute': hosp_clean,
                        'sort_date': d or '0000/00/00'
                    })

        # Pass 2: Extract historical procedures from Conclusion or narrative
        for img in raw_imgs:
            d = norm_date(img.get('date', ''))
            raw = img.get('summary', '') or ''
            hosp_clean = str(img.get('hospital', '')).split('|')[0].strip() or '病歷摘錄'

            # Historical PTA sessions mentioned in Conclusion narrative (e.g. 2025/11/24, 2026/1/2)
            m_pta_hist = re.findall(r'S/P\s+Thrombectomy\s*\+\s*PTA[,\s]+([0-9\/\s,]+)', raw, re.IGNORECASE)
            for hist_block in m_pta_hist:
                for date_match in re.findall(r'(\d{4}/\d{1,2}/\d{1,2})', hist_block):
                    std_d = to_standard_date(date_match)
                    key = ('PTA', std_d)
                    if key not in seen:
                        seen.add(key)
                        procedures.append({
                            'date': std_d,
                            'name': 'AV fistula Thrombectomy + PTA (動靜脈瘻管血栓清除暨氣球擴張術)',
                            'detail': f'病歷摘錄處置日 ({std_d})',
                            'category': 'PTA 介入處置',
                            'hospital': hosp_clean,
                            'institute': hosp_clean,
                            'sort_date': std_d
                        })

            # 3. Left brachiocephalic AV fistula creation
            m_fistula = re.search(r's/p\s+([^\.\n]*?fistula\s+creation[^\.\n]*?)(?:,\s*(\d{4}|\d{3}/\d{1,2}/\d{1,2}))?', raw, re.IGNORECASE)
            if m_fistula:
                f_date = m_fistula.group(2)
                f_date_str = to_standard_date(f_date) if f_date else '2025'
                key = ('FistulaCreation', f_date_str)
                if key not in seen:
                    seen.add(key)
                    procedures.append({
                        'date': f_date_str,
                        'name': 'Left brachiocephalic AV fistula creation (左側動靜脈瘻管建立術)',
                        'detail': '左側頭靜脈-肱動脈瘻管建立手術',
                        'category': '瘻管手術',
                        'sort_date': f"{f_date_str}/01/01" if len(f_date_str) == 4 else f_date_str
                    })

            # 4. CABG / Sternotomy wires from CXR or Conclusion
            if 'cabg' in raw.lower() or 'sternotomy' in raw.lower():
                key = ('CABG', 'Past')
                if key not in seen:
                    seen.add(key)
                    procedures.append({
                        'date': '既往病史 (Past)',
                        'name': 'CAD s/p CABG (冠狀動脈繞道手術)',
                        'detail': 'Midline sternotomy surgical wires (CXR 術後固定鋼線)',
                        'category': '心臟手術',
                        'sort_date': '2015/01/01'
                    })

            # 5. Hemodialysis initiation
            m_hd = re.search(r'(?:starting|started)\s+hemodialysis\s+(?:since|in)\s+(\d{4})', raw, re.IGNORECASE)
            if m_hd:
                hd_year = m_hd.group(1)
                hd_date_str = to_standard_date(hd_year) if hd_year else '2023'
                key = ('HD', hd_date_str)
                if key not in seen:
                    seen.add(key)
                    procedures.append({
                        'date': hd_date_str,
                        'name': 'Hemodialysis initiation (開始規律血液透析)',
                        'detail': '每週 3 次維持性血液透析 (H/D)',
                        'category': '透析治療',
                        'sort_date': f"{hd_date_str}/01/01" if len(hd_date_str) == 4 else hd_date_str
                    })

            # 6. Surgical Implants (Hickman, Double lumen)
            if 'hickman' in raw.lower():
                key = ('Hickman', d)
                if key not in seen:
                    seen.add(key)
                    procedures.append({
                        'date': d or '既往',
                        'name': 'Right subclavian Hickman catheter placement (希克曼導管置入)',
                        'detail': '長期靜脈導管植入',
                        'category': '導管手術',
                        'sort_date': d or '0000/00/00'
                    })
            if 'double lumen' in raw.lower():
                key = ('DoubleLumen', d)
                if key not in seen:
                    seen.add(key)
                    procedures.append({
                        'date': d or '既往',
                        'name': 'Right neck double lumen catheter placement (雙腔透析導管置入)',
                        'detail': '暫時性血液透析導管',
                        'category': '導管手術',
                        'sort_date': d or '0000/00/00'
                    })

        # Pass 3: Extract biopsy / surgical procedures from Pathology Reports
        if pathology_records:
            for prec in pathology_records:
                d = norm_date(prec.get('date', ''))
                val = str(prec.get('val', '')).replace('\r\n', '\n')
                order = str(prec.get('order', ''))
                if any(k in val.lower() for k in ['cold biopsy', 'biopsy', '切片', 'polypectomy']) or '25004' in order:
                    proc_name = "大腸鏡瘜肉切片處置 (Colonoscopic Cold Biopsy)"
                    m_proc = re.search(r'手術名稱[：:\s]+(.*?)(?=\n|代碼|檢查名稱|$)', val)
                    if m_proc and m_proc.group(1).strip():
                        proc_name = f"{m_proc.group(1).strip()} (大腸息肉切片)"
                    
                    detail = "Tubular adenoma (管狀腺瘤切片)"
                    if "sigmoid" in val.lower() or "ascending" in val.lower():
                        detail = "Ascending & Sigmoid colon polyps (0.4 cm) 管狀腺瘤"

                    key = ('Biopsy', d, proc_name)
                    if key not in seen:
                        seen.add(key)
                        procedures.append({
                            'date': d or '近期',
                            'name': proc_name,
                            'detail': detail,
                            'category': '內視鏡切片處置',
                            'sort_date': d or '0000/00/00'
                        })

        # Sort descending by sort_date
        procedures.sort(key=lambda x: x.get('sort_date', ''), reverse=True)
        return procedures

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
