"""
Laboratory test name standardization, reference range parsing, and physiological classification.
"""

import re
from typing import Optional, Tuple


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
    if "albumin" in panel_lower or "白蛋白" in combined:
        if "urine" in combined or "微量" in combined or "micro" in combined:
            return "Urine Microalbumin"
        return "Albumin"
    if "total protein" in panel_lower or "總蛋白" in combined:
        return "Total Protein"
    if "afp" in sub_lower or "胎兒蛋白" in combined or "alpha-fetoprotein" in combined:
        return "AFP (Alpha-Fetoprotein)"

    # Renal & Urine
    if "egfr" in combined or "腎絲球過濾" in combined:
        return "eGFR"
    if "creatinine" in combined or "肌酸酐" in combined:
        if "urine" in combined or "尿" in sub_lower:
            return "Urine Creatinine"
        return "Creatinine"
    if re.search(r'\bbun\b', combined) or "blood urea nitrogen" in combined or "尿素氮" in combined:
        return "BUN"
    if "uric acid" in combined or "尿酸" in combined:
        return "Uric Acid"
    if "acr" in combined or ("urine" in combined and "creatinine" in combined and "albumin" in combined):
        return "Urine ACR"

    # Metabolic & Glycemic
    if "hba1c" in combined or "糖化血色素" in combined:
        return "HbA1c"
    if "glucose" in combined or "血糖" in combined or "ac" in sub_lower or "飯前血糖" in combined:
        if "pc" in sub_lower or "飯後" in combined:
            return "Glucose (PC)"
        return "Glucose (AC)"
    if "cholesterol" in sub_lower or "膽固醇" in combined:
        if "hdl" in sub_lower or "高密度" in combined:
            return "HDL-C"
        if "ldl" in sub_lower or "低密度" in combined:
            return "LDL-C"
        return "Total Cholesterol"
    if "triglyceride" in sub_lower or "三酸甘油" in combined:
        return "Triglyceride"
    if "sodium" in sub_lower or "na" in sub_lower or "鈉" in combined:
        return "Sodium (Na)"
    if "potassium" in sub_lower or re.search(r'\bk\b', sub_lower) or "鉀" in combined:
        return "Potassium (K)"
    if "chloride" in sub_lower or "cl" in sub_lower or "氯" in combined:
        return "Chloride (Cl)"
    if "calcium" in sub_lower or "ca" in sub_lower or "鈣" in combined:
        return "Calcium (Ca)"
    if "phosphorus" in sub_lower or re.search(r'\bp\b', sub_lower) or "磷" in combined:
        return "Inorganic Phosphorus (P)"
    if "magnesium" in sub_lower or "mg" in sub_lower or "鎂" in combined:
        return "Magnesium (Mg)"

    # Hematology & Coagulation
    if "wbc" in sub_lower or "白血球計數" in combined:
        return "WBC"
    if "rbc" in sub_lower or "紅血球計數" in combined:
        return "RBC"
    if "hemoglobin" in sub_lower or re.search(r'\bhb\b', sub_lower) or "血色素" in combined:
        return "Hemoglobin (Hb)"
    if "hematocrit" in sub_lower or re.search(r'\bhct\b', sub_lower) or "血球容積" in combined:
        return "Hematocrit (Hct)"
    if "platelet" in sub_lower or re.search(r'\bplt\b', sub_lower) or "血小板計數" in combined:
        return "Platelet"
    if "mcv" in sub_lower:
        return "MCV"
    if "mch" in sub_lower and "mchc" not in sub_lower:
        return "MCH"
    if "mchc" in sub_lower:
        return "MCHC"
    if "prothrombin" in combined or "pt" in sub_lower or "inr" in sub_lower or "凝血酶原" in combined:
        if "inr" in sub_lower or "inr" in item_s.lower():
            return "INR"
        return "PT / INR"
    if "aptt" in sub_lower or "partial thromboplastin" in combined or "活化部分凝血" in combined:
        return "aPTT"

    # Inflammatory & Cardiac & Endocrine
    if "crp" in sub_lower or "c-reactive" in combined or "c反應蛋白" in combined:
        if "hs" in sub_lower or "高敏" in combined:
            return "hs-CRP"
        return "CRP"
    if "esr" in sub_lower or "紅血球沉降" in combined:
        return "ESR"
    if "troponin" in sub_lower or "肌鈣蛋白" in combined:
        return "Troponin-I"
    if "bnp" in sub_lower or "nt-probnp" in sub_lower or "利尿鈉肽" in combined:
        return "NT-proBNP"
    if "tsh" in sub_lower or "甲狀腺刺激素" in combined:
        return "TSH"
    if "free t4" in sub_lower or "ft4" in sub_lower or "游離甲狀腺素" in combined:
        return "Free T4"
    if "hba1c" in sub_lower:
        return "HbA1c"

    # Fallback to order / item descriptions if English is extractable
    m_eng = re.search(r'([A-Za-z0-9\-\/\.\s\(\)]{3,})', sub_desc)
    if m_eng:
        cand = m_eng.group(1).strip()
        if len(cand) >= 3 and not cand.isdigit() and cand.upper() not in ["NORMAL", "NEGATIVE", "POSITIVE", "REPORT"]:
            return cand

    m_panel = re.search(r'([A-Za-z0-9\-\/\.\s\(\)]{3,})', panel_desc)
    if m_panel:
        cand = m_panel.group(1).strip()
        if len(cand) >= 3 and not cand.isdigit() and cand.upper() not in ["NORMAL", "NEGATIVE", "POSITIVE", "REPORT"]:
            return cand

    # Handle standard Chinese lab tests directly
    clean_mappings = {
        "血小板": "Platelet",
        "白血球": "WBC",
        "紅血球": "RBC",
        "血色素": "Hemoglobin (Hb)",
        "血紅素": "Hemoglobin (Hb)",
        "肌酸酐": "Creatinine",
        "尿素氮": "BUN",
        "尿酸": "Uric Acid",
        "三酸甘油酯": "Triglyceride",
        "膽固醇": "Total Cholesterol",
        "低密度脂蛋白": "LDL-C",
        "高密度脂蛋白": "HDL-C",
        "飯前血糖": "Glucose (AC)",
        "飯後血糖": "Glucose (PC)",
        "鉀": "Potassium (K)",
        "鈉": "Sodium (Na)",
        "氯": "Chloride (Cl)",
        "鈣": "Calcium (Ca)",
        "鎂": "Magnesium (Mg)",
        "鹼性磷酸酶": "Alk-P (ALP)",
        "總膽紅素": "Total Bilirubin",
        "直接膽紅素": "Direct Bilirubin",
        "白蛋白": "Albumin",
        "球蛋白": "Globulin",
        "總蛋白": "Total Protein",
        "澱粉酶": "Amylase",
        "解脂酶": "Lipase",
        "甲狀腺刺激素": "TSH",
        "尿液常規": "Urine Routine",
        "糞便潛血": "Stool FOBT",
        "微量白蛋白": "Urine Microalbumin"
    }
    for zh, eng in clean_mappings.items():
        if zh in combined:
            return eng

    if order_s:
        # If there's an alphanumeric test code like '09002C', clean it
        clean_order = re.sub(r'^[0-9A-Za-z]+\s*', '', order_parts[0]).strip()
        if clean_order:
            return clean_order

    # Try extracting any latin letters
    if item_s:
        m = re.search(r'([A-Za-z0-9\s\-\/\.\(\)]{2,})', item_s)
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

    # Check for gender specific sub-part if present, e.g. M; 4.4-7.6 or F; 2.3-6.6, or M; < 41
    if gender:
        g = gender.upper()
        if g.startswith('M') or '男' in g:
            m_gen = re.search(r'[M男][~;:\s]+([0-9.]+\s*[-~至–]\s*[0-9.]+)', s, re.I)
            if m_gen:
                s = m_gen.group(1)
            else:
                m_gen_th = re.search(r'[M男][~;:\s]+([<>≤≥≦≧＜＞]?\s*[0-9]+(?:\.[0-9]+)?)', s, re.I)
                if m_gen_th:
                    s = m_gen_th.group(1)
        elif g.startswith('F') or '女' in g:
            m_gen = re.search(r'[F女][~;:\s]+([0-9.]+\s*[-~至–]\s*[0-9.]+)', s, re.I)
            if m_gen:
                s = m_gen.group(1)
            else:
                m_gen_th = re.search(r'[F女][~;:\s]+([<>≤≥≦≧＜＞]?\s*[0-9]+(?:\.[0-9]+)?)', s, re.I)
                if m_gen_th:
                    s = m_gen_th.group(1)

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
    m3 = re.search(r'(?:<|<=|＜|≦|≤)\s*([0-9]+(?:\.[0-9]+)?)', s)
    if m3:
        try:
            return None, float(m3.group(1))
        except Exception:
            pass

    # 4. Lower limit only: > 10, ＞10, ≧10, >= 10
    m4 = re.search(r'(?:>|>=|＞|≧|≥)\s*([0-9]+(?:\.[0-9]+)?)', s)
    if m4:
        try:
            return float(m4.group(1)), None
        except Exception:
            pass

    return None, None


