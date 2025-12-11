"""
Weather Simulator Configuration
"""

# Base temperatures by season (Celsius)
SEASON_BASE_TEMPS = {
    "winter": {"min": 5, "max": 15, "base": 10},
    "spring": {"min": 15, "max": 25, "base": 20},
    "summer": {"min": 25, "max": 35, "base": 30},
    "fall": {"min": 10, "max": 20, "base": 15},
}

# Daily temperature variation range (±)
DAILY_VARIATION = 5

# Extreme weather event probabilities
EXTREME_EVENT_PROBABILITY = 0.15  # 15% chance per day

# Extreme weather thresholds
HEATWAVE_THRESHOLD = 35  # Celsius
COLD_SNAP_THRESHOLD = 5  # Celsius

# Weather conditions
WEATHER_CONDITIONS = [
    "sunny",
    "partly_cloudy",
    "cloudy",
    "rainy",
    "stormy",
    "snowy",
    "foggy",
]

# Condition probabilities by temperature
def get_condition_weights(temp_celsius):
    """Get weather condition probabilities based on temperature"""
    if temp_celsius >= 30:
        return {"sunny": 0.6, "partly_cloudy": 0.3, "cloudy": 0.1}
    elif temp_celsius >= 20:
        return {"sunny": 0.4, "partly_cloudy": 0.4, "cloudy": 0.15, "rainy": 0.05}
    elif temp_celsius >= 10:
        return {"partly_cloudy": 0.3, "cloudy": 0.4, "rainy": 0.25, "foggy": 0.05}
    else:
        return {"cloudy": 0.4, "rainy": 0.3, "snowy": 0.2, "foggy": 0.1}


# Humidity ranges by condition
HUMIDITY_RANGES = {
    "sunny": (30, 50),
    "partly_cloudy": (40, 60),
    "cloudy": (50, 70),
    "rainy": (70, 90),
    "stormy": (75, 95),
    "snowy": (60, 80),
    "foggy": (80, 95),
}
