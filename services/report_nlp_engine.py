"""
Radiology & Narrative Clinical Report NLP Engine.
Extracts main findings, lesions, dimensions, and devices deterministically,
with optional deep synthesis via the local LLM (LM Studio).
"""

import re
import json
import sqlite3
import hashlib
from contextlib import closing
from typing import Dict, List, Any, Optional

import config
from services import llm_client
from services.patient_mcp_client import to_standard_date

# Initialize SQLite Cache for NLP & AI extractions
def init_cache_db():
    with closing(sqlite3.connect(config.CACHE_DB_PATH)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS nlp_report_cache (
                report_hash TEXT PRIMARY KEY,
                report_type TEXT,
                result_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

init_cache_db()


class ReportNlpEngine:
    """Extracts structured clinical findings and lesion/device measurements."""

    # Regex patterns for dimensions and devices
    SIZE_2D_3D_PATTERN = re.compile(
        r'\b(\d+(?:\.\d+)?)\s*(?:x|×|\*)\s*(\d+(?:\.\d+)?)(?:\s*(?:x|×|\*)\s*(\d+(?:\.\d+)?))?\s*(cm|mm)\b',
        re.IGNORECASE
    )
    SIZE_1D_PATTERN = re.compile(
        r'\b(?:(?:about|approx(?:\.)?|up\s+to|<|>|＜|＞)\s*)?(\d+(?:\.\d+)?)\s*(?:-|–)?\s*(cm|mm)\b(?:\s*(?:in\s+(?:diameter|size|length|width)|mass|nodule|cyst|stone|polyp|lesion|tumor|aneurysm|ulcer))?',
        re.IGNORECASE
    )
    FRENCH_SIZE_PATTERN = re.compile(
        r'\b(\d+)\s*Fr(?:\s+(?:introducer|catheter|sheath|double\s+lumen))?\b',
        re.IGNORECASE
    )
    PRESSURE_ATM_PATTERN = re.compile(
        r'\b(\d+(?:\.\d+)?)\s*ATM\b',
        re.IGNORECASE
    )
    CTR_PATTERN = re.compile(
        r'(?:cadiothoracic|cardiothoracic)\s+ratio\s*(?:larger\s+than|greater\s+than|>|is)?\s*(?:half|50%|0\.\d+)',
        re.IGNORECASE
    )

    # Clinical Keyword Categories
    FINDING_CATEGORIES = {
        "Abdominal & Liver / GI": [
            "tumor", "hemangioma", "polyp", "cyst", "gallbladder", "cholecystitis",
            "bowel obstruction", "fatty liver", "pancreas", "aneurysm", "aortic aneurysm",
            "diverticulum", "hernia", "ascites"
        ],
        "Neurology / Brain": [
            "hemorrhage", "infarction", "stroke", "ischemia", "brain atrophy",
            "demyelination", "periventricular lucency", "calcification", "subarachnoid",
            "mass effect", "midline shift"
        ],
        "Pulmonary / CXR": [
            "pneumonia", "infiltration", "reticulonodular", "patchy", "consolidation",
            "blunting", "c-p angle", "effusion", "pleural", "atelectasis", "pneumothorax",
            "crowding of lung markings"
        ],
        "Cardiovascular": [
            "cardiomegaly", "cardiothoracic ratio", "aortic arch", "calcification",
            "tortuous thoracic aorta", "chf", "heart failure", "cad", "cabg",
            "abnormal ekg", "sternotomy"
        ],
        "Vascular Access / Cath": [
            "av fistula", "fistula", "thrombectomy", "pta", "stenosis", "occlusion",
            "thrombus", "balloon", "cephalic vein", "radial artery", "introducer",
            "fistulogram", "urokinase", "hickman", "double lumen"
        ],
        "Renal & Metabolic": [
            "esrd", "end stage renal", "uremia", "hemodialysis", "diabetes", "dm",
            "hypertension", "htn"
        ],
        "Musculoskeletal & Joint": [
            "acl", "meniscus", "tear", "fracture", "degenerative change", "spurs formation",
            "spine", "scoliosis", "joint space narrowing", "sclerosis", "osteophyte", "wire"
        ]
    }

    def parse_report_sections(self, text: str) -> Dict[str, str]:
        """Split narrative report into standard sections."""
        clean_text = text.replace('\r\n', '\n').strip()
        sections = {
            "indication": "",
            "impression": "",
            "findings": "",
            "conclusion": "",
            "raw": clean_text
        }

        # Look for INDICATION section
        ind_match = re.search(r'(?:Indication|適應症)[：:\(]\s*(.*?)(?=\n|大腸鏡|Insertion|Finding|$)', clean_text, re.DOTALL | re.IGNORECASE)
        if ind_match:
            sections["indication"] = ind_match.group(1).strip()

        # Look for IMPRESSION section
        imp_match = re.search(r'(?:IMPRESSION|Impression|IMP)[：:]\s*(.*?)(?=\n\n|[A-Z\s]{4,}[：:]|$)', clean_text, re.DOTALL)
        if imp_match:
            sections["impression"] = imp_match.group(1).strip()

        # Look for FINDINGS section
        find_match = re.search(r'(?:CXR\s+PA\s+view\s+showed|Imaging\s+findings[：:]|FINDINGS[：:])\s*(.*?)(?=\n\n|Impression[：:]|$)', clean_text, re.DOTALL | re.IGNORECASE)
        if find_match:
            sections["findings"] = find_match.group(1).strip()

        # Look for CONCLUSION section
        conc_match = re.search(r'(?:Conclusion[：:]|CONCLUSION[：:])\s*(.*?)(?=\n\n|$)', clean_text, re.DOTALL)
        if conc_match:
            sections["conclusion"] = conc_match.group(1).strip()

        return sections

    def extract_lesion_name_and_site(self, sent: str, dim: str, nhi_code: str = "", match_start: int = -1, match_end: int = -1) -> Optional[Dict[str, str]]:
        """
        Identify specific lesion/finding name and anatomical site in English.
        Uses clause segmentation and local context window to avoid site bleed
        between multiple findings in the same sentence (e.g. Right kidney vs Left kidney).
        """
        # Determine local context around the match if offsets are given
        if match_start >= 0 and match_end >= 0:
            pre_text = sent[:match_start]
            pre_clauses = re.split(r'\b(?:and|but|while)\b|[,;]', pre_text)
            local_pre = pre_clauses[-1] if pre_clauses else pre_text[-60:]

            post_text = sent[match_end:]
            post_clauses = re.split(r'\b(?:and|but|while)\b|[,;]', post_text)
            local_post = post_clauses[0] if post_clauses else post_text[:60]

            scope = f"{local_pre} {dim} {local_post}".strip()
        else:
            scope = sent

        scope_l = scope.lower()
        sent_l = sent.lower()

        # Reject endoscopy insertion depth from anal verge (AV)
        if re.search(r'\b\d+\s*cm\s+(?:from\s+av|proximal\s+to\s+anal|from\s+anal)\b', scope_l) or '距離肛門口' in scope:
            if re.search(rf'\b{re.escape(dim)}\s*(?:from\s+av|proximal|公分)', scope_l):
                return None
            if any(dim.strip() == d for d in ['10cm', '40cm', '45cm', '50cm', '60cm', '70cm', '75cm', '80cm']):
                return None

        # Clean dimension: remove trailing 'in size', 'in length', 'in diameter'
        clean_dim = re.sub(r'\s+in\s+(?:size|diameter|length|width)', '', dim, flags=re.I).strip()

        # 1. Identify Anatomical Site (English only)
        site = ''
        for txt in [scope, sent]:
            if re.search(r'\bright\s+kidney|rt\s+kidney\b', txt, re.I):
                site = 'Right Kidney'
                break
            elif re.search(r'\bleft\s+kidney|lt\s+kidney\b', txt, re.I):
                site = 'Left Kidney'
                break
            elif re.search(r'\b(?:bil\.\s+kidneys|bilateral\s+kidneys)\b', txt, re.I):
                site = 'Bilateral Kidneys'
                break
            elif re.search(r'\b(?:at|over|in)?\s*S8\s+of\s+liver\b|\bS8\b', txt, re.I):
                site = 'Liver S8'
                break
            elif re.search(r'\b(?:at|over|in)?\s*S5\s+of\s+liver\b|\bS5\b', txt, re.I):
                site = 'Liver S5'
                break
            elif re.search(r'\bS5-6\b', txt, re.I):
                site = 'Liver S5-6'
                break
            elif re.search(r'\bS4\b', txt, re.I):
                site = 'Liver S4'
                break
            elif re.search(r'\blower\s+end\s+of\s+ab[od]+minal\s+aorta\b', txt, re.I):
                site = 'Lower Abdominal Aorta'
                break
            elif re.search(r'\bab[od]+minal\s+aorta\b', txt, re.I):
                site = 'Abdominal Aorta'
                break
            elif re.search(r'\bLLL\b|left\s+lower\s+lung|left\s+lower\s+lobe', txt, re.I):
                site = 'Lung LLL'
                break
            elif re.search(r'\bRLL\b|right\s+lower\s+lung|right\s+lower\s+lobe', txt, re.I):
                site = 'Lung RLL'
                break
            elif re.search(r'\bpancreatic\s+(?:neck\/body\/tail|body\/tail|body|tail|neck|head)\b', txt, re.I):
                m_p = re.search(r'pancreatic\s+([a-z\/]+)', txt, re.I)
                site = f'Pancreas ({m_p.group(1).title()})'
                break
            elif re.search(r'\b(?:gallbladder|gallbaldder|gb)\b', txt, re.I) or ('polyp' in txt.lower() and nhi_code in ['19009C', '19001C']):
                site = 'Gallbladder'
                break
            elif re.search(r'\bright\s+lobe\s+of\s+liver|rt\s+lobe\s+of\s+liver\b', txt, re.I):
                site = 'Right Liver Lobe'
                break
            elif re.search(r'\bleft\s+lobe\s+of\s+liver|lt\s+lobe\s+of\s+liver\b', txt, re.I):
                site = 'Left Liver Lobe'
                break
            elif re.search(r'\b(?:rt\/lt|bilateral)\s+lobes\s+of\s+liver\b', txt, re.I):
                site = 'Bilateral Liver Lobes'
                break
            elif re.search(r'\bascending\s+colon|a-colon\b', txt, re.I):
                site = 'Ascending Colon'
                break
            elif re.search(r'\bsigmoid\s+colon|s-colon\b', txt, re.I):
                site = 'Sigmoid Colon'
                break
            elif re.search(r'\btransverse\s+colon|t-colon\b', txt, re.I):
                site = 'Transverse Colon'
                break
            elif re.search(r'\bdescending\s+colon|d-colon\b', txt, re.I):
                site = 'Descending Colon'
                break
            elif re.search(r'\bsplenic\s+flex(?:ion|ure)\b', txt, re.I):
                site = 'Splenic Flexure'
                break
            elif re.search(r'\bhepatic\s+flex(?:ion|ure)\b', txt, re.I):
                site = 'Hepatic Flexure'
                break
            elif re.search(r'\brectum|rectal\b', txt, re.I):
                site = 'Rectum'
                break
            elif re.search(r'\bcecum|cecal\b', txt, re.I):
                site = 'Cecum'
                break
            elif re.search(r'\b(?:left\s+breast|lt\s+breast)\b', txt, re.I):
                site = 'Left Breast'
                break
            elif re.search(r'\b(?:right\s+breast|rt\s+breast)\b', txt, re.I):
                site = 'Right Breast'
                break
            elif re.search(r'\bbreasts?\b', txt, re.I):
                site = 'Breast'
                break
            elif re.search(r'\bav\s+fistula|fistula\b', txt, re.I) or nhi_code == '33074B':
                site = 'AV Fistula'
                break
            elif re.search(r'\bliver|hepatic\b', txt, re.I):
                site = 'Liver'
                break
            elif re.search(r'\bpancreas|pancreatic\b', txt, re.I):
                site = 'Pancreas'
                break
            elif re.search(r'\bspleen\b', txt, re.I):
                site = 'Spleen'
                break
            elif re.search(r'\bkidney|renal\b', txt, re.I):
                site = 'Kidney'
                break

        # 2. Identify Lesion Name (English only)
        lesion_name = ''
        s_eval = scope_l if len(scope_l) > 10 else sent_l

        if 'right kidney' in s_eval or 'rt kidney' in s_eval:
            lesion_name = 'Right Kidney'
            site = 'Right Kidney'
        elif 'left kidney' in s_eval or 'lt kidney' in s_eval:
            lesion_name = 'Left Kidney'
            site = 'Left Kidney'
        elif 'nodule' in s_eval and ('hemangioma' in s_eval or 'r/o' in s_eval):
            lesion_name = 'Liver Nodule / r/o Hemangioma'
        elif any(k in s_eval for k in ['hemangioma', 'hypervasculer tumor', 'hypervascular tumor']):
            lesion_name = 'Liver Hemangioma'
        elif 'aneurysm' in s_eval or 'aneurysmal' in s_eval:
            lesion_name = 'Aortic Aneurysm'
        elif any(k in s_eval for k in ['gallbladder polyp', 'gb polyp']) or (('gallbladder' in s_eval or 'gallbaldder' in s_eval or 'gb' in s_eval or nhi_code in ['19009C', '19001C']) and 'polyp' in s_eval):
            lesion_name = 'Gallbladder Polyp'
            if not site:
                site = 'Gallbladder'
        elif 'polyp' in s_eval or '瘜肉' in s_eval or '息肉' in s_eval:
            lesion_name = 'Colon Polyp'
            if not site:
                site = 'Colon'
        elif 'echo-free' in s_eval or 'anechoic' in s_eval or ('hepatic' in s_eval and 'cyst' in s_eval):
            lesion_name = 'Hepatic Cyst'
            if not site:
                site = 'Liver'
        elif 'calcification' in s_eval or 'calicification' in s_eval:
            if 'renal' in s_eval or 'kidney' in s_eval:
                lesion_name = 'Renal Calcification'
            elif 'aorta' in s_eval:
                lesion_name = 'Aortic Calcification'
            else:
                lesion_name = 'Calcification'
        elif any(k in s_eval for k in ['nodule', '結節']):
            if 'lll' in s_eval or 'lung' in s_eval or 'pleural' in s_eval:
                lesion_name = 'Lung Nodule'
            elif 'breast' in s_eval or 'mammo' in s_eval:
                lesion_name = 'Breast Nodule'
            elif 'liver' in s_eval or 'hepatic' in s_eval or any(f's{x}' in s_eval for x in range(1, 9)):
                lesion_name = 'Liver Nodule'
            elif 'thyroid' in s_eval:
                lesion_name = 'Thyroid Nodule'
            else:
                lesion_name = 'Nodule'
        elif any(k in s_eval for k in ['cyst', 'cystic', '囊腫']):
            if 'pancrea' in s_eval:
                lesion_name = 'Pancreatic Cyst'
            elif 'liver' in s_eval or 'hepatic' in s_eval:
                lesion_name = 'Hepatic Cyst'
            elif 'kidney' in s_eval or 'renal' in s_eval:
                lesion_name = 'Renal Cyst'
            else:
                lesion_name = 'Cyst'
        elif 'echogenic lesion' in s_eval or 'heterogeneous' in s_eval:
            lesion_name = 'Liver Echogenic Lesion'
        elif 'tumor' in s_eval or 'mass' in s_eval or 'neoplasm' in s_eval:
            lesion_name = 'Tumor / Mass'
        elif 'balloon' in s_eval or 'mustang' in s_eval:
            lesion_name = 'PTA Balloon'
        elif 'introducer' in s_eval or 'sheath' in s_eval or 'catheter' in s_eval:
            lesion_name = 'Catheter / Sheath'
        elif 'spleen' in s_eval:
            lesion_name = 'Spleen'
            site = 'Spleen'
        else:
            lesion_name = 'Lesion Finding'

        # Form clean English clinical label
        if site and site.lower() != lesion_name.lower():
            full_label = f'{lesion_name} ({site}): {clean_dim}'
        else:
            full_label = f'{lesion_name}: {clean_dim}'

        return {
            'lesion_name': lesion_name,
            'site': site,
            'dimension': clean_dim,
            'clean_dimension': clean_dim,
            'full_label': full_label
        }

    def extract_dimensions_and_devices(self, text: str, nhi_code: str = "") -> List[Dict[str, Any]]:
        """Extract quantitative measurements, lesions, and intervention device sizes with specific lesion names."""
        measurements = []
        # Split by newlines, semicolons, bullets (＞, >, •, ·, ◆, ◇, ■, □, 【, 】), isolated asterisks, list numbering (1., 2.), and periods (not decimals)
        sentences = re.split(r'(?:\n|;|＞|>|•|·|◆|◇|■|□|【|】|(?:\s+\*|\*\s+)|(?<=\n)\s*\d+[\.\)]\s+|(?<=[;>＞•·\s])\d+[\.\)]\s+(?=[A-Z\u4e00-\u9fa5])|(?<!\d)\.(?!\d))+', text)
        seen_keys = set()

        for sent in sentences:
            sent_clean = sent.strip()
            if not sent_clean:
                continue

            matched_spans = []

            # Check for 2D/3D size (e.g. 7*40mm, 6x40mm)
            for m_2d in self.SIZE_2D_3D_PATTERN.finditer(sent_clean):
                start, end = m_2d.start(), m_2d.end()
                matched_spans.append((start, end))
                unit = m_2d.group(4) or m_2d.group(3) or "mm"
                size_str = m_2d.group(0)
                details = self.extract_lesion_name_and_site(sent_clean, size_str, nhi_code, match_start=start, match_end=end)
                if not details:
                    continue
                clean_dim = details.get("clean_dimension", size_str)
                k = (details["lesion_name"], details["site"], clean_dim)
                if k in seen_keys:
                    continue
                seen_keys.add(k)
                measurements.append({
                    "type": details["lesion_name"],
                    "lesion_name": details["lesion_name"],
                    "site": details["site"],
                    "dimension": clean_dim,
                    "unit": unit,
                    "full_label": details["full_label"],
                    "context": sent_clean,
                    "category": "Intervention / Device" if "balloon" in sent_clean.lower() else "Lesion Size"
                })

            # Check for 1D lesion size (e.g. 8.8cm tumor, 1.5cm nodule, 3.6cm aneurysm, 0.4-cm polyp, kidney 11.8cm)
            for m_1d in self.SIZE_1D_PATTERN.finditer(sent_clean):
                start, end = m_1d.start(), m_1d.end()
                if any(s <= start < e or s < end <= e for s, e in matched_spans):
                    continue
                matched_spans.append((start, end))
                unit = m_1d.group(2)
                full_m = m_1d.group(0).strip()
                details = self.extract_lesion_name_and_site(sent_clean, full_m, nhi_code, match_start=start, match_end=end)
                if not details:
                    continue
                clean_dim = details.get("clean_dimension", full_m)
                k = (details["lesion_name"], details["site"], clean_dim)
                if k in seen_keys:
                    continue
                seen_keys.add(k)
                measurements.append({
                    "type": details["lesion_name"],
                    "lesion_name": details["lesion_name"],
                    "site": details["site"],
                    "dimension": clean_dim,
                    "unit": unit,
                    "full_label": details["full_label"],
                    "context": sent_clean,
                    "category": "Organ Measurement" if "kidney" in details["lesion_name"].lower() or "spleen" in details["lesion_name"].lower() else "Lesion Measurement"
                })

            # Check for French catheter / introducer size
            m_fr = self.FRENCH_SIZE_PATTERN.search(sent_clean)
            if m_fr:
                fr_str = f"{m_fr.group(1)} Fr"
                k = ("Catheter / Sheath", fr_str)
                if k not in seen_keys:
                    seen_keys.add(k)
                    measurements.append({
                        "type": "Catheter / Sheath",
                        "lesion_name": "Catheter / Sheath",
                        "site": "AV Fistula" if nhi_code == "33074B" else "",
                        "dimension": fr_str,
                        "unit": "Fr",
                        "full_label": f"Catheter / Sheath: {fr_str}",
                        "context": sent_clean,
                        "category": "Interventional Device"
                    })

            # Check for Pressure ATM
            m_atm = self.PRESSURE_ATM_PATTERN.search(sent_clean)
            if m_atm:
                atm_str = f"{m_atm.group(1)} ATM"
                k = ("Balloon Pressure", atm_str)
                if k not in seen_keys:
                    seen_keys.add(k)
                    measurements.append({
                        "type": "Balloon Pressure",
                        "lesion_name": "Balloon Pressure",
                        "site": "AV Fistula" if nhi_code == "33074B" else "",
                        "dimension": atm_str,
                        "unit": "ATM",
                        "full_label": f"Balloon Pressure: {atm_str}",
                        "context": sent_clean,
                        "category": "Interventional Parameter"
                    })

            # Check for Cardiothoracic Ratio > 0.5
            if self.CTR_PATTERN.search(sent_clean):
                k = ("Cardiomegaly", "CTR > 0.5")
                if k not in seen_keys:
                    seen_keys.add(k)
                    measurements.append({
                        "type": "Cardiothoracic Ratio (CTR)",
                        "lesion_name": "Cardiomegaly (CTR)",
                        "site": "Chest",
                        "dimension": "> 0.5",
                        "unit": "Ratio",
                        "full_label": "CTR > 0.5 (Cardiomegaly)",
                        "context": "Cardiothoracic ratio larger than half (Cardiomegaly)",
                        "category": "Cardiac Metric"
                    })

        return measurements

    def extract_main_findings(self, text: str) -> Dict[str, List[str]]:
        """Extract categorized positive clinical findings, strictly ignoring negated statements."""
        findings_by_cat = {}
        # Split by newlines, semicolons, and sentence-ending periods
        lines = [line.strip() for line in re.split(r'[\n;]+|(?<=\w\.)\s+(?=[A-Z0-9])', text) if line.strip()]

        for line in lines:
            line_clean = re.sub(r'^(?:findings|impression|conclusion|indication|result|結論)[：:\s]+', '', line, flags=re.I).strip()
            line_lower = line_clean.lower()
            if not line_lower:
                continue

            for cat, keywords in self.FINDING_CATEGORIES.items():
                for kw in keywords:
                    m_kw = re.search(r'\b' + re.escape(kw) + r'\b', line_lower)
                    if not m_kw:
                        continue

                    # Check for negation preceding this keyword in its clause
                    prefix = line_lower[:m_kw.start()]
                    clause_prefix = prefix.split(',')[-1]
                    is_negated = bool(re.search(
                        r'\b(?:no|not|without|free\s+of|negative\s+for|ruled\s+out|unremarkable|unrevealing)\b(?:\s+\w+){0,4}$',
                        clause_prefix.strip()
                    )) or bool(re.search(
                        r'^(?:no|not|without|free\s+of|negative\s+for)\s+',
                        line_lower.strip()
                    )) or bool(re.search(
                        r'\b(?:without|no|free\s+of)\s+' + re.escape(kw),
                        line_lower
                    ))

                    if not is_negated:
                        if cat not in findings_by_cat:
                            findings_by_cat[cat] = []
                        cleaned_line = re.sub(r'^\d+[\.\)]\s*', '', line_clean).strip()
                        if cleaned_line and cleaned_line not in findings_by_cat[cat]:
                            findings_by_cat[cat].append(cleaned_line)
                        break

        return findings_by_cat

    def detect_study_details(self, nhi_code: str, raw_summary: str, hospital: str = "") -> Dict[str, Any]:
        """Classify study modality, specific exam name, body region, and contrast status."""
        c = (nhi_code or "").strip().upper()
        s = (raw_summary or "").strip()
        s_clean = s.replace('\r', '').strip()
        s_upper = s_clean.upper()

        title = ""
        modality = "Other"
        category = "other"
        body_site = ""
        contrast_status = ""
        is_ct = False
        is_mri = False

        bracket_m = re.search(r'\[\s*([A-Za-z0-9\s\(\)\+\-\/]+?)\s*\]', s_clean)
        bracket_tag = bracket_m.group(1).strip() if bracket_m else ""

        # Primary study header line match
        study_line_m = re.search(
            r'(?:Finding:\s*|檢查項目:\s*\d*_?|Result:\s*)?((?:Pre\s*(?:-|&|＆|and)\s*post[^\n:\.]+)?'
            r'(?:CT\s+scan|CT\s+of|\bCT\b|MRI|MRCP|Plain\s+MRI|Colon\s+fiberoscopy|Abdominal\s+sonography|Mammogram|CXR|Chest\s+PA|Chest\s+AP|心電圖)'
            r'[^\n:\.;]{3,80})',
            s_clean,
            re.IGNORECASE
        )
        extracted_title = study_line_m.group(1).strip() if study_line_m else ""
        extracted_title = extracted_title.replace("dynanmic", "dynamic")

        # 1. CT Scan Detection
        if any(k in c for k in ["33070", "33071", "33072", "33073", "3700", "3701", "3702", "3703"]) or \
           "BRAIN CT" in bracket_tag.upper() or re.search(r'\b(?:CT\s+SCAN|CT\s+OF|COMPUTED\s+TOMOGRAPHY)\b', s_upper):
            is_ct = True
            modality = "CT Scan (電腦斷層)"
            category = "ct_mri"
            
            if "33072" in c or re.search(r'\b(?:WITH\s+(?:DYNAMIC\s+)?CONTRAST|WITH\s+IV\s+CONTRAST|POST\s+IV\s+CONTRAST|CONTRAST\s+ENHANCE)\b', s_upper):
                contrast_status = "With Contrast"
            elif "33070" in c or re.search(r'\b(?:WITHOUT\s+(?:IV\s+)?CONTRAST|WITHOUT\s+ENHANCEMENT|NON-CONTRAST|PLAIN)\b', s_upper):
                contrast_status = "Non-contrast (Plain)"
                
            if "BRAIN" in s_upper or "BRAIN" in bracket_tag.upper():
                body_site = "Brain / Head"
                title = extracted_title if ("BRAIN" in extracted_title.upper() and len(extracted_title) > 8) else f"Brain CT ({contrast_status})" if contrast_status else "Brain CT"
            elif "CHEST" in s_upper and ("CHEST" in extracted_title.upper() or "LUNG" in extracted_title.upper()):
                body_site = "Chest"
                title = extracted_title if len(extracted_title) > 8 else f"Chest CT ({contrast_status})" if contrast_status else "Chest CT"
            elif "ABDOMEN" in s_upper or "ABDOMINAL" in s_upper or "LIVER" in s_upper:
                body_site = "Abdomen"
                title = extracted_title if ("ABDOMEN" in extracted_title.upper() or "ABDOMINAL" in extracted_title.upper()) else f"Abdominal CT ({contrast_status})" if contrast_status else "Abdominal CT"
            elif "PELVIS" in s_upper:
                body_site = "Pelvis"
                title = f"Pelvic CT ({contrast_status})" if contrast_status else "Pelvic CT"
            elif "SPINE" in s_upper:
                body_site = "Spine"
                title = f"Spine CT ({contrast_status})" if contrast_status else "Spine CT"
            else:
                body_site = "General"
                title = extracted_title or (f"CT Scan ({contrast_status})" if contrast_status else "CT Scan")

        # 2. MRI Detection
        elif any(k in c for k in ["33084", "33085", "3704", "3705"]) or re.search(r'\b(?:MRI|MRCP|MAGNETIC\s+RESONANCE)\b', s_upper):
            is_mri = True
            modality = "MRI"
            category = "ct_mri"
            
            if "33085" in c or re.search(r'\b(?:POST-GD|WITH\s+CONTRAST|GD-CONTRAST|ENHANCED)\b', s_upper):
                contrast_status = "With Contrast (Gd)"
            elif "33084" in c or re.search(r'\b(?:PLAIN|WITHOUT\s+CONTRAST|NON-CONTRAST)\b', s_upper):
                contrast_status = "Non-contrast (Plain)"
                
            if "PANCREAS" in s_upper or "MRCP" in s_upper:
                body_site = "Pancreas / Biliary"
                title = extracted_title or f"Pancreas MRI & MRCP ({contrast_status})" if contrast_status else "Pancreas MRI & MRCP"
            elif "KNEE" in s_upper or "ACL" in s_upper or "MENISCUS" in s_upper:
                body_site = "Knee Joint"
                title = extracted_title or f"Knee Joint MRI ({contrast_status})" if contrast_status else "Knee Joint MRI"
            elif "BRAIN" in s_upper:
                body_site = "Brain"
                title = extracted_title or f"Brain MRI ({contrast_status})" if contrast_status else "Brain MRI"
            elif "SPINE" in s_upper:
                body_site = "Spine"
                title = extracted_title or f"Spine MRI ({contrast_status})" if contrast_status else "Spine MRI"
            else:
                body_site = "General"
                title = extracted_title or (f"MRI Study ({contrast_status})" if contrast_status else "MRI Study")

        # 3. Endoscopy (Colonoscopy / Sigmoidoscopy / Gastroscopy)
        elif "28017" in c or re.search(r'\b(?:COLON\s+FIBEROSCOPY|COLONOSCOPY|CECUM|POLYPECTOMY)\b', s_upper):
            modality = "Endoscopy"
            category = "endoscopy_pta"
            body_site = "Colon / Lower GI"
            title = "Colon Fiberoscopy"
        elif "28016" in c or "SIGMOIDOSCOPY" in s_upper:
            modality = "Endoscopy"
            category = "endoscopy_pta"
            body_site = "Sigmoid / Lower GI"
            title = "Sigmoidoscopy"
        elif "28011" in c or re.search(r'\b(?:GASTROSCOPY|PANENDOSCOPY|PES)\b', s_upper):
            modality = "Endoscopy"
            category = "endoscopy_pta"
            body_site = "Upper GI"
            title = "Panendoscopy / Gastroscopy"

        # 4. Vascular Intervention (TAME vs AV Fistula PTA)
        elif "33075" in c or re.search(r'\b(?:TAME|MICRO-EMBOLIZATION|TRANSCATHETER\s+ARTERIAL\s+MICRO-EMBOLIZATION)\b', s_upper):
            modality = "Intervention"
            category = "endoscopy_pta"
            body_site = "Left Ankle" if "ANKLE" in s_upper else "Vascular Microcirculation"
            title = "Transcatheter Arterial Micro-Embolization (TAME)"
        elif "33074" in c or re.search(r'\b(?:FISTULOGRAM|AV\s+FISTULA|BALLOON\s+DILATATION)\b', s_upper) or (re.search(r'\b(?:THROMBECTOMY|PTA)\b', s_upper) and any(k in s_upper for k in ["FISTULA", "AVF", "GRAFT", "SHUNT", "CEPHALIC", "BASILIC", "BRACHIAL", "DIALYSIS"])):
            modality = "Intervention"
            category = "endoscopy_pta"
            body_site = "Vascular Access (AV Fistula)"
            title = "AV Fistula Fistulogram & PTA"

        # 5. X-Ray
        elif "32001" in c or re.search(r'\b(?:CHEST\s+PA|CHEST\s+AP|CXR)\b', s_upper):
            modality = "X-Ray"
            category = "xray_sono"
            body_site = "Chest"
            title = "Chest X-Ray (PA/AP)"
        elif "32002" in c or "KUB" in s_upper:
            modality = "X-Ray"
            category = "xray_sono"
            body_site = "Abdomen"
            title = "Abdomen X-Ray (KUB)"
        elif re.search(r'\b320\d\d\b', c) or (re.search(r'\b(?:SPINE|SCOLIOSIS|ELBOW|KNEE|JOINT)\b', s_upper) and not any(k in c for k in ["18010", "19007", "20013", "20026"])):
            modality = "X-Ray"
            category = "xray_sono"
            body_site = "Skeletal / Spine"
            title = f"Plain Radiography ({c})"

        # 6. Ultrasound (including Carotid/TCD and Musculoskeletal/PRP)
        elif any(k in c for k in ["18010", "20013", "20026"]) or "NECK DUPLEX" in s_upper or re.search(r'\bTCD\b', s_upper):
            modality = "Ultrasound"
            category = "xray_sono"
            body_site = "Carotid & Cranial"
            title = "Carotid & Transcranial Doppler Ultrasound"
        elif "19007" in c or re.search(r'\b(?:SONOGUIDED|HA-PRP|PRP\s+INJECTION|SOFT\s+TISSUE\s+ECHO)\b', s_upper):
            modality = "Ultrasound"
            category = "xray_sono"
            body_site = "Musculoskeletal"
            title = "Sonoguided Musculoskeletal Injection (HA-PRP)"
        elif any(k in c for k in ["19001", "19009", "19002", "19003", "19004", "19005", "19014"]) or \
             "ULTRASONO" in s_upper or "ECHOCARDIOGRAPHY" in s_upper or \
             re.search(r'\b(?:ABDOMINAL\s+SONOGRAPHY|ABDOMINAL\s+ULTRASOUND|LIVER\s+SONO|SONOGRAPHY|ULTRASOUND|超音波)\b', s_upper) or \
             ("LIVER" in s_upper and ("GALLBLADDER" in s_upper or "GALLBALDDER" in s_upper or "GB" in s_upper)):
            modality = "Ultrasound"
            category = "xray_sono"
            body_site = "Abdomen / Hepatobiliary"
            title = "Abdominal Sonography"
        elif "33005" in c or re.search(r'\b(?:MAMMOGRAM|MAMMOGRAPHY)\b', s_upper):
            modality = "Mammography"
            category = "xray_sono"
            body_site = "Breast"
            title = "Mammography & Breast Ultrasound"

        # 7. Electrocardiogram
        elif "18001" in c or re.search(r'\b(?:EKG|ECG|SINUS\s+RHYTHM|ELECTROCARDIOGRAM)\b', s_upper):
            modality = "ECG"
            category = "other"
            body_site = "Cardiovascular"
            title = "12-Lead Electrocardiogram (ECG)"

        # 8. Screening / Lab
        elif "14084" in c or re.search(r'\b(?:FOBT|OCCULT\s+BLOOD|大腸癌篩檢)\b', s_upper):
            modality = "Screening"
            category = "other"
            body_site = "GI / Stool"
            title = "Stool Occult Blood (FOBT)"
        else:
            title = extracted_title or f"Clinical Examination ({c})"

        return {
            "modality": modality,
            "category": category,
            "study_name": title,
            "body_site": body_site,
            "contrast_status": contrast_status,
            "is_ct": is_ct,
            "is_mri": is_mri
        }

    def parse_imaging_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive deterministic extraction on a single imaging report record."""
        raw_summary = record.get("summary", "") or ""
        date = to_standard_date(record.get("date", ""))
        hospital = record.get("hospital", "")
        nhi_code = record.get("NHICode", "")

        sections = self.parse_report_sections(raw_summary)
        measurements = self.extract_dimensions_and_devices(raw_summary, nhi_code)
        categorized_findings = self.extract_main_findings(raw_summary)

        # Detect study details, modality, region, and contrast status
        study_info = self.detect_study_details(nhi_code, raw_summary, hospital)

        # Determine critical alerts (Strictly Negation-Aware, Context-Guarded, English-Only)
        alerts = []
        raw_lower = raw_summary.lower()

        # 1. Infection / Pneumonia
        has_pneumonia_kw = bool(re.search(r'\b(?:pneumonia|consolidation|patchy\s+infiltrat\w+)\b', raw_lower))
        if has_pneumonia_kw:
            is_negated_pneu = bool(re.search(
                r'\b(?:no\s+(?:definite\s+)?(?:active\s+)?(?:lung\s+lesion|infiltrat\w+|pneumonia|consolidation)|'
                r'negative\s+for\s+pneumonia|without\s+(?:active\s+)?pneumonia|free\s+of\s+pneumonia|ruled\s+out\s+pneumonia)\b',
                raw_lower
            ))
            if not is_negated_pneu:
                alerts.append("Suspected Infection / Pneumonia")

        # 2. AV Fistula Failure (ONLY on true vascular fistula access exams)
        is_fistula_study = (
            nhi_code == '33074B' or 
            'fistulogram' in raw_lower or 
            ('av fistula' in raw_lower and ('stenosis' in raw_lower or 'thromb' in raw_lower))
        ) and not any(k in raw_lower for k in ['tame', 'micro-embolization', 'carotid', 'tcd', 'cerebral'])
        if is_fistula_study:
            if re.search(r'(?<!no\s)\b(?:total\s+occlusion|fistula\s+failure|critical\s+stenosis|re-stenosis)\b', raw_lower):
                alerts.append("AV Fistula Occlusion / Severe Stenosis")

        # 3. Pleural Effusion
        has_effusion_kw = bool(re.search(r'\b(?:pleural\s+effusion|blunting\s+of\s+(?:bilateral|left|right)\s+c-p\s+angle)\b', raw_lower))
        if has_effusion_kw:
            is_negated_eff = bool(re.search(
                r'\b(?:no\s+pleural\s+effusion|no\s+effusion|without\s+effusion|cp\s+angles\s+are\s+(?:sharp|clear))\b',
                raw_lower
            ))
            if not is_negated_eff:
                alerts.append("Pleural Effusion")

        # 4. Cardiomegaly
        has_cardio_kw = bool(re.search(r'\bcardiomegaly\b', raw_lower)) or bool(re.search(r'cardiothoracic\s+ratio\s*(?:>|larger\s+than|is\s+greater\s+than)\s*(?:half|0\.5|50%)', raw_lower))
        if has_cardio_kw:
            is_negated_cardio = bool(re.search(
                r'\b(?:no\s+cardiomegaly|heart\s+size\s+(?:is\s+)?normal|normal\s+heart\s+size|normal\s+cardiac\s+shadow)\b',
                raw_lower
            ))
            if not is_negated_cardio:
                alerts.append("Cardiomegaly")

        # 5. Aortic Aneurysm
        has_aneurysm_kw = bool(re.search(r'\b(?:aortic\s+aneurysm|aneurysmal\s+dilatation\s+of\s+aorta)\b', raw_lower))
        if has_aneurysm_kw:
            is_negated_aneurysm = bool(re.search(
                r'\b(?:no\s+(?:aortic\s+)?aneurysm|without\s+(?:aortic\s+)?aneurysm)\b',
                raw_lower
            ))
            if not is_negated_aneurysm:
                alerts.append("Aortic Aneurysm")

        # 6. Significant Carotid Stenosis (>=50%)
        if "carotid" in study_info["study_name"].lower() or "duplex" in raw_lower:
            high_stenosis = re.findall(r'(\d+(?:\.\d+)?)\s*%\s+stenosis', raw_lower)
            if any(float(pct) >= 50.0 for pct in high_stenosis):
                alerts.append("Significant Carotid Stenosis (>=50%)")

        # Surgical and Device Implants
        surgical_implants = []
        if "sternotomy" in raw_summary.lower() or "surgical wires" in raw_summary.lower():
            surgical_implants.append("Midline sternotomy surgical wires (CABG)")
        if "hickman" in raw_summary.lower():
            surgical_implants.append("Right subclavian Hickman catheter")
        if "double lumen" in raw_summary.lower():
            surgical_implants.append("Right neck double lumen catheter")

        return {
            "date": date,
            "hospital": hospital,
            "nhi_code": nhi_code,
            "study_name": study_info["study_name"],
            "modality": study_info["modality"],
            "modality_category": study_info["category"],
            "body_site": study_info["body_site"],
            "contrast_status": study_info["contrast_status"],
            "is_ct": study_info["is_ct"],
            "is_mri": study_info["is_mri"],
            "sections": sections,
            "measurements": measurements,
            "lesion_findings": [m.get("full_label") for m in measurements if m.get("full_label")],
            "findings_by_category": categorized_findings,
            "alerts": alerts,
            "surgical_implants": surgical_implants,
            "raw_summary": raw_summary
        }

    def parse_pathology_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Perform clinical NLP extraction on a narrative surgical pathology or cytopathology report."""
        raw_val = str(record.get("val", "")).replace('\r\n', '\n').strip()
        date = to_standard_date(record.get("date", ""))
        ordercode = str(record.get("ordercode") or record.get("order_code") or "").strip()
        order = str(record.get("order", "")).strip()
        item = str(record.get("item", "")).strip()
        val_lower = raw_val.lower()

        # NHI code
        m_code = re.search(r'\b((?:150\d{2}|250\d{2})[A-Za-z]?(?:\/\d+)?)\b', f"{ordercode} {order} {raw_val}")
        nhi_code = m_code.group(1) if m_code else (ordercode or "")

        # Determine if Cytology / Pap Smear or Surgical Pathology
        is_pap_smear = bool(
            (nhi_code and "15017" in nhi_code) or 
            "15017" in order or 
            "pap" in order.lower() or 
            "vagina-cervix" in val_lower or 
            ("cervix" in val_lower and ("smear" in val_lower or "cytopatholog" in val_lower))
        )
        is_cytology = is_pap_smear or bool(
            "cytolog" in order.lower() or 
            "細胞" in order or 
            "cytopatholog" in val_lower or 
            "cytological" in val_lower or 
            "fluid" in val_lower
        )

        if not nhi_code:
            nhi_code = "15017C" if is_pap_smear else "25004C"

        # Study Name & Modality (English only)
        if is_pap_smear:
            study_name = "Cervical Pap Smear Cytology (15017C)"
            modality = "Cytopathology (Pap Smear)"
        elif is_cytology:
            study_name = "Cytopathology Examination"
            modality = "Cytopathology"
        elif "25004" in nhi_code or "25004" in order or "level iv" in order.lower() or "第四級" in order or "第四級" in item:
            study_name = "Surgical Pathology Level IV (25004C)"
            modality = "Surgical Pathology"
        elif "25003" in nhi_code or "25003" in order or "level iii" in order.lower() or "第三級" in order or "第三級" in item:
            study_name = "Surgical Pathology Level III (25003C)"
            modality = "Surgical Pathology"
        elif "25002" in nhi_code or "25002" in order or "level ii" in order.lower() or "第二級" in order or "第二級" in item:
            study_name = "Surgical Pathology Level II (25002C)"
            modality = "Surgical Pathology"
        elif "25001" in nhi_code or "25001" in order or "level i" in order.lower() or "第一級" in order or "第一級" in item:
            study_name = "Surgical Pathology Level I (25001C)"
            modality = "Surgical Pathology"
        else:
            study_name = "Surgical Pathology"
            modality = "Surgical Pathology"

        # Hospital / Pathology Lab
        hospital = record.get("hospital", "")
        m_hosp = re.search(r'【\s*(.*?病理.*?)\s*】|醫院名稱[：:\s]+(.*?)(?=\s|醫師|\n)', raw_val)
        if m_hosp:
            hospital = (m_hosp.group(1) or m_hosp.group(2) or "").strip()
        if not hospital:
            hospital = "External Pathology Lab"

        # Body Site / Specimen Organ (Medical English)
        if is_pap_smear or "cervix" in val_lower or "vagina" in val_lower or "endocervix" in val_lower or nhi_code == "15017C":
            body_site = "Cervix"
        elif "ascites" in val_lower or "peritoneal" in val_lower:
            body_site = "Peritoneal Fluid / Ascites"
        elif "pleural" in val_lower:
            body_site = "Pleural Fluid"
        elif any(k in val_lower for k in ["colon", "intestine", "大腸", "結腸", "直腸", "sigmoid", "ascending", "cecum", "polyp"]):
            body_site = "Colon / Rectum"
        elif any(k in val_lower for k in ["stomach", "gastric", "胃", "antrum"]):
            body_site = "Stomach"
        elif any(k in val_lower for k in ["liver", "hepatic", "肝"]):
            body_site = "Liver"
        elif any(k in val_lower for k in ["breast", "乳房"]):
            body_site = "Breast"
        elif any(k in val_lower for k in ["thyroid", "甲狀腺"]):
            body_site = "Thyroid"
        elif any(k in val_lower for k in ["thrombus", "intima", "vessel", "血管"]):
            body_site = "Vascular"
        else:
            m_site = re.search(r'(?:組織器官|組織由來)[：:\s]+(.*?)(?=\n|手術名稱|代碼|臨床診斷|$)', raw_val)
            if m_site:
                body_site = m_site.group(1).strip()
            else:
                body_site = "Tissue Specimen"

        # Clinical Diagnosis
        clin_diag = ""
        m_cd = re.search(r'臨床診斷[：:\s]+(.*?)(?=\n|組織器官|手術名稱|病理診斷|CYTOPATHOLOGICAL|$)', raw_val)
        if m_cd:
            clin_diag = m_cd.group(1).strip()

        # Pathological / Cytopathological Diagnosis extraction
        path_diag = ""
        m_pd = re.search(r'(?:CYTOPATHOLOGICAL\s+DIAGNOSIS|PATHOLOGICAL\s+DIAGNOSIS|FINAL\s+DIAGNOSIS|病理診斷)[：:\s]+(.*?)(?=(?:\.|\n)\s*(?:ADEQUACY|MICROSCOPIC|GROSS|NOTE|COMMENT|The specimen|檢查報告|#T-)|$)', raw_val, re.DOTALL | re.IGNORECASE)
        if m_pd:
            path_diag = " ".join([line.strip() for line in m_pd.group(1).strip().splitlines() if line.strip()])
            if path_diag.endswith('.'):
                path_diag = path_diag[:-1].strip()
        elif "tubular adenoma" in val_lower:
            path_diag = "Tubular adenoma, low grade dysplasia"
        elif "thrombus" in val_lower:
            path_diag = "Thrombus composed of blood, fibrinoid material and neutrophils infiltrate"
        elif "negative for intraepithelial lesion or malignancy" in val_lower:
            path_diag = "Negative for intraepithelial lesion or malignancy (NILM)"

        # Procedure / Surgery
        proc = ""
        m_proc = re.search(r'手術名稱[：:\s]+(.*?)(?=\n|代碼|檢查名稱|$)', raw_val)
        if m_proc:
            proc = m_proc.group(1).strip()

        # Malignancy evaluation (Robust Negation-Aware Classification)
        is_nilm = bool(re.search(
            r'(?:negative\s+for\s+(?:intraepithelial\s+lesion\s+or\s+)?malignan(?:cy|t)|nilm\b)',
            val_lower
        ))
        is_negative_malignancy = is_nilm or bool(re.search(
            r'(?:negative\s+for\s+(?:any\s+)?(?:intraepithelial\s+lesion\s+or\s+)?malignan(?:cy|t)(?:\s+cells?)?|'
            r'negative\s+for\s+malignant\s+cells?|'
            r'no\s+(?:evidence\s+of\s+)?(?:intraepithelial\s+lesion\s+or\s+)?malignan(?:cy|t)(?:\s+cells?)?|'
            r'without\s+(?:evidence\s+of\s+)?malignan(?:cy|t)|'
            r'free\s+of\s+(?:any\s+)?malignan(?:cy|t)|'
            r'no\s+malignant\s+cells?(?:\s+seen)?|'
            r'no\s+malignancy|'
            r'benign\s+smear|'
            r'negative\s+result\s+of\s+cervical)',
            val_lower
        ))

        # Check for true positive malignant findings only when not negated
        has_malignancy = False
        matched_cancer_term = ""
        if not is_negative_malignancy:
            true_malignant_terms = [
                "adenocarcinoma", "squamous cell carcinoma", "invasive carcinoma",
                "carcinoma in situ", "high grade squamous intraepithelial lesion", "hsil",
                "malignant neoplasm", "malignant lymphoma", "malignant melanoma",
                "metastatic carcinoma", "poorly differentiated carcinoma",
                "moderately differentiated carcinoma", "positive for malignant cell"
            ]
            for term in true_malignant_terms:
                if re.search(r'(?<!no\s)(?<!negative\sfor\s)(?<!without\s)(?<!free\sof\s)\b' + re.escape(term), val_lower):
                    has_malignancy = True
                    matched_cancer_term = term.title()
                    break

            if not has_malignancy and ("carcinoma" in val_lower or "malignant" in val_lower or "malignancy" in val_lower):
                scrubbed = re.sub(r'(?:negative\s+for|no\s+evidence\s+of|without|free\s+of|no)\s+[^\.\,\n;]*(?:malignan\w*|carcinoma\w*)', '', val_lower)
                if any(k in scrubbed for k in ["carcinoma", "malignant", "malignancy"]):
                    has_malignancy = True
                    matched_cancer_term = "Malignancy"

        if is_nilm:
            malignancy_status = "Negative for Intraepithelial Lesion or Malignancy (NILM)"
            malignancy_badge = "success"
        elif is_negative_malignancy:
            malignancy_status = "Benign / Negative for Malignancy"
            malignancy_badge = "success"
        elif "tubular adenoma" in val_lower or "hyperplastic polyp" in val_lower:
            malignancy_status = "Benign / Tubular Adenoma"
            malignancy_badge = "success"
        elif "benign" in val_lower and not has_malignancy:
            malignancy_status = "Benign Finding"
            malignancy_badge = "success"
        elif has_malignancy:
            malignancy_status = f"Malignant Finding ({matched_cancer_term})" if matched_cancer_term and matched_cancer_term != "Malignancy" else "Malignant Finding"
            malignancy_badge = "danger"
        else:
            malignancy_status = "Non-malignant Finding"
            malignancy_badge = "info"

        # Measurements / Lesions
        measurements = self.extract_dimensions_and_devices(raw_val, nhi_code)
        specimen_findings = []
        if "polyp" in val_lower:
            m_polyps = re.findall(r'(?:a\s+)?(\d+(?:\.\d+)?\s*-?\s*cm\s+polyp[^\n,\.]+)', raw_val, re.I)
            for p in m_polyps:
                specimen_findings.append(f"Colon polyp: {p.strip()}")
        if not specimen_findings and measurements:
            specimen_findings = [m.get("full_label") for m in measurements if m.get("full_label")]

        # Split into sections
        impression_text = path_diag if path_diag else malignancy_status
        sections = {
            "indication": clin_diag or proc,
            "impression": impression_text,
            "findings": raw_val[:350] + "..." if len(raw_val) > 350 else raw_val,
            "conclusion": impression_text,
            "raw": raw_val
        }

        alerts = []
        if has_malignancy and malignancy_badge == "danger":
            alerts.append("Malignancy Finding")

        return {
            "date": date,
            "hospital": hospital,
            "nhi_code": nhi_code,
            "study_name": study_name,
            "modality": modality,
            "modality_category": "pathology",
            "body_site": body_site,
            "contrast_status": "",
            "is_ct": False,
            "is_mri": False,
            "is_pathology": True,
            "clinical_diagnosis": clin_diag,
            "pathological_diagnosis": path_diag,
            "procedure_name": proc,
            "malignancy_status": malignancy_status,
            "malignancy_badge": malignancy_badge,
            "sections": sections,
            "measurements": measurements,
            "lesion_findings": specimen_findings or [m.get("full_label") for m in measurements if m.get("full_label")],
            "findings_by_category": {modality: [path_diag]} if path_diag else {},
            "alerts": alerts,
            "surgical_implants": [],
            "raw_summary": raw_val
        }

    @staticmethod
    def _cache_get(report_hash: str) -> Optional[Dict[str, Any]]:
        try:
            with closing(sqlite3.connect(config.CACHE_DB_PATH)) as conn:
                row = conn.execute("SELECT result_json FROM nlp_report_cache WHERE report_hash = ?", (report_hash,)).fetchone()
            return json.loads(row[0]) if row else None
        except Exception:
            return None

    @staticmethod
    def _cache_put(report_hash: str, modality: str, result: Dict[str, Any]) -> None:
        try:
            with closing(sqlite3.connect(config.CACHE_DB_PATH)) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO nlp_report_cache (report_hash, report_type, result_json) VALUES (?, ?, ?)",
                    (report_hash, modality, json.dumps(result, ensure_ascii=False))
                )
                conn.commit()
        except Exception:
            pass

    def extract_with_local_llm(self, text: str, modality: str = "") -> Optional[Dict[str, Any]]:
        """
        Deep clinical extraction via the local LLM (LM Studio).
        Caches result in SQLite for 0s repeat responses.
        """
        report_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
        cached = self._cache_get(report_hash)
        if cached:
            return cached

        system_prompt = (
            "You are an expert clinical informatics and radiology AI assistant. "
            "Analyze the medical report and extract: 1. Main diagnostic findings, "
            "2. Any lesion, organ, or intervention device measurements/sizes, "
            "3. Clinical impressions. Return valid JSON only with keys: "
            "'main_findings' (list of strings), 'measurements' (list of objects with site, size, description), "
            "'impression' (string), 'critical_alert' (string or null)."
        )
        user_content = f"Modality: {modality}\nReport Content:\n{text}\n\nReturn JSON only."

        try:
            content = llm_client.chat_completion(
                [{"role": "system", "content": system_prompt},
                 {"role": "user", "content": user_content}],
                temperature=0.1, max_tokens=600, timeout=20,
            )
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
            else:
                parsed = {"impression": content, "main_findings": [], "measurements": []}
        except Exception as e:
            return {"error": f"Local LLM extraction failed: {str(e)}", "impression": text[:200]}

        self._cache_put(report_hash, modality, parsed)
        return parsed
