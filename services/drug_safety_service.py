"""
Clinical Drug Safety Information Service.
Extracts structured safety data from:
  1. FDC Knowledge Base (fdc_knowledge.db, ingredient_limits.json) for Fixed-Dose Combinations
  2. CDSS Knowledge Base (cdss_knowledge.db: drugs, renal_adjustments, side_effects, ddis, taiwan_nhi_drugs, drug_products)
  3. OKF Clinical Pharmacology Knowledge Base (okf_kb/drugs/{slug}.md for 2,904 clinical entities)
  4. Labels_FDA_XML/*.json (1,526 US FDA SPL structured prescribing information files)
  5. Authoritative Outpatient Clinical Dosing Knowledge Dictionary (Taiwan & international guidelines)
"""

import os
import re
import json
import sqlite3
import logging
from typing import Dict, Any, Optional, List, Tuple, Set

import yaml

import config

logger = logging.getLogger(__name__)

MED_INFO_DIR = os.path.join(config.PARENT_DIR, "Medication_Info")
DB_PATH = os.path.join(MED_INFO_DIR, "okf_kb", "cdss_knowledge.db")
DRUGS_MD_DIR = os.path.join(MED_INFO_DIR, "okf_kb", "drugs")
LABELS_FDA_DIR = os.path.join(MED_INFO_DIR, "Labels_FDA_XML")
FDC_DB_PATH = os.path.join(config.PARENT_DIR, "FDCs", "data", "fdc_knowledge.db")
FDC_LIMITS_PATH = os.path.join(config.PARENT_DIR, "FDCs", "data", "ingredient_limits.json")

# Chinese name mapping for active moieties
from services.drug_safety_data import (
    CLINICAL_DOSING_KB,
    FALLBACK_LIMITS,
    MOIETY_CHINESE_NAMES,
    MOIETY_CLINICAL_REMARKS,
    MOIETY_DRUG_CLASSES,
    MOIETY_MONOTHERAPY_DOSES,
)



