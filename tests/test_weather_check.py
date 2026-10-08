import unittest
from unittest.mock import patch

import app as smartfarm_app


class WeatherCheckFeatureTests(unittest.TestCase):
    def setUp(self):
        self.client = smartfarm_app.app.test_client()
        with self.client.session_transaction() as session:
            session["farm_assistant_context"] = {
                "crop": "Rice",
                "location": "Guntur",
                "latitude": 16.3,
                "longitude": 80.4,
            }

    @staticmethod
    def weather_data(with_forecast=True):
        forecast = [
            {
                "date": f"2026-10-{day:02d}",
                "weekday": f"Day {day - 8}",
                "condition": "Rain showers",
                "max_temp": 30,
                "min_temp": 23,
                "rain_chance": 85 if day == 9 else 35,
                "rainfall": 28 if day == 9 else 2,
                "wind_speed": 18,
                "warning": "Heavy rain possible" if day == 9 else None,
            }
            for day in range(9, 16)
        ] if with_forecast else []
        return {
            "location": "Guntur",
            "date": "2026-10-08",
            "temperature": 29,
            "humidity": 72,
            "today_rainfall": 4,
            "today_rain_chance": 45,
            "wind_speed": 16,
            "condition": "Cloudy",
            "icon": "☁️",
            "forecast": forecast,
        }

    def test_weather_page_keeps_current_display_and_adds_check_button(self):
        with patch(
            "app.get_weather_for_location",
            return_value=(self.weather_data(), None),
        ) as weather_lookup:
            response = self.client.get("/weather")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Today's Weather", response.data)
        self.assertIn(b"Temperature", response.data)
        self.assertIn(b"Check Weather", response.data)
        self.assertIn(b"Weather Farming Advice", response.data)
        self.assertIn(b'<details class="weather-check-disclosure">', response.data)
        self.assertNotIn(b'<details class="weather-check-disclosure" open>', response.data)
        weather_lookup.assert_called_once_with("Guntur", 16.3, 80.4)

    def test_check_weather_uses_saved_location_and_shows_advice_and_outlook(self):
        with patch(
            "app.get_weather_for_location",
            return_value=(self.weather_data(), None),
        ) as weather_lookup:
            response = self.client.get("/weather")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Weather Farming Advice", response.data)
        self.assertIn(b"Generally suitable", response.data)
        self.assertIn(b"Recommended crop", response.data)
        self.assertIn(b"Rain probability", response.data)
        self.assertIn(b"Current wind is", response.data)
        self.assertIn(b"Postpone irrigation", response.data)
        self.assertIn(b"Heavy rain possible", response.data)
        self.assertIn(b"Important outlook for the next 3", response.data)
        self.assertIn(b"What should I do today?", response.data)
        self.assertNotIn(b'name="location"', response.data)
        weather_lookup.assert_called_once_with("Guntur", 16.3, 80.4)

    def test_missing_forecast_is_reported_without_inventing_outlook_or_alerts(self):
        with patch(
            "app.get_weather_for_location",
            return_value=(self.weather_data(with_forecast=False), None),
        ):
            response = self.client.get("/weather")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Forecast data unavailable", response.data)
        self.assertIn(
            b"Weather alert information is unavailable because forecast data is unavailable.",
            response.data,
        )

    def test_manual_location_is_looked_up_and_results_use_recommended_crop(self):
        saved_weather = self.weather_data()
        entered_weather = self.weather_data()
        entered_weather["location"] = "Mandapeta, Andhra Pradesh"
        with patch(
            "app.get_weather_for_location",
            side_effect=[(saved_weather, None), (entered_weather, None)],
        ) as weather_lookup:
            response = self.client.post(
                "/weather",
                data={
                    "action": "check_weather",
                    "farmer_location": "Mandapeta, Andhra Pradesh",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"WEATHER FOR ENTERED LOCATION", response.data)
        self.assertIn(b"Mandapeta, Andhra Pradesh", response.data)
        self.assertIn(b"Current Weather", response.data)
        self.assertIn(b"Humidity", response.data)
        self.assertIn(b"Farming Weather Advice", response.data)
        self.assertIn(b"Rice prefers warm conditions", response.data)
        self.assertEqual(
            weather_lookup.call_args_list[1].args,
            ("Mandapeta, Andhra Pradesh",),
        )

    def test_empty_manual_location_is_rejected_without_weather_lookup(self):
        with patch(
            "app.get_weather_for_location",
            return_value=(self.weather_data(), None),
        ) as weather_lookup:
            response = self.client.post(
                "/weather",
                data={"action": "check_weather", "farmer_location": "   "},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Weather data could not be found for this location. Please check the location name.",
            response.data,
        )
        weather_lookup.assert_called_once_with("Guntur", 16.3, 80.4)

    def test_unmatched_manual_location_shows_required_message(self):
        with patch(
            "app.get_weather_for_location",
            side_effect=[
                (self.weather_data(), None),
                (None, "The entered location could not be found."),
            ],
        ):
            response = self.client.post(
                "/weather",
                data={
                    "action": "check_weather",
                    "farmer_location": "Not a real village",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Weather data could not be found for this location. Please check the location name.",
            response.data,
        )


if __name__ == "__main__":
    unittest.main()
