"""
Social Media Trends Simulation Engine
Simulates trending topics, events, and social media buzz
"""

import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import config
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json


class SocialSimulator:
    def __init__(self):
        self.active_trends = []
        self.scheduled_events = []
        self.forced_virals = []
        self.db_config = {
            "host": os.getenv("DB_HOST", "postgres"),
            "port": int(os.getenv("DB_PORT", 5432)),
            "user": os.getenv("DB_USER", "pricing_user"),
            "password": os.getenv("DB_PASSWORD", "pricing_pass"),
            "database": os.getenv("DB_NAME", "pricing_intelligence"),
        }
        self._initialize_trends()
        self._initialize_events()

    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

    def write_trend_to_db(self, trend: Dict[str, Any]) -> bool:
        """Write trend data to external_factors table"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # Prepare factor_value JSON
            factor_value = {
                "platform": trend["platform"],
                "category": trend["category"],
                "sentiment_score": trend["sentiment_score"],
                "sentiment_type": trend["sentiment_type"],
                "mentions": trend["mentions"],
                "related_skus": trend["related_skus"],
                "is_viral": trend["is_viral"]
            }

            query = """
                INSERT INTO external_factors
                (factor_type, factor_name, store_id, factor_value, intensity, start_date, end_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(query, (
                "trend",
                trend["name"],
                None,  # Trends are not store-specific
                json.dumps(factor_value),
                trend["intensity"],
                trend["start_time"],
                trend["end_time"]
            ))

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            print(f"Error writing trend to DB: {e}")
            return False

    def write_event_to_db(self, event: Dict[str, Any]) -> bool:
        """Write event data to external_factors table"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # Prepare factor_value JSON
            factor_value = {
                "event_type": event["event_type"],
                "expected_attendance": event["expected_attendance"],
                "impact_categories": event["impact_categories"],
                "location_id": event["location_id"]
            }

            # Calculate intensity based on attendance
            attendance = event["expected_attendance"]
            if attendance >= 5000:
                intensity = 85
            elif attendance >= 2000:
                intensity = 70
            elif attendance >= 1000:
                intensity = 60
            else:
                intensity = 50

            query = """
                INSERT INTO external_factors
                (factor_type, factor_name, store_id, factor_value, intensity, start_date, end_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(query, (
                "event",
                event["name"],
                event["location_id"],
                json.dumps(factor_value),
                intensity,
                event["start_time"],
                event["end_time"]
            ))

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            print(f"Error writing event to DB: {e}")
            return False

    def _initialize_trends(self):
        """Initialize with some active trends"""
        # Start with 2-3 random trends
        num_initial_trends = random.randint(2, 3)
        for _ in range(num_initial_trends):
            self._generate_new_trend()

    def _initialize_events(self):
        """Initialize with some scheduled events"""
        # Create 5-7 upcoming events
        num_initial_events = random.randint(5, 7)
        for _ in range(num_initial_events):
            self._generate_new_event()

    def _generate_new_trend(self) -> Dict[str, Any]:
        """Generate a new trending topic"""
        topic = random.choice(config.TRENDING_TOPICS)
        intensity = random.randint(*config.TREND_INTENSITY_RANGE)
        duration_hours = random.randint(*config.TREND_DURATION_HOURS_RANGE)
        platform = random.choice(config.PLATFORMS)

        # Determine sentiment
        sentiment_type = random.choices(
            ["positive", "neutral", "negative"], weights=[0.6, 0.3, 0.1], k=1
        )[0]
        sentiment_range = config.SENTIMENT_CATEGORIES[sentiment_type]
        sentiment_score = random.randint(*sentiment_range)

        # Mentions count based on intensity
        mentions = int((intensity / 100) * random.randint(5000, 50000))

        trend = {
            "id": f"trend_{datetime.now().timestamp()}_{random.randint(1000, 9999)}",
            "name": topic["name"],
            "category": topic["category"],
            "related_skus": topic["related_skus"],
            "platform": platform,
            "intensity": intensity,
            "sentiment_score": sentiment_score,
            "sentiment_type": sentiment_type,
            "mentions": mentions,
            "start_time": datetime.now(),
            "end_time": datetime.now() + timedelta(hours=duration_hours),
            "is_viral": False,
        }

        self.active_trends.append(trend)

        # Write to database
        self.write_trend_to_db(trend)

        return trend

    def _generate_new_event(self, location_id: Optional[int] = None) -> Dict[str, Any]:
        """Generate a new scheduled event"""
        event_type = random.choice(list(config.EVENT_TYPES.keys()))
        event_config = config.EVENT_TYPES[event_type]

        event_name = random.choice(event_config["examples"])
        attendance = random.randint(*event_config["attendance_range"])
        duration_hours = random.randint(*config.EVENT_DURATION_HOURS_RANGE)
        days_ahead = random.randint(*config.EVENT_ADVANCE_NOTICE_DAYS)

        start_time = datetime.now() + timedelta(days=days_ahead)
        end_time = start_time + timedelta(hours=duration_hours)

        # Random location if not specified
        if location_id is None:
            location_id = random.randint(1, 5)

        event = {
            "id": f"event_{datetime.now().timestamp()}_{random.randint(1000, 9999)}",
            "name": event_name,
            "event_type": event_type,
            "location_id": location_id,
            "expected_attendance": attendance,
            "impact_categories": event_config["impact_categories"],
            "start_time": start_time,
            "end_time": end_time,
            "created_at": datetime.now(),
        }

        self.scheduled_events.append(event)

        # Write to database
        self.write_event_to_db(event)

        return event

    def get_trending_topics(
        self, location_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get currently trending topics"""
        now = datetime.now()

        # Update trends - remove expired, decay intensity
        active = []
        for trend in self.active_trends:
            if now < trend["end_time"]:
                # Apply decay
                hours_elapsed = (now - trend["start_time"]).total_seconds() / 3600
                decay_factor = config.TREND_DECAY_RATE ** (hours_elapsed / 24)
                trend["current_intensity"] = max(
                    10, int(trend["intensity"] * decay_factor)
                )
                active.append(trend)

        self.active_trends = active

        # Maybe generate new trend
        if random.random() < (config.NEW_TREND_PROBABILITY_DAILY / 24):
            self._generate_new_trend()

        # Format for output
        return [
            {
                "name": t["name"],
                "category": t["category"],
                "related_skus": t["related_skus"],
                "platform": t["platform"],
                "intensity": t.get("current_intensity", t["intensity"]),
                "sentiment_score": t["sentiment_score"],
                "sentiment_type": t["sentiment_type"],
                "mentions": t["mentions"],
                "is_viral": t["is_viral"],
                "time_remaining_hours": round(
                    (t["end_time"] - now).total_seconds() / 3600, 1
                ),
            }
            for t in self.active_trends
        ]

    def get_event_calendar(
        self, location_id: Optional[int] = None, days_ahead: int = 7
    ) -> List[Dict[str, Any]]:
        """Get upcoming events"""
        now = datetime.now()
        cutoff = now + timedelta(days=days_ahead)

        # Filter events
        upcoming = [
            e
            for e in self.scheduled_events
            if e["start_time"] <= cutoff and e["start_time"] >= now
        ]

        # Filter by location if specified
        if location_id:
            upcoming = [e for e in upcoming if e["location_id"] == location_id]

        # Maybe generate new event
        if random.random() < (config.NEW_EVENT_PROBABILITY_WEEKLY / (7 * 24)):
            self._generate_new_event(location_id)

        # Format for output
        return [
            {
                "name": e["name"],
                "event_type": e["event_type"],
                "location_id": e["location_id"],
                "expected_attendance": e["expected_attendance"],
                "impact_categories": e["impact_categories"],
                "start_time": e["start_time"].isoformat(),
                "end_time": e["end_time"].isoformat(),
                "days_until": (e["start_time"] - now).days,
                "hours_until": round((e["start_time"] - now).total_seconds() / 3600, 1),
            }
            for e in sorted(upcoming, key=lambda x: x["start_time"])
        ]

    def check_sku_sentiment(self, sku_category: str) -> Dict[str, Any]:
        """Check sentiment/buzz for a SKU category"""
        relevant_trends = [
            t
            for t in self.active_trends
            if sku_category.lower() in [s.lower() for s in t["related_skus"]]
        ]

        if not relevant_trends:
            return {
                "sku_category": sku_category,
                "has_buzz": False,
                "overall_sentiment": 50,
                "trending_topics": [],
            }

        # Aggregate sentiment
        total_intensity = sum(
            t.get("current_intensity", t["intensity"]) for t in relevant_trends
        )
        weighted_sentiment = sum(
            t["sentiment_score"] * t.get("current_intensity", t["intensity"])
            for t in relevant_trends
        )
        overall_sentiment = (
            int(weighted_sentiment / total_intensity) if total_intensity > 0 else 50
        )

        return {
            "sku_category": sku_category,
            "has_buzz": True,
            "overall_sentiment": overall_sentiment,
            "trending_topic_count": len(relevant_trends),
            "trending_topics": [t["name"] for t in relevant_trends],
            "peak_intensity": max(
                t.get("current_intensity", t["intensity"]) for t in relevant_trends
            ),
        }

    def inject_viral_moment(self, topic: str, intensity: int) -> Dict[str, Any]:
        """Manually inject a viral trending topic"""
        if not (50 <= intensity <= 100):
            raise ValueError("Viral moment intensity must be between 50 and 100")

        # Create high-impact trend
        viral_trend = {
            "id": f"viral_{datetime.now().timestamp()}_{random.randint(1000, 9999)}",
            "name": topic,
            "category": "viral",
            "related_skus": ["all"],
            "platform": random.choice(config.PLATFORMS),
            "intensity": intensity,
            "sentiment_score": random.randint(70, 95),
            "sentiment_type": "positive",
            "mentions": int((intensity / 100) * random.randint(50000, 200000)),
            "start_time": datetime.now(),
            "end_time": datetime.now() + timedelta(hours=48),
            "is_viral": True,
        }

        self.active_trends.append(viral_trend)
        self.forced_virals.append(viral_trend["id"])

        # Write to database
        self.write_trend_to_db(viral_trend)

        return {
            "topic": topic,
            "intensity": intensity,
            "mentions": viral_trend["mentions"],
            "platform": viral_trend["platform"],
            "injected_at": datetime.now().isoformat(),
            "status": "active",
        }

    def create_event(
        self,
        event_name: str,
        event_type: str,
        location_id: int,
        start_time: str,
        attendance: int,
    ) -> Dict[str, Any]:
        """Manually create an event"""
        if event_type not in config.EVENT_TYPES:
            raise ValueError(
                f"Invalid event_type. Must be one of: {list(config.EVENT_TYPES.keys())}"
            )

        event_config = config.EVENT_TYPES[event_type]
        start_dt = datetime.fromisoformat(start_time)
        end_dt = start_dt + timedelta(hours=random.randint(2, 6))

        event = {
            "id": f"custom_{datetime.now().timestamp()}_{random.randint(1000, 9999)}",
            "name": event_name,
            "event_type": event_type,
            "location_id": location_id,
            "expected_attendance": attendance,
            "impact_categories": event_config["impact_categories"],
            "start_time": start_dt,
            "end_time": end_dt,
            "created_at": datetime.now(),
        }

        self.scheduled_events.append(event)

        # Write to database
        self.write_event_to_db(event)

        return {
            "event_name": event_name,
            "event_type": event_type,
            "location_id": location_id,
            "start_time": start_dt.isoformat(),
            "created_at": datetime.now().isoformat(),
            "status": "scheduled",
        }

    def get_state(self) -> Dict:
        """Get current simulator state"""
        return {
            "active_trends_count": len(self.active_trends),
            "scheduled_events_count": len(self.scheduled_events),
            "viral_moments_count": len(self.forced_virals),
            "trending_topics": [t["name"] for t in self.active_trends],
            "upcoming_events": [
                e["name"] for e in self.scheduled_events[:5]
            ],  # Next 5
        }


# Global simulator instance
social_sim = SocialSimulator()
