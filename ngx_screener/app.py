import streamlit as st
import pandas as pd
import os

# Configuration
DATA_PATH = "data/ngx daily price list.csv"

@st.cache_data
def load_data():
    try:
        if os.path.exists(DATA_PATH):
            df = pd.read_csv(DATA_PATH)
            return df
        else:
            st.error(f"Data file not found at: {DATA_PATH}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# Main app
st.title("📊 NGX Stock Screener")
st.markdown("*Nigerian Exchange Stock Analysis*")

# Load data
df = load_data()

if df.empty:
    st.warning("⚠️ No data available. Please check your data file.")
    st.stop()

# Show basic info
st.success(f"✅ Loaded {len(df)} records")
st.dataframe(df.head())

# Basic analysis
if 'COMPANY' in df.columns and '%CHANGE' in df.columns:
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🚀 Top Gainers")
        gainers = df.nlargest(10, '%CHANGE')[['COMPANY', 'CLOSE', '%CHANGE']]
        st.dataframe(gainers)
    
    with col2:
        st.markdown("### 📉 Top Losers") 
        losers = df.nsmallest(10, '%CHANGE')[['COMPANY', 'CLOSE', '%CHANGE']]
        st.dataframe(losers)
else:
    st.info("Basic analysis requires COMPANY and %CHANGE columns")
