# -*- coding: utf-8 -*-
from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from functools import wraps
import io
import math
import os
import re
from urllib.parse import urlparse
import joblib
import mysql.connector
import requests
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from db_config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME


def load_env_file():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(env_path):
        return

    with open(env_path, 'r', encoding='utf-8') as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


load_env_file()

app = Flask(__name__)
app.secret_key = "smart_crop_farmer_app_secret"

# Load the saved model without retraining.
model_path = os.path.join("model", "crop_recommendation_model.pkl")
model = joblib.load(model_path)
MAX_DISEASE_IMAGE_BYTES = 8 * 1024 * 1024

LANGUAGES = {
    "en": {
        "home": "Home",
        "register": "Register",
        "login": "Login",
        "dashboard": "Dashboard",
        "logout": "Logout",
        "weather": "Weather",
        "forecast": "Forecast",
        "fertilizer": "Fertilizer",
        "irrigation": "Irrigation",
        "market": "Market Price",
        "profit": "Profit",
        "assistant": "AI Chatbot",
        "smart_crop_recommendation": "Smart Crop Recommendation",
        "recommended_crop": "Recommended Crop",
        "predict": "Predict Crop",
        "language": "Language",
        "ai_chatbot": "AI Chatbot",
        "npk_warning": "For better accuracy, get your soil tested to know the correct NPK values.",
        "soil_testing_message": "For better accuracy, get your soil tested to know the correct NPK values.",
        "recommended_crop_text": "This crop is recommended based on the soil and weather values you entered.",
        "today_weather": "Today's Weather",
        "upcoming_weather": "Upcoming Weather",
        "temperature": "Temperature",
        "humidity": "Humidity",
        "rainfall": "Rainfall",
        "weather_condition": "Weather condition",
        "wind": "Wind",
        "date": "Date",
        "rain_possibility": "Rain possibility",
        "warning": "Weather warning",
        "market_price_for": "Market Price",
        "farmer_location": "Farmer Location",
        "nearby_mandi": "Nearby Mandi",
        "current_price": "Current Price",
        "minimum": "Minimum",
        "maximum": "Maximum",
        "modal_price": "Modal Price",
        "last_updated": "Last Updated",
        "source": "Data source",
        "future_price_trend": "Estimated Future Price Trend",
        "seven_day_trend": "7-Day Trend",
        "thirty_day_trend": "30-Day Trend",
        "trend_disclaimer": "Estimated trend only — future prices are not guaranteed.",
        "location_prompt": "Use your browser location or enter a village, town, or district.",
        "manual_location": "Farmer location",
        "use_my_location": "Use My Location",
        "load_farmer_information": "Load Farmer Information",
        "loading_farmer_information": "Loading live weather and market data…",
        "location_required": "Choose or enter a location to load weather and market information.",
        "weather_unavailable": "Weather data is currently unavailable.",
        "market_unavailable": "Live market price is currently unavailable.",
        "trend_unavailable": "Insufficient recent mandi history to estimate this trend.",
        "increase": "Increase",
        "stable": "Stable",
        "decrease": "Decrease",
        "crop_advice_rice": "Rice grows best in warm, wet conditions. Keep fields evenly watered and monitor drainage.",
        "crop_advice_wheat": "Wheat prefers cool growing weather. Maintain balanced nutrients and avoid waterlogging.",
        "crop_advice_maize": "Maize needs good sunlight and regular moisture, especially while flowering and forming grain.",
        "crop_advice_cotton": "Cotton needs warm weather and well-drained soil. Monitor regularly for pests during flowering.",
        "crop_advice_banana": "Banana thrives in warm conditions with steady moisture and good drainage.",
        "crop_advice_mango": "Mango grows well in warm climates. Protect young plants and avoid excess water around roots.",
        "crop_advice_default": "Follow local agricultural guidance for this crop and check soil moisture and plant health regularly.",
        "clear_form": "Clear",
        "sample_values": "Use sample values",
        "chatbot_title": "AI Chatbot",
        "chatbot_intro": "Ask a farming question and get quick guidance.",
        "type_message": "Type your farming question...",
        "send": "Send",
        "market_price": "Market Price",
        "home_link": "Home",
    },
    "te": {
        "home": "హోమ్",
        "register": "నమోదు",
        "login": "లాగిన్",
        "dashboard": "డాష్‌బోర్డ్",
        "logout": "లాగ్అవుట్",
        "weather": "వాతావరణం",
        "forecast": "ముందస్తు అంచనా",
        "fertilizer": "ఎరువులు",
        "irrigation": "సాగునీటి నిర్వహణ",
        "market": "మార్కెట్ ధర",
        "profit": "లాభం",
        "assistant": "AI చాట్‌బాట్",
        "smart_crop_recommendation": "స్మార్ట్ పంట సిఫార్సు",
        "recommended_crop": "సిఫార్సు చేసిన పంట",
        "predict": "పంటను అంచనా వేయండి",
        "language": "భాష",
        "ai_chatbot": "AI చాట్‌బాట్",
        "npk_warning": "మెరుగైన ఖచ్చితత్వానికి, సరైన NPK విలువలు తెలుసుకోవడానికి మీ మట్టిని పరీక్షించండి.",
        "soil_testing_message": "మెరుగైన ఖచ్చితత్వానికి, సరైన NPK విలువలు తెలుసుకోవడానికి మీ మట్టిని పరీక్షించండి.",
        "recommended_crop_text": "మీరు నమోదు చేసిన మట్టి మరియు వాతావరణ విలువల ఆధారంగా ఈ పంట సిఫార్సు చేయబడింది.",
        "today_weather": "నేటి వాతావరణం",
        "upcoming_weather": "రాబోయే వాతావరణం",
        "temperature": "ఉష్ణోగ్రత",
        "humidity": "తేమ",
        "rainfall": "వర్షపాతం",
        "weather_condition": "వాతావరణ పరిస్థితి",
        "wind": "గాలి",
        "date": "తేదీ",
        "rain_possibility": "వర్షం అవకాశం",
        "warning": "వాతావరణ హెచ్చరిక",
        "market_price_for": "మార్కెట్ ధర",
        "farmer_location": "రైతు స్థానం",
        "nearby_mandi": "సమీప మార్కెట్",
        "current_price": "ప్రస్తుత ధర",
        "minimum": "కనిష్టం",
        "maximum": "గరిష్టం",
        "modal_price": "మోడల్ ధర",
        "last_updated": "చివరిగా నవీకరించబడింది",
        "source": "డేటా మూలం",
        "future_price_trend": "అంచనా భవిష్యత్ ధర ధోరణి",
        "seven_day_trend": "7 రోజుల ధోరణి",
        "thirty_day_trend": "30 రోజుల ధోరణి",
        "trend_disclaimer": "ఇది అంచనా మాత్రమే — భవిష్యత్ ధరలకు హామీ లేదు.",
        "location_prompt": "మీ బ్రౌజర్ స్థానాన్ని ఉపయోగించండి లేదా గ్రామం, పట్టణం లేదా జిల్లాను నమోదు చేయండి.",
        "manual_location": "రైతు స్థానం",
        "use_my_location": "నా స్థానాన్ని ఉపయోగించండి",
        "load_farmer_information": "రైతు సమాచారం పొందండి",
        "loading_farmer_information": "ప్రత్యక్ష వాతావరణం మరియు మార్కెట్ సమాచారం లోడ్ అవుతోంది…",
        "location_required": "వాతావరణం మరియు మార్కెట్ సమాచారం కోసం స్థానాన్ని ఎంచుకోండి లేదా నమోదు చేయండి.",
        "weather_unavailable": "ప్రస్తుతం వాతావరణ సమాచారం అందుబాటులో లేదు.",
        "market_unavailable": "ప్రత్యక్ష మార్కెట్ ధర ప్రస్తుతం అందుబాటులో లేదు.",
        "trend_unavailable": "ఈ ధోరణిని అంచనా వేయడానికి ఇటీవలి మార్కెట్ చరిత్ర సరిపోదు.",
        "increase": "పెరుగుదల",
        "stable": "స్థిరం",
        "decrease": "తగ్గుదల",
        "crop_advice_rice": "వరి వెచ్చని, తేమగల వాతావరణంలో బాగా పెరుగుతుంది. పొలంలో నీటిని సమంగా ఉంచి పారుదలను గమనించండి.",
        "crop_advice_wheat": "గోధుమకు చల్లని వాతావరణం అనుకూలం. పోషకాలను సమతుల్యంగా ఉంచి నీరు నిలవకుండా చూడండి.",
        "crop_advice_maize": "మొక్కజొన్నకు మంచి సూర్యకాంతి, క్రమమైన తేమ అవసరం; ముఖ్యంగా పూత మరియు గింజ ఏర్పడే సమయంలో.",
        "crop_advice_cotton": "పత్తికి వెచ్చని వాతావరణం, నీరు నిలవని నేల అవసరం. పూత సమయంలో పురుగులను గమనించండి.",
        "crop_advice_banana": "అరటి వెచ్చని వాతావరణంలో, స్థిరమైన తేమ మరియు మంచి పారుదలతో బాగా పెరుగుతుంది.",
        "crop_advice_mango": "మామిడి వెచ్చని వాతావరణంలో బాగా పెరుగుతుంది. చిన్న మొక్కలను కాపాడి వేర్ల దగ్గర అధిక నీటిని నివారించండి.",
        "crop_advice_default": "ఈ పంటకు స్థానిక వ్యవసాయ సూచనలను అనుసరించి నేల తేమ మరియు మొక్కల ఆరోగ్యాన్ని క్రమం తప్పకుండా పరిశీలించండి.",
        "clear_form": "స్పష్టంగా",
        "sample_values": "నమూనా విలువలు",
        "chatbot_title": "AI చాట్‌బాట్",
        "chatbot_intro": "పంటపై ప్రశ్న అడగండి, త్వరిత సహాయాన్ని పొందండి.",
        "type_message": "మీ వ్యవసాయ ప్రశ్నను టైప్ చేయండి...",
        "send": "పంపించండి",
        "market_price": "మార్కెట్ ధర",
        "home_link": "హోమ్",
    },
    "hi": {
        "home": "होम",
        "register": "रजिस्टर",
        "login": "लॉगिन",
        "dashboard": "डैशबोर्ड",
        "logout": "लॉगआउट",
        "weather": "मौसम",
        "forecast": "पूर्वानुमान",
        "fertilizer": "उर्वरक",
        "irrigation": "सिंचाई",
        "market": "बाज़ार मूल्य",
        "profit": "लाभ",
        "assistant": "एआई चैटबॉट",
        "smart_crop_recommendation": "स्मार्ट फसल अनुशंसा",
        "recommended_crop": "अनुशंसित फसल",
        "predict": "फसल की भविष्यवाणी करें",
        "language": "भाषा",
        "ai_chatbot": "एआई चैटबॉट",
        "npk_warning": "बेहतर सटीकता के लिए, सही NPK मान जानने के लिए अपने मिट्टी का परीक्षण कराएँ।",
        "soil_testing_message": "बेहतर सटीकता के लिए, सही NPK मान जानने के लिए अपने मिट्टी का परीक्षण कराएँ।",
        "recommended_crop_text": "यह फसल आपके द्वारा दर्ज की गई मिट्टी और मौसम मानों के आधार पर अनुशंसित है।",
        "today_weather": "आज का मौसम",
        "upcoming_weather": "आगामी मौसम",
        "temperature": "तापमान",
        "humidity": "नमी",
        "rainfall": "वर्षा",
        "weather_condition": "मौसम की स्थिति",
        "wind": "हवा",
        "date": "तारीख",
        "rain_possibility": "बारिश की संभावना",
        "warning": "मौसम चेतावनी",
        "market_price_for": "मंडी भाव",
        "farmer_location": "किसान का स्थान",
        "nearby_mandi": "नज़दीकी मंडी",
        "current_price": "वर्तमान भाव",
        "minimum": "न्यूनतम",
        "maximum": "अधिकतम",
        "modal_price": "मॉडल भाव",
        "last_updated": "अंतिम अपडेट",
        "source": "डेटा स्रोत",
        "future_price_trend": "अनुमानित भविष्य मूल्य रुझान",
        "seven_day_trend": "7-दिन का रुझान",
        "thirty_day_trend": "30-दिन का रुझान",
        "trend_disclaimer": "यह केवल अनुमानित रुझान है — भविष्य के भाव की गारंटी नहीं है।",
        "location_prompt": "अपने ब्राउज़र का स्थान उपयोग करें या गाँव, कस्बा अथवा जिला दर्ज करें।",
        "manual_location": "किसान का स्थान",
        "use_my_location": "मेरा स्थान उपयोग करें",
        "load_farmer_information": "किसान की जानकारी लोड करें",
        "loading_farmer_information": "लाइव मौसम और मंडी की जानकारी लोड हो रही है…",
        "location_required": "मौसम और मंडी की जानकारी के लिए स्थान चुनें या दर्ज करें।",
        "weather_unavailable": "मौसम की जानकारी अभी उपलब्ध नहीं है।",
        "market_unavailable": "लाइव मंडी भाव अभी उपलब्ध नहीं है।",
        "trend_unavailable": "इस रुझान का अनुमान लगाने के लिए हाल का मंडी इतिहास पर्याप्त नहीं है।",
        "increase": "बढ़त",
        "stable": "स्थिर",
        "decrease": "गिरावट",
        "crop_advice_rice": "धान गर्म और नम परिस्थितियों में अच्छा बढ़ता है। खेत में समान पानी रखें और जल निकासी पर ध्यान दें।",
        "crop_advice_wheat": "गेहूँ के लिए ठंडा मौसम बेहतर है। पोषक तत्व संतुलित रखें और खेत में पानी जमा न होने दें।",
        "crop_advice_maize": "मक्का को अच्छी धूप और नियमित नमी चाहिए, विशेषकर फूल और दाना बनने के समय।",
        "crop_advice_cotton": "कपास को गर्म मौसम और अच्छी जल निकासी वाली मिट्टी चाहिए। फूल आने पर कीटों की निगरानी करें।",
        "crop_advice_banana": "केला गर्म मौसम, नियमित नमी और अच्छी जल निकासी में अच्छा बढ़ता है।",
        "crop_advice_mango": "आम गर्म जलवायु में अच्छा बढ़ता है। नए पौधों की रक्षा करें और जड़ों के पास अधिक पानी न रहने दें।",
        "crop_advice_default": "इस फसल के लिए स्थानीय कृषि सलाह अपनाएँ और मिट्टी की नमी तथा पौधों के स्वास्थ्य की नियमित जाँच करें।",
        "clear_form": "साफ करें",
        "sample_values": "नमूना मान",
        "chatbot_title": "एआई चैटबॉट",
        "chatbot_intro": "कृषि प्रश्न पूछें और त्वरित मार्गदर्शन प्राप्त करें।",
        "type_message": "अपना कृषि प्रश्न टाइप करें...",
        "send": "भेजें",
        "market_price": "बाज़ार मूल्य",
        "home_link": "होम",
    },
}

