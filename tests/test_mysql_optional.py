import os
import unittest
from unittest.mock import MagicMock, patch

import mysql.connector
from werkzeug.security import generate_password_hash

with (
    patch.dict(
        os.environ,
        {
            "DB_HOST": "test-db.example",
            "DB_PORT": "3307",
            "DB_NAME": "crop_test",
            "DB_USER": "test_user",
            "DB_PASSWORD": "test-password",
        },
    ),
    patch("mysql.connector.connect", return_value=MagicMock()),
):
    import app as smartfarm_app
    import db_config


class MySQLConnectivityTests(unittest.TestCase):
    def setUp(self):
        self.client = smartfarm_app.app.test_client()

    def set_authenticated_session(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 7
            session["username"] = "farmer"
            session["farm_assistant_context"] = {
                "crop": "Rice",
                "location": "Mandapeta, Andhra Pradesh",
                "temperature": 26,
                "humidity": 70,
                "rainfall": 120,
            }

    def test_connection_uses_configured_host_port_and_database(self):
        with patch("db_config.mysql.connector.connect") as connect:
            db_config.get_mysql_connection()
            db_config.get_mysql_connection(include_database=False)

        configured_options = connect.call_args_list[0].kwargs
        self.assertEqual(configured_options["host"], db_config.DB_HOST)
        self.assertEqual(configured_options["port"], db_config.DB_PORT)
        self.assertEqual(configured_options["user"], db_config.DB_USER)
        self.assertEqual(configured_options["database"], db_config.DB_NAME)
        self.assertNotIn("database", connect.call_args_list[1].kwargs)

    def test_database_initialization_does_not_suppress_connection_errors(self):
        with patch.object(
            smartfarm_app,
            "get_db_connection",
            side_effect=mysql.connector.Error("simulated unavailable database"),
        ):
            with self.assertRaises(mysql.connector.Error):
                smartfarm_app.init_db()

    def test_database_initialization_creates_and_migrates_required_tables(self):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        cursor.fetchall.return_value = [(column,) for column in (
            "username", "nitrogen", "phosphorus", "potassium", "temperature",
            "humidity", "ph_value", "rainfall", "crop_name",
        )]
        with (
            patch.object(smartfarm_app, "get_db_connection", return_value=connection),
        ):
            smartfarm_app.init_db()

        executed_sql = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS users" in sql for sql in executed_sql))
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS crop_history" in sql for sql in executed_sql))
        connection.commit.assert_called_once_with()

    def test_login_and_registration_show_generic_database_unavailable_message(self):
        for route in ("/login", "/register"):
            with self.subTest(route=route):
                with patch(
                    "app.get_db_connection",
                    side_effect=mysql.connector.Error("private database details"),
                ):
                    response = self.client.post(
                        route,
                        data={"username": "farmer", "password": "password"},
                    )

                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Database temporarily unavailable", response.data)
                self.assertNotIn(b"private database details", response.data)

    def test_database_backed_pages_and_crop_recommendation_survive_outage(self):
        self.set_authenticated_session()
        unavailable = mysql.connector.Error("simulated unavailable database")

        with patch("app.get_db_connection", side_effect=unavailable):
            dashboard = self.client.get("/dashboard")
            market = self.client.get(
                "/market?crop_name=Rice&location=Mandapeta&state=Andhra+Pradesh"
            )
            crop_history = self.client.get("/crop-history")
            profit = self.client.post(
                "/profit",
                data={
                    "crop_name": "Rice",
                    "location": "Mandapeta",
                    "land_area": "1",
                    "expected_yield_kg": "1000",
                    "expected_selling_price": "25",
                    "seed_cost": "1000",
                    "fertilizer_cost": "2000",
                    "labour_cost": "3000",
                    "irrigation_cost": "500",
                    "other_expenses": "250",
                },
            )

        with (
            patch("app.get_db_connection", side_effect=unavailable),
            patch(
                "app.get_weather_for_location",
                return_value=(None, "Weather data is currently unavailable."),
            ),
        ):
            weather = self.client.get("/weather")

        with patch("app.get_db_connection", side_effect=unavailable):
            recommendation = self.client.post(
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

        for response in (dashboard, market, profit, weather):
            with self.subTest(path=response.request.path):
                self.assertEqual(response.status_code, 200)
        self.assertIn(b"Database temporarily unavailable", dashboard.data)
        self.assertEqual(crop_history.status_code, 503)
        self.assertIn(b"Database temporarily unavailable", crop_history.data)
        self.assertIn(b"Calculate estimate", profit.data)
        self.assertIn(b"Database temporarily unavailable", weather.data)
        self.assertEqual(recommendation.status_code, 503)
        self.assertIn(b"crop recommendation could not be saved", recommendation.data)

    def test_manual_weather_lookup_continues_during_database_outage(self):
        self.set_authenticated_session()
        weather_data = {
            "location": "Mandapeta, Andhra Pradesh",
            "date": "2026-10-08",
            "temperature": 29,
            "humidity": 72,
            "today_rainfall": 4,
            "today_rain_chance": 45,
            "wind_speed": 16,
            "condition": "Cloudy",
            "icon": "cloudy",
            "forecast": [],
        }
        with (
            patch(
                "app.get_db_connection",
                side_effect=mysql.connector.Error("simulated unavailable database"),
            ),
            patch("app.get_weather_for_location", return_value=(weather_data, None)),
        ):
            response = self.client.post(
                "/weather",
                data={
                    "action": "check_weather",
                    "farmer_location": "Mandapeta, Andhra Pradesh",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Database temporarily unavailable", response.data)
        self.assertIn(b"WEATHER FOR ENTERED LOCATION", response.data)
        self.assertIn(b"Mandapeta, Andhra Pradesh", response.data)

    def test_authentication_still_uses_database_when_available(self):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        cursor.fetchone.return_value = None
        with patch("app.get_db_connection", return_value=connection):
            registration = self.client.post(
                "/register",
                data={"username": "new-farmer", "password": "password"},
            )

        self.assertEqual(registration.status_code, 302)
        self.assertEqual(registration.headers["Location"], "/login")
        cursor.execute.assert_any_call(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
            unittest.mock.ANY,
        )
        connection.commit.assert_called_once_with()

        connection = MagicMock()
        connection.cursor.return_value.fetchone.return_value = (
            7,
            "farmer",
            generate_password_hash("password"),
        )
        with patch("app.get_db_connection", return_value=connection):
            login = self.client.post(
                "/login",
                data={"username": "farmer", "password": "password"},
            )

        self.assertEqual(login.status_code, 302)
        self.assertEqual(login.headers["Location"], "/dashboard")
        with self.client.session_transaction() as session:
            self.assertEqual(session["username"], "farmer")

        logout = self.client.get("/logout")
        self.assertEqual(logout.status_code, 302)
        with self.client.session_transaction() as session:
            self.assertNotIn("user_id", session)

    def test_crop_recommendation_writes_prediction_and_history_when_database_is_available(self):
        self.set_authenticated_session()
        prediction_connection = MagicMock()
        history_connection = MagicMock()
        history_connection.cursor.return_value.lastrowid = 101

        with patch(
            "app.get_db_connection",
            side_effect=[prediction_connection, history_connection],
        ):
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
        prediction_connection.cursor.return_value.execute.assert_called_once()
        history_connection.cursor.return_value.execute.assert_called_once()
        history_connection.commit.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
