"""
Integration tests for OPD Clinical Summarizer REST API endpoints.
"""

import json
import unittest

from app import create_app


class PatientApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_health_check(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("status"), "online")
        self.assertIn("hospital_api_host", data)

    def test_roster_endpoint(self):
        response = self.client.get("/api/roster")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertIsInstance(data.get("patients"), list)

    def test_patient_summary_endpoint(self):
        response = self.client.get("/api/patient/B100134889?date=2026/09/01")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("patient_id"), "B100134889")
        self.assertIn("profile", data)
        self.assertIn("conditions", data)
        self.assertIn("findings", data)
        self.assertIn("medications", data)
        self.assertIn("emr_preconsult_note", data)

    def test_patient_summary_roc_date_endpoint(self):
        response = self.client.get("/api/patient/B100134889?date=1150721")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("patient_id"), "B100134889")
        self.assertEqual(data.get("clinic_date"), "1150721")

    def test_drug_safety_endpoint(self):
        response = self.client.get(
            "/api/drug_safety?code=AC57797100&brand=Exnortan+F.C.+Tablets+5/80mg&generic=Valsartan+%2B+Amlodipine+Besylate"
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertTrue(data.get("found"))
        self.assertTrue(data.get("is_fdc"))
        self.assertIn("safety_dose_range", data)
        self.assertIn("renal_adjustment", data)

    def test_drug_info_endpoint(self):
        response = self.client.get(
            "/api/drug_info?code=AC57797100&brand=Exnortan&generic=Valsartan"
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("nhi_code", data)

    def test_roc_birthdate_to_age_and_launch_updates_chart_no_and_age(self):
        from services.patient_mcp_client import calculate_age_from_birthdate

        self.assertEqual(calculate_age_from_birthdate("0450512", "1150721"), 70)
        self.assertEqual(calculate_age_from_birthdate("450512", "1150721"), 70)
        self.assertEqual(calculate_age_from_birthdate("045/05/12", "1150721"), 70)

        launch_res = self.client.post(
            "/launch",
            json={
                "patientID": "B200218355",
                "date": "1150721",
                "chartNo": "99887766",
                "birthdate": "0450512",
                "relayed": True,
            },
        )
        self.assertEqual(launch_res.status_code, 200)
        launch_json = launch_res.get_json()
        self.assertEqual(launch_json.get("status"), "ok")
        self.assertEqual(launch_json.get("chart_no"), "99887766")
        self.assertEqual(launch_json.get("age"), 70)
        self.assertEqual(launch_json.get("birth_date"), "0450512")

        summary_res = self.client.get("/api/patient/B200218355?date=1150721")
        self.assertEqual(summary_res.status_code, 200)
        summary_data = summary_res.get_json()
        self.assertEqual(summary_data.get("status"), "success")
        profile = summary_data.get("profile", {})
        self.assertEqual(profile.get("chart_no"), "99887766")
        self.assertEqual(profile.get("age"), "70")
        self.assertEqual(profile.get("birth_date"), "0450512")

    def test_patient_summary_query_param_chart_no_and_birthdate(self):
        res = self.client.get(
            "/api/patient/B100134889?date=1150721&chartNo=88776655&birthdate=0550721"
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")
        prof = data.get("profile", {})
        self.assertEqual(prof.get("chart_no"), "88776655")
        self.assertEqual(prof.get("age"), "60")
        self.assertEqual(prof.get("birth_date"), "0550721")

    def test_default_date_follows_last_queried_patient_date(self):
        from clinical_common.launch import reset_last_query

        reset_last_query()
        self.client.post(
            "/launch",
            json={"patientID": "Q122601701", "date": "1150818", "relayed": True},
        )
        cur = self.client.get("/api/launch/current").get_json()
        self.assertEqual(cur.get("last_query_date"), "1150818")
        self.assertEqual(cur.get("last_patient_id"), "Q122601701")

        # Subsequent query without explicit date follows the last queried date (1150818)
        res = self.client.get("/api/patient/B100134889")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json().get("clinic_date"), "1150818")
        reset_last_query()


if __name__ == "__main__":
    unittest.main()
