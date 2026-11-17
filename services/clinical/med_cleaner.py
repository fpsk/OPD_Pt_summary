"""
Medication ingredient normalization, brand name cleaning, and dosage string extraction.
"""

import re


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
