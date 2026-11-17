"""
Drug Photo and Product Information Service.
Connects to Medication_Info/okf_kb/cdss_knowledge.db,
reads pill photos from pills_jpeg_archive.zip and disk images.
"""

import os
import re
import sqlite3
import zipfile
import logging
import threading
from contextlib import closing
from typing import Optional, Dict, Any, Tuple

import config

logger = logging.getLogger(__name__)

MED_INFO_DIR = os.path.join(config.PARENT_DIR, "Medication_Info")

DB_PATH = os.path.join(MED_INFO_DIR, "okf_kb", "cdss_knowledge.db")
ZIP_PATH = os.path.join(MED_INFO_DIR, "pills_jpeg_archive.zip")
PILLS_DISK_DIR = os.path.join(MED_INFO_DIR, "okf_kb", "assets", "images", "pills")
LABELS_TW_DIR = os.path.join(MED_INFO_DIR, "Labels_Taiwan")
LABELS_FDA_DIR = os.path.join(MED_INFO_DIR, "Labels")

IMAGE_EXTS = ('.png', '.jpg', '.jpeg')

# Only products that actually have a photo on record
_HAS_PHOTO = "local_image_path IS NOT NULL AND local_image_path != 'NO_MCP_PHOTO'"

# Dosage-form noise words ignored when matching brand names
_BRAND_STOPWORDS = {'TABLET', 'TABLETS', 'CAPSULE', 'CAPSULES', 'MG', 'INJECTION',
                    'SOLUTION', 'FILM', 'COATED'}


def _mime_for(path: str) -> str:
    return "image/png" if path.lower().endswith(".png") else "image/jpeg"


def _stem_of(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0].lower()