MARKET_CROPS = ("Rice", "Wheat", "Maize", "Cotton", "Sugarcane", "Coconut", "Pulses", "Potato")

CROP_NEEDS = {
    "rice": {"nitrogen": 80, "phosphorus": 40, "potassium": 40, "ph": 5.5},
    "wheat": {"nitrogen": 70, "phosphorus": 35, "potassium": 35, "ph": 6.0},
    "maize": {"nitrogen": 90, "phosphorus": 45, "potassium": 45, "ph": 6.2},
    "cotton": {"nitrogen": 85, "phosphorus": 50, "potassium": 50, "ph": 6.5},
    "sugarcane": {"nitrogen": 100, "phosphorus": 55, "potassium": 55, "ph": 6.3},
    "coconut": {"nitrogen": 75, "phosphorus": 35, "potassium": 40, "ph": 6.2},
    "pulses": {"nitrogen": 65, "phosphorus": 30, "potassium": 30, "ph": 6.4},
    "potato": {"nitrogen": 80, "phosphorus": 40, "potassium": 45, "ph": 5.8},
}

ALTERNATIVE_CROPS = {
    "rice": ["Wheat", "Maize", "Pulses"],
    "wheat": ["Rice", "Maize", "Potato"],
    "maize": ["Rice", "Cotton", "Wheat"],
    "cotton": ["Maize", "Wheat", "Pulses"],
    "sugarcane": ["Rice", "Maize", "Potato"],
    "coconut": ["Rice", "Pulses", "Maize"],
    "pulses": ["Wheat", "Rice", "Maize"],
    "potato": ["Wheat", "Rice", "Maize"],
}

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Cloudy",
    45: "Fog",
    48: "Fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Heavy drizzle",
    56: "Freezing drizzle",
    57: "Heavy freezing drizzle",
    61: "Light rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Heavy freezing rain",
    71: "Light snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Light rain shower",
    81: "Moderate rain shower",
    82: "Heavy rain shower",
    85: "Snow shower",
    86: "Heavy snow shower",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with hail",
}


