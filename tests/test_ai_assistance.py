import os
import unittest
from unittest.mock import Mock, patch

import requests

import app as smartfarm_app


class AIAssistanceFlowTests(unittest.TestCase):
    def setUp(self):
        self.client = smartfarm_app.app.test_client()

    def _set_farm_context(self):
        with self.client.session_transaction() as session:
            session["farm_assistant_context"] = {
                "crop": "Rice",
                "nitrogen": 80,
                "phosphorus": 40,
                "potassium": 40,
                "location": "Guntur",
                "latitude": 16.3,
                "longitude": 80.4,
            }

    def test_chat_route_sends_question_and_context_to_provider(self):
        provider_response = Mock(ok=True)
        provider_response.json.return_value = {
            "choices": [{"message": {"content": "Water the rice field evenly."}}]
        }
        self._set_farm_context()

        with (
            patch.dict(os.environ, {"FARM_ASSISTANT_API_KEY": "test-key"}, clear=True),
            patch("app.requests.post", return_value=provider_response) as provider_call,
            patch(
                "app.get_weather_for_location",
                return_value=(
                    {
                        "temperature": 29,
                        "humidity": 70,
                        "condition": "Clear",
                        "rainfall": 0,
                    },
                    None,
                ),
            ),
            patch(
                "app.get_market_price_for_location",
                return_value=(
                    {
                        "current_price": 2200,
                        "market_name": "Guntur Mandi",
                        "price_unit": "INR/quintal",
                        "source": "Test market feed",
                    },
                    None,
                ),
            ),
        ):
            response = self.client.post(
                "/chatbot", data={"question": "How should I water my crop?"}
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Water the rice field evenly.", response.data)
        self.assertNotIn(b"test-key", response.data)
        provider_call.assert_called_once()
        args, kwargs = provider_call.call_args
        self.assertEqual(args[0], "https://api.openai.com/v1/chat/completions")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(kwargs["json"]["model"], "gpt-4o-mini")
        self.assertEqual(kwargs["timeout"], (5, 35))
        self.assertEqual(
            kwargs["json"]["messages"][-1]["content"], "How should I water my crop?"
        )
        system_prompt = kwargs["json"]["messages"][0]["content"]
        self.assertIn('"nitrogen": 80', system_prompt)
        self.assertIn('"current_weather"', system_prompt)
        self.assertIn('"current_market"', system_prompt)

    def test_prompt_requests_each_supported_language(self):
        provider_response = Mock(ok=True)
        provider_response.json.return_value = {
            "choices": [{"message": {"content": "Provider response"}}]
        }

        with (
            patch.dict(os.environ, {"FARM_ASSISTANT_API_KEY": "test-key"}, clear=True),
            patch("app.requests.post", return_value=provider_response) as provider_call,
            patch("app.get_weather_for_location", return_value=(None, None)),
            patch("app.get_market_price_for_location", return_value=(None, None)),
        ):
            for language, expected in (
                ("en", "English"),
                ("te", "Telugu"),
                ("hi", "Hindi"),
            ):
                with self.client.session_transaction() as session:
                    session["language"] = language
                self.client.post("/chatbot", data={"question": "Farming advice"})
                prompt = provider_call.call_args.kwargs["json"]["messages"][0]["content"]
                self.assertIn(f"Answer in {expected}", prompt)

    def test_missing_api_key_returns_setup_error_without_calling_provider(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("app.requests.post") as provider_call,
        ):
            response = self.client.post(
                "/chatbot", data={"question": "What should I plant?"}
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No AI answer will be generated", response.data)
        provider_call.assert_not_called()

    def test_timeout_returns_error_without_adding_an_ai_answer(self):
        with (
            patch.dict(os.environ, {"FARM_ASSISTANT_API_KEY": "test-key"}, clear=True),
            patch("app.requests.post", side_effect=requests.Timeout),
        ):
            response = self.client.post(
                "/chatbot", data={"question": "How much water does rice need?"}
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"AI Assistance took too long to respond", response.data)
        self.assertNotIn(b"Water the rice field evenly.", response.data)
        self.assertNotIn(b'class="chat-message bot"', response.data)

    def test_provider_http_error_returns_error_without_an_ai_answer(self):
        provider_response = Mock(ok=False, status_code=429)
        with (
            patch.dict(os.environ, {"FARM_ASSISTANT_API_KEY": "test-key"}, clear=True),
            patch("app.requests.post", return_value=provider_response),
        ):
            response = self.client.post(
                "/chatbot", data={"question": "How much water does rice need?"}
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"AI Assistance could not reach its configured provider",
            response.data,
        )
        self.assertNotIn(b'class="chat-message bot"', response.data)


if __name__ == "__main__":
    unittest.main()
