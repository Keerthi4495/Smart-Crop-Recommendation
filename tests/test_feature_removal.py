import unittest
from unittest.mock import patch

import app as smartfarm_app


class DiseaseDetectionRemovalTests(unittest.TestCase):
    def setUp(self):
        self.client = smartfarm_app.app.test_client()

    def test_disease_route_is_removed(self):
        response = self.client.get("/disease")

        self.assertEqual(response.status_code, 404)

    def test_home_and_dashboard_have_no_disease_detection_links(self):
        for route in ("/", "/dashboard"):
            with self.subTest(route=route):
                response = self.client.get(route)

                self.assertEqual(response.status_code, 200)
                self.assertNotIn(b"Disease Detection", response.data)
                self.assertNotIn(b"disease information", response.data.lower())

    def test_crop_recommendation_still_returns_a_result(self):
        with patch("app.save_prediction_to_db"):
            response = self.client.post(
                "/predict",
                data={
                    "nitrogen": "90",
                    "phosphorus": "42",
                    "potassium": "43",
                    "temperature": "21",
                    "humidity": "82",
                    "ph_value": "6.5",
                    "rainfall": "202",
                    "location": "Mandapeta, Andhra Pradesh",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Recommended Crop", response.data)


if __name__ == "__main__":
    unittest.main()
