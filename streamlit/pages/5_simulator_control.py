import streamlit as st
import httpx
import sys
sys.path.append('..')
from common import render_sidebar

render_sidebar(show_navigation=False, key_prefix="simulator_control")

st.title("🎮 Simulator Control Panel")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["🌤️ Weather", "🏪 Competitors", "📱 Social Trends"])

# Weather Simulator
with tab1:
    st.subheader("Weather Simulator")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Current Weather**")
        location_id = st.number_input("Location ID", min_value=1, max_value=5, value=1, key="weather_loc")

        if st.button("Get Current Weather"):
            try:
                response = httpx.get(f"http://mcp-weather:3001/weather/{location_id}", timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    st.json(data)
                else:
                    st.error("Failed to get weather data")
            except Exception as e:
                st.error(f"Error: {e}")

    with col2:
        st.write("**Set Weather Scenario**")
        scenario = st.selectbox(
            "Scenario",
            ["normal", "heatwave", "cold_snap", "storm", "rainy_week"],
            key="weather_scenario"
        )
        scenario_location = st.number_input("Location ID", min_value=1, max_value=5, value=1, key="scenario_loc")

        if st.button("Apply Scenario"):
            try:
                response = httpx.post(
                    f"http://mcp-weather:3001/scenario?location_id={scenario_location}&scenario={scenario}",
                    timeout=10.0
                )
                if response.status_code == 200:
                    st.success(f"✅ Scenario '{scenario}' applied to location {scenario_location}")
                else:
                    st.error("Failed to apply scenario")
            except Exception as e:
                st.error(f"Error: {e}")

# Competitor Simulator
with tab2:
    st.subheader("Competitor Pricing Simulator")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**View Competitor Prices**")
        sku_id = st.number_input("SKU ID", min_value=1, value=1, key="comp_sku")

        if st.button("Get Prices"):
            try:
                response = httpx.get(f"http://mcp-competitor:3002/prices/{sku_id}", timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    for comp in data:
                        promo_text = "🔥 PROMO" if comp.get("promotion") else ""
                        st.write(f"**{comp['competitor_name']}**: ${comp['price']:.2f} {promo_text}")
                else:
                    st.error("Failed to get competitor prices")
            except Exception as e:
                st.error(f"Error: {e}")

    with col2:
        st.write("**Trigger Competitor Promotion**")
        competitor = st.selectbox(
            "Competitor",
            ["Competitor A - MegaMart", "Competitor B - Premium Foods", "Competitor C - QuickStop"],
            key="comp_name"
        )
        promo_sku = st.number_input("SKU ID", min_value=1, value=1, key="promo_sku")
        discount = st.slider("Discount %", min_value=5, max_value=50, value=20, key="discount")

        if st.button("Trigger Promotion"):
            try:
                response = httpx.post(
                    f"http://mcp-competitor:3002/promotion/trigger?competitor_name={competitor}&sku_id={promo_sku}&discount_percent={discount}",
                    timeout=10.0
                )
                if response.status_code == 200:
                    st.success(f"✅ {competitor} promotion triggered: {discount}% off SKU {promo_sku}")
                else:
                    st.error("Failed to trigger promotion")
            except Exception as e:
                st.error(f"Error: {e}")

# Social Trends Simulator
with tab3:
    st.subheader("Social Media Trends Simulator")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Current Trending Topics**")

        if st.button("Get Trending"):
            try:
                response = httpx.get("http://mcp-social:3003/trending", timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    for trend in data[:5]:
                        st.write(f"**{trend['name']}** ({trend['category']})")
                        st.write(f"   Intensity: {trend['intensity']}/100, Sentiment: {trend['sentiment_score']}/100")
                else:
                    st.error("Failed to get trends")
            except Exception as e:
                st.error(f"Error: {e}")

    with col2:
        st.write("**Inject Viral Moment**")
        topic = st.text_input("Topic", value="Summer Ice Cream Sale", key="viral_topic")
        intensity = st.slider("Intensity", min_value=50, max_value=100, value=80, key="viral_intensity")

        if st.button("Inject Viral Moment"):
            try:
                response = httpx.post(
                    f"http://mcp-social:3003/viral?topic={topic}&intensity={intensity}",
                    timeout=10.0
                )
                if response.status_code == 200:
                    st.success(f"✅ Viral moment '{topic}' injected with intensity {intensity}")
                else:
                    st.error("Failed to inject viral moment")
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("---")
    st.write("**Upcoming Events**")
    if st.button("Get Events"):
        try:
            response = httpx.get("http://mcp-social:3003/events?days_ahead=7", timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                for event in data[:10]:
                    st.write(f"**{event['name']}** - {event['event_type']}")
                    st.write(f"   Location: {event['location_id']}, Attendance: {event['expected_attendance']}, In {event['days_until']} days")
            else:
                st.error("Failed to get events")
        except Exception as e:
            st.error(f"Error: {e}")