def get_language():
    return session.get("language", "en")


def get_env_value(key, default=""):
    return os.environ.get(key, default)


def get_translations():
    return LANGUAGES.get(get_language(), LANGUAGES["en"])


@app.context_processor
def inject_translations():
    return {"t": get_translations(), "current_language": get_language()}


def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )


def create_database_if_needed():
    connection = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    cursor = connection.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    cursor.close()
    connection.close()


def init_db():
    create_database_if_needed()
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100),
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS crop_predictions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50),
            nitrogen FLOAT,
            phosphorus FLOAT,
            potassium FLOAT,
            temperature FLOAT,
            humidity FLOAT,
            ph_value FLOAT,
            rainfall FLOAT,
            crop_name VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS crop_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            crop_name VARCHAR(50) NOT NULL,
            nitrogen FLOAT NOT NULL,
            phosphorus FLOAT NOT NULL,
            potassium FLOAT NOT NULL,
            temperature FLOAT NOT NULL,
            humidity FLOAT NOT NULL,
            ph_value FLOAT NOT NULL,
            rainfall FLOAT NOT NULL,
            location VARCHAR(255) NULL,
            estimated_cost DECIMAL(12, 2) NULL,
            estimated_revenue DECIMAL(12, 2) NULL,
            estimated_profit_loss DECIMAL(12, 2) NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_crop_history_user_created (user_id, created_at),
            CONSTRAINT fk_crop_history_user
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    try:
        cursor.execute("ALTER TABLE crop_predictions ADD COLUMN IF NOT EXISTS username VARCHAR(50)")
    except mysql.connector.Error:
        pass

    connection.commit()
    cursor.close()
    connection.close()


init_db()


def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return function(*args, **kwargs)

    return wrapper


def save_prediction_to_db(username, nitrogen, phosphorus, potassium, temperature, humidity, ph_value, rainfall, crop_name):
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("ALTER TABLE crop_predictions ADD COLUMN IF NOT EXISTS username VARCHAR(50)")
        cursor.execute("ALTER TABLE crop_predictions ADD COLUMN IF NOT EXISTS nitrogen FLOAT")
        cursor.execute("ALTER TABLE crop_predictions ADD COLUMN IF NOT EXISTS phosphorus FLOAT")
        cursor.execute("ALTER TABLE crop_predictions ADD COLUMN IF NOT EXISTS potassium FLOAT")
        cursor.execute("ALTER TABLE crop_predictions ADD COLUMN IF NOT EXISTS temperature FLOAT")
        cursor.execute("ALTER TABLE crop_predictions ADD COLUMN IF NOT EXISTS humidity FLOAT")
        cursor.execute("ALTER TABLE crop_predictions ADD COLUMN IF NOT EXISTS ph_value FLOAT")
        cursor.execute("ALTER TABLE crop_predictions ADD COLUMN IF NOT EXISTS rainfall FLOAT")
        cursor.execute("ALTER TABLE crop_predictions ADD COLUMN IF NOT EXISTS crop_name VARCHAR(50)")

        query = """
            INSERT INTO crop_predictions
            (username, nitrogen, phosphorus, potassium, temperature, humidity, ph_value, rainfall, crop_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (username, nitrogen, phosphorus, potassium, temperature, humidity, ph_value, rainfall, crop_name)
        cursor.execute(query, values)
        connection.commit()
    except mysql.connector.Error as error:
        print("MySQL save error:", error)
    finally:
        if connection is not None and connection.is_connected():
            connection.close()


def save_crop_history(user_id, nitrogen, phosphorus, potassium, temperature, humidity, ph_value, rainfall, crop_name):
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO crop_history
                (user_id, crop_name, nitrogen, phosphorus, potassium, temperature,
                 humidity, ph_value, rainfall, location, estimated_cost,
                 estimated_revenue, estimated_profit_loss)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, NULL, NULL, NULL)
            """,
            (user_id, crop_name, nitrogen, phosphorus, potassium, temperature,
             humidity, ph_value, rainfall),
        )
        connection.commit()
        return cursor.lastrowid
    finally:
        if connection is not None and connection.is_connected():
            connection.close()


