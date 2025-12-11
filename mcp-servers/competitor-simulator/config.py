"""
Competitor Pricing Simulator Configuration
"""

# Competitor Strategies
COMPETITORS = {
    "Competitor A - MegaMart": {
        "strategy": "aggressive",
        "price_multiplier_range": (0.80, 0.90),  # 10-20% below market
        "promotion_frequency": 0.30,  # 30% chance weekly
        "reaction_speed_hours": 24,  # Reacts within 24 hours
        "reaction_probability": 0.15,  # 15% chance to react to our changes
    },
    "Competitor B - Premium Foods": {
        "strategy": "premium",
        "price_multiplier_range": (1.10, 1.20),  # 10-20% above market
        "promotion_frequency": 0.10,  # 10% chance weekly
        "reaction_speed_hours": 72,  # Slower to react
        "reaction_probability": 0.05,  # Rarely reacts
    },
    "Competitor C - QuickStop": {
        "strategy": "follower",
        "price_multiplier_range": (0.95, 1.05),  # Matches market
        "promotion_frequency": 0.20,  # 20% chance weekly
        "reaction_speed_hours": 12,  # Quick to react
        "reaction_probability": 0.40,  # 40% chance to match lowest competitor
    },
}

# Sale/Promotion Settings
PROMOTION_DISCOUNT_RANGE = (0.10, 0.30)  # 10-30% discount
PROMOTION_DURATION_HOURS = (4, 48)  # 4 to 48 hours

# Price Update Frequency
PRICE_UPDATE_INTERVAL_HOURS = 24  # Check and update prices daily

# Weekend/Holiday multipliers
WEEKEND_PROMOTION_MULTIPLIER = 2.0  # 2x more likely on weekends
HOLIDAY_PROMOTION_MULTIPLIER = 3.0  # 3x more likely on holidays