def _connect_ro(path: str) -> sqlite3.Connection:
    """Connect to SQLite database in read-only immutable mode for sandbox resilience."""
    db_uri = f"file:{os.path.abspath(path).replace(os.sep, '/')}?immutable=1"
    try:
        conn = sqlite3.connect(db_uri, uri=True, timeout=5)
    except Exception:
        conn = sqlite3.connect(path, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


class DrugSafetyService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DrugSafetyService, cls).__new__(cls)
            cls._instance._init_service()
        return cls._instance

    def _init_service(self):
        self._fda_file_cache = None
        self._ingredient_limits = None

    def _get_ingredient_limits(self) -> Dict[str, Any]:
        if self._ingredient_limits is not None:
            return self._ingredient_limits
        self._ingredient_limits = {}
        if os.path.exists(FDC_LIMITS_PATH):
            try:
                with open(FDC_LIMITS_PATH, "r", encoding="utf-8") as f:
                    self._ingredient_limits = json.load(f)
            except Exception as e:
                logger.error("Failed to load ingredient_limits.json: %s", e)
        return self._ingredient_limits

    def _get_fda_files(self) -> Dict[str, str]:
        if self._fda_file_cache is not None:
            return self._fda_file_cache
        self._fda_file_cache = {}
        if os.path.exists(LABELS_FDA_DIR):
            try:
                for fname in os.listdir(LABELS_FDA_DIR):
                    if fname.lower().endswith(".json"):
                        self._fda_file_cache[fname.lower()] = os.path.join(LABELS_FDA_DIR, fname)
            except Exception as e:
                logger.error("Failed to index FDA XML directory: %s", e)
        return self._fda_file_cache

    def _lookup_fdc_info(self, clean_code: str, clean_brand: str, clean_gen: str) -> Optional[Dict[str, Any]]:
        """Query fdc_knowledge.db for structured FDC metadata."""
        if not os.path.exists(FDC_DB_PATH):
            return None

        try:
            conn = _connect_ro(FDC_DB_PATH)
            cur = conn.cursor()

            row = None
            if clean_code:
                cur.execute("SELECT * FROM nhi_drugs WHERE nhi_code = ?", (clean_code,))
                row = cur.fetchone()

            if not row and clean_brand:
                # Strip leading numbering (e.g., '3   ')
                brand_stem = re.sub(r"^[0-9\s\.\-]+", "", clean_brand).strip()
                core_b = re.split(r"[\s0-9/]+", brand_stem)[0]
                if len(core_b) >= 2:
                    cur.execute(
                        "SELECT * FROM nhi_drugs WHERE brand_name_chi LIKE ? OR brand_name_eng LIKE ? LIMIT 1",
                        (f"%{core_b}%", f"%{core_b}%")
                    )
                    row = cur.fetchone()

            if not row and clean_gen:
                parts = [p.strip().upper() for p in re.split(r"[\+/&]", clean_gen) if len(p.strip()) >= 3]
                if len(parts) >= 2:
                    where_clauses = ["ingredient_count = ?"]
                    params = [len(parts)]
                    for p in parts:
                        where_clauses.append("active_moiety_summary LIKE ?")
                        params.append(f"%{p}%")
                    cur.execute(
                        f"SELECT * FROM nhi_drugs WHERE {' AND '.join(where_clauses)} LIMIT 1",
                        params
                    )
                    row = cur.fetchone()

            conn.close()

            if row:
                ings = []
                if row["ingredients_json"]:
                    try:
                        ings = json.loads(row["ingredients_json"])
                    except Exception:
                        pass
                return {
                    "nhi_code": row["nhi_code"],
                    "brand_eng": row["brand_name_eng"] or "",
                    "brand_chi": row["brand_name_chi"] or "",
                    "atc_code": row["atc_code"] or "",
                    "dosage_form": row["dosage_form"] or "",
                    "is_fdc": bool(row["is_fdc"]),
                    "ingredient_count": row["ingredient_count"] or len(ings),
                    "active_moiety_summary": row["active_moiety_summary"] or "",
                    "clinical_base_strength": row["clinical_base_strength"] or "",
                    "chemical_salt_summary": row["chemical_salt_summary"] or "",
                    "ingredients": ings
                }
        except Exception as e:
            logger.error("Error querying fdc_knowledge.db: %s", e)

        return None

    def _score_fda_file(self, fname_lower: str, query: str, active_moieties: List[str]) -> int:
        q = query.lower().strip()
        base = fname_lower.replace("_spl.json", "").replace(".json", "")
        if q not in base:
            return 0
        score = 10
        if base.startswith(q + "_") or base.startswith(q + "-"):
            score += 80
        if base.startswith(f"{q}_{q}"):
            score += 40

        # Heavily penalize mismatching combination products
        if len(active_moieties) >= 2:
            m_lowers = [m.lower() for m in active_moieties]
            # e.g., if query is valsartan + amlodipine, penalize hydrochlorothiazide
            if "hydrochlorothiazide" in base and "hydrochlorothiazide" not in m_lowers:
                score -= 150
            if "and" in base:
                matched_all = all(m in base for m in m_lowers)
                if matched_all:
                    score += 100
                else:
                    score -= 60
        else:
            if "and" in base and not q.startswith("and"):
                score -= 40

        if any(k in base for k in [",", "spray", "minoxidil", "hair", "topical", "shampoo"]) and q not in ["minoxidil", "spray"]:
            score -= 70

        if any(statin in base for statin in ["rosuvastatin", "atorvastatin", "pitavastatin"]) and "statin" not in q:
            score -= 100

        return score

    def _find_fda_json(self, generic_name: str, brand_name: str, active_moieties: List[str]) -> Optional[Dict[str, Any]]:
        files_map = self._get_fda_files()
        cands = []
        if generic_name:
            clean_g = generic_name.lower().strip()
            cands.append(clean_g)
            first_w = re.split(r"[\s\(\)/,]+", clean_g)[0]
            if first_w and len(first_w) >= 3 and first_w != clean_g:
                cands.append(first_w)
        if brand_name:
            clean_b = brand_name.lower().strip()
            first_b = re.split(r"[\s\(\)/,\"]+", clean_b)[0]
            if first_b and len(first_b) >= 3:
                cands.append(first_b)

        best_match = None
        best_score = 0
        for cand in cands:
            if not cand or len(cand) < 3:
                continue
            for fname_lower, fpath in files_map.items():
                s = self._score_fda_file(fname_lower, cand, active_moieties)
                if s > best_score:
                    best_score = s
                    best_match = fpath

        if best_match and best_score > 0:
            try:
                with open(best_match, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error("Failed to load FDA JSON %s: %s", best_match, e)
        return None

    def _match_dosing_kb(self, is_fdc: bool, active_moieties: List[str], matched_name: str, clean_gen: str, clean_brand: str) -> Optional[Dict[str, str]]:
        # 1. Multi-moiety FDC match first
        if is_fdc and len(active_moieties) >= 2:
            m_set = set(m.lower() for m in active_moieties)
            for key, val in CLINICAL_DOSING_KB.items():
                if "+" in key or "/" in key:
                    parts = set(p.strip().lower() for p in re.split(r"[\+/]", key))
                    if parts == m_set:
                        return val

            # Also test clean_brand / clean_gen against combo keys
            tokens = [clean_brand.lower(), clean_gen.lower(), matched_name.lower()]
            for key in sorted([k for k in CLINICAL_DOSING_KB.keys() if "+" in k or "/" in k], key=lambda x: -len(x)):
                parts = [p.strip().lower() for p in re.split(r"[\+/]", key)]
                if all(any(p in t for t in tokens) for p in parts):
                    return CLINICAL_DOSING_KB[key]

        # 2. Single ingredient match (STRICTLY IGNORE combo keys containing '+' or '/')
        single_kb = {k: v for k, v in CLINICAL_DOSING_KB.items() if "+" not in k and "/" not in k}

        tokens = []
        for s in active_moieties + [clean_gen, matched_name, clean_brand]:
            if not s:
                continue
            low = s.lower().strip()
            tokens.append(low)
            parts = re.split(r"[\s\(\)/,\"]+", low)
            tokens.extend([p for p in parts if len(p) >= 3])

        # Priority A: exact key matches
        for t in tokens:
            if t in single_kb:
                return single_kb[t]

        # Priority B: word-prefix matches (never substring within multi-ingredient names)
        for key in sorted(single_kb.keys(), key=lambda k: -len(k)):
            for t in tokens:
                if key == t or key.startswith(t) or t.startswith(key):
                    return single_kb[key]

        return None

    def _build_fdc_components(self, active_moieties: List[str], fdc_ingredients: List[Dict], strength_str: str) -> List[Dict[str, Any]]:
        """Construct structured component breakdown for Card 1."""
        limits = self._get_ingredient_limits()
        components = []

        # Map amounts from fdc_ingredients
        amount_map = {}
        for ing in fdc_ingredients:
            m = ing.get("active_moiety", "").upper()
            val = ing.get("amount_value")
            unit = ing.get("amount_unit") or "MG"
            if m:
                amount_map[m] = (val, unit)

        for m_raw in active_moieties:
            m = m_raw.upper()
            zh_name = MOIETY_CHINESE_NAMES.get(m, m.capitalize())
            drug_class = MOIETY_DRUG_CLASSES.get(m, "")
            mono_dose = MOIETY_MONOTHERAPY_DOSES.get(m, "")

            # Dose limit
            max_daily_val = None
            unit = "mg"
            if m in limits:
                max_daily_val = limits[m].get("standard_adult_max_daily")
                unit = limits[m].get("unit", "mg").lower()
            elif m in FALLBACK_LIMITS:
                max_daily_val = FALLBACK_LIMITS[m]

            max_str = f"{int(max_daily_val) if max_daily_val == int(max_daily_val) else max_daily_val} {unit}/天" if max_daily_val else "依臨床指引滴定"

            # Clinical warning & renal note
            rem = MOIETY_CLINICAL_REMARKS.get(m, {})
            warning = rem.get("warning", "")
            renal = rem.get("renal", "")

            # Pill strength
            amt_str = ""
            amt_val = None
            if m in amount_map:
                amt_val, u = amount_map[m]
                if amt_val is not None:
                    amt_str = f"{int(amt_val) if amt_val == int(amt_val) else amt_val} {u.lower()}"

            components.append({
                "moiety": m,
                "display_name": zh_name,
                "drug_class": drug_class,
                "amount_str": amt_str,
                "amount_value": amt_val,
                "amount_unit": unit,
                "monotherapy_dose": mono_dose,
                "max_daily_dose": max_str,
                "warning": warning,
                "renal_note": renal
            })

        return components

    def get_safety_profile(self, nhi_code: str = "", brand_name: str = "", generic_name: str = "") -> Dict[str, Any]:
        """
        Synthesize full clinical safety profile for a medication.
        Supports both Fixed-Dose Combinations (FDC) and single-ingredient medications.
        """
        if not os.path.exists(DB_PATH):
            return {"status": "error", "message": "Knowledge base not found"}

        clean_code = (nhi_code or "").strip().upper()
        # Clean brand name: strip leading numbers and spaces (e.g. '3   易德壓悅膜衣錠5/80毫克')
        clean_brand = re.sub(r"^[0-9\s\.\-]+", "", (brand_name or "")).strip()
        clean_gen = (generic_name or "").strip()

        trade_zh = ""
        trade_en = ""
        dosage_form = ""
        strength = ""
        atc_code = ""
        okf_drug_name = ""

        # Step 1: Query FDC Knowledge Base (fdc_knowledge.db)
        fdc_info = self._lookup_fdc_info(clean_code, clean_brand, clean_gen)

        is_fdc = False
        active_moieties: List[str] = []
        fdc_ingredients: List[Dict] = []

        if fdc_info:
            is_fdc = fdc_info["is_fdc"]
            trade_zh = trade_zh or fdc_info["brand_chi"]
            trade_en = trade_en or fdc_info["brand_eng"]
            atc_code = atc_code or fdc_info["atc_code"]
            dosage_form = dosage_form or fdc_info["dosage_form"]
            strength = strength or fdc_info["clinical_base_strength"]
            fdc_ingredients = fdc_info.get("ingredients") or []

            if fdc_info["active_moiety_summary"]:
                summary_parts = [p.strip().upper() for p in fdc_info["active_moiety_summary"].split("/") if p.strip()]
                active_moieties.extend(summary_parts)

            if is_fdc and not clean_gen:
                clean_gen = " + ".join([p.capitalize() for p in active_moieties])

        # Step 2: Query CDSS Knowledge Base (cdss_knowledge.db)
        try:
            conn = _connect_ro(DB_PATH)
            cur = conn.cursor()

            if clean_code:
                cur.execute("SELECT * FROM taiwan_nhi_drugs WHERE nhi_code = ?", (clean_code,))
                row = cur.fetchone()
                if row:
                    trade_zh = trade_zh or row["brand_name_chi"] or ""
                    trade_en = trade_en or row["brand_name_eng"] or ""
                    atc_code = atc_code or row["atc_code"] or ""
                    dosage_form = dosage_form or row["dosage_form"] or ""
                    okf_drug_name = row["okf_drug_name"] or ""
                    if not clean_gen and row["ingredient"]:
                        clean_gen = row["ingredient"]

            if clean_code or clean_brand:
                cur.execute(
                    "SELECT * FROM drug_products WHERE nhi_code = ? OR trade_name_en LIKE ? OR trade_name_zh LIKE ?",
                    (clean_code, f"%{clean_brand}%", f"%{clean_brand}%")
                )
                prod = cur.fetchone()
                if prod:
                    trade_zh = trade_zh or prod["trade_name_zh"] or ""
                    trade_en = trade_en or prod["trade_name_en"] or ""
                    dosage_form = dosage_form or prod["dosage_form"] or ""
                    strength = strength or prod["strength"] or ""
                    atc_code = atc_code or prod["atc_code"] or ""
                    if not clean_gen and prod["generic_drug_name"]:
                        clean_gen = prod["generic_drug_name"]

            # If active_moieties still empty, parse from clean_gen
            if not active_moieties and clean_gen:
                if any(sep in clean_gen for sep in ["+", "/", " and ", "&", " with "]):
                    parts = re.split(r"[\+/&]|(?:\s+and\s+)|\s+with\s+", clean_gen, flags=re.I)
                    for p in parts:
                        clean_p = re.split(r"[\s\(\)/,]+", p.strip())[0].upper()
                        if clean_p and len(clean_p) >= 3 and clean_p not in active_moieties:
                            active_moieties.append(clean_p)
                    if len(active_moieties) >= 2:
                        is_fdc = True
                else:
                    m_moi = re.match(r"^([A-Za-z\-]+)", clean_gen.strip())
                    if m_moi:
                        active_moieties.append(m_moi.group(1).upper())

            if not active_moieties and okf_drug_name:
                active_moieties.append(okf_drug_name.upper())

            if not active_moieties and clean_brand:
                m_b = re.match(r"^([A-Za-z\-]+)", clean_brand.strip())
                if m_b:
                    active_moieties.append(m_b.group(1).upper())

            # Step 3: Match in drugs table
            drugs_rows = []
            for cand in active_moieties + [clean_gen, clean_brand, okf_drug_name]:
                if not cand or len(cand) < 2:
                    continue
                cur.execute("SELECT * FROM drugs WHERE drug_name = ? COLLATE NOCASE", (cand,))
                r = cur.fetchone()
                if r and r not in drugs_rows:
                    drugs_rows.append(r)

            # Look for combination drug row if FDC
            combo_row = None
            if len(active_moieties) >= 2:
                combo_name1 = "".join([m.capitalize() for m in active_moieties])
                combo_name2 = " and ".join([m.capitalize() for m in active_moieties])
                combo_name3 = " / ".join([m.capitalize() for m in active_moieties])
                for c_cand in [combo_name1, combo_name2, combo_name3]:
                    cur.execute("SELECT * FROM drugs WHERE drug_name LIKE ? COLLATE NOCASE", (f"%{c_cand}%",))
                    combo_row = cur.fetchone()
                    if combo_row:
                        break

            primary_drug_row = combo_row or (drugs_rows[0] if drugs_rows else None)
            matched_name = primary_drug_row["drug_name"] if primary_drug_row else (" + ".join([m.capitalize() for m in active_moieties]) if active_moieties else (clean_gen or clean_brand))

            # Step 4: Check okf_kb markdown files
            md_data = {}
            md_body = ""
            component_mds = []

            # 4a. Check combination markdown file
            if len(active_moieties) >= 2:
                combo_slugs = [
                    "".join(m.lower() for m in active_moieties),
                    "_".join(m.lower() for m in active_moieties),
                    "-".join(m.lower() for m in active_moieties),
                    f"{active_moieties[0].lower()}_and_{active_moieties[1].lower()}"
                ]
                for cs in combo_slugs:
                    mpath = os.path.join(DRUGS_MD_DIR, f"{cs}.md")
                    if os.path.exists(mpath):
                        try:
                            with open(mpath, "r", encoding="utf-8") as f:
                                parts = f.read().split("---")
                                if len(parts) >= 3:
                                    md_data = yaml.safe_load(parts[1]) or {}
                                    md_body = "---".join(parts[2:])
                                    break
                        except Exception:
                            pass

            # 4b. Check individual component markdown files
            for m in active_moieties:
                slug = m.lower()
                mpath = os.path.join(DRUGS_MD_DIR, f"{slug}.md")
                if os.path.exists(mpath):
                    try:
                        with open(mpath, "r", encoding="utf-8") as f:
                            parts = f.read().split("---")
                            if len(parts) >= 3:
                                component_mds.append({
                                    "moiety": m,
                                    "data": yaml.safe_load(parts[1]) or {},
                                    "body": "---".join(parts[2:])
                                })
                    except Exception:
                        pass

            # Step 5: Check FDA SPL JSON with scoring
            fda_data = self._find_fda_json(clean_gen or matched_name, clean_brand, active_moieties)

            # Step 6: Query DB tables: renal_adjustments, side_effects, ddis
            renal_db_rows = []
            side_effects_db = []
            ddis_db = []

            query_names = list(active_moieties)
            if matched_name and matched_name not in query_names:
                query_names.append(matched_name)

            for qn in query_names:
                cur.execute(
                    "SELECT egfr_min, egfr_max, dose_recommendation FROM renal_adjustments WHERE drug_name = ? OR drug_name LIKE ?",
                    (qn, f"%{qn}%")
                )
                renal_db_rows.extend([dict(r) for r in cur.fetchall()])

                cur.execute(
                    "SELECT organ_system, side_effect, is_severe FROM side_effects WHERE drug_name = ? OR drug_name LIKE ?",
                    (qn, f"%{qn}%")
                )
                side_effects_db.extend([dict(r) for r in cur.fetchall()])

                cur.execute(
                    "SELECT drug_b, severity, mechanism, action, clinical_effect FROM ddis WHERE drug_a = ? OR drug_a LIKE ? LIMIT 8",
                    (qn, f"%{qn}%")
                )
                ddis_db.extend([dict(r) for r in cur.fetchall()])

            conn.close()
        except Exception as e:
            logger.error("Error querying cdss_knowledge.db: %s", e)
            return {"status": "error", "message": str(e)}

        # ==================== SYNTHESIZE CLINICAL SECTIONS ====================

        # A. Build FDC Components if multiple active moieties
        components = []
        if is_fdc or len(active_moieties) >= 2:
            is_fdc = True
            components = self._build_fdc_components(active_moieties, fdc_ingredients, strength)

        # B. Safety Dose Range
        dose_info = self._extract_dose_range(
            is_fdc, components, active_moieties, fda_data, md_data, md_body,
            strength, matched_name, clean_gen, clean_brand
        )

        # C. Renal Adjustment
        renal_info = self._extract_renal_adjustment(is_fdc, active_moieties, renal_db_rows, md_data, component_mds, fda_data)

        # D. Side Effects
        side_effects_info = self._extract_side_effects(side_effects_db, md_data, component_mds, fda_data)

        # E. Contraindications
        contraindications_list = self._extract_contraindications(is_fdc, active_moieties, primary_drug_row, md_data, component_mds, fda_data)

        # F. Pregnancy Warning
        pregnancy_info = self._extract_pregnancy(is_fdc, active_moieties, fda_data, md_body, md_data, component_mds)

        # G. Safety Remarks (Boxed warnings, Monitoring, DDIs)
        remarks_info = self._extract_safety_remarks(is_fdc, active_moieties, primary_drug_row, md_data, component_mds, fda_data, ddis_db)

        # Extract drug classes
        drug_classes = []
        if md_data.get("drug_classes"):
            drug_classes.extend(md_data["drug_classes"])
        for m in active_moieties:
            cls_name = MOIETY_DRUG_CLASSES.get(m)
            if cls_name and cls_name not in drug_classes:
                drug_classes.append(cls_name)

        return {
            "status": "success",
            "found": True,
            "drug_name": matched_name,
            "brand_name_zh": trade_zh,
            "brand_name_en": trade_en or clean_brand,
            "generic_name": clean_gen or (" + ".join([m.capitalize() for m in active_moieties]) if active_moieties else matched_name),
            "nhi_code": clean_code,
            "atc_code": atc_code or md_data.get("atc_code") or "",
            "dosage_form": dosage_form,
            "strength": strength,
            "is_fdc": is_fdc,
            "drug_classes": drug_classes[:4],
            "high_alert": bool(md_data.get("high_alert") or (primary_drug_row and primary_drug_row["indications"] and "high_alert" in str(primary_drug_row["indications"]))),
            "safety_dose_range": dose_info,
            "renal_adjustment": renal_info,
            "side_effects": side_effects_info,
            "contraindications": contraindications_list,
            "pregnancy_warning": pregnancy_info,
            "safety_remarks": remarks_info
        }

    def _extract_dose_range(
        self,
        is_fdc: bool,
        components: List[Dict],
        active_moieties: List[str],
        fda_data: Optional[Dict],
        md_data: Dict,
        md_body: str,
        strength: str,
        matched_name: str,
        clean_gen: str,
        clean_brand: str
    ) -> Dict[str, Any]:
        """Synthesize detailed clinical dosing parameters."""
        kb_entry = self._match_dosing_kb(is_fdc, active_moieties, matched_name, clean_gen, clean_brand)

        starting_dose = ""
        max_dose = ""
        timing = ""
        titration = ""
        summary = ""

        if kb_entry:
            starting_dose = kb_entry.get("starting_dose", "")
            max_dose = kb_entry.get("max_daily_dose", "")
            timing = kb_entry.get("timing", "")
            titration = kb_entry.get("titration", "")
            summary = kb_entry.get("summary", "")

        # Dynamic fallback for FDC if not in KB
        if is_fdc and components:
            if not starting_dose:
                starting_dose = f"複方起始：每日 1 錠 (隨餐或空腹)；依處方規格 ({strength or '標準規格'}) 每日一次"
            if not max_dose:
                comp_limits = [f"{c['display_name'].split('(')[0].strip()} {c['max_daily_dose']}" for c in components if c.get("max_daily_dose")]
                max_dose = f"複方每日上限 1 錠 (各主成分單日安全上限：{'; '.join(comp_limits)})"
            if not timing:
                timing = "每日一次固定時間服用，可隨餐或空腹 (早晨服用為佳)"
            if not titration:
                titration = "複方製劑通常每日給藥一次。建議治療 1~2 週後依臨床療效與耐受性評估是否調整規格。"
            if not summary:
                comp_names = [c["display_name"] for c in components]
                comp_limits = [f"{c['display_name'].split('(')[0].strip()} 上限 {c['max_daily_dose']}" for c in components]
                summary = f"固定劑量複方製劑 (FDC)，包含 {', '.join(comp_names)}。機轉互補提升臨床療效。各成分每日安全上限分別為：{'; '.join(comp_limits)}。"

        fda_dose = ""
        if not is_fdc and fda_data and fda_data.get("dosage_and_administration"):
            raw_d = fda_data["dosage_and_administration"]
            fda_dose = " ".join(raw_d) if isinstance(raw_d, list) else str(raw_d)
            fda_dose = fda_dose.replace('\xbd', '1/2').replace('\xbc', '1/4').replace('\xbe', '3/4')
            fda_dose = re.sub(r"\(\s*[0-9]+(?:\.[0-9]+)?\s*\)", "", fda_dose)
            fda_dose = re.sub(r"\s+", " ", fda_dose).strip()

        # Monotherapy fallbacks
        if not starting_dose:
            starting_dose = f"依規格 ({strength}) 每日 1 次起始" if strength else "依臨床處方適應症起始"
        if not max_dose:
            max_dose = "依臨床療效與耐受性滴定，參閱處方指引"
        if not timing:
            timing = "每日固定時間服用，可隨餐或空腹"
        if not summary:
            summary = f"常規用法：依門診醫師指示服用。給藥規格為 {strength or '標準錠劑'}，請依處方頻率與適應症定期回診追蹤。"

        return {
            "is_fdc": is_fdc,
            "components": components,
            "summary": summary,
            "starting_dose": starting_dose,
            "max_daily_dose": max_dose,
            "administration_timing": timing,
            "titration": titration,
            "full_text": fda_dose[:1200] if fda_dose else ""
        }

    def _extract_renal_adjustment(
        self,
        is_fdc: bool,
        active_moieties: List[str],
        renal_db_rows: List[Dict],
        md_data: Dict,
        component_mds: List[Dict],
        fda_data: Optional[Dict]
    ) -> Dict[str, Any]:
        """Synthesize comprehensive renal adjustment guidelines."""
        brackets = []
        limits = self._get_ingredient_limits()

        # Check if FDC contains Valsartan + Amlodipine
        m_set = set(m.upper() for m in active_moieties)
        if "VALSARTAN" in m_set and "AMLODIPINE" in m_set:
            brackets = [
                {
                    "egfr_range": ">= 30 mL/min",
                    "severity": "normal",
                    "recommendation": "輕中度腎功能不全者無需調整起始劑量；維持常規監測。"
                },
                {
                    "egfr_range": "15 - 29 mL/min",
                    "severity": "moderate",
                    "recommendation": "謹慎使用；Amlodipine 無需減量，但 Valsartan 需加強監測血清鉀離子與肌酸酐變化。"
                },
                {
                    "egfr_range": "< 15 mL/min",
                    "severity": "severe",
                    "recommendation": "重度腎衰竭缺乏充分臨床試驗數據；極為謹慎使用並密切追蹤血鉀、血壓與體液狀態。"
                }
            ]
            dialysis_note = "Amlodipine 與 Valsartan 均高度結合於血漿蛋白 (分別 > 95% 與 95%)，血液透析無法有效清除。"
            hepatic_note = "Amlodipine 由肝臟大量代謝 (嚴重肝硬化或肝衰竭上限 5 mg/天)；Valsartan 主要經由膽汁排泄 (嚴重肝損或膽道阻塞者慎用)。建議重度肝病患者由低劑量起始並定期追蹤 AST/ALT。"
            return {
                "brackets": brackets,
                "dialysis_note": dialysis_note,
                "hepatic_adjustment": hepatic_note
            }

        # Check if FDC contains Metformin
        if "METFORMIN" in m_set:
            brackets = [
                {
                    "egfr_range": ">= 60 mL/min",
                    "severity": "normal",
                    "recommendation": "腎功能正常或輕度下降，可使用常規劑量 (Metformin 上限 2,000~2,550 mg/天)。"
                },
                {
                    "egfr_range": "45 - 59 mL/min",
                    "severity": "normal",
                    "recommendation": "需評估腎功能相關危險因子；Metformin 每日最大劑量建議不超過 2,000 mg/天。"
                },
                {
                    "egfr_range": "30 - 44 mL/min",
                    "severity": "moderate",
                    "recommendation": "不建議起始治療；已使用者劑量應減半，Metformin 每日上限 1,000 mg/天，每 3 個月密切追蹤腎功能。"
                },
                {
                    "egfr_range": "< 30 mL/min",
                    "severity": "severe",
                    "recommendation": "嚴格絕對禁用！Metformin 在重度腎功能障礙下體內蓄積，可能引發致死性乳酸中毒 (MALA)。"
                }
            ]
            dialysis_note = "末期腎病 (ESRD) 與透析患者絕對禁用 Metformin 製劑 (致死性乳酸中毒風險)。"
            hepatic_note = "肝功能不全或失代償性肝硬化會顯著降低乳酸清除能力，嚴禁使用 Metformin。"
            return {
                "brackets": brackets,
                "dialysis_note": dialysis_note,
                "hepatic_adjustment": hepatic_note
            }

        # General extraction from MD frontmatter
        md_renal = md_data.get("dosage_adjustments", {}).get("renal") or []
        if isinstance(md_renal, list) and len(md_renal) > 0:
            for item in md_renal:
                min_v = item.get("egfr_min")
                max_v = item.get("egfr_max")
                rec = item.get("dose_recommendation", "")
                if min_v is not None and max_v is not None:
                    rng = f"{min_v} - {max_v} mL/min"
                elif min_v is not None:
                    rng = f">= {min_v} mL/min"
                elif max_v is not None:
                    rng = f"< {max_v} mL/min"
                else:
                    rng = "臨床腎功能考量"

                sev = "severe" if (max_v and max_v <= 30) else ("moderate" if (max_v and max_v <= 60) else "normal")
                brackets.append({
                    "egfr_range": rng,
                    "severity": sev,
                    "recommendation": rec
                })

        # Fallback to DB rows
        if not brackets and renal_db_rows:
            seen_rec = set()
            for r in renal_db_rows:
                min_v = r.get("egfr_min")
                max_v = r.get("egfr_max")
                rec = r.get("dose_recommendation", "")
                if rec in seen_rec:
                    continue
                seen_rec.add(rec)
                rng = f"{min_v or 0} - {max_v or '上限'} mL/min" if (min_v or max_v) else "腎功能指標"
                sev = "severe" if (max_v and max_v <= 30) else "moderate"
                brackets.append({
                    "egfr_range": rng,
                    "severity": sev,
                    "recommendation": rec
                })
                if len(brackets) >= 4:
                    break

        if not brackets:
            brackets.append({
                "egfr_range": "一般腎功能指引",
                "severity": "normal",
                "recommendation": "多數輕中度腎功能不全患者一般無需調整劑量，重度腎衰竭或透析患者建議監測藥物血中濃度及腎功能指數。"
            })

        dialysis_note = "依透析清除率與殘餘腎功能調整劑量，並密切監測臨床療效及體液平衡。"
        hepatic_text = "輕中度肝損通常無需調整劑量；重度肝損患者建議謹慎使用並定期監測 AST/ALT。"

        return {
            "brackets": brackets,
            "dialysis_note": dialysis_note,
            "hepatic_adjustment": hepatic_text
        }

    def _extract_side_effects(
        self,
        side_effects_db: List[Dict],
        md_data: Dict,
        component_mds: List[Dict],
        fda_data: Optional[Dict]
    ) -> Dict[str, Any]:
        common = []
        severe = []
        by_system = {}

        # Collect from main md_data
        md_se = md_data.get("side_effects") or []
        if isinstance(md_se, list):
            for item in md_se:
                term = item.get("term") or item.get("side_effect")
                is_sev = bool(item.get("is_severe"))
                sys_name = item.get("organ_system") or "全身性"
                if term:
                    if is_sev and term not in severe:
                        severe.append(term)
                    elif not is_sev and term not in common:
                        common.append(term)
                    if sys_name not in by_system:
                        by_system[sys_name] = []
                    if term not in by_system[sys_name]:
                        by_system[sys_name].append(term)

        # Collect from component MDs
        for c_md in component_mds:
            c_se = c_md.get("data", {}).get("side_effects") or []
            if isinstance(c_se, list):
                for item in c_se:
                    term = item.get("term") or item.get("side_effect")
                    is_sev = bool(item.get("is_severe"))
                    sys_name = item.get("organ_system") or "全身性"
                    if term:
                        if is_sev and term not in severe:
                            severe.append(term)
                        elif not is_sev and term not in common:
                            common.append(term)
                        if sys_name not in by_system:
                            by_system[sys_name] = []
                        if term not in by_system[sys_name]:
                            by_system[sys_name].append(term)

        # Collect from DB
        for row in side_effects_db:
            se_name = row.get("side_effect")
            sys_name = row.get("organ_system") or "全身性"
            is_sev = bool(row.get("is_severe"))
            if se_name:
                if is_sev and se_name not in severe:
                    severe.append(se_name)
                elif not is_sev and se_name not in common:
                    common.append(se_name)
                if sys_name not in by_system:
                    by_system[sys_name] = []
                if se_name not in by_system[sys_name]:
                    by_system[sys_name].append(se_name)

        if not common:
            common = ["周邊水腫 (踝部水腫)", "頭暈 (Dizziness)", "頭痛 (Headache)", "噁心/嘔吐", "疲倦與潮紅"]
        if not severe:
            severe = ["血管性水腫 (Angioedema)", "高血鉀症 (Hyperkalemia)", "嚴重急性低血壓 / 暈厥", "急性腎損傷 (AKI)"]

        return {
            "common": common[:8],
            "severe": severe[:6],
            "by_system": by_system
        }

    def _extract_contraindications(
        self,
        is_fdc: bool,
        active_moieties: List[str],
        primary_drug_row: Optional[sqlite3.Row],
        md_data: Dict,
        component_mds: List[Dict],
        fda_data: Optional[Dict]
    ) -> List[str]:
        res = []
        limits = self._get_ingredient_limits()

        # 1. Pregnancy contraindication check
        for m in active_moieties:
            if m in limits and limits[m].get("profile_adjustments", {}).get("pregnancy_contraindicated"):
                res.append(f"懷孕婦女嚴格禁用 ({MOIETY_CHINESE_NAMES.get(m, m)} 具第 D 級致畸胎性與胎兒腎毒性)")

        # 2. Check MD contraindications
        for source in [md_data] + [c.get("data", {}) for c in component_mds]:
            md_c = source.get("contraindications")
            if isinstance(md_c, list):
                for c in md_c:
                    s = str(c).strip()
                    if s and len(s) > 3 and not s.isdigit() and s.lower() != "hypersensitivity":
                        res.append(s)

        # 3. Check DB contraindications
        if primary_drug_row and primary_drug_row["contraindications"]:
            raw_c = primary_drug_row["contraindications"]
            try:
                parsed_c = json.loads(raw_c)
                if isinstance(parsed_c, list):
                    res.extend([str(x).strip() for x in parsed_c if len(str(x).strip()) > 3 and str(x).lower() != "hypersensitivity"])
            except Exception:
                res.append(str(raw_c))

        # Common baseline
        res.insert(0, "對本藥任何主成分或賦形劑曾有嚴重過敏病史者禁用 (Hypersensitivity)")

        # FDC specific additions
        m_set = set(m.upper() for m in active_moieties)
        if "VALSARTAN" in m_set or "LOSARTAN" in m_set or "TELMISARTAN" in m_set:
            if not any("aliskiren" in x.lower() for x in res):
                res.append("糖尿病患者嚴禁併用含 Aliskiren (阿利吉崙) 之降血壓藥物")
            if not any("腎動脈狹窄" in x for x in res):
                res.append("雙側腎動脈狹窄或單腎動脈狹窄患者慎用 (恐誘發急性腎衰竭)")
        if "METFORMIN" in m_set:
            if not any("eGFR < 30" in x for x in res):
                res.append("嚴重腎功能不全 (eGFR < 30 mL/min) 或急性/慢性代謝性酸中毒 (含糖尿病酮酸中毒) 絕對禁用")
        if "AMLODIPINE" in m_set:
            if not any("心因性休克" in x for x in res):
                res.append("嚴重心因性休克、重度主動脈瓣狹窄或不穩定型心絞痛禁用")

        seen = set()
        clean_res = []
        noise_contra = {"patients", "hypersensitivity", "none", "unknown", "product", "component"}
        for item in res:
            it = item.strip().rstrip(".,;:")
            if not it or len(it) < 4:
                continue
            if it.lower() in noise_contra:
                continue
            # Filter incomplete sentence fragments without Chinese characters
            if len(it) < 12 and not any('\u4e00' <= ch <= '\u9fff' for ch in it):
                continue
            norm = it.lower().replace(" ", "")
            if norm not in seen:
                seen.add(norm)
                clean_res.append(it)
        return clean_res[:6]

    def _extract_pregnancy(
        self,
        is_fdc: bool,
        active_moieties: List[str],
        fda_data: Optional[Dict],
        md_body: str,
        md_data: Dict,
        component_mds: List[Dict]
    ) -> Dict[str, Any]:
        category = ""
        limits = self._get_ingredient_limits()

        # Check if any component is contraindicated in pregnancy
        has_preg_contra = False
        preg_danger_moiety = ""
        for m in active_moieties:
            if m in limits and limits[m].get("profile_adjustments", {}).get("pregnancy_contraindicated"):
                has_preg_contra = True
                preg_danger_moiety = MOIETY_CHINESE_NAMES.get(m, m)
                break

        if has_preg_contra or any(m in ["VALSARTAN", "LOSARTAN", "TELMISARTAN", "OLMESARTAN", "SACUBITRIL"] for m in active_moieties):
            category = "Category D (孕婦嚴格禁用)"
            summary = f"【{preg_danger_moiety or 'RAS 阻斷成分'} 黑框警語】直接作用於腎素-血管收縮素系統 (RAS) 之藥物，懷孕中期與晚期使用會造成發育中胎兒腎毒性、羊水過少、顱面發育不全甚至胎兒死亡。一旦發現懷孕必須立即停藥！"
            lactation = "藥物可能分泌至人類母乳，哺乳婦女用藥期間建議諮詢醫師評估停藥或暫停哺乳以維嬰兒安全。"
            return {
                "category": category,
                "risk_summary": summary,
                "lactation": lactation
            }

        # Otherwise check FDA or MD
        fda_preg = ""
        if fda_data:
            raw_p = fda_data.get("pregnancy") or fda_data.get("use_in_specific_populations")
            if raw_p:
                fda_preg = " ".join(raw_p) if isinstance(raw_p, list) else str(raw_p)
                fda_preg = re.sub(r"\s+", " ", fda_preg).strip()

        m_cat = re.search(r"Pregnancy Category\s*([A-D|X])\b", fda_preg, re.I)
        if m_cat:
            category = f"Category {m_cat.group(1).upper()}"

        summary = fda_preg[:380] if fda_preg else "懷孕期間用藥應經醫師審慎評估母體治療利益與胎兒潛在風險；若有更具確立安全之替代藥物應優先考慮。"
        lactation = "藥物是否分泌至人類母乳尚無完全定論，哺乳婦女用藥期間建議諮詢醫師評估暫停哺乳或改用替代藥品。"

        return {
            "category": category or "評估利益風險 (FDA PLLR Standard)",
            "risk_summary": summary,
            "lactation": lactation
        }

    def _extract_safety_remarks(
        self,
        is_fdc: bool,
        active_moieties: List[str],
        primary_drug_row: Optional[sqlite3.Row],
        md_data: Dict,
        component_mds: List[Dict],
        fda_data: Optional[Dict],
        ddis_db: List[Dict]
    ) -> Dict[str, Any]:
        has_boxed = False
        boxed_texts = []

        # 1. Check component MDs for boxed warnings
        for c_md in component_mds:
            c_moiety = c_md.get("moiety", "")
            bw = c_md.get("data", {}).get("boxed_warning")
            if isinstance(bw, dict) and bw.get("present"):
                has_boxed = True
                s = bw.get("summary", "").strip()
                if "FETAL TOXICITY" in s.upper():
                    boxed_texts.append(f"【{MOIETY_CHINESE_NAMES.get(c_moiety, c_moiety)}】胎兒毒性 (Fetal Toxicity)：懷孕期間使用會導致胎兒受傷甚至死亡。發現懷孕時應儘速停藥。")
                elif s:
                    boxed_texts.append(f"【{MOIETY_CHINESE_NAMES.get(c_moiety, c_moiety)}】{s[:250]}")

        # 2. Check main md_data
        md_bw = md_data.get("boxed_warning")
        if isinstance(md_bw, dict) and md_bw.get("present") and not boxed_texts:
            has_boxed = True
            boxed_texts.append(md_bw.get("summary") or "")

        # 3. Known RAS / Metformin boxed warning fallbacks
        if not boxed_texts:
            m_set = set(m.upper() for m in active_moieties)
            for ras_m in ["VALSARTAN", "LOSARTAN", "TELMISARTAN", "OLMESARTAN", "SACUBITRIL"]:
                if ras_m in m_set:
                    has_boxed = True
                    boxed_texts.append(f"【{MOIETY_CHINESE_NAMES.get(ras_m, ras_m)}】胎兒毒性 (Fetal Toxicity)：懷孕期間使用會導致發育中胎兒嚴重損傷甚至死亡。一旦發現懷孕應立即停藥。")
                    break
            if "METFORMIN" in m_set:
                has_boxed = True
                boxed_texts.append("【Metformin】乳酸中毒 (Lactic Acidosis)：罕見但具潛在致命性。重度腎功能障礙 (eGFR < 30 mL/min) 及急性失代償性心衰竭患者嚴格禁用。")

        boxed_text = "；\n".join(boxed_texts)

        # Lab monitoring
        monitoring = []
        m_set = set(m.upper() for m in active_moieties)
        if any(m in ["VALSARTAN", "LOSARTAN", "TELMISARTAN", "AMLODIPINE", "BISOPROLOL"] for m in m_set):
            monitoring.append("血壓與心率 (Blood Pressure & Pulse，監測降壓療效與心律)")
        if any(m in ["VALSARTAN", "LOSARTAN", "TELMISARTAN", "SPIRONOLACTONE"] for m in m_set):
            monitoring.append("血清鉀離子 (Serum Potassium，預防高血鉀症)")
        if any(m in ["VALSARTAN", "LOSARTAN", "METFORMIN", "FUROSEMIDE"] for m in m_set):
            monitoring.append("腎功能指標 (Serum Creatinine & eGFR)")
        if "AMLODIPINE" in m_set:
            monitoring.append("周邊下肢水腫評估 (Peripheral Edema)")
        if "METFORMIN" in m_set or "SITAGLIPTIN" in m_set or "EMPAGLIFLOZIN" in m_set:
            monitoring.append("血糖與糖化血色素 (HbA1c)")

        monitoring.append("例行肝功能指數 (ALT / AST)")

        # Key interactions
        interactions = []
        noise_words = {
            "concomitant", "intervention:", "examples:", "dosage", "precautions",
            "none", "interaction", "monitor", "king", "therapy", "patients", "valsartan:"
        }
        seen_ddi = set()
        for ddi in ddis_db:
            drug_b = (ddi.get("drug_b") or "").strip().rstrip(":,.-")
            if not drug_b or len(drug_b) < 3 or drug_b.lower() in noise_words or drug_b.lower() in seen_ddi:
                continue
            seen_ddi.add(drug_b.lower())
            interactions.append({
                "drug": drug_b.capitalize(),
                "severity": ddi.get("severity") or "中度",
                "effect": ddi.get("clinical_effect") or ddi.get("action") or "需注意臨床併用療效與劑量監測"
            })
            if len(interactions) >= 6:
                break

        return {
            "has_boxed_warning": has_boxed,
            "boxed_warning_text": boxed_text,
            "lab_monitoring": monitoring,
            "key_interactions": interactions
        }


# Global singleton
drug_safety_service = DrugSafetyService()
