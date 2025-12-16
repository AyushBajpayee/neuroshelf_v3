"""
Competitor Pricing Simulation Engine
Simulates realistic competitor pricing behavior and strategies
"""

import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import config
import os
import psycopg2
from psycopg2.extras import RealDictCursor


class CompetitorSimulator:
    def __init__(self):
        self.state = {}
        self.forced_promotions = {}
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

    def get_base_price(self, sku_id: int) -> float:
        """Get base price for SKU from database"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("SELECT base_price FROM skus WHERE id = %s", (sku_id,))
            result = cursor.fetchone()

            cursor.close()
            conn.close()

            return float(result["base_price"]) if result else 5.99
        except Exception as e:
            print(f"Error getting base price: {e}")
            return 5.99  # Default fallback

    def generate_competitor_price(
        self, competitor_name: str, base_price: float, sku_id: int
    ) -> Dict[str, Any]:
        """Generate price for a competitor based on their strategy"""
        competitor_config = config.COMPETITORS.get(competitor_name)
        if not competitor_config:
            return {"price": base_price, "promotion": False}

        # Get price multiplier range
        min_mult, max_mult = competitor_config["price_multiplier_range"]
        price_multiplier = random.uniform(min_mult, max_mult)

        # Base price calculation
        competitor_price = base_price * price_multiplier

        # Check if promotion is active
        state_key = f"{competitor_name}_{sku_id}_promo"
        is_promotion = self.forced_promotions.get(state_key, False)

        # Random promotion chance if not forced
        if not is_promotion:
            promotion_chance = competitor_config["promotion_frequency"]

            # Weekend bonus
            if datetime.now().weekday() >= 5:  # Saturday or Sunday
                promotion_chance *= config.WEEKEND_PROMOTION_MULTIPLIER

            is_promotion = random.random() < promotion_chance

        # Apply promotion discount
        if is_promotion:
            discount = random.uniform(*config.PROMOTION_DISCOUNT_RANGE)
            competitor_price *= 1 - discount

        # Add small random variation (±2%)
        competitor_price *= random.uniform(0.98, 1.02)

        return {
            "competitor_name": competitor_name,
            "price": round(competitor_price, 2),
            "promotion": is_promotion,
            "strategy": competitor_config["strategy"],
        }

    def write_to_db(self, price_data: Dict[str, Any]) -> bool:
        """Write competitor price data to competitor_prices table"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            query = """
                INSERT INTO competitor_prices
                (competitor_name, sku_id, store_id, competitor_price, competitor_promotion, observed_date)
                VALUES (%s, %s, %s, %s, %s, %s)
            """

            cursor.execute(query, (
                price_data["competitor_name"],
                price_data["sku_id"],
                price_data["location_id"],
                price_data["price"],
                price_data["promotion"],
                datetime.now()
            ))

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            print(f"Error writing competitor price to DB: {e}")
            return False

    def get_competitor_prices(
        self, sku_id: int, location_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get current prices from all competitors for a SKU"""
        base_price = self.get_base_price(sku_id)
        prices = []

        for competitor_name in config.COMPETITORS.keys():
            price_data = self.generate_competitor_price(
                competitor_name, base_price, sku_id
            )
            price_data["sku_id"] = sku_id
            price_data["location_id"] = location_id
            price_data["timestamp"] = datetime.now().isoformat()

            # Write to database
            self.write_to_db(price_data)

            prices.append(price_data)

        return prices

    def get_competitor_history(
        self, sku_id: int, days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """Get historical competitor prices from database"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            query = """
                SELECT
                    competitor_name,
                    sku_id,
                    store_id AS location_id,
                    competitor_price AS price,
                    competitor_promotion AS promotion,
                    observed_date AS timestamp
                FROM competitor_prices
                WHERE sku_id = %s
                  AND observed_date >= NOW() - INTERVAL '%s days'
                ORDER BY observed_date DESC
            """

            cursor.execute(query, (sku_id, days_back))
            results = cursor.fetchall()

            cursor.close()
            conn.close()

            return [dict(row) for row in results]
        except Exception as e:
            print(f"Error getting competitor history: {e}")
            return []

    def trigger_competitor_promo(
        self, competitor_name: str, sku_id: int, discount_percent: float
    ) -> Dict[str, Any]:
        """Manually trigger a competitor promotion"""
        if competitor_name not in config.COMPETITORS:
            raise ValueError(f"Unknown competitor: {competitor_name}")

        if not (0 < discount_percent <= 50):
            raise ValueError("Discount must be between 0 and 50 percent")

        state_key = f"{competitor_name}_{sku_id}_promo"
        self.forced_promotions[state_key] = True

        base_price = self.get_base_price(sku_id)
        competitor_config = config.COMPETITORS[competitor_name]
        min_mult, max_mult = competitor_config["price_multiplier_range"]
        base_competitor_price = base_price * random.uniform(min_mult, max_mult)

        promo_price = base_competitor_price * (1 - discount_percent / 100)

        return {
            "competitor_name": competitor_name,
            "sku_id": sku_id,
            "original_price": round(base_competitor_price, 2),
            "promotional_price": round(promo_price, 2),
            "discount_percent": discount_percent,
            "triggered_at": datetime.now().isoformat(),
            "status": "active",
        }

    def end_competitor_promo(self, competitor_name: str, sku_id: int) -> Dict[str, Any]:
        """End a competitor promotion"""
        state_key = f"{competitor_name}_{sku_id}_promo"
        was_active = self.forced_promotions.pop(state_key, False)

        return {
            "competitor_name": competitor_name,
            "sku_id": sku_id,
            "was_active": was_active,
            "ended_at": datetime.now().isoformat(),
            "status": "ended",
        }

    def react_to_our_promotion(
        self, sku_id: int, our_price: float
    ) -> List[Dict[str, Any]]:
        """Simulate competitor reactions to our pricing changes"""
        reactions = []

        for competitor_name, competitor_config in config.COMPETITORS.items():
            # Check if this competitor will react
            if random.random() < competitor_config["reaction_probability"]:
                # Follower strategy - match or undercut
                if competitor_config["strategy"] == "follower":
                    new_price = our_price * random.uniform(0.95, 1.00)
                    reaction_type = "match_and_undercut"

                # Aggressive strategy - sometimes undercut aggressively
                elif competitor_config["strategy"] == "aggressive":
                    if random.random() < 0.3:  # 30% chance to respond
                        new_price = our_price * random.uniform(0.85, 0.95)
                        reaction_type = "aggressive_undercut"
                    else:
                        continue  # No reaction

                # Premium strategy - rarely reacts, maintains premium
                else:
                    continue  # Premium doesn't react

                reactions.append(
                    {
                        "competitor_name": competitor_name,
                        "sku_id": sku_id,
                        "our_price": our_price,
                        "competitor_new_price": round(new_price, 2),
                        "reaction_type": reaction_type,
                        "reaction_time_hours": competitor_config["reaction_speed_hours"],
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        return reactions

    def update_strategy(
        self, competitor_name: str, new_strategy: str
    ) -> Dict[str, Any]:
        """Update a competitor's strategy (for testing)"""
        if competitor_name not in config.COMPETITORS:
            raise ValueError(f"Unknown competitor: {competitor_name}")

        valid_strategies = ["aggressive", "premium", "follower"]
        if new_strategy not in valid_strategies:
            raise ValueError(
                f"Invalid strategy. Must be one of: {valid_strategies}"
            )

        # Update in-memory config
        old_strategy = config.COMPETITORS[competitor_name]["strategy"]
        config.COMPETITORS[competitor_name]["strategy"] = new_strategy

        # Adjust price multipliers based on new strategy
        if new_strategy == "aggressive":
            config.COMPETITORS[competitor_name]["price_multiplier_range"] = (0.80, 0.90)
        elif new_strategy == "premium":
            config.COMPETITORS[competitor_name]["price_multiplier_range"] = (1.10, 1.20)
        else:  # follower
            config.COMPETITORS[competitor_name]["price_multiplier_range"] = (0.95, 1.05)

        return {
            "competitor_name": competitor_name,
            "old_strategy": old_strategy,
            "new_strategy": new_strategy,
            "updated_at": datetime.now().isoformat(),
        }

    def get_state(self) -> Dict:
        """Get current simulator state"""
        return {
            "competitors": config.COMPETITORS,
            "forced_promotions": self.forced_promotions,
            "active_promotion_count": len(self.forced_promotions),
        }


# Global simulator instance
competitor_sim = CompetitorSimulator()
