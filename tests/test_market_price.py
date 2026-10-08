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
        self.assertIn(b"Select a crop to check live mandi prices.", response.data)
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
            b"Live market price is temporarily unavailable. Please try again later.",
            response.data,
        )
        for value in (b'value="Rice"', b'value="Mandapeta"', b'value="Andhra Pradesh"'):
            self.assertIn(value, response.data)
        self.assertNotIn(b"Live Mandi Price", response.data)

    def test_agmarknet_request_filters_crop_state_district_and_optional_mandi(self):
        response = Mock(status_code=200, ok=True)
        response.json.return_value = {
            "records": [
                {
                    "commodity": "Rice",
                    "variety": "Common",
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
        self.assertEqual(result["market_state"], "Andhra Pradesh")
        self.assertEqual(result["commodity"], "Rice")
        self.assertEqual(result["variety"], "Common")
        self.assertEqual(result["last_updated"], "2026-10-07")
        self.assertEqual(
            result["source"],
            "Government agricultural market data (AGMARKNET via data.gov.in)",
        )
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
        self.assertEqual(api_call.call_args.kwargs["timeout"], (5, 15))

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
        self.assertIn(b"Live Mandi Price", page.data)
        self.assertIn(b"Government agricultural market data", page.data)
        self.assertIn(b"2250", page.data)
        self.assertIn(b"Mandapeta", page.data)

    def test_market_form_does_not_show_provider_errors_to_farmers(self):
        invalid_json = Mock(status_code=200, ok=True)
        invalid_json.json.side_effect = ValueError("private JSON parse details")
        rate_limited = Mock(status_code=429, ok=False)
        rejected_key = Mock(status_code=403, ok=False)
        failures = (
            {"side_effect": requests.Timeout("private timeout detail")},
            {"side_effect": requests.ConnectionError("private connection detail")},
            {"return_value": invalid_json},
            {"return_value": rate_limited},
            {"return_value": rejected_key},
        )

        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
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
                    patch("app.requests.get", **failure),
                ):
                    response = self.client.post(
                        "/market",
                        data={
                            "crop_name": "Rice",
                            "location": "Mandapeta",
                            "state": "Andhra Pradesh",
                        },
                    )

                self.assertEqual(response.status_code, 200)
                self.assertIn(
                    b"Live market price is temporarily unavailable. Please try again later.",
                    response.data,
                )
                self.assertNotIn(b"private", response.data)
                self.assertNotIn(b"DATA_GOV_IN_API_KEY", response.data)
                self.assertNotIn(b"429", response.data)

    def test_market_lookup_can_search_by_crop_without_a_selected_mandi(self):
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
            patch("app.requests.get", return_value=response) as api_call,
        ):
            result, error = smartfarm_app.get_market_price(
                "Rice", "", state="Andhra Pradesh"
            )

        self.assertIsNone(error)
        self.assertEqual(result["market_name"], "Mandapeta")
        params = api_call.call_args.kwargs["params"]
        self.assertEqual(params["filters[commodity]"], "Rice")
        self.assertEqual(params["filters[state]"], "Andhra Pradesh")
        self.assertNotIn("filters[market]", params)

    def test_invalid_crop_is_not_sent_to_official_api(self):
        with (
            patch.dict(os.environ, {"DATA_GOV_IN_API_KEY": "test-key"}, clear=True),
            patch("app.requests.get") as api_call,
        ):
            result, error = smartfarm_app.get_market_price(
                "Unlisted Crop", "Mandapeta", state="Andhra Pradesh"
            )

        self.assertIsNone(result)
        self.assertEqual(
            error,
            "Live market price is temporarily unavailable. Please try again later.",
        )
        api_call.assert_not_called()

    def test_agmarknet_empty_result_has_farmer_friendly_message(self):
        response = Mock(status_code=200, ok=True)
        response.json.return_value = {"records": []}
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
            result, error = smartfarm_app.get_market_price_for_location(
                "Rice", "Mandapeta", state="Andhra Pradesh"
            )

        self.assertIsNone(result)
        self.assertEqual(
            error,
            "Live market price is temporarily unavailable. Please try again later.",
        )


if __name__ == "__main__":
    unittest.main()
