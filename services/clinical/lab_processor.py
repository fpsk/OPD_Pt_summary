"""
Laboratory test processor, longitudinal flowsheet constructor, and liver score calculator.
"""

import math
import re
from typing import Any, Dict, List, Optional, Tuple

from services.clinical.lab_cleaner import (
    classify_lab_group,
    clean_display_reference_range,
    clean_lab_item_name,
    parse_reference_range,
)
from services.patient_mcp_client import to_standard_date


class LabProcessor:
    """Processes raw laboratory orders into clinical panels, longitudinal flowsheets, and liver assessments."""

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

            clean_r = clean_display_reference_range(ref, gender=str(patient_gender or ""), item_name=cleaned_name)

            entry = {
                "item": cleaned_name,
                "raw_item": item,
                "order": order,
                "value_str": val_str,
                "value_num": val_num,
                "unit": unit,
                "ref": clean_r,
                "raw_ref": ref,
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
        flowsheet = self._build_lab_flowsheet(grouped["all"], patient_age=patient_age, patient_gender=patient_gender)

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
        patient_age: Optional[float] = None,
        patient_gender: Optional[str] = None
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

        # Track most recent reference range and unit per analyte by latest date
        item_latest_meta: Dict[str, Dict[str, Any]] = {}

        for e in entries:
            it_name = e.get("item") or "Unknown"
            raw_it = e.get("raw_item") or ""
            ord_str = e.get("order") or ""
            d = e.get("date") or ""
            val_num = e.get("value_num")
            u = e.get("unit") or ""
            c_ref = e.get("ref") or ""
            raw_r = e.get("raw_ref") or c_ref

            if not c_ref and raw_r:
                c_ref = clean_display_reference_range(raw_r, gender=str(patient_gender or ""), item_name=it_name)

            cat_id = classify_lab_group(it_name, raw_it, ord_str)
            if cat_id not in cat_items_map:
                cat_id = "others"

            # Track liver biomarkers for calculated fibrosis rows
            it_lower = it_name.lower()
            if ("ast" in it_lower or "got" in it_lower) and val_num is not None and d:
                ast_by_date[d] = val_num
            elif ("alt" in it_lower or "gpt" in it_lower) and val_num is not None and d:
                alt_by_date[d] = val_num
            elif "platelet" in it_lower and val_num is not None and d:
                plt_by_date[d] = val_num

            # Track latest unit & reference range by comparing date
            if it_name not in item_latest_meta:
                item_latest_meta[it_name] = {
                    "latest_date": d,
                    "unit": u,
                    "ref": c_ref,
                    "raw_ref": raw_r
                }
            else:
                meta = item_latest_meta[it_name]
                is_newer_date = d > meta["latest_date"]
                is_same_date = d == meta["latest_date"]
                if is_newer_date:
                    meta["latest_date"] = d
                    if u:
                        meta["unit"] = u
                    if c_ref or raw_r:
                        meta["ref"] = c_ref
                        meta["raw_ref"] = raw_r
                elif is_same_date:
                    if not meta["ref"] and c_ref:
                        meta["ref"] = c_ref
                        meta["raw_ref"] = raw_r
                    if not meta["unit"] and u:
                        meta["unit"] = u
                else:
                    if not meta["unit"] and u:
                        meta["unit"] = u
                    if not meta["ref"] and c_ref:
                        meta["ref"] = c_ref
                        meta["raw_ref"] = raw_r

            if it_name not in cat_items_map[cat_id]:
                cat_items_map[cat_id][it_name] = {
                    "item": it_name,
                    "unit": u,
                    "ref": c_ref,
                    "raw_ref": raw_r,
                    "category": cat_id,
                    "values": {}
                }

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

        # Synchronize most recent unit and reference range to all item rows
        for cat_id in cat_items_map:
            for it_name, it_dict in cat_items_map[cat_id].items():
                if it_name in item_latest_meta and not it_dict.get("is_calculated"):
                    meta = item_latest_meta[it_name]
                    if meta.get("ref"):
                        it_dict["ref"] = meta["ref"]
                    if meta.get("raw_ref"):
                        it_dict["raw_ref"] = meta["raw_ref"]
                    if meta.get("unit"):
                        it_dict["unit"] = meta["unit"]

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


    # Backwards-compatible aliases
    process_laboratory_tests = _process_laboratory_tests
    build_lab_flowsheet = _build_lab_flowsheet
    calculate_liver_scores = _calculate_liver_scores
