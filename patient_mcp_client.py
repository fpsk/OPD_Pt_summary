"""
Patient Clinical MCP Client for OPD Summaries.
Connects to the hospital REST API, local FastMCP, OMOP CDM PostgreSQL DB,
and Outpatient Rosters in Cloud_Data.
"""

import os
import sys
import re
import csv
import json
import base64
import zipfile
import xml.etree.ElementTree as ET
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

import config

def to_standard_date(d_str: Optional[str]) -> str:
    """
    Converts ROC (民國) or Gregorian dates to International Standard YYYY/MM/DD.
    Examples:
      '1150826' -> '2026/08/26'
      '115/08/26' -> '2026/08/26'
      '1141124' -> '2025/11/24'
      '2025/11/24' -> '2025/11/24'
      '2025' -> '2025'
      '114' -> '2025'
    """
    if not d_str:
        return ''
    s = str(d_str).strip().replace('-', '/')
    
    # 4-digit year format: YYYY/MM/DD
    m_greg = re.match(r'^(\d{4})/(\d{1,2})/(\d{1,2})$', s)
    if m_greg:
        return f"{int(m_greg.group(1)):04d}/{int(m_greg.group(2)):02d}/{int(m_greg.group(3)):02d}"
    
    # 8-digit Gregorian: YYYYMMDD
    if len(s) == 8 and s.isdigit():
        y, m, d = int(s[:4]), int(s[4:6]), int(s[6:8])
        if 1900 <= y <= 2100 and 1 <= m <= 12 and 1 <= d <= 31:
            return f"{y:04d}/{m:02d}/{d:02d}"
            
    # 7-digit ROC: e.g. 1150826 -> 2026/08/26
    if len(s) == 7 and s.isdigit():
        y, m, d = int(s[:3]), int(s[3:5]), int(s[5:7])
        return f"{y + 1911:04d}/{m:02d}/{d:02d}"

    # 6-digit ROC: e.g. 980101 -> 2009/01/01
    if len(s) == 6 and s.isdigit():
        y, m, d = int(s[:2]), int(s[2:4]), int(s[4:6])
        return f"{y + 1911:04d}/{m:02d}/{d:02d}"
        
    # ROC with slashes: e.g. 115/08/26 or 114/11/24
    m_roc = re.match(r'^(\d{2,3})/(\d{1,2})/(\d{1,2})$', s)
    if m_roc:
        y, m, d = int(m_roc.group(1)), int(m_roc.group(2)), int(m_roc.group(3))
        if y < 1900:
            y += 1911
        return f"{y:04d}/{m:02d}/{d:02d}"
        
    # Just year: e.g. '2025' or '114'
    if s.isdigit():
        val = int(s)
        if 1900 <= val <= 2100:
            return str(val)
        if 10 <= val < 200:
            return str(val + 1911)
            
    return s

def to_roc_date(d_str: Optional[str]) -> str:
    """Converts Gregorian or ROC date to 7-digit ROC string (e.g. '1150901') for hospital API calls."""
    if not d_str:
        return '1150901'
    s = str(d_str).strip().replace('-', '').replace('/', '')
    if len(s) == 8 and s.isdigit():  # YYYYMMDD
        y = int(s[:4]) - 1911
        return f"{y:03d}{s[4:]}"
    if len(s) == 7 and s.isdigit():  # ROC 7-digit
        return s
    return s

def datetime_to_standard(dt: Optional[datetime]) -> str:
    """Format Python datetime as International Standard date string (e.g. '2026/08/26')."""
    if not dt:
        return "N/A"
    return f"{dt.year:04d}/{dt.month:02d}/{dt.day:02d}"

def roc_to_datetime(roc_str: Optional[str]) -> Optional[datetime]:
    """Convert ROC date or Gregorian string to Python datetime."""
    if not roc_str:
        return None
    try:
        s = str(roc_str).replace('/', '').replace('-', '').strip()
        if len(s) == 8 and s.isdigit():  # YYYYMMDD
            y, m, d = int(s[:4]), int(s[4:6]), int(s[6:8])
            return datetime(y, m, d)
        elif len(s) == 7 and s.isdigit():  # ROC 1150826
            y, m, d = int(s[:3]), int(s[3:5]), int(s[5:7])
            return datetime(y + 1911, m, d)
        elif len(s) == 6 and s.isdigit():
            y, m, d = int(s[:2]), int(s[2:4]), int(s[4:6])
            return datetime(y + 1911, m, d)
        else:
            parts = str(roc_str).replace('-', '/').split('/')
            y = int(parts[0])
            if y < 1900:
                y += 1911
            m, d = int(parts[1]), int(parts[2])
            return datetime(y, m, d)
    except Exception:
        return None