def trim_display_zeros(num_str: str) -> str:
    """Trim redundant trailing zeros from decimal strings e.g. '11.500' -> '11.5', '12.0' -> '12'."""
    s = num_str.strip()
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def clean_display_reference_range(ref_str: str, gender: str = "", item_name: str = "") -> str:
    """
    Clean and simplify raw laboratory reference range strings into clean numerical format:
      e.g.
        '[(5~34)[112年8月23日起更新參考值]][(5~34)...]' -> '5 - 34'
        '[( 0.0 - 0.5)[112年8月23日起更新參考值]]'       -> '0 - 0.5'
        '[(M~;~< 41 U/L; F~;~ <33 U/L)...]' (Male)      -> '< 41'
        '[(M~;~13.5-17.5;F~;~12.0-16.0)]' (Male)        -> '13.5 - 17.5'
        '[65][175]'                                     -> '65 - 175'
        '[60][999]'                                     -> '>= 60'
        '[11.500][14.500]'                              -> '11.5 - 14.5'
        '[-][-]', '[Nil][Nil]', '[Negative]'            -> ''
    """
    if not ref_str:
        return ""

    s = str(ref_str).strip()
    if not s or s in ["-", "--", "N/A", "NA", "null", "None"]:
        return ""

    # Check for known non-numeric / qualitative strings
    non_numeric_keywords = [
        "NEGATIVE", "TARGET NOT DETECTED", "NON-REACTIVE", "REACTIVE", "POSITIVE",
        "CLEAR", "YELLOW", "VARIABLE", "NOT DETECTED", "陰性", "陽性", "未檢出",
        "A,B,O,AB", "STAGE 1", "STAGE 2", "STAGE 3", "STAGE 4", "STAGE 5",
        "WEEKS", "YEARS", "MONTHS", "ASCITES", "BODY FLUID"
    ]
    s_upper = s.upper()
    if any(k in s_upper for k in non_numeric_keywords) and not re.search(r'[0-9]', s):
        return ""

    # If duplicate concatenated chunks e.g. [chunk][chunk] or [(chunk)][(chunk)]
    half = len(s) // 2
    if len(s) > 10 and s[:half] == s[half:]:
        s = s[:half].strip()

    # 1. Strip administrative update dates and formulas
    s = re.sub(r'[,，、;；]\s*(?:自)?\d{1,3}年[^\)\]]*', '', s)
    s = re.sub(r'[\[(（][^\])）]*(?:\d{2,3}年|\d{1,2}月\d{1,2}日|更新|修訂|計算公式|CKD-EPI)[^\])）]*[\])）]', ' ', s)
    s = re.sub(r'[\[(（][^\])）]*[xy]=.*?[\])）]', ' ', s)
    s = re.sub(r'\([^)0-9><≤≥≦≧=-]*\)', ' ', s)

    # Special handling for eGFR
    if item_name and "egfr" in item_name.lower():
        if "60" in s or "90" in s:
            return ">= 60"

    # 2. Gender-specific extraction if present
    is_gender_split = bool(re.search(r'\b[MF男][~;:\s]+.*?[女F][~;:\s]+', s, re.I) or 
                           re.search(r'\b[MF女][~;:\s]+.*?[男M][~;:\s]+', s, re.I))

    if is_gender_split:
        g = (gender or "").upper().strip()
        is_male = g.startswith('M') or '男' in g
        is_female = g.startswith('F') or '女' in g

        m_male = re.search(r'[M男][~;:\s]+([<>≤≥≦≧＜＞]?\s*[0-9]+(?:\.[0-9]+)?(?:\s*[-~至–]\s*[0-9]+(?:\.[0-9]+)?)?)', s, re.I)
        m_fem = re.search(r'[F女][~;:\s]+([<>≤≥≦≧＜＞]?\s*[0-9]+(?:\.[0-9]+)?(?:\s*[-~至–]\s*[0-9]+(?:\.[0-9]+)?)?)', s, re.I)

        def norm_subpart(sub: str) -> str:
            if not sub:
                return ""
            sub = sub.strip()
            # If range: low - high
            m_rng = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*[-~至–]\s*([0-9]+(?:\.[0-9]+)?)', sub)
            if m_rng:
                return f"{trim_display_zeros(m_rng.group(1))} - {trim_display_zeros(m_rng.group(2))}"
            # If threshold: < X, <= X, > X
            m_th = re.search(r'([<>≤≥≦≧＜＞])\s*([0-9]+(?:\.[0-9]+)?)', sub)
            if m_th:
                op = "<" if m_th.group(1) in ["<", "＜", "≤", "≦"] else ">"
                return f"{op} {trim_display_zeros(m_th.group(2))}"
            return sub

        male_clean = norm_subpart(m_male.group(1)) if m_male else ""
        fem_clean = norm_subpart(m_fem.group(1)) if m_fem else ""

        if is_male and male_clean:
            return male_clean
        elif is_female and fem_clean:
            return fem_clean
        elif male_clean and fem_clean:
            return f"M: {male_clean}, F: {fem_clean}"
        elif male_clean:
            return f"M: {male_clean}"
        elif fem_clean:
            return f"F: {fem_clean}"

    # 3. Standard Bracket Pair: [low][high] e.g. [0][40], [65][175], [0.2][1.2], [60][999]
    m_pair = re.search(r'\[\s*([0-9]+(?:\.[0-9]+)?)\s*\]\s*\[\s*([0-9]+(?:\.[0-9]+)?)\s*\]', s)
    if m_pair:
        try:
            low_val = float(m_pair.group(1))
            high_val = float(m_pair.group(2))

            # Check for invalid sentinel pair like [0][99999] or [0][0]
            if low_val == 0 and high_val >= 9999:
                return ""
            if low_val == 0 and high_val == 0:
                return ""
            # eGFR sentinel high bound: [60][999] -> >= 60
            if high_val >= 999:
                return f">= {trim_display_zeros(m_pair.group(1))}"

            return f"{trim_display_zeros(m_pair.group(1))} - {trim_display_zeros(m_pair.group(2))}"
        except Exception:
            pass

    # 4. Range with separator: 5~34, 0.0 - 0.5, 9.5 - 11.7, 1000 - 3400
    m_range = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(?:-|~|至|–)\s*([0-9]+(?:\.[0-9]+)?)', s)
    if m_range:
        try:
            low_s = trim_display_zeros(m_range.group(1))
            high_s = trim_display_zeros(m_range.group(2))
            return f"{low_s} - {high_s}"
        except Exception:
            pass

    # 5. Threshold only: < 0.55, <= 8.78, < 130, > 10
    m_thresh = re.search(r'([<>≤≥≦≧＜＞])\s*([0-9]+(?:\.[0-9]+)?)', s)
    if m_thresh:
        op_char = m_thresh.group(1)
        val_s = trim_display_zeros(m_thresh.group(2))
        op = "<" if op_char in ["<", "＜", "≤", "≦"] else ">"
        return f"{op} {val_s}"

    # 6. Single standalone number: e.g. eGFR '60' -> '>= 60'
    m_single = re.search(r'^\s*([0-9]+(?:\.[0-9]+)?)\s*$', s)
    if m_single:
        val_f = float(m_single.group(1))
        if val_f == 60.0:
            return ">= 60"
        return trim_display_zeros(m_single.group(1))

    # If nothing matched numeric patterns, return empty (don't display garbage)
    return ""


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
    is_hba1c = ('hba1c' in comb) or ('糖化' in comb)

    # 1. Liver
    if not is_aptt and (
        any(k in comb for k in [
            'got', 'ast', '草酸', 'gpt', 'alt', '丙酮酸', 'r-gt', 'ggt', '麩胺醯',
            'alk-p', 'alp', '鹼性磷酸', 'bilirubin', '膽紅素', 'total protein', '總蛋白',
            'afp', '胎兒蛋白', 'ammonia', '血氨', 'ldh', '乳酸脫氫'
        ]) or (('albumin' in comb or '白蛋白' in comb) and not is_urine_alb)
    ):
        return 'liver'

    # 2. Hematological
    if not is_hba1c and (
        is_aptt
        or any(k in comb for k in [
            'wbc', 'rbc', 'hb', 'hgb', 'hemoglobin', 'hct', 'hematocrit',
            'platelet', 'plt', 'mcv', 'mch', 'mchc', 'rdw', 'mpv',
            'pt', 'prothrombin', 'inr', 'fibrinogen', 'd-dimer', '凝血',
            'segment', 'neutrophil', 'lymphocyte', 'monocyte', 'eosinophil', 'basophil',
            'reticulocyte', 'ferritin', 'iron', 'tibc', '白血球', '紅血球', '血小板', '血色素', '血球容積'
        ])
    ):
        return 'hematological'

    # 3. Renal & Urine
    if any(k in comb for k in [
        'creatinine', '肌酸酐', 'bun', 'urea', '尿素氮', 'egfr', '腎絲球',
        'uric acid', '尿酸', 'microalbumin', 'u-alb', 'upcr', 'uacr', 'cystatin',
        'urine protein', '尿蛋白', 'urine routine', '尿常規'
    ]):
        return 'renal'

    # 4. Metabolic, Electrolytes & Lipids
    if any(k in comb for k in [
        'glucose', '血糖', 'hba1c', '糖化血色素', 'cholesterol', '膽固醇',
        'triglyceride', '三酸甘油', 'hdl', 'ldl', 'sodium', 'na', '鈉',
        'potassium', 'k', '鉀', 'chloride', 'cl', '氯', 'calcium', 'ca', '鈣',
        'phosphorus', 'inorganic p', '磷', 'magnesium', 'mg', '鎂',
        'c-peptide', 'insulin', '胰島素', 'ketone', '酮體', 'lactate', '乳酸'
    ]):
        return 'metabolic'

    # 5. Immunological & Infectious
    if any(k in comb for k in [
        'crp', 'hs-crp', 'c-reactive', 'esr', 'ana', 'ra factor', 'rheumatoid',
        'hbsag', 'anti-hbs', 'hbeag', 'anti-hbe', 'anti-hcv', 'hcv rna', 'hbv dna',
        'hiv', 'vdrl', 'tpha', 'sts', '梅毒', 'widal', 'streptococcus', 'c3', 'c4', 'igg', 'iga', 'igm'
    ]):
        return 'immunological'

    # 6. Cardiac & Endocrine (Others)
    if any(k in comb for k in [
        'troponin', 'ck-mb', 'cpk', 'myoglobin', 'bnp', 'nt-probnp',
        'tsh', 'free t4', 'ft4', 't3', 't4', 'cortisol', 'acth', 'psa',
        'cea', 'ca125', 'ca19-9', 'ca-125', 'ca-199'
    ]):
        return 'metabolic'

    return 'others'