def update_crop_history_location(history_id, user_id, location):
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE crop_history
            SET location = %s
            WHERE id = %s AND user_id = %s
            """,
            (location, history_id, user_id),
        )
        connection.commit()
    finally:
        if connection is not None and connection.is_connected():
            connection.close()


def weather_code_to_text(code):
    return WEATHER_CODES.get(code, "Unknown condition")


def reverse_geocode_coordinates(lat, lon):
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "jsonv2",
            "addressdetails": 1,
        }
        response = requests.get(url, params=params, headers={"User-Agent": "SmartCropApp/1.0"}, timeout=10)
        data = response.json()
        if not data:
            return "Location unavailable"

        address = data.get("address", {})
        city = address.get("city") or address.get("town") or address.get("village") or address.get("municipality")
        state = address.get("state") or address.get("state_district") or address.get("county")
        if city and state:
            return f"{city}, {state}"
        if city:
            return city
        if state:
            return state
        return data.get("display_name", "Location unavailable")
    except Exception:
        return "Location unavailable"


def parse_market_date(value):
    if not value:
        return None
    for date_format in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(value).strip(), date_format).date()
        except ValueError:
            continue
    return None


def market_trend_from_history(records, latest_record, days):
    latest_date = parse_market_date(latest_record.get("arrival_date") or latest_record.get("date"))
    latest_price = latest_record.get("_modal_price")
    if latest_date is None or latest_price is None:
        return None

    cutoff = latest_date - timedelta(days=days)
    historical_prices = []
    for record in records:
        record_date = parse_market_date(record.get("arrival_date") or record.get("date"))
        price = record.get("_modal_price")
        if record_date is not None and cutoff <= record_date < latest_date and price is not None:
            historical_prices.append(price)
    if not historical_prices:
        return None

    baseline = sum(historical_prices) / len(historical_prices)
    if baseline <= 0:
        return None
    change = (latest_price - baseline) / baseline
    if change > 0.01:
        return "Increase"
    if change < -0.01:
        return "Decrease"
    return "Stable"


def get_market_price(crop_name, location, state=None, district=None):
    crop_name = (crop_name or "").strip().title()
    location = (location or "").strip()
    app.logger.info(
        "Market lookup requested: crop=%s location=%s state=%s district=%s",
        crop_name[:80],
        location[:120],
        (state or "")[:80],
        (district or "")[:80],
    )

    if not crop_name or not location:
        return None, "Please enter a location and select a crop."

    data_gov_key = os.environ.get("DATA_GOV_IN_API_KEY", "").strip()
    if data_gov_key:
        if not state or not district:
            app.logger.warning(
                "Market lookup unavailable: state and district are required for Agmarknet."
            )
            return None, (
                "Live market price is currently unavailable. "
                "The location could not be matched to a state and district."
            )
        api_url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
        params = {
            "api-key": data_gov_key,
            "format": "json",
            "limit": 1000,
            "filters[commodity]": crop_name,
            "filters[state]": state,
            "sort[arrival_date]": "desc",
        }
        if district:
            params["filters[district]"] = district

        try:
            response = requests.get(api_url, params=params, timeout=15)
            if response.status_code != 200:
                app.logger.warning(
                    "Agmarknet market request failed with HTTP status %s.", response.status_code
                )
                return None, (
                    "Live market price is currently unavailable. "
                    "The mandi data service could not complete the request; please try again later."
                )
            payload = response.json()
            records = payload.get("records", []) if isinstance(payload, dict) else []
            if not isinstance(records, list):
                app.logger.warning("Agmarknet returned an invalid records value.")
                return None, (
                    "Live market price is currently unavailable. "
                    "The mandi data service returned an unexpected response."
                )
            records = [record for record in records if isinstance(record, dict)]
            crop_records = [
                record for record in records
                if str(record.get("commodity", "")).strip().casefold() == crop_name.casefold()
            ]
            app.logger.info(
                "Agmarknet response received: records=%s crop_matches=%s",
                len(records),
                len(crop_records),
            )
            crop_records = [
                record for record in crop_records
                if str(record.get("state", "")).strip().casefold() == state.casefold()
                and str(record.get("district", "")).strip().casefold() == district.casefold()
            ]

            for record in crop_records:
                try:
                    modal_price = float(record.get("modal_price"))
                    record["_modal_price"] = modal_price if math.isfinite(modal_price) and modal_price > 0 else None
                except (TypeError, ValueError):
                    record["_modal_price"] = None

            priced_records = [record for record in crop_records if record["_modal_price"] is not None]
            if not priced_records:
                app.logger.info(
                    "Agmarknet returned no priced %s records for %s, %s.",
                    crop_name,
                    district,
                    state,
                )
                return None, (
                    "Live market price is currently unavailable. "
                    "No priced listing was found for this crop in the matched district."
                )
            priced_records.sort(
                key=lambda record: parse_market_date(record.get("arrival_date")) or datetime.min.date(),
                reverse=True,
            )
            latest = priced_records[0]
            market_name = str(latest.get("market", "")).strip()
            if not market_name:
                app.logger.warning("Agmarknet's latest priced record has no market name.")
                return None, (
                    "Live market price is currently unavailable. "
                    "The mandi data service did not identify a market for this listing."
                )
            mandi_records = [
                record for record in priced_records
                if str(record.get("market", "")).strip().casefold() == market_name.casefold()
            ]

            def parse_price(record, field):
                try:
                    value = record.get(field)
                    parsed = float(value) if value not in (None, "") else None
                    return parsed if parsed is not None and math.isfinite(parsed) and parsed > 0 else None
                except (TypeError, ValueError):
                    return None

            return {
                "crop_name": crop_name,
                "current_price": latest["_modal_price"],
                "minimum_price": parse_price(latest, "min_price"),
                "maximum_price": parse_price(latest, "max_price"),
                "modal_price": latest["_modal_price"],
                "market_name": market_name,
                "market_district": latest.get("district") or district or "",
                "price_date": latest.get("arrival_date") or "",
                "source": "data.gov.in — Agmarknet daily mandi prices",
                "trend_7_days": market_trend_from_history(mandi_records, latest, 7),
                "trend_30_days": market_trend_from_history(mandi_records, latest, 30),
            }, None
        except (requests.RequestException, ValueError, TypeError, AttributeError) as error:
            app.logger.warning(
                "Agmarknet market request or response parsing failed: error_type=%s",
                type(error).__name__,
            )
            return None, (
                "Live market price is currently unavailable. "
                "The mandi data service could not be reached or returned invalid data."
            )

    api_url = os.environ.get("MARKET_API_URL", "").strip()
    api_key = os.environ.get("MARKET_API_KEY", "").strip()

    if not api_url:
        app.logger.warning(
            "Market data unavailable: configure DATA_GOV_IN_API_KEY or MARKET_API_URL."
        )
        return None, (
            "Live market price is currently unavailable. "
            "Market data is not configured; set DATA_GOV_IN_API_KEY or MARKET_API_URL."
        )

    try:
        headers = {"User-Agent": "SmartCropApp/1.0"}
        params = {
            "crop": crop_name,
            "location": location,
        }
        if api_key:
            params["api_key"] = api_key

        response = requests.get(api_url, params=params, headers=headers, timeout=10)
        if response.status_code != 200:
            app.logger.warning(
                "Configured market API request failed with HTTP status %s.", response.status_code
            )
            return None, (
                "Live market price is currently unavailable. "
                "The configured market data service could not complete the request."
            )

        data = response.json()
        app.logger.info(
            "Configured market API response received: http_status=%s payload_type=%s",
            response.status_code,
            type(data).__name__,
        )
        if not data:
            return None, "Live market price is currently unavailable."

        market_record = None
        if isinstance(data, list):
            if data:
                market_record = data[0]
        elif isinstance(data, dict):
            if "records" in data and isinstance(data["records"], list) and data["records"]:
                market_record = data["records"][0]
            elif "data" in data and isinstance(data["data"], list) and data["data"]:
                market_record = data["data"][0]
            else:
                market_record = data

        if market_record is None:
            app.logger.info("Configured market API returned no matching record.")
            return None, (
                "Live market price is currently unavailable. "
                "No matching crop and location listing was returned."
            )
        if not isinstance(market_record, dict):
            app.logger.warning("Configured market API returned a record in an unsupported format.")
            return None, (
                "Live market price is currently unavailable. "
                "The configured service returned an unexpected response."
            )

        def parse_price(*fields):
            for field in fields:
                value = market_record.get(field)
                try:
                    parsed = float(value) if value not in (None, "") else None
                except (TypeError, ValueError):
                    continue
                if parsed is not None and math.isfinite(parsed) and parsed > 0:
                    return parsed
            return None

        current_price = parse_price(
            "price", "current_price", "market_price", "rate", "price_per_quintal", "modal_price"
        )
        market_name = (
            market_record.get("market")
            or market_record.get("mandi")
            or market_record.get("market_name")
            or market_record.get("location")
        )
        source = market_record.get("source") or market_record.get("api_source") or urlparse(api_url).netloc
        price_date = market_record.get("date") or market_record.get("price_date") or market_record.get("updated_at")
        trend_7 = market_record.get("trend_7_days") or market_record.get("trend7")
        trend_30 = market_record.get("trend_30_days") or market_record.get("trend30")

        if current_price is None or not market_name or not source:
            app.logger.warning(
                "Configured market API response is missing a valid price, market name, or data source."
            )
            return None, (
                "Live market price is currently unavailable. "
                "The configured service did not return a valid price and market."
            )

        return {
            "crop_name": crop_name,
            "current_price": current_price,
            "minimum_price": parse_price("min_price", "minimum_price"),
            "maximum_price": parse_price("max_price", "maximum_price"),
            "modal_price": parse_price("modal_price") or current_price,
            "market_name": market_name,
            "price_date": price_date,
            "source": source,
            "trend_7_days": str(trend_7).capitalize() if trend_7 else None,
            "trend_30_days": str(trend_30).capitalize() if trend_30 else None,
        }, None
    except (requests.RequestException, ValueError, TypeError, AttributeError) as error:
        app.logger.warning(
            "Configured market API request or response parsing failed: error_type=%s",
            type(error).__name__,
        )
        return None, (
            "Live market price is currently unavailable. "
            "The configured market data service could not be reached or returned invalid data."
        )


def reverse_geocode_details(lat, lon):
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": lat,
        "lon": lon,
        "format": "jsonv2",
        "addressdetails": 1,
    }
    response = requests.get(url, params=params, headers={"User-Agent": "SmartCropApp/1.0"}, timeout=10)
    response.raise_for_status()
    data = response.json()
    address = data.get("address", {})
    city = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("municipality")
        or address.get("county")
    )
    state = address.get("state") or address.get("state_district")
    district = address.get("state_district") or address.get("county") or address.get("city_district")
    location = ", ".join(part for part in (city, state) if part) or data.get("display_name")
    return {"location": location or "Location unavailable", "state": state, "district": district}


def resolve_market_location_details(location, latitude=None, longitude=None):
    if latitude is not None and longitude is not None:
        lat = float(latitude)
        lon = float(longitude)
        if not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise ValueError("Location coordinates are invalid.")
        return reverse_geocode_details(lat, lon)

    if not location:
        return {}

    response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": location, "count": 1, "language": "en", "format": "json"},
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results", []) if isinstance(payload, dict) else []
    if not isinstance(results, list) or not results or not isinstance(results[0], dict):
        return {}

    place = results[0]
    city = place.get("name")
    state = place.get("admin1")
    return {
        "location": ", ".join(part for part in (city, state) if part) or location,
        "state": state,
        "district": place.get("admin2"),
    }


def get_weather_for_location(location, latitude=None, longitude=None):
    location = (location or "").strip()
    app.logger.info(
        "Weather lookup requested: location=%s browser_coordinates=%s",
        location[:120] if location else "(not entered)",
        latitude is not None and longitude is not None,
    )
    try:
        if latitude is not None and longitude is not None:
            lat = float(latitude)
            lon = float(longitude)
            if (
                not math.isfinite(lat)
                or not math.isfinite(lon)
                or not -90 <= lat <= 90
                or not -180 <= lon <= 180
            ):
                return None, (
                    "Weather data is currently unavailable. "
                    "The selected location coordinates are invalid."
                )
            try:
                place_details = reverse_geocode_details(lat, lon)
            except requests.RequestException:
                place_details = {"location": location or "Detected location", "state": None, "district": None}
            city_name = place_details["location"]
        else:
            if not location:
                return None, (
                    "Weather data is currently unavailable. "
                    "Please enter a village, town, or district."
                )
            geo_url = "https://geocoding-api.open-meteo.com/v1/search"
            geo_params = {
                "name": location,
                "count": 1,
                "language": "en",
                "format": "json",
            }

            geo_response = requests.get(geo_url, params=geo_params, timeout=10)
            app.logger.info(
                "Weather geocoding response received: http_status=%s",
                geo_response.status_code,
            )
            geo_response.raise_for_status()
            geo_data = geo_response.json()
            if not isinstance(geo_data, dict):
                raise ValueError("Unexpected geocoding response")
            geo_results = geo_data.get("results")
            if not isinstance(geo_results, list) or not geo_results:
                app.logger.info(
                    "Weather geocoding found no location match for entered location=%s",
                    location[:120],
                )
                return None, (
                    "Weather data is currently unavailable. "
                    "The entered location could not be found; check its spelling and try again."
                )

            place = geo_results[0]
            if not isinstance(place, dict):
                raise ValueError("Unexpected geocoding result")
            lat = float(place["latitude"])
            lon = float(place["longitude"])
            if (
                not math.isfinite(lat)
                or not math.isfinite(lon)
                or not -90 <= lat <= 90
                or not -180 <= lon <= 180
            ):
                raise ValueError("Invalid coordinates returned by geocoding")
            city_name = ", ".join(
                part for part in (place.get("name"), place.get("admin1")) if part
            )
            place_details = {
                "location": city_name or location,
                "state": place.get("admin1"),
                "district": place.get("admin2"),
            }

        forecast_url = "https://api.open-meteo.com/v1/forecast"
        forecast_params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,wind_speed_10m_max",
            "timezone": "auto",
            "forecast_days": 8,
        }

        forecast_response = requests.get(forecast_url, params=forecast_params, timeout=10)
        app.logger.info(
            "Weather forecast response received: http_status=%s",
            forecast_response.status_code,
        )
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()
        if not isinstance(forecast_data, dict):
            raise ValueError("Unexpected forecast response")

        current = forecast_data.get("current", {})
        daily = forecast_data.get("daily", {})
        if not isinstance(current, dict) or not isinstance(daily, dict):
            raise ValueError("Unexpected weather data format")
        if not any(
            current.get(field) is not None
            for field in ("temperature_2m", "relative_humidity_2m", "precipitation")
        ):
            raise ValueError("Current weather values are missing")

        daily_dates = daily.get("time", [])
        if not isinstance(daily_dates, list):
            raise ValueError("Unexpected forecast dates")
        daily_weather = daily.get("weather_code", [])
        high_temp = daily.get("temperature_2m_max", [])
        low_temp = daily.get("temperature_2m_min", [])
        rain_prob = daily.get("precipitation_probability_max", [])
        rain_amount = daily.get("precipitation_sum", [])
        max_wind = daily.get("wind_speed_10m_max", [])

        forecast_list = []
        for index in range(1, min(len(daily_dates), 8)):
            code = daily_weather[index] if index < len(daily_weather) else None
            chance = rain_prob[index] if index < len(rain_prob) else None
            rain_mm = rain_amount[index] if index < len(rain_amount) else None
            wind = max_wind[index] if index < len(max_wind) else None
            warning = None
            if code in (95, 96, 99):
                warning = "Thunderstorm risk"
            elif (chance is not None and chance >= 80) or (rain_mm is not None and rain_mm >= 20):
                warning = "Heavy rain possible"
            elif wind is not None and wind >= 50:
                warning = "Strong winds possible"
            forecast_list.append(
                {
                    "date": daily_dates[index],
                    "condition": weather_code_to_text(code),
                    "max_temp": high_temp[index] if index < len(high_temp) else None,
                    "min_temp": low_temp[index] if index < len(low_temp) else None,
                    "rain_chance": chance,
                    "warning": warning,
                }
            )

        weather_result = {
            "location": place_details["location"],
            "state": place_details.get("state"),
            "district": place_details.get("district"),
            "temperature": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "rainfall": current.get("precipitation"),
            "wind_speed": current.get("wind_speed_10m"),
            "condition": weather_code_to_text(current.get("weather_code")),
            "forecast": forecast_list,
        }
        app.logger.info(
            "Weather lookup succeeded: resolved_location=%s forecast_days=%s",
            weather_result["location"][:120],
            len(forecast_list),
        )
        return weather_result, None
    except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError) as error:
        response = getattr(error, "response", None)
        status_code = getattr(response, "status_code", None)
        app.logger.warning(
            "Weather lookup failed: location=%s error_type=%s http_status=%s",
            location[:120] if location else "(browser coordinates)",
            type(error).__name__,
            status_code or "n/a",
        )
        return None, (
            "Weather data is currently unavailable. "
            "The weather service could not be reached or returned invalid data; please try again later."
        )


def fertilizer_recommendation(crop_name, nitrogen, phosphorus, potassium, ph_value):
    crop_key = crop_name.lower().strip()
    crop_data = CROP_NEEDS.get(crop_key, {
        "nitrogen": 70,
        "phosphorus": 35,
        "potassium": 35,
        "ph": 6.0,
    })

    suggestions = []
    if nitrogen < crop_data["nitrogen"]:
        suggestions.append("Add nitrogen-rich fertilizer such as urea or ammonium sulfate.")
    if phosphorus < crop_data["phosphorus"]:
        suggestions.append("Use phosphate fertilizer to improve root growth.")
    if potassium < crop_data["potassium"]:
        suggestions.append("Use potassium fertilizer for healthy flowering and stress resistance.")
    if ph_value < crop_data["ph"]:
        suggestions.append("Soil pH is low. Add lime to improve the soil balance.")
    if ph_value > crop_data["ph"] + 0.8:
        suggestions.append("Soil pH is high. Use sulfur or organic compost to reduce pH.")

    if not suggestions:
        suggestions.append("Soil values are close to the crop need. Maintain regular nutrient monitoring.")

    reason = "This recommendation is based on general crop nutrition guidance for farming."
    return "; ".join(suggestions), reason


def irrigation_recommendation(crop_name, temperature, humidity, rainfall, forecast_list):
    crop_name = crop_name.title()
    rain_total = rainfall
    for item in forecast_list:
        if item.get("rain_chance", 0) > 60:
            rain_total += 20

    if rain_total > 100 or humidity > 75:
        irrigation_level = "Low irrigation"
        message = "Rain and moisture are enough. Use less irrigation."
    elif rain_total > 40 or temperature > 30:
        irrigation_level = "Moderate irrigation"
        message = "Use steady irrigation with careful monitoring."
    else:
        irrigation_level = "High irrigation"
        message = "The field is dry. Increase irrigation carefully and check soil moisture."

    return irrigation_level, message


def risk_information(crop_name, temperature, humidity, rainfall):
    crop_name = crop_name.title()
    risk = "Low risk"
    note = "Current field conditions look healthy. Continue regular monitoring."

    if temperature > 35 or rainfall < 30:
        risk = "Medium risk"
        note = "Heat stress or low rainfall may affect yield. Use irrigation and soil mulching."
    if temperature > 40 or rainfall < 15:
        risk = "High risk"
        note = "Very high temperature or low rainfall may reduce growth. Protect the crop quickly."
    if humidity > 85 and rainfall > 80:
        risk = "Disease risk"
        note = "High humidity and rainfall may increase fungal disease risk. Improve air flow and drainage."

    return risk, note


def profit_calculation(yield_kg, price_per_kg, total_cost):
    total_income = yield_kg * price_per_kg
    profit = total_income - total_cost
    return total_income, profit


def farming_assistant_answer(question):
    q = question.lower()

    if "fertilizer" in q:
        return "Use a fertilizer based on the crop type and soil test. Add nitrogen for leaf growth, phosphorus for roots, and potassium for stress resistance."
    if "irrigation" in q:
        return "Water the land based on rainfall, humidity, and crop stage. If rainfall is low and soil is dry, increase irrigation carefully."
    if "weather" in q:
        return "Check rainfall and temperature before field work. Heavy rain may delay sowing, while high temperature may increase water stress."
    if "soil" in q:
        return "Healthy soil should have balanced nutrients, good drainage, and a suitable pH level for the crop."
    if "pest" in q:
        return "Monitor plants often. Early detection is very important. Remove weak plants and use safe crop protection."
    if "yield" in q:
        return "Good seed quality, proper nutrients, pest control, and regular watering help improve yield."
    if "rice" in q:
        return "Rice needs water, good soil drainage, and balanced nitrogen. Keep the field moist during the growing stage."
    if "maize" in q or "corn" in q:
        return "Maize needs regular watering, moderate nitrogen, and enough sunlight. Watch for leaf stress during hot weather."
    if "cotton" in q:
        return "Cotton grows well with regular nutrition and proper drainage. Avoid water stress during flowering."
    if "banana" in q:
        return "Banana plants need plenty of water, potassium, and organic matter in the soil."
    if "mango" in q:
        return "Mango trees need sunlight, drainage, and good nutrient balance. Protect young plants from strong winds."
    return "For best results, keep checking soil health, weather, watering, and crop nutrition regularly."


def chatbot_reply(question):
    question_text = (question or "").lower()
    if not question_text:
        return "Please type your farm question."
    return farming_assistant_answer(question_text)


def extract_soil_report_values(report_text):
    text = (report_text or "").lower()
    values = {}
    patterns = {
        "nitrogen": [r"(?:n|nitrogen)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:kg/ha|kg ha|ppm|mg/kg|%)?"],
        "phosphorus": [r"(?:p|phosphorus)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:kg/ha|kg ha|ppm|mg/kg|%)?"],
        "potassium": [r"(?:k|potassium)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:kg/ha|kg ha|ppm|mg/kg|%)?"],
        "ph": [r"(?:ph|ph value|soil ph)\s*[:=]?\s*(\d+(?:\.\d+)?)"],
        "organic_carbon": [r"(?:organic carbon|oc)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:%|percent)?"],
    }

    for key, regex_list in patterns.items():
        for pattern in regex_list:
            match = re.search(pattern, text)
            if match:
                values[key] = float(match.group(1))
                break

    if values:
        return values
    return {}


@app.route("/")
def home():
    return render_template("index.html", translations=get_translations(), language=get_language())


@app.route("/about")
def about():
    return render_template("about.html", translations=get_translations(), language=get_language())


@app.route("/help")
def help_page():
    return render_template("help.html", translations=get_translations(), language=get_language())


@app.route("/language/<lang>")
def set_language(lang):
    if lang in LANGUAGES:
        session["language"] = lang
    return redirect(request.referrer or url_for("home"))


@app.route("/register", methods=["GET", "POST"])
def register():
    message = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            message = "Please enter username and password."
        else:
            connection = None
            try:
                connection = get_db_connection()
                cursor = connection.cursor()
                cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                result = cursor.fetchone()
                if result is not None:
                    message = "This username already exists. Please choose another one."
                else:
                    password_hash = generate_password_hash(password)
                    cursor.execute(
                        "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                        (username, email, password_hash),
                    )
                    connection.commit()
                    return redirect(url_for("login"))
            except mysql.connector.Error as error:
                print("Registration error:", error)
                message = "Database error. Please try again later."
            finally:
                if connection is not None and connection.is_connected():
                    connection.close()

    return render_template("register.html", message=message, translations=get_translations(), language=get_language())


@app.route("/login", methods=["GET", "POST"])
def login():
    message = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            message = "Please enter username and password."
        else:
            connection = None
            try:
                connection = get_db_connection()
                cursor = connection.cursor()
                cursor.execute("SELECT id, username, password_hash FROM users WHERE username = %s", (username,))
                account = cursor.fetchone()
                if account is not None:
                    user_id, stored_username, password_hash = account
                    if check_password_hash(password_hash, password):
                        session["user_id"] = user_id
                        session["username"] = stored_username
                        return redirect(url_for("dashboard"))
                    message = "Incorrect password."
                else:
                    message = "User not found. Please register first."
            except mysql.connector.Error as error:
                print("Login error:", error)
                message = "Database error. Please try again later."
            finally:
                if connection is not None and connection.is_connected():
                    connection.close()

    return render_template("login.html", message=message, translations=get_translations(), language=get_language())


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", translations=get_translations(), language=get_language())


@app.route("/crop-history")
@login_required
def crop_history():
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT created_at, crop_name, location, estimated_cost,
                   estimated_revenue, estimated_profit_loss
            FROM crop_history
            WHERE user_id = %s
            ORDER BY created_at DESC, id DESC
            """,
            (session["user_id"],),
        )
        history_rows = cursor.fetchall()
    except mysql.connector.Error as error:
        print("MySQL crop history read error:", error)
        return render_template(
            "error.html",
            message="Crop history is unavailable right now. Please try again later.",
            translations=get_translations(),
            language=get_language(),
        ), 500
    finally:
        if connection is not None and connection.is_connected():
            connection.close()

    return render_template(
        "dashboard.html",
        translations=get_translations(),
        language=get_language(),
        show_crop_history=True,
        history_rows=history_rows,
    )