class DrugPhotoService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DrugPhotoService, cls).__new__(cls)
                cls._instance._init_service()
            return cls._instance

    def _init_service(self):
        self.zip_ref = None
        self.zip_stem_map = {}  # stem.lower() -> zip_entry_name
        self.disk_stem_map = {} # stem.lower() -> full_path

        # 1. Index disk images
        if os.path.exists(PILLS_DISK_DIR):
            for fname in os.listdir(PILLS_DISK_DIR):
                if fname.lower().endswith(IMAGE_EXTS):
                    self.disk_stem_map[_stem_of(fname)] = os.path.join(PILLS_DISK_DIR, fname)

        # 2. Open persistent zip archive
        if os.path.exists(ZIP_PATH):
            try:
                self.zip_ref = zipfile.ZipFile(ZIP_PATH, 'r')
                for name in self.zip_ref.namelist():
                    if name.lower().endswith(IMAGE_EXTS):
                        self.zip_stem_map[_stem_of(name)] = name
            except Exception as e:
                logger.error("Failed to open zip %s: %s", ZIP_PATH, e)

        logger.info("DrugPhotoService indexed %d disk + %d zip images",
                    len(self.disk_stem_map), len(self.zip_stem_map))

    def _get_db_conn(self) -> sqlite3.Connection:
        db_uri = f"file:{os.path.abspath(DB_PATH).replace(os.sep, '/')}?immutable=1"
        try:
            conn = sqlite3.connect(db_uri, uri=True, timeout=5)
        except Exception:
            conn = sqlite3.connect(DB_PATH, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def has_photo(self, stem: str) -> bool:
        return bool(stem) and (stem in self.disk_stem_map or stem in self.zip_stem_map)

    def find_drug_product(self, nhi_code: Optional[str] = None, brand_name: Optional[str] = None, generic_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Find matching drug_products record using NHI code, license id, brand name, or generic name.
        Tiers are tried in order; the first hit wins.
        """
        if not os.path.exists(DB_PATH):
            return None

        clean_code = (nhi_code or "").strip().upper()
        clean_brand = (brand_name or "").strip()
        clean_gen = (generic_name or "").strip()

        with closing(self._get_db_conn()) as conn:
            cur = conn.cursor()

            def first(where: str, arg: Any) -> Optional[Dict[str, Any]]:
                cur.execute(f"SELECT * FROM drug_products WHERE {where} AND {_HAS_PHOTO} ORDER BY id LIMIT 1", (arg,))
                row = cur.fetchone()
                return dict(row) if row else None

            if clean_code:
                # 1. Exact NHI code
                product = first("UPPER(nhi_code) = ?", clean_code)
                if product:
                    return product

                # 2. 5-6 digit license extracted from NHI code (e.g. AC311681G0 -> 031168)
                m = re.search(r'^[A-Z]{1,2}0?(\d{5,6})', clean_code)
                if m:
                    product = first("tfda_license_id LIKE ?", f"%{m.group(1).zfill(6)}%")
                    if product:
                        return product

                # 3. Resolve license via taiwan_nhi_drugs
                cur.execute("SELECT tfda_license_id FROM taiwan_nhi_drugs WHERE nhi_code = ? LIMIT 1", (clean_code,))
                nhi_row = cur.fetchone()
                if nhi_row and nhi_row["tfda_license_id"]:
                    product = first("tfda_license_id = ?", nhi_row["tfda_license_id"])
                    if product:
                        return product

            # 4. Brand name words (e.g. 'Exnortan' + '5/80'); best word-overlap wins
            if clean_brand:
                words = [w for w in re.sub(r'[^A-Za-z0-9]', ' ', clean_brand).split()
                         if len(w) > 2 and w.upper() not in _BRAND_STOPWORDS]
                if words:
                    cur.execute(f"SELECT * FROM drug_products WHERE trade_name_en LIKE ? AND {_HAS_PHOTO} ORDER BY id",
                                (f"%{words[0]}%",))
                    candidates = [dict(r) for r in cur.fetchall()]
                    if candidates:
                        best_cand, best_score = candidates[0], 0
                        for cand in candidates:
                            cand_name = (cand.get("trade_name_en") or "").upper()
                            score = sum(1 for w in words if w.upper() in cand_name)
                            if score > best_score:
                                best_score, best_cand = score, cand
                        return best_cand

            # 5. Generic name fallback
            if clean_gen:
                gen_words = [w for w in re.sub(r'[^A-Za-z0-9]', ' ', clean_gen).split() if len(w) > 3]
                if gen_words:
                    return first("generic_drug_name LIKE ?", f"%{gen_words[0]}%")

        return None

    def get_photo_bytes(self, image_stem: str) -> Tuple[Optional[bytes], str]:
        """
        Retrieve photo bytes for a given image stem (e.g. 'tw01031168' or 'bc20890100').
        Returns (bytes, mime_type) or (None, '').
        """
        stem = _stem_of(image_stem)

        # Check disk first
        disk_path = self.disk_stem_map.get(stem)
        if disk_path:
            try:
                with open(disk_path, "rb") as f:
                    return f.read(), _mime_for(disk_path)
            except Exception as e:
                logger.warning("Error reading disk image %s: %s", disk_path, e)

        # Check zip archive (ZipFile is not thread-safe for concurrent reads)
        zip_entry = self.zip_stem_map.get(stem)
        if self.zip_ref and zip_entry:
            try:
                with self._lock:
                    content = self.zip_ref.read(zip_entry)
                return content, _mime_for(zip_entry)
            except Exception as e:
                logger.warning("Error reading zip entry %s: %s", zip_entry, e)

        return None, ""

    def _find_label_pdf(self, brand_name: Optional[str]) -> Optional[str]:
        if not brand_name or not brand_name.split():
            return None
        first_w = brand_name.split()[0].replace('/', '').replace('\\', '')
        for ldir in (LABELS_TW_DIR, LABELS_FDA_DIR):
            if os.path.exists(os.path.join(ldir, f"{first_w}.pdf")):
                return f"{first_w}.pdf"
        return None

    def get_drug_info_payload(self, nhi_code: Optional[str] = None, brand_name: Optional[str] = None, generic_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Returns full structured details for drug photo modal display.
        """
        prod = self.find_drug_product(nhi_code, brand_name, generic_name)
        if not prod:
            return {
                "status": "not_found",
                "has_photo": False,
                "brand_name_query": brand_name,
                "nhi_code_query": nhi_code,
                "generic_name_query": generic_name,
                "message": "資料庫中暫無該藥品之實體圖資。"
            }

        local_img = prod.get("local_image_path") or ""
        stem = _stem_of(local_img) if local_img else ""
        has_photo = self.has_photo(stem)

        def field(key: str) -> str:
            return prod.get(key) or ""

        return {
            "status": "success",
            "found": True,
            "has_photo": has_photo,
            "image_stem": stem if has_photo else None,
            "photo_url": f"/api/drug_photo?img_id={stem}" if has_photo else None,
            "brand_name_zh": field("trade_name_zh"),
            "brand_name_en": prod.get("trade_name_en") or brand_name or "",
            "generic_name": prod.get("generic_drug_name") or generic_name or "",
            "nhi_code": prod.get("nhi_code") or nhi_code or "",
            "tfda_license_id": field("tfda_license_id"),
            "strength": field("strength"),
            "dosage_form": field("dosage_form"),
            "manufacturer": field("manufacturer"),
            "appearance_shape": field("appearance_shape"),
            "appearance_color": field("appearance_color"),
            "appearance_markings": field("appearance_markings"),
            "has_score_line": field("has_score_line"),
            "excipients": field("excipients"),
            "storage_condition": field("storage_condition"),
            "atc_code": field("atc_code"),
            "label_pdf": self._find_label_pdf(brand_name),
        }


# Global singleton
drug_photo_service = DrugPhotoService()
