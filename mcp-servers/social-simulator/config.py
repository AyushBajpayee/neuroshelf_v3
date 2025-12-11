"""
Social Media Trends Simulator Configuration
"""

# Trending Topics Pool
TRENDING_TOPICS = [
    # Food & Beverage
    {"name": "Ice Cream Challenge", "category": "food", "related_skus": ["ice cream", "frozen"]},
    {"name": "Summer BBQ Ideas", "category": "food", "related_skus": ["snacks", "beverages"]},
    {"name": "Healthy Eating Tips", "category": "lifestyle", "related_skus": ["dairy", "bakery"]},
    {"name": "Quick Breakfast Hacks", "category": "food", "related_skus": ["bread", "dairy"]},
    {"name": "Party Snack Recipes", "category": "food", "related_skus": ["snacks", "beverages"]},

    # Events & Activities
    {"name": "Weekend Picnic Plans", "category": "lifestyle", "related_skus": ["beverages", "snacks"]},
    {"name": "Movie Night Essentials", "category": "entertainment", "related_skus": ["snacks", "beverages"]},
    {"name": "Game Day Prep", "category": "sports", "related_skus": ["snacks", "beverages"]},

    # Seasonal
    {"name": "Beat The Heat", "category": "lifestyle", "related_skus": ["frozen", "beverages"]},
    {"name": "Comfort Food Favorites", "category": "food", "related_skus": ["bakery", "dairy"]},

    # Wellness
    {"name": "Hydration Challenge", "category": "health", "related_skus": ["beverages"]},
    {"name": "Protein Power", "category": "fitness", "related_skus": ["dairy", "snacks"]},
]

# Event Types
EVENT_TYPES = {
    "sports": {
        "examples": ["Football Game", "Baseball Match", "Basketball Tournament"],
        "attendance_range": (1000, 10000),
        "impact_categories": ["snacks", "beverages"],
    },
    "festival": {
        "examples": ["Music Festival", "Food Fest", "Art Fair"],
        "attendance_range": (3000, 20000),
        "impact_categories": ["snacks", "beverages", "frozen"],
    },
    "community": {
        "examples": ["Community Picnic", "Farmers Market", "Block Party"],
        "attendance_range": (500, 3000),
        "impact_categories": ["all"],
    },
    "concert": {
        "examples": ["Rock Concert", "Jazz Night", "Pop Show"],
        "attendance_range": (2000, 15000),
        "impact_categories": ["snacks", "beverages"],
    },
    "holiday": {
        "examples": ["Independence Day", "Memorial Day", "Labor Day"],
        "attendance_range": (5000, 50000),
        "impact_categories": ["all"],
    },
}

# Trend Parameters
TREND_INTENSITY_RANGE = (30, 95)  # 0-100 scale
TREND_DURATION_HOURS_RANGE = (6, 72)  # 6 hours to 3 days
TREND_DECAY_RATE = 0.85  # 15% decay per check (exponential)

# Event Parameters
EVENT_DURATION_HOURS_RANGE = (2, 48)
EVENT_ADVANCE_NOTICE_DAYS = (1, 14)  # Events scheduled 1-14 days ahead

# Generation Frequencies
NEW_TREND_PROBABILITY_DAILY = 0.3  # 30% chance of new trend per day
NEW_EVENT_PROBABILITY_WEEKLY = 0.6  # 60% chance of new event per week

# Sentiment Mapping
SENTIMENT_CATEGORIES = {
    "positive": (60, 95),
    "neutral": (40, 60),
    "negative": (10, 40),
}

# Platform Distribution
PLATFORMS = ["Twitter", "Instagram", "Facebook", "TikTok", "Reddit"]
