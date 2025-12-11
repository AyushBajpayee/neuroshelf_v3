import streamlit as st
import sys
sys.path.append('..')
from app import get_db_connection
import pandas as pd

st.set_page_config(page_title="Promotion Manager", page_icon="🎯", layout="wide")

st.title("🎯 Promotion Manager")
st.markdown("---")

try:
    conn = get_db_connection()
    cursor = conn.cursor()

    tab1, tab2, tab3 = st.tabs(["Active Promotions", "Completed Promotions", "Retracted Promotions"])

    with tab1:
        st.subheader("Active Promotions")
        cursor.execute("""
            SELECT
                p.id,
                p.promotion_code,
                s.name as sku,
                st.name as store,
                p.promotional_price,
                p.valid_from,
                p.valid_until,
                p.actual_units_sold,
                p.expected_units_sold,
                p.actual_revenue
            FROM promotions p
            JOIN skus s ON p.sku_id = s.id
            JOIN stores st ON p.store_id = st.id
            WHERE p.status = 'active'
            ORDER BY p.valid_until
        """)
        active = cursor.fetchall()

        if active:
            df = pd.DataFrame(active, columns=["ID", "Code", "SKU", "Store", "Price", "From", "Until", "Sold", "Expected", "Revenue"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No active promotions")

    with tab2:
        st.subheader("Completed Promotions")
        cursor.execute("""
            SELECT
                p.promotion_code,
                s.name as sku,
                p.actual_units_sold,
                p.expected_units_sold,
                p.actual_revenue,
                p.margin_percent,
                p.created_at
            FROM promotions p
            JOIN skus s ON p.sku_id = s.id
            WHERE p.status = 'completed'
            ORDER BY p.created_at DESC
            LIMIT 20
        """)
        completed = cursor.fetchall()

        if completed:
            df = pd.DataFrame(completed, columns=["Code", "SKU", "Units Sold", "Expected", "Revenue", "Margin %", "Created"])
            df["Performance %"] = (df["Units Sold"] / df["Expected"] * 100).round(1)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No completed promotions")

    with tab3:
        st.subheader("Retracted Promotions")
        cursor.execute("""
            SELECT
                p.promotion_code,
                s.name as sku,
                p.retraction_reason,
                p.actual_units_sold,
                p.expected_units_sold,
                p.retracted_at
            FROM promotions p
            JOIN skus s ON p.sku_id = s.id
            WHERE p.status = 'retracted'
            ORDER BY p.retracted_at DESC
            LIMIT 20
        """)
        retracted = cursor.fetchall()

        if retracted:
            df = pd.DataFrame(retracted, columns=["Code", "SKU", "Reason", "Units Sold", "Expected", "Retracted At"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No retracted promotions")

    cursor.close()
    conn.close()

except Exception as e:
    st.error(f"Error: {e}")
