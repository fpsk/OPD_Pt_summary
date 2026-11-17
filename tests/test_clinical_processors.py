"""
Unit tests for clinical domain processors and cleaners.
"""

import unittest
from datetime import datetime

from services.clinical import (
    BadgeSynthesizer,
    ConditionProcessor,
    EmrNoteGenerator,
    LabProcessor,
    MedProcessor,
    classify_lab_group,
    clean_brand_name,
    clean_display_reference_range,
    clean_ingredient,
    clean_lab_item_name,
    extract_med_dose,
    parse_reference_range,
    trim_display_zeros,
)


class ClinicalProcessorsTestCase(unittest.TestCase):
    def test_clean_lab_item_name(self):
        self.assertEqual(clean_lab_item_name("GOT", ";(S-GOT/AST)"), "AST / GOT")
        self.assertEqual(clean_lab_item_name("GPT", ";(S-GPT/ALT)"), "ALT / GPT")
        self.assertEqual(clean_lab_item_name("GLU", "Glucose AC"), "Glucose (AC)")
        self.assertEqual(clean_lab_item_name("HbA1c", "糖化血色素"), "HbA1c")
        self.assertEqual(clean_lab_item_name("CRE", "Creatinine"), "Creatinine")
        self.assertEqual(clean_lab_item_name("eGFR", "eGFR"), "eGFR")

    def test_parse_reference_range(self):
        low, high = parse_reference_range("[65][175]")
        self.assertEqual((low, high), (65.0, 175.0))

        low, high = parse_reference_range("< 150")
        self.assertIsNone(low)
        self.assertEqual(high, 150.0)

        low, high = parse_reference_range("> 10")
        self.assertEqual(low, 10.0)
        self.assertIsNone(high)

    def test_clean_display_reference_range(self):
        # Bracketed ranges
        self.assertEqual(clean_display_reference_range("[65][175]"), "65 - 175")
        self.assertEqual(clean_display_reference_range("[11.500][14.500]"), "11.5 - 14.5")
        self.assertEqual(clean_display_reference_range("[60][999]"), ">= 60")
        self.assertEqual(clean_display_reference_range("< 140"), "< 140")

    def test_classify_lab_group(self):
        self.assertEqual(classify_lab_group("AST / GOT"), "liver")
        self.assertEqual(classify_lab_group("ALT / GPT"), "liver")
        self.assertEqual(classify_lab_group("WBC"), "hematological")
        self.assertEqual(classify_lab_group("Platelet"), "hematological")
        self.assertEqual(classify_lab_group("Creatinine"), "renal")
        self.assertEqual(classify_lab_group("eGFR"), "renal")
        self.assertEqual(classify_lab_group("Glucose (AC)"), "metabolic")
        self.assertEqual(classify_lab_group("HbA1c"), "metabolic")
        self.assertEqual(classify_lab_group("hs-CRP"), "immunological")

    def test_med_cleaner(self):
        self.assertEqual(clean_ingredient("VALSARTAN；AMLODIPINE"), "VALSARTAN + AMLODIPINE")
        self.assertEqual(clean_brand_name("易德壓悅膜衣錠(鋁箔/膠箔)"), "易德壓悅膜衣錠")
        self.assertEqual(extract_med_dose("Exnortan 5/80mg"), "5/80mg")
        self.assertEqual(extract_med_dose("Norvasc 5mg"), "5mg")

    def test_badge_synthesizer(self):
        synthesizer = BadgeSynthesizer()
        lab_panel = {
            "key_metrics": {
                "egfr": {"value": 45.0},
                "creatinine": {"value": 1.5},
            }
        }
        surgical_history = set()
        all_conditions = {"Diabetes mellitus", "Essential (primary) hypertension"}
        med_summary = {}

        badges = synthesizer.synthesize_clinical_badges(
            lab_panel, surgical_history, all_conditions, med_summary
        )
        labels = [b.get("label") for b in badges]
        self.assertIn("Hypertension", labels)
        self.assertIn("Type 2 DM", labels)
        self.assertIn("CKD (eGFR 45.0)", labels)

    def test_condition_processor_pathology_check(self):
        cp = ConditionProcessor()
        path_record = {
            "item": "Pathology",
            "order": "25001C Surgical Pathology",
            "val": "specimen submitted tubular adenoma with low grade dysplasia",
        }
        self.assertTrue(cp.is_pathology_report(path_record))

        lab_record = {
            "item": "GLU",
            "order": "09005C Glucose AC",
            "val": "105",
        }
        self.assertFalse(cp.is_pathology_report(lab_record))


if __name__ == "__main__":
    unittest.main()
