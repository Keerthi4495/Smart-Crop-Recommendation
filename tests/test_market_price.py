import os
import unittest
from unittest.mock import Mock, patch

import requests

import app as smartfarm_app


class MarketPriceFeatureTests(unittest.TestCase):
    def setUp(self):
        self.client = smartfarm_app.app.test_client()

    def test_market_page_keeps_form_usable_without_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            response = self.client.get("/market")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Live mandi price data is currently unavailable. Please try again later.",
            response.data,
        )
        for field in (b"crop_name", b"location", b"state", b"market_name"):
            self.assertIn(field, response.data)
        self.assertNotIn(b"DATA_GOV_IN_API_KEY", response.data)

    def test_market_form_submit_without_api_key_shows_friendly_message(self):
        with patch.dict(os.environ, {}, clear=True):
            response = self.client.post(
                "/market",
                data={
                    "crop_name": "Rice",
                    "location": "Mandapeta",
                    "state": "Andhra Pradesh",
                    "market_name": "Mandapeta",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Live mandi price data is currently unavailable. Please try again later.",
            response.data,
        )
        for value in (b'value="Rice"', b'value="Mandapeta"', b'value="Andhra Pradesh"'):
            self.assertIn(value, response.data)
        self.assertNotIn(b"Latest reported price", response.data)

    def test_agmarknet_request_filters_crop_state_district_and_optional_mandi(self):
        response = Mock(status_code=200, ok=True)
        response.json.return_value = {
            "records": [
                {
                    "commodity": "Rice",
                    "state": "Andhra Pradesh",
                    "district": "East Godavari",
                    "market": "Mandapeta",
                    "arrival_date": "2026-10-07",
                    "min_price": "2100",
                    "max_price": "2400",
                    "modal_price": "2250",
                },
                {
                    "commodity": "Rice",
                    "state": "Andhra Pradesh",
                    "district": "East Godavari",
                    "market": "Another Mandi",
                    "arrival_date": "2026-10-07",
                    "min_price": "2000",
                    "max_price": "2300",
                    "modal_price": "2150",
                },
            ]
        }

        with (
            patch.dict(os.environ, {"DATA_GOV_IN_API_KEY": "test-key"}, clear=True),
            patch("app.requests.get", return_value=response) as api_call,
        ):
            result, error = smartfarm_app.get_market_price(
                "Rice",
                "Mandapeta",
                state="Andhra Pradesh",
                district="East Godavari",
                market_name="Mandapeta",
            )

        self.assertIsNone(error)
        self.assertEqual(result["minimum_price"], 2100)
        self.assertEqual(result["maximum_price"], 2400)
        self.assertEqual(result["modal_price"], 2250)
        self.assertEqual(result["market_name"], "Mandapeta")
        self.assertEqual(result["price_date"], "2026-10-07")
        self.assertEqual(result["source"], "data.gov.in — Agmarknet daily mandi prices")
        api_call.assert_called_once()
        self.assertEqual(
            api_call.call_args.kwargs["params"]["filters[commodity]"], "Rice"
        )
        self.assertEqual(
            api_call.call_args.kwargs["params"]["filters[state]"], "Andhra Pradesh"
        )
        self.assertEqual(
            api_call.call_args.kwargs["params"]["filters[district]"], "East Godavari"
        )
        self.assertEqual(
            api_call.call_args.kwargs["params"]["filters[market]"], "Mandapeta"
        )

    def test_market_form_passes_entered_district_state_and_mandi(self):
        response = Mock(status_code=200, ok=True)
        response.json.return_value = {
            "records": [
                {
                    "commodity": "Rice",
                    "state": "Andhra Pradesh",
                    "district": "East Godavari",
                    "market": "Mandapeta",
                    "arrival_date": "2026-10-07",
                    "min_price": "2100",
                    "max_price": "2400",
                    "modal_price": "2250",
                }
            ]
        }
        with (
            patch.dict(os.environ, {"DATA_GOV_IN_API_KEY": "test-key"}, clear=True),
            patch(
                "app.resolve_market_location_details",
                return_value={
                    "location": "Mandapeta",
                    "state": "Andhra Pradesh",
                    "district": "East Godavari",
                },
            ),
            patch("app.requests.get", return_value=response),
        ):
            page = self.client.post(
                "/market",
                data={
                    "crop_name": "Rice",
                    "location": "Mandapeta",
                    "state": "Andhra Pradesh",
                    "market_name": "Mandapeta",
                },
            )

        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Latest reported price", page.data)
        self.assertIn(b"2250", page.data)
        self.assertIn(b"Mandapeta", page.data)

    def test_agmarknet_timeout_has_specific_error(self):
        with (
            patch.dict(os.environ, {"DATA_GOV_IN_API_KEY": "test-key"}, clear=True),
            patch("app.requests.get", side_effect=requests.Timeout),
        ):
            result, error = smartfarm_app.get_market_price(
                "Rice", "Mandapeta", state="Andhra Pradesh", district="East Godavari"
            )

        self.assertIsNone(result)
        self.assertIn("took too long", error)

    def test_agmarknet_invalid_json_has_specific_error(self):
        response = Mock(status_code=200, ok=True)
        response.json.side_effect = ValueError("invalid JSON")
        with (
            patch.dict(os.environ, {"DATA_GOV_IN_API_KEY": "test-key"}, clear=True),
            patch("app.requests.get", return_value=response),
        ):
            result, error = smartfarm_app.get_market_price(
                "Rice", "Mandapeta", state="Andhra Pradesh", district="East Godavari"
            )

        self.assertIsNone(result)
        self.assertIn("unreadable response", error)

    def test_agmarknet_rejected_api_key_has_specific_error(self):
        response = Mock(status_code=403, ok=False)
        with (
            patch.dict(os.environ, {"DATA_GOV_IN_API_KEY": "test-key"}, clear=True),
            patch("app.requests.get", return_value=response),
        ):
            result, error = smartfarm_app.get_market_price(
                "Rice", "Mandapeta", state="Andhra Pradesh", district="East Godavari"
            )

        self.assertIsNone(result)
        self.assertIn("API key was rejected", error)
        self.assertIn("DATA_GOV_IN_API_KEY", error)

    def test_agmarknet_no_records_reports_unavailable_crop_and_area(self):
        response = Mock(status_code=200, ok=True)
        response.json.return_value = {"records": []}
        with (
            patch.dict(os.environ, {"DATA_GOV_IN_API_KEY": "test-key"}, clear=True),
            patch("app.requests.get", return_value=response),
        ):
            result, error = smartfarm_app.get_market_price(
                "Rice", "Mandapeta", state="Andhra Pradesh", district="East Godavari"
            )

        self.assertIsNone(result)
        self.assertIn("No reported Rice mandi price", error)
        self.assertIn("East Godavari, Andhra Pradesh", error)


if __name__ == "__main__":
    unittest.main()