@app.route("/predict", methods=["POST"])
def predict():
    try:
        nitrogen = float(request.form["nitrogen"])
        phosphorus = float(request.form["phosphorus"])
        potassium = float(request.form["potassium"])
        temperature = float(request.form["temperature"])
        humidity = float(request.form["humidity"])
        ph_value = float(request.form["ph_value"])
        rainfall = float(request.form["rainfall"])
    except ValueError:
        return render_template("error.html", message="Please enter valid numbers in all fields.", translations=get_translations(), language=get_language())

    values = [nitrogen, phosphorus, potassium, temperature, humidity, ph_value, rainfall]
    if any(value <= 0 for value in values):
        return render_template("error.html", message="Please enter positive values for all fields.", translations=get_translations(), language=get_language())

    feature_list = [nitrogen, phosphorus, potassium, temperature, humidity, ph_value, rainfall]
    prediction = model.predict([feature_list])[0]

    username = session.get("username", "guest")
    save_prediction_to_db(username, nitrogen, phosphorus, potassium, temperature, humidity, ph_value, rainfall, prediction)
    history_id = None
    user_id = session.get("user_id")
    if user_id is not None:
        try:
            history_id = save_crop_history(
                user_id, nitrogen, phosphorus, potassium, temperature, humidity,
                ph_value, rainfall, prediction,
            )
        except mysql.connector.Error as error:
            print("MySQL crop history save error:", error)
            return render_template(
                "error.html",
                message="Your recommendation was generated, but it could not be saved to crop history. Please try again later.",
                translations=get_translations(),
                language=get_language(),
            )

    message = "This crop is recommended for your soil and weather values."
    crop_advice_key = f"crop_advice_{str(prediction).strip().lower()}"
    crop_advice = get_translations().get(crop_advice_key, get_translations()["crop_advice_default"])
    return render_template(
        "result.html",
        crop=prediction,
        message=message,
        crop_advice=crop_advice,
        translations=get_translations(),
        result_labels=get_translations(),
        language=get_language(),
        history_id=history_id,
    )