def datetime_to_roc(dt: Optional[datetime]) -> str:
    """Format Python datetime as ROC date string (e.g. '115/08/26')."""
    if not dt:
        return "N/A"
    return f"{dt.year - 1911:03d}/{dt.month:02d}/{dt.day:02d}"

FREQ_NORM_MAP = {
    "QD": "QD", "Q.D.": "QD", "ONCE DAILY": "QD", "1#QD": "QD", "QDPC": "QD", "QDAC": "QD",
    "BID": "BID", "B.I.D.": "BID", "TWICE DAILY": "BID", "BIDPC": "BID", "BIDAC": "BID",
    "TID": "TID", "T.I.D.": "TID", "THREE TIMES DAILY": "TID", "TIDPC": "TID", "TIDAC": "TID",
    "QID": "QID", "Q.I.D.": "QID", "FOUR TIMES DAILY": "QID",
    "HS": "HS", "H.S.": "HS", "AT BEDTIME": "HS", "HSAC": "HS", "HSPC": "HS",
    "Q4H": "Q4H", "Q-4-H": "Q4H", "EVERY 4 HOURS": "Q4H",
    "Q6H": "Q6H", "Q-6-H": "Q6H", "EVERY 6 HOURS": "Q6H",
    "Q8H": "Q8H", "Q-8-H": "Q8H", "EVERY 8 HOURS": "Q8H",
    "Q12H": "Q12H", "Q-12-H": "Q12H", "EVERY 12 HOURS": "Q12H",
    "QOD": "QOD", "Q.O.D.": "QOD", "EVERY OTHER DAY": "QOD",
    "QW": "QW", "Q.W.": "QW", "ONCE WEEKLY": "QW",
    "TIW": "TIW", "BIW": "BIW",
    "PRN": "PRN", "AS NEEDED": "PRN", "SOS": "PRN",
    "STAT": "STAT", "IMMEDIATELY": "STAT"
}

def normalize_freq(freq_str: Optional[str]) -> str:
    """Normalize raw hospital frequency code into standard code."""
    if not freq_str:
        return "QD"
    clean = str(freq_str).strip().upper()
    if clean in FREQ_NORM_MAP:
        return FREQ_NORM_MAP[clean]
    match = re.search(r'(Q[1-9]?[0-9]?H|QD|BID|TID|QID|HS|QOD|QW|PRN|STAT|TIW|BIW)', clean)
    if match:
        found = match.group(1)
        return FREQ_NORM_MAP.get(found, found)
    return "QD"


