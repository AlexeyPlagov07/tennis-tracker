import pandas as pd
import streamlit as st

from src.database.database import Database

st.set_page_config(page_title="Tennis Tracker", layout="wide")
st.title("Tennis Racket Price Tracker")

db = Database()
latest = pd.DataFrame(db.get_latest_prices())

if latest.empty:
    st.info("No data yet. Run `python run.py` to collect some prices first.")
else:
    st.subheader("Latest prices")
    st.dataframe(
        latest[["name", "brand", "source", "price", "in_stock", "scraped_at"]],
        use_container_width=True,
    )

    product_name = st.selectbox("View price history for:", latest["name"])
    product_id = int(latest.loc[latest["name"] == product_name, "id"].iloc[0])
    history = pd.DataFrame(db.get_price_history(product_id))

    if not history.empty:
        history["scraped_at"] = pd.to_datetime(history["scraped_at"])
        st.subheader(f"Price history \u2014 {product_name}")
        st.line_chart(history.set_index("scraped_at")["price"])
