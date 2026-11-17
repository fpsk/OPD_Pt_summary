"""
Patient Clinical MCP Client for OPD Summaries.
Connects to the hospital REST API, local FastMCP, OMOP CDM PostgreSQL DB,
and Outpatient Rosters in Cloud_Data.
"""

import os
import re
import sys
import json
import base64
import threading
import urllib.error
import urllib.request
import urllib.parse
from typing import Dict, List, Any, Optional

import config

_WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, _WORKSPACE_ROOT)

from clinical_common import roc_dates as _roc
from clinical_common.demographics import (  # noqa: F401  (re-exported for routes / tests)
    AGE_KEYS,
    BIRTHDATE_KEYS,
    CHART_NO_KEYS,
    GENDER_KEYS,
    NAME_KEYS,
    extract_demographics_from_dict,
    lookup_key as _lookup_key_in_dict,
    normalize_gender as normalize_gender_value,
    resolve_age,
)
from clinical_common.roc_dates import (  # noqa: F401  (re-exported for services.clinical.*)
    calculate_age_from_birthdate,
    datetime_to_roc,
    datetime_to_standard,
    format_roc_birthdate,
    parse_roc_birthdate,
    roc_to_datetime,
    to_standard_date,
)
from clinical_common.roster import SNAPSHOT_DATES, PatientRoster  # noqa: F401

DEFAULT_API_DATE = "1150901"


def to_roc_date(d_str: Optional[str]) -> str:
    """Gregorian or ROC date -> 7-digit ROC string for hospital API calls (empty -> '1150901')."""
    return _roc.to_roc_date(d_str, default=DEFAULT_API_DATE)


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

    _runtime_demographics: Dict[str, Dict[str, Any]] = {}
    _demo_lock = threading.Lock()

    def __init__(self):
        self.roster = PatientRoster(config.CLOUD_DATA_PATH)
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
        params = {"idNo": (id_no or "").strip().upper(), "date": roc_date, "daterange": str(daterange)}
        return self._call_api("/getLatestMed", params)

    def get_lab_tests(self, id_no: str, date: str, daterange: int = getattr(config, 'DEFAULT_DATERANGE', 1095)) -> Dict[str, Any]:
        """Fetch latest lab tests for patient ID and date (default daterange covers maximum cloud data)."""
        roc_date = to_roc_date(date)
        params = {"idNo": (id_no or "").strip().upper(), "date": roc_date, "daterange": str(daterange)}
        return self._call_api("/getLatestLabTest", params)

    def get_image_summary(self, id_no: str, date: str) -> Dict[str, Any]:
        """Fetch radiology and imaging summary for patient ID and date."""
        roc_date = to_roc_date(date)
        params = {"idNo": (id_no or "").strip().upper(), "date": roc_date}
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

    @staticmethod
    def _roster_view(entry: Dict[str, Any]) -> Dict[str, Any]:
        """Roster entry as served to the UI (age as string, '' when unknown)."""
        view = dict(entry)
        view["age"] = "" if entry.get("age") is None else str(entry["age"])
        return view

    def load_patient_roster(self) -> List[Dict[str, Any]]:
        """Outpatient roster from Cloud_Data (Pt_ID_Table.xlsx + CSVs), sorted by 序號."""
        return [self._roster_view(p) for p in self.roster.all()]

    def update_patient_demographics(
        self,
        patient_id: str,
        chart_no: Optional[str] = None,
        birth_date: Optional[str] = None,
        age: Optional[Any] = None,
        name: Optional[str] = None,
        gender: Optional[str] = None,
        reference_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Store or update live patient demographics received from the clinic push API or gateway."""
        pid = (patient_id or "").strip().upper()
        if not pid:
            return {"id_no": "", "name": "", "age": "", "birth_date": "", "gender": "", "chart_no": ""}

        extracted = extract_demographics_from_dict({
            "chart_no": chart_no,
            "birth_date": birth_date,
            "age": age,
            "name": name,
            "gender": gender,
        }, reference_date=reference_date)

        with self._demo_lock:
            existing = dict(self._runtime_demographics.get(pid, {}))
            for k, v in extracted.items():
                if v not in (None, ""):
                    existing[k] = v
            self._runtime_demographics[pid] = existing

        return self.get_patient_demographics(pid, reference_date=reference_date)

    def get_patient_demographics(self, patient_id: str, reference_date: Optional[str] = None) -> Dict[str, Any]:
        """Patient demographics (name, age, birth_date, gender, chart_no, clinic_date) from roster + runtime push cache."""
        pid = (patient_id or "").strip().upper()
        base: Dict[str, Any] = {"id_no": pid, "name": "", "age": "", "birth_date": "", "gender": "", "chart_no": ""}
        entry = self.roster.get(pid)
        if entry:
            base.update(self._roster_view(entry))

        with self._demo_lock:
            rt = dict(self._runtime_demographics.get(pid, {}))
        for k in ("name", "gender", "chart_no", "birth_date", "age"):
            if rt.get(k) not in (None, ""):
                base[k] = rt[k]

        # A Taiwan-calendar birthdate (also when pushed in the age field) gives age as of reference_date
        age, norm_bdate = resolve_age(base.get("birth_date"), base.get("age"), reference_date)
        if norm_bdate:
            base["birth_date"] = norm_bdate
        if age is not None:
            base["age"] = str(age)
        return base


# Public names (several are re-exported from clinical_common for services.clinical.*, routes and tests)
__all__ = [
    "PatientMcpClient",
    "SNAPSHOT_DATES",
    "DEFAULT_API_DATE",
    "AGE_KEYS",
    "BIRTHDATE_KEYS",
    "CHART_NO_KEYS",
    "GENDER_KEYS",
    "NAME_KEYS",
    "normalize_freq",
    "normalize_gender_value",
    "extract_demographics_from_dict",
    "resolve_age",
    "to_roc_date",
    "to_standard_date",
    "roc_to_datetime",
    "datetime_to_roc",
    "datetime_to_standard",
    "parse_roc_birthdate",
    "format_roc_birthdate",
    "calculate_age_from_birthdate",
    "_lookup_key_in_dict",
]