class PatientMcpClient:
    """Client for retrieving hospital cloud data via REST API and OMOP DB."""

    def __init__(self):
        auth_bytes = f"{config.HOSPITAL_AUTH_USER}:{config.HOSPITAL_AUTH_PASS}".encode("ascii")
        self.auth_header = f"Basic {base64.b64encode(auth_bytes).decode('ascii')}"
        self.headers = {
            "Authorization": self.auth_header,
            "User-Agent": "OPD-Patient-Summarizer/1.0"
        }

    def _call_api(self, endpoint: str, params: dict) -> Dict[str, Any]:
        """Make authorized GET request to hospital gateway."""
        query_str = urllib.parse.urlencode(params)
        url = f"{config.HOSPITAL_API_HOST}{endpoint}?{query_str}"
        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                raw_bytes = response.read()
                try:
                    return json.loads(raw_bytes.decode("utf-8"))
                except UnicodeDecodeError:
                    return json.loads(raw_bytes.decode("cp950", errors="replace"))
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}: {e.reason}", "messageCode": "500", "latestMed": [], "latestLab": [], "imageSummary": []}
        except Exception as e:
            return {"error": str(e), "messageCode": "500", "latestMed": [], "latestLab": [], "imageSummary": []}

    def get_medications(self, id_no: str, date: str, daterange: int = getattr(config, 'DEFAULT_DATERANGE', 1095)) -> Dict[str, Any]:
        """Fetch latest medications for patient ID and date (default daterange covers maximum cloud data)."""
        roc_date = to_roc_date(date)
        params = {"idNo": id_no.strip(), "date": roc_date, "daterange": str(daterange)}
        return self._call_api("/getLatestMed", params)

    def get_lab_tests(self, id_no: str, date: str, daterange: int = getattr(config, 'DEFAULT_DATERANGE', 1095)) -> Dict[str, Any]:
        """Fetch latest lab tests for patient ID and date (default daterange covers maximum cloud data)."""
        roc_date = to_roc_date(date)
        params = {"idNo": id_no.strip(), "date": roc_date, "daterange": str(daterange)}
        return self._call_api("/getLatestLabTest", params)

    def get_image_summary(self, id_no: str, date: str) -> Dict[str, Any]:
        """Fetch radiology and imaging summary for patient ID and date."""
        roc_date = to_roc_date(date)
        params = {"idNo": id_no.strip(), "date": roc_date}
        return self._call_api("/getImageSummary", params)

    def get_omop_data(self, person_id: int) -> Dict[str, Any]:
        """Fetch OMOP CDM profile if available."""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(
                host=config.OMOP_DB_HOST,
                port=config.OMOP_DB_PORT,
                dbname=config.OMOP_DB_NAME,
                user=config.OMOP_DB_USER,
                password=config.OMOP_DB_PASSWORD,
                options=f"-c search_path={config.OMOP_DB_SCHEMA},public",
                connect_timeout=3
            )
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"SELECT * FROM {config.OMOP_DB_SCHEMA}.person WHERE person_id = %s", (person_id,))
                demo = cur.fetchone()
                cur.execute(f"""
                    SELECT co.*, c.concept_name 
                    FROM {config.OMOP_DB_SCHEMA}.condition_occurrence co
                    LEFT JOIN {config.OMOP_DB_SCHEMA}.concept c ON co.condition_concept_id = c.concept_id
                    WHERE co.person_id = %s ORDER BY co.condition_start_date DESC LIMIT 30
                """, (person_id,))
                conditions = cur.fetchall()
            conn.close()
            return {"demographics": dict(demo) if demo else {}, "conditions": [dict(c) for c in conditions]}
        except Exception:
            return {"demographics": {}, "conditions": []}

    def load_patient_roster(self) -> List[Dict[str, Any]]:
        """Load outpatient patient list from Cloud_Data for quick OPD selection."""
        patients = []
        seen_ids = set()

        # 1. Try reading CSV files in Cloud_Data
        csv_files = ["patient_list_20260804.csv", "patient_list_20260804A.csv"]
        for fname in csv_files:
            p_path = os.path.join(config.CLOUD_DATA_PATH, fname)
            if not os.path.exists(p_path):
                continue
            for enc in ["cp950", "utf-8", "big5"]:
                try:
                    with open(p_path, "r", encoding=enc) as f:
                        reader = csv.reader(f)
                        header = next(reader, None)
                        for row in reader:
                            if len(row) >= 6:
                                seq, name, gender, age, chart_no, pid = row[0].strip(), row[1].strip(), row[2].strip(), row[3].strip(), row[4].strip(), row[5].strip()
                                if pid and pid not in seen_ids:
                                    seen_ids.add(pid)
                                    patients.append({
                                        "seq": seq,
                                        "name": name,
                                        "gender": gender,
                                        "age": age,
                                        "chart_no": chart_no,
                                        "id_no": pid,
                                        "source": fname
                                    })
                    break
                except Exception:
                    continue

        # 2. Try reading Pt_ID_Table.xlsx via zipfile/XML if CSV missed any
        xlsx_path = os.path.join(config.CLOUD_DATA_PATH, "Pt_ID_Table.xlsx")
        if os.path.exists(xlsx_path):
            try:
                with zipfile.ZipFile(xlsx_path) as z:
                    with z.open('xl/sharedStrings.xml') as f:
                        sst = [elem.text for elem in ET.parse(f).iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')]
                    sheet_names = [n for n in z.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')]
                    for sname in sheet_names:
                        with z.open(sname) as f:
                            sheet_tree = ET.parse(f)
                        for row in sheet_tree.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row'):
                            row_vals = []
                            for c in row.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
                                t = c.get('t')
                                v = c.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
                                val = v.text if v is not None else ''
                                if t == 's' and val.isdigit() and int(val) < len(sst):
                                    val = sst[int(val)]
                                row_vals.append(val)
                            if len(row_vals) >= 6 and re.match(r'^[A-Z][1289]\d{8}$', row_vals[5].strip()):
                                pid = row_vals[5].strip()
                                if pid not in seen_ids:
                                    seen_ids.add(pid)
                                    patients.append({
                                        "seq": row_vals[0].strip(),
                                        "name": row_vals[1].strip(),
                                        "gender": row_vals[2].strip(),
                                        "age": row_vals[3].strip(),
                                        "chart_no": row_vals[4].strip(),
                                        "id_no": pid,
                                        "source": f"Pt_ID_Table.xlsx"
                                    })
            except Exception:
                pass

        # Sort by seq numeric if possible
        def get_sort_key(p):
            try:
                return int(p.get("seq", 999))
            except Exception:
                return 999
        patients.sort(key=get_sort_key)
        return patients

    def get_patient_demographics(self, patient_id: str) -> Dict[str, Any]:
        """Look up patient demographic info (name, age, gender, chart_no) from roster."""
        pid = (patient_id or "").strip().upper()
        for p in self.load_patient_roster():
            if p.get("id_no", "").strip().upper() == pid:
                return p
        return {"id_no": pid, "name": "", "age": "", "gender": "", "chart_no": ""}

