"""
Drug Photo and Product Information Service.
Connects to Medication_Info/okf_kb/cdss_knowledge.db,
reads pill photos from pills_jpeg_archive.zip and disk images.
"""

import os
import re
import sqlite3
import zipfile
import threading
from typing import Optional, Dict, Any, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)
MED_INFO_DIR = os.path.join(PARENT_DIR, "Medication_Info")

DB_PATH = os.path.join(MED_INFO_DIR, "okf_kb", "cdss_knowledge.db")
ZIP_PATH = os.path.join(MED_INFO_DIR, "pills_jpeg_archive.zip")
PILLS_DISK_DIR = os.path.join(MED_INFO_DIR, "okf_kb", "assets", "images", "pills")
LABELS_TW_DIR = os.path.join(MED_INFO_DIR, "Labels_Taiwan")
LABELS_FDA_DIR = os.path.join(MED_INFO_DIR, "Labels")

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
        self.zip_namelist_set = set()
        self.zip_stem_map = {}  # stem.lower() -> zip_entry_name
        self.disk_stem_map = {} # stem.lower() -> full_path

        # 1. Index disk images
        if os.path.exists(PILLS_DISK_DIR):
            for fname in os.listdir(PILLS_DISK_DIR):
                if fname.lower().endswith(('.png', '.jpg', '.jpeg')):
                    stem = os.path.splitext(fname)[0].lower()
                    self.disk_stem_map[stem] = os.path.join(PILLS_DISK_DIR, fname)

        # 2. Open persistent zip archive
        if os.path.exists(ZIP_PATH):
            try:
                self.zip_ref = zipfile.ZipFile(ZIP_PATH, 'r')
                for name in self.zip_ref.namelist():
                    if name.lower().endswith(('.jpg', '.jpeg', '.png')):
                        stem = os.path.splitext(os.path.basename(name))[0].lower()
                        self.zip_stem_map[stem] = name
            except Exception as e:
                print(f"[DrugPhotoService] Failed to open zip {ZIP_PATH}: {e}")

    def _get_db_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def find_drug_product(self, nhi_code: Optional[str] = None, brand_name: Optional[str] = None, generic_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Find matching drug_products record using NHI code, license id, brand name, or generic name.
        """
        if not os.path.exists(DB_PATH):
            return None

        conn = self._get_db_conn()
        cur = conn.cursor()
        product = None

        clean_code = (nhi_code or "").strip().upper()
        clean_brand = (brand_name or "").strip()
        clean_gen = (generic_name or "").strip()

        # 1. Search by exact NHI code in drug_products
        if clean_code:
            cur.execute("""
                SELECT * FROM drug_products 
                WHERE UPPER(nhi_code) = ? AND local_image_path IS NOT NULL AND local_image_path != 'NO_MCP_PHOTO'
                ORDER BY id LIMIT 1
            """, (clean_code,))
            row = cur.fetchone()
            if row:
                product = dict(row)

        # 2. Search by 5-6 digit license extracted from NHI code (e.g. AC311681G0 -> 031168)
        if not product and clean_code:
            m = re.search(r'^[A-Z]{1,2}0?(\d{5,6})', clean_code)
            if m:
                lic_num = m.group(1).zfill(6)
                cur.execute("""
                    SELECT * FROM drug_products 
                    WHERE tfda_license_id LIKE ? AND local_image_path IS NOT NULL AND local_image_path != 'NO_MCP_PHOTO'
                    ORDER BY id LIMIT 1
                """, (f"%{lic_num}%",))
                row = cur.fetchone()
                if row:
                    product = dict(row)

        # 3. Search taiwan_nhi_drugs by exact code to find tfda_license_id if not found yet
        if not product and clean_code:
            cur.execute("SELECT tfda_license_id, brand_name_eng FROM taiwan_nhi_drugs WHERE nhi_code = ? LIMIT 1", (clean_code,))
            nhi_row = cur.fetchone()
            if nhi_row and nhi_row["tfda_license_id"]:
                cur.execute("""
                    SELECT * FROM drug_products 
                    WHERE tfda_license_id = ? AND local_image_path IS NOT NULL AND local_image_path != 'NO_MCP_PHOTO'
                    ORDER BY id LIMIT 1
                """, (nhi_row["tfda_license_id"],))
                p_row = cur.fetchone()
                if p_row:
                    product = dict(p_row)

        # 4. Search by Brand Name with Strength (e.g. 'Exnortan' + '5/80')
        if not product and clean_brand:
            words = [w for w in re.sub(r'[^A-Za-z0-9]', ' ', clean_brand).split() 
                     if len(w) > 2 and w.upper() not in ['TABLET', 'TABLETS', 'CAPSULE', 'CAPSULES', 'MG', 'INJECTION', 'SOLUTION', 'FILM', 'COATED']]
            if words:
                primary_word = words[0]
                # Look for matching primary word
                cur.execute("""
                    SELECT * FROM drug_products 
                    WHERE trade_name_en LIKE ? AND local_image_path IS NOT NULL AND local_image_path != 'NO_MCP_PHOTO'
                    ORDER BY id
                """, (f"%{primary_word}%",))
                candidates = [dict(r) for r in cur.fetchall()]
                
                if candidates:
                    # Score candidates based on words match
                    best_cand = candidates[0]
                    best_score = 0
                    brand_upper = clean_brand.upper()
                    for cand in candidates:
                        cand_name = (cand.get("trade_name_en") or "").upper()
                        score = sum(1 for w in words if w.upper() in cand_name)
                        if score > best_score:
                            best_score = score
                            best_cand = cand
                    product = best_cand

        # 5. Search by Generic name as fallback
        if not product and clean_gen:
            gen_words = [w for w in re.sub(r'[^A-Za-z0-9]', ' ', clean_gen).split() if len(w) > 3]
            if gen_words:
                cur.execute("""
                    SELECT * FROM drug_products 
                    WHERE generic_drug_name LIKE ? AND local_image_path IS NOT NULL AND local_image_path != 'NO_MCP_PHOTO'
                    ORDER BY id LIMIT 1
                """, (f"%{gen_words[0]}%",))
                row = cur.fetchone()
                if row:
                    product = dict(row)

        conn.close()
        return product

    def get_photo_bytes(self, image_stem: str) -> Tuple[Optional[bytes], str]:
        """
        Retrieve photo bytes for a given image stem (e.g. 'tw01031168' or 'bc20890100').
        Returns (bytes, mime_type) or (None, '').
        """
        stem = os.path.splitext(os.path.basename(image_stem))[0].lower()

        # Check disk first
        if stem in self.disk_stem_map:
            disk_path = self.disk_stem_map[stem]
            try:
                with open(disk_path, "rb") as f:
                    content = f.read()
                mime = "image/png" if disk_path.lower().endswith(".png") else "image/jpeg"
                return content, mime
            except Exception as e:
                print(f"[DrugPhotoService] Error reading disk image {disk_path}: {e}")

        # Check zip archive
        if self.zip_ref and stem in self.zip_stem_map:
            zip_entry = self.zip_stem_map[stem]
            try:
                with self._lock:
                    content = self.zip_ref.read(zip_entry)
                mime = "image/png" if zip_entry.lower().endswith(".png") else "image/jpeg"
                return content, mime
            except Exception as e:
                print(f"[DrugPhotoService] Error reading zip entry {zip_entry}: {e}")

        return None, ""

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
        stem = os.path.splitext(os.path.basename(local_img))[0].lower() if local_img else ""
        has_photo = bool(stem and (stem in self.disk_stem_map or stem in self.zip_stem_map))

        # Check for Label PDF if any
        pdf_name = None
        if brand_name:
            first_w = brand_name.split()[0].replace('/', '').replace('\\', '')
            for ldir in [LABELS_TW_DIR, LABELS_FDA_DIR]:
                if os.path.exists(ldir):
                    cand = os.path.join(ldir, f"{first_w}.pdf")
                    if os.path.exists(cand):
                        pdf_name = f"{first_w}.pdf"
                        break

        return {
            "status": "success",
            "found": True,
            "has_photo": has_photo,
            "image_stem": stem if has_photo else None,
            "photo_url": f"/api/drug_photo?img_id={stem}" if has_photo else None,
            "brand_name_zh": prod.get("trade_name_zh") or "",
            "brand_name_en": prod.get("trade_name_en") or brand_name or "",
            "generic_name": prod.get("generic_drug_name") or generic_name or "",
            "nhi_code": prod.get("nhi_code") or nhi_code or "",
            "tfda_license_id": prod.get("tfda_license_id") or "",
            "strength": prod.get("strength") or "",
            "dosage_form": prod.get("dosage_form") or "",
            "manufacturer": prod.get("manufacturer") or "",
            "appearance_shape": prod.get("appearance_shape") or "",
            "appearance_color": prod.get("appearance_color") or "",
            "appearance_markings": prod.get("appearance_markings") or "",
            "has_score_line": prod.get("has_score_line") or "",
            "excipients": prod.get("excipients") or "",
            "storage_condition": prod.get("storage_condition") or "",
            "atc_code": prod.get("atc_code") or "",
            "label_pdf": pdf_name
        }

# Global singleton
drug_photo_service = DrugPhotoService()
