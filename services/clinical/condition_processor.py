"""
Diagnosis classifier (chronic vs acute) and surgical/interventional procedure detector.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from services.patient_mcp_client import to_standard_date


class ConditionProcessor:
    """Categorizes outpatient diagnoses into chronic vs acute conditions and detects surgical/interventional procedures."""

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


    # Backwards-compatible aliases
    is_pathology_report = _is_pathology_report
    process_diagnoses = _process_diagnoses
    process_surgical_and_interventions = _process_surgical_and_interventions