@app.route("/recommendation-data", methods=["POST"])
def recommendation_data():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "message": "Location details are required."}), 400

    crop_value = data.get("crop", "")
    location_value = data.get("location", "")
    crop = crop_value.strip() if isinstance(crop_value, str) else ""
    location = location_value.strip() if isinstance(location_value, str) else ""
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    if not crop:
        return jsonify({"success": False, "message": "Recommended crop is missing."}), 400
    if (latitude is None) != (longitude is None):
        return jsonify({"success": False, "message": "Both location coordinates are required."}), 400
    if latitude is None and not location:
        return jsonify({"success": False, "message": "Please choose or enter a location."}), 400

    app.logger.info(
        "Recommendation data request received: crop=%s location=%s browser_coordinates=%s",
        crop[:80],
        location[:120] if location else "(not entered)",
        latitude is not None,
    )
    weather_result, weather_error = get_weather_for_location(location, latitude, longitude)
    if weather_result is None:
        app.logger.warning(
            "Recommendation weather unavailable for crop=%s location=%s",
            crop[:80],
            location[:120] if location else "(browser coordinates)",
        )
    location_details = weather_result or {}
    state = location_details.get("state")
    district = location_details.get("district")
    needs_market_location = (
        (
            os.environ.get("DATA_GOV_IN_API_KEY", "").strip()
            and (not state or not district)
        )
        or (
            os.environ.get("MARKET_API_URL", "").strip()
            and latitude is not None
            and not location_details.get("location")
            and not location
        )
    )
    if needs_market_location:
        try:
            location_details = resolve_market_location_details(location, latitude, longitude)
        except (requests.RequestException, ValueError, TypeError, KeyError):
            app.logger.warning("Could not resolve market state and district from the farmer location.")
            location_details = {}
    resolved_location = (
        (weather_result or {}).get("location")
        or location_details.get("location")
        or location
        or ("Detected location" if latitude is not None else "")
    )
    state = state or location_details.get("state")
    district = district or location_details.get("district")
    history_id_value = data.get("history_id")
    user_id = session.get("user_id")
    if history_id_value is not None and user_id is not None and resolved_location:
        if isinstance(history_id_value, bool):
            return jsonify({"success": False, "message": "Invalid crop history reference."}), 400
        try:
            history_id = int(history_id_value)
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "Invalid crop history reference."}), 400
        if history_id <= 0:
            return jsonify({"success": False, "message": "Invalid crop history reference."}), 400
        try:
            update_crop_history_location(history_id, user_id, resolved_location)
        except mysql.connector.Error as error:
            print("MySQL crop history location update error:", error)
            return jsonify(
                {"success": False, "message": "Location could not be saved to crop history."}
            ), 500

    market_data, market_error = get_market_price(crop, resolved_location, state=state, district=district)
    if market_data is None:
        app.logger.warning(
            "Recommendation market data unavailable for crop=%s location=%s",
            crop[:80],
            resolved_location[:120],
        )
    else:
        app.logger.info(
            "Recommendation market data received: crop=%s location=%s market=%s price_date=%s",
            crop[:80],
            resolved_location[:120],
            str(market_data.get("market_name", ""))[:100],
            str(market_data.get("price_date", ""))[:40],
        )

    return jsonify(
        {
            "success": True,
            "location": resolved_location,
            "weather": weather_result,
            "weather_error": weather_error,
            "market": market_data,
            "market_error": market_error,
        }
    )


