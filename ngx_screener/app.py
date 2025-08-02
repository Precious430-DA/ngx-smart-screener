import streamlit as st
import pandas as pd
import numpy as np
import os

# Load CSV
DATA_PATH = "data/ngx daily price list.csv"

@st.cache_data
def load_data():
    if not os.path.exists(DATA_PATH):
        return pd.DataFrame()
    df = pd.read_csv(DATA_PATH)
    return df

df = load_data()
st.title("📊 NGX Daily Screener")

if df.empty:
    st.warning("No data found. Please run the parser first to create/update the CSV.")
    st.stop()

# Show basic data
st.dataframe(df)

# Top movers
if '%CHANGE' in df.columns:
    st.markdown("### 🚀 Top Gainers")
    top_gainers = df.sort_values('%CHANGE', ascending=False).head(10)
    st.dataframe(top_gainers)
