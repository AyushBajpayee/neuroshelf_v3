import streamlit as st
import sys
sys.path.append('..')
from app import get_db_connection
import pandas as pd

st.title("📦 SKU Monitor")
st.markdown("---")

try:
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all SKUs
    cursor.execute("SELECT id, sku_code, name, category FROM skus WHERE is_active = true ORDER BY name")
    skus = cursor.fetchall()

    sku_options = {f"{sku[1]} - {sku[2]}": sku[0] for sku in skus}
    selected_sku = st.selectbox("Select SKU", options=list(sku_options.keys()))

    if selected_sku:
        sku_id = sku_options[selected_sku]

        # Get inventory status
        st.subheader("Inventory Status")
        cursor.execute("""
            SELECT
                st.name as store,
                i.quantity,
                i.reorder_point,
                i.max_capacity,
                CASE
                    WHEN i.quantity <= i.reorder_point THEN 'Low'
                    WHEN i.quantity >= i.max_capacity * 0.8 THEN 'Excess'
                    ELSE 'Normal'
                END as status
            FROM inventory i
            JOIN stores st ON i.store_id = st.id
            WHERE i.sku_id = %s
        """, (sku_id,))
        inventory = cursor.fetchall()

        if inventory:
            df = pd.DataFrame(inventory, columns=["Store", "Quantity", "Reorder Point", "Max Capacity", "Status"])
            st.dataframe(df, use_container_width=True)

        # Get recent promotions
        st.subheader("Recent Promotions")
        cursor.execute("""
            SELECT
                promotion_code,
                status,
                promotional_price,
                actual_units_sold,
                expected_units_sold,
                actual_revenue,
                created_at
            FROM promotions
            WHERE sku_id = %s
            ORDER BY created_at DESC
            LIMIT 10
        """, (sku_id,))
        promos = cursor.fetchall()

        if promos:
            df = pd.DataFrame(promos, columns=["Code", "Status", "Price", "Units Sold", "Expected Units", "Revenue", "Created"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No promotions for this SKU yet")

    cursor.close()
    conn.close()

except Exception as e:
    st.error(f"Error: {e}")