@app.route("/location-detect", methods=["POST"])
def location_detect():
    data = request.get_json(silent=True) or request.form
    lat = data.get("lat") if isinstance(data, dict) else None
    lon = data.get("lon") if isinstance(data, dict) else None

    if lat is None or lon is None:
        return jsonify({"success": False, "message": "Location not available"}), 400

    try:
        lat_value = float(lat)
        lon_value = float(lon)
    except ValueError:
        return jsonify({"success": False, "message": "Invalid coordinates"}), 400

    location_name = reverse_geocode_coordinates(lat_value, lon_value)
    return jsonify({"success": True, "location": location_name, "display": f"Your Location: {location_name}"})


@app.route("/weather", methods=["GET", "POST"])
def weather():
    weather_result = None
    error_message = None
    detected_location = None

    location = request.form.get("location", "").strip() or request.args.get("location", "").strip()
    if request.method == "POST":
        if location:
            weather_result, error_message = get_weather_for_location(location)
            if error_message:
                weather_result = None
        else:
            error_message = "Please enter a location name or use your browser location."
    elif location:
        weather_result, error_message = get_weather_for_location(location)
        if error_message:
            weather_result = None

    if not weather_result and not error_message:
        error_message = "Weather data is currently unavailable."

    return render_template(
        "weather.html",
        weather_result=weather_result,
        error_message=error_message,
        detected_location=detected_location,
        translations=get_translations(),
        language=get_language(),
    )


@app.route("/forecast", methods=["GET", "POST"])
def forecast():
    forecast_result = None
    error_message = None

    if request.method == "POST":
        location = request.form.get("location", "").strip()
        if location:
            weather_result, error_message = get_weather_for_location(location)
            if weather_result is not None:
                forecast_result = weather_result.get("forecast", [])
        else:
            error_message = "Please enter a location name."

    return render_template(
        "forecast.html",
        forecast_result=forecast_result,
        error_message=error_message,
        translations=get_translations(),
        language=get_language(),
    )


