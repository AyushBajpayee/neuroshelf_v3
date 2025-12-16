"""
Weather Simulation Engine
Generates realistic weather data with controllable scenarios
"""

import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import config
import math
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json


class WeatherSimulator:
    def __init__(self):
        self.state = {}
        self.forced_scenarios = {}  # Manual scenario overrides
        self.db_config = {
            "host": os.getenv("DB_HOST", "postgres"),
            "port": int(os.getenv("DB_PORT", 5432)),
            "user": os.getenv("DB_USER", "pricing_user"),
            "password": os.getenv("DB_PASSWORD", "pricing_pass"),
            "database": os.getenv("DB_NAME", "pricing_intelligence"),
        }

    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

    def write_to_db(self, weather_data: Dict[str, Any]) -> bool:
        """Write weather data to external_factors table"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # Prepare factor_value JSON
            factor_value = {
                "temperature_celsius": weather_data["temperature_celsius"],
                "temperature_fahrenheit": weather_data["temperature_fahrenheit"],
                "condition": weather_data["condition"],
                "humidity_percent": weather_data["humidity_percent"],
                "season": weather_data["season"],
                "is_extreme": weather_data["is_extreme"]
            }

            # Determine intensity based on temperature extremes
            temp = weather_data["temperature_celsius"]
            if temp >= 35:
                intensity = 90
            elif temp >= 30:
                intensity = 75
            elif temp <= 0:
                intensity = 85
            elif temp <= 5:
                intensity = 70
            else:
                intensity = 50

            # Determine factor name based on condition and temperature
            if weather_data["is_extreme"]:
                if temp >= 35:
                    factor_name = "Extreme Heat"
                elif temp <= 0:
                    factor_name = "Extreme Cold"
                else:
                    factor_name = f"{weather_data['condition'].title()} Weather"
            else:
                factor_name = f"{weather_data['condition'].title()} Weather"

            # Insert into external_factors table
            query = """
                INSERT INTO external_factors
                (factor_type, factor_name, store_id, factor_value, intensity, start_date, end_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(query, (
                "weather",
                factor_name,
                weather_data.get("location_id"),
                json.dumps(factor_value),
                intensity,
                datetime.now(),
                datetime.now() + timedelta(hours=1)  # Weather data valid for 1 hour
            ))

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            print(f"Error writing weather data to DB: {e}")
            return False

    def get_current_season(self) -> str:
        """Determine current season based on date"""
        month = datetime.now().month
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "fall"

    def generate_temperature(
        self, location_id: int, season: str, forced_scenario: Optional[str] = None
    ) -> float:
        """Generate temperature with seasonal patterns and random variation"""

        if forced_scenario == "heatwave":
            return round(random.uniform(36, 42), 1)
        elif forced_scenario == "cold_snap":
            return round(random.uniform(-5, 5), 1)

        # Get base temperature for season
        season_config = config.SEASON_BASE_TEMPS[season]
        base_temp = season_config["base"]

        # Add daily variation (random walk)
        state_key = f"temp_{location_id}"
        if state_key in self.state:
            # Continue from last temperature with small change
            last_temp = self.state[state_key]
            variation = random.uniform(-2, 2)
            new_temp = last_temp + variation
        else:
            # Initialize with base + random variation
            new_temp = base_temp + random.uniform(
                -config.DAILY_VARIATION, config.DAILY_VARIATION
            )

        # Clamp to season min/max
        new_temp = max(season_config["min"], min(season_config["max"], new_temp))

        # Random extreme events
        if random.random() < config.EXTREME_EVENT_PROBABILITY:
            if season in ["summer", "spring"] and random.random() < 0.5:
                new_temp += random.uniform(5, 10)  # Heatwave
            elif season in ["winter", "fall"] and random.random() < 0.5:
                new_temp -= random.uniform(5, 10)  # Cold snap

        self.state[state_key] = new_temp
        return round(new_temp, 1)

    def determine_condition(self, temperature: float) -> str:
        """Determine weather condition based on temperature"""
        weights = config.get_condition_weights(temperature)

        # Random selection based on weights
        conditions = list(weights.keys())
        probabilities = list(weights.values())

        return random.choices(conditions, weights=probabilities, k=1)[0]

    def get_humidity(self, condition: str) -> int:
        """Get humidity based on weather condition"""
        humidity_range = config.HUMIDITY_RANGES.get(
            condition, (40, 60)
        )
        return random.randint(*humidity_range)

    def get_current_weather(self, location_id: int) -> Dict[str, Any]:
        """Get current weather for a location"""
        season = self.get_current_season()
        forced_scenario = self.forced_scenarios.get(location_id)

        temperature = self.generate_temperature(location_id, season, forced_scenario)
        condition = self.determine_condition(temperature)
        humidity = self.get_humidity(condition)

        weather_data = {
            "location_id": location_id,
            "temperature_celsius": temperature,
            "temperature_fahrenheit": round(temperature * 9 / 5 + 32, 1),
            "condition": condition,
            "humidity_percent": humidity,
            "season": season,
            "timestamp": datetime.now().isoformat(),
            "is_extreme": temperature >= config.HEATWAVE_THRESHOLD
            or temperature <= config.COLD_SNAP_THRESHOLD,
        }

        # Write to database
        self.write_to_db(weather_data)

        return weather_data

    def get_weather_forecast(
        self, location_id: int, hours_ahead: int
    ) -> list[Dict[str, Any]]:
        """Get weather forecast for specified hours ahead"""
        forecasts = []
        season = self.get_current_season()

        for hour in range(1, hours_ahead + 1):
            # Generate future weather with slight randomness
            forced_scenario = self.forced_scenarios.get(location_id)
            base_temp = self.generate_temperature(location_id, season, forced_scenario)

            # Add some forecast uncertainty
            temp_with_uncertainty = base_temp + random.uniform(-1, 1)
            condition = self.determine_condition(temp_with_uncertainty)
            humidity = self.get_humidity(condition)

            forecast_time = datetime.now() + timedelta(hours=hour)

            forecasts.append(
                {
                    "location_id": location_id,
                    "forecast_hour": hour,
                    "forecast_time": forecast_time.isoformat(),
                    "temperature_celsius": round(temp_with_uncertainty, 1),
                    "temperature_fahrenheit": round(
                        temp_with_uncertainty * 9 / 5 + 32, 1
                    ),
                    "condition": condition,
                    "humidity_percent": humidity,
                    "confidence": round(max(0.6, 1.0 - (hour * 0.02)), 2),
                }
            )

        return forecasts

    def set_weather_scenario(
        self, location_id: int, scenario: str, duration_hours: int = 24
    ) -> Dict[str, Any]:
        """Manually set weather scenario for testing"""
        valid_scenarios = [
            "heatwave",
            "cold_snap",
            "storm",
            "clear",
            "rainy_week",
            "normal",
        ]

        if scenario not in valid_scenarios:
            raise ValueError(f"Invalid scenario. Must be one of: {valid_scenarios}")

        if scenario == "normal":
            # Remove forced scenario
            self.forced_scenarios.pop(location_id, None)
        else:
            self.forced_scenarios[location_id] = scenario

        return {
            "location_id": location_id,
            "scenario": scenario,
            "duration_hours": duration_hours,
            "set_at": datetime.now().isoformat(),
            "status": "active" if scenario != "normal" else "cleared",
        }

    def get_state(self) -> Dict:
        """Get current simulator state"""
        return {
            "temperature_state": self.state,
            "forced_scenarios": self.forced_scenarios,
            "current_season": self.get_current_season(),
        }

    def load_state(self, state: Dict):
        """Load simulator state from storage"""
        self.state = state.get("temperature_state", {})
        self.forced_scenarios = state.get("forced_scenarios", {})


# Global simulator instance
weather_sim = WeatherSimulator()
