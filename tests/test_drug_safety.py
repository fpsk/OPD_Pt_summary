"""
Unit tests for clinical drug safety service and FDC decomposition.
"""

import unittest

from services.drug_safety_data import (
    FALLBACK_LIMITS,
    MOIETY_CHINESE_NAMES,
    MOIETY_DRUG_CLASSES,
)
from services.drug_safety_service import DrugSafetyService


class DrugSafetyTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = DrugSafetyService()

    def test_single_ingredient_norvasc(self):
        res = self.service.get_safety_profile("BC21571100", "NORVASC TABLETS 5MG", "Amlodipine Besylate")
        self.assertEqual(res.get("status"), "success")
        self.assertTrue(res.get("found"))
        self.assertFalse(res.get("is_fdc"))
        dose_info = res.get("safety_dose_range", {})
        self.assertIsNotNone(dose_info.get("starting_dose"))
        self.assertIsNotNone(dose_info.get("max_daily_dose"))

    def test_single_ingredient_diovan(self):
        res = self.service.get_safety_profile("B022415100", "Diovan 80mg", "Valsartan")
        self.assertEqual(res.get("status"), "success")
        self.assertTrue(res.get("found"))
        self.assertFalse(res.get("is_fdc"))

    def test_fdc_exnortan(self):
        res = self.service.get_safety_profile(
            "AC57797100", "Exnortan F.C. Tablets 5/80mg", "Valsartan + Amlodipine Besylate"
        )
        self.assertEqual(res.get("status"), "success")
        self.assertTrue(res.get("found"))
        self.assertTrue(res.get("is_fdc"))
        dose_info = res.get("safety_dose_range", {})
        components = dose_info.get("components", [])
        self.assertGreaterEqual(len(components), 2)
        moieties = [c.get("moiety") for c in components]
        self.assertIn("VALSARTAN", moieties)
        self.assertIn("AMLODIPINE", moieties)

    def test_fdc_janumet(self):
        res = self.service.get_safety_profile("BC25041100", "JANUMET 50/850 mg", "Sitagliptin / Metformin")
        self.assertEqual(res.get("status"), "success")
        self.assertTrue(res.get("found"))
        self.assertTrue(res.get("is_fdc"))
        components = res.get("safety_dose_range", {}).get("components", [])
        self.assertGreaterEqual(len(components), 2)

    def test_safety_data_mappings(self):
        self.assertIn("VALSARTAN", MOIETY_CHINESE_NAMES)
        self.assertIn("AMLODIPINE", MOIETY_CHINESE_NAMES)
        self.assertIn("METFORMIN", MOIETY_CHINESE_NAMES)
        self.assertIn("VALSARTAN", FALLBACK_LIMITS)
        self.assertIn("AMLODIPINE", FALLBACK_LIMITS)


if __name__ == "__main__":
    unittest.main()