@app.route("/fertilizer", methods=["GET", "POST"])
def fertilizer():
    recommendation = None
    reason = None
    if request.method == "POST":
        crop_name = request.form.get("crop_name", "").strip()
        nitrogen = float(request.form.get("nitrogen", 0))
        phosphorus = float(request.form.get("phosphorus", 0))
        potassium = float(request.form.get("potassium", 0))
        ph_value = float(request.form.get("ph_value", 0))
        recommendation, reason = fertilizer_recommendation(crop_name, nitrogen, phosphorus, potassium, ph_value)

    return render_template(
        "fertilizer.html",
        recommendation=recommendation,
        reason=reason,
        translations=get_translations(),
        language=get_language(),
    )


@app.route("/irrigation", methods=["GET", "POST"])
def irrigation():
    result = None
    message = None
    if request.method == "POST":
        crop_name = request.form.get("crop_name", "").strip()
        temperature = float(request.form.get("temperature", 25))
        humidity = float(request.form.get("humidity", 60))
        rainfall = float(request.form.get("rainfall", 50))
        forecast_list = [
            {"rain_chance": 50},
            {"rain_chance": 60},
            {"rain_chance": 30},
        ]
        result, message = irrigation_recommendation(crop_name, temperature, humidity, rainfall, forecast_list)

    return render_template(
        "irrigation.html",
        result=result,
        message=message,
        translations=get_translations(),
        language=get_language(),
    )


@app.route("/alternative-crops", methods=["GET", "POST"])
def alternative_crops():
    suggestions = []
    if request.method == "POST":
        crop_name = request.form.get("crop_name", "").strip().lower()
        suggestions = ALTERNATIVE_CROPS.get(crop_name, ["Rice", "Wheat", "Maize"])
    return render_template(
        "alternative_crops.html",
        suggestions=suggestions,
        translations=get_translations(),
        language=get_language(),
    )


@app.route("/crop-risk", methods=["GET", "POST"])
def crop_risk():
    risk = None
    note = None
    if request.method == "POST":
        crop_name = request.form.get("crop_name", "").strip()
        temperature = float(request.form.get("temperature", 25))
        humidity = float(request.form.get("humidity", 60))
        rainfall = float(request.form.get("rainfall", 50))
        risk, note = risk_information(crop_name, temperature, humidity, rainfall)

    return render_template(
        "risk.html",
        risk=risk,
        note=note,
        translations=get_translations(),
        language=get_language(),
    )


@app.route("/market", methods=["GET", "POST"])
def market():
    selected_crop = request.form.get("crop_name", "") or request.args.get("crop_name", "Rice")
    selected_location = request.form.get("location", "") or request.args.get("location", "")
    market_message = "Live market price is currently unavailable."
    market_data = None

    if request.method == "POST":
        if not selected_location:
            market_message = "Please enter a location or use your browser location to check market conditions."
        else:
            market_data, market_message = get_market_price(selected_crop, selected_location)
            if market_data is None and market_message is None:
                market_message = "Live market price is currently unavailable."

    return render_template(
        "market.html",
        market_crops=MARKET_CROPS,
        market_message=market_message,
        selected_crop=selected_crop,
        selected_location=selected_location,
        market_data=market_data,
        translations=get_translations(),
        language=get_language(),
    )


@app.route("/profit", methods=["GET", "POST"])
def profit():
    income = None
    profit_value = None
    if request.method == "POST":
        yield_kg = float(request.form.get("yield_kg", 0))
        price_per_kg = float(request.form.get("price_per_kg", 0))
        total_cost = float(request.form.get("total_cost", 0))
        income, profit_value = profit_calculation(yield_kg, price_per_kg, total_cost)

    return render_template(
        "profit.html",
        income=income,
        profit_value=profit_value,
        translations=get_translations(),
        language=get_language(),
    )


@app.route("/disease", methods=["GET", "POST"])
def disease():
    upload_error = None
    detection_status = None
    if request.method == "POST":
        if request.content_length and request.content_length > MAX_DISEASE_IMAGE_BYTES + 128 * 1024:
            upload_error = "The image is too large. Please upload an image smaller than 8 MB."
        else:
            uploaded_file = next(
                (
                    photo for photo in request.files.getlist("photo")
                    if photo and photo.filename
                ),
                None,
            )
            if uploaded_file is None:
                upload_error = "Please choose or take a crop/leaf photo first."
            else:
                extension = os.path.splitext(uploaded_file.filename)[1].lower()
                image_signatures = {
                    ".jpg": (b"\xff\xd8\xff", "image/jpeg"),
                    ".jpeg": (b"\xff\xd8\xff", "image/jpeg"),
                    ".png": (b"\x89PNG\r\n\x1a\n", "image/png"),
                    ".webp": (b"RIFF", "image/webp"),
                }
                image_info = image_signatures.get(extension)
                image_bytes = uploaded_file.stream.read(MAX_DISEASE_IMAGE_BYTES + 1)
                is_valid_image = bool(
                    image_info
                    and image_bytes
                    and len(image_bytes) <= MAX_DISEASE_IMAGE_BYTES
                    and image_bytes.startswith(image_info[0])
                    and (
                        extension != ".webp"
                        or image_bytes[8:12] == b"WEBP"
                    )
                    and uploaded_file.mimetype in ("", image_info[1])
                )
                if len(image_bytes) > MAX_DISEASE_IMAGE_BYTES:
                    upload_error = "The image is too large. Please upload an image smaller than 8 MB."
                elif not is_valid_image:
                    upload_error = "Please upload a valid JPEG, PNG, or WebP image."
                else:
                    detection_status = (
                        "The image was received, but no trained crop/leaf disease model is installed. "
                        "It was not analyzed, and no disease prediction or treatment guidance was generated."
                    )

    return render_template(
        "disease.html",
        upload_error=upload_error,
        detection_status=detection_status,
        translations=get_translations(),
        language=get_language(),
    )


@app.route("/chatbot", methods=["GET", "POST"])
def chatbot():
    conversation = session.get("chat_history", [])
    if request.method == "POST":
        user_question = request.form.get("question", "").strip()
        if user_question:
            conversation.append({"role": "user", "text": user_question})
            conversation.append({"role": "bot", "text": chatbot_reply(user_question)})
            session["chat_history"] = conversation
    return render_template(
        "chatbot.html",
        conversation=conversation,
        translations=get_translations(),
        language=get_language(),
    )


@app.route("/soil-report", methods=["GET", "POST"])
def soil_report():
    extracted_values = {}
    message = ""
    if request.method == "POST":
        uploaded_file = request.files.get("soil_report")
        if uploaded_file and uploaded_file.filename:
            file_data = uploaded_file.read()
            file_name = uploaded_file.filename.lower()
            report_text = ""

            if file_name.endswith(".txt") or file_name.endswith(".csv"):
                try:
                    report_text = file_data.decode("utf-8", errors="ignore")
                except Exception:
                    report_text = str(file_data)
            elif file_name.endswith(".pdf"):
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(io.BytesIO(file_data))
                    pages = []
                    for page in reader.pages:
                        pages.append(page.extract_text() or "")
                    report_text = "\n".join(pages)
                except Exception:
                    message = "This soil report could not be read. Please enter the values manually or get a laboratory soil test."
                    report_text = ""
            else:
                message = "Unsupported file type. Please upload a PDF, TXT or CSV Soil Report."

            extracted_values = extract_soil_report_values(report_text)
            if not extracted_values:
                message = "For accurate NPK values, use a laboratory soil test. The uploaded report could not be read clearly."
            else:
                message = "Values were extracted from the uploaded soil report. Please verify them before use."
        else:
            message = "Please upload a soil report file."

    return render_template(
        "soil_report.html",
        extracted_values=extracted_values,
        message=message,
        translations=get_translations(),
        language=get_language(),
    )


@app.route("/assistant", methods=["GET", "POST"])
def assistant():
    return redirect(url_for("chatbot"))


if __name__ == "__main__":
    app.run(debug=True)
