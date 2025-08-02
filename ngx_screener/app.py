import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# Load CSV
DATA_PATH = "data/ngx daily price list.csv"

@st.cache_data
def load_data():
    if not os.path.exists(DATA_PATH):
        return pd.DataFrame()
    df = pd.read_csv(DATA_PATH)
    
    # Debug: Show column names
    st.write("Debug - CSV Columns:", df.columns.tolist())
    st.write("Debug - First few rows:")
    st.write(df.head())
    
    if 'DATE' in df.columns:
        df['DATE'] = pd.to_datetime(df['DATE'])
    
    # Check if COMPANY column exists, if not, find the correct column name
    if 'COMPANY' not in df.columns:
        st.error(f"Expected 'COMPANY' column not found. Available columns: {df.columns.tolist()}")
        return pd.DataFrame()
    
    return df.sort_values(['COMPANY', 'DATE'])

def calculate_technical_indicators(df):
    """Calculate technical indicators for each stock"""
    results = []
    
    for company in df['COMPANY'].unique():
        company_data = df[df['COMPANY'] == company].sort_values('DATE')
        
        if len(company_data) < 2:
            continue
            
        latest = company_data.iloc[-1]
        previous = company_data.iloc[-2] if len(company_data) > 1 else latest
        
        # Price momentum indicators
        price_change_1d = ((latest['CLOSE'] - previous['CLOSE']) / previous['CLOSE']) * 100
        
        # Volume analysis
        avg_volume = company_data['VOLUME'].mean()
        volume_surge = (latest['VOLUME'] / avg_volume) if avg_volume > 0 else 0
        
        # Volatility (using HIGH-LOW range)
        volatility = ((latest['HIGH'] - latest['LOW']) / latest['CLOSE']) * 100
        
        # Support/Resistance levels
        recent_data = company_data.tail(min(5, len(company_data)))
        support_level = recent_data['LOW'].min()
        resistance_level = recent_data['HIGH'].max()
        
        # Price position relative to range
        price_position = ((latest['CLOSE'] - support_level) / (resistance_level - support_level)) * 100 if resistance_level != support_level else 50
        
        # Trend strength
        if len(company_data) >= 3:
            prices = company_data['CLOSE'].tail(3).values
            trend_strength = (prices[-1] - prices[0]) / prices[0] * 100
        else:
            trend_strength = price_change_1d
        
        results.append({
            'COMPANY': company,
            'DATE': latest['DATE'],
            'CLOSE': latest['CLOSE'],
            'OPEN': latest['OPEN'],
            'HIGH': latest['HIGH'],
            'LOW': latest['LOW'],
            'VOLUME': latest['VOLUME'],
            'VALUE': latest['VALUE'],
            '%CHANGE': latest['%CHANGE'],
            'PRICE_CHANGE_1D': price_change_1d,
            'VOLUME_SURGE': volume_surge,
            'VOLATILITY': volatility,
            'SUPPORT': support_level,
            'RESISTANCE': resistance_level,
            'PRICE_POSITION': price_position,
            'TREND_STRENGTH': trend_strength,
            'AVG_VOLUME': avg_volume
        })
    
    return pd.DataFrame(results)

def weekly_momentum_strategy(df):
    """High-frequency momentum strategy for weekly cashouts"""
    screened = df[
        (df['VOLUME_SURGE'] >= 1.5) &  # Volume 50% above average
        (df['%CHANGE'] > 0) &  # Positive momentum
        (df['TREND_STRENGTH'] > 2) &  # Strong uptrend
        (df['PRICE_POSITION'] > 30) &  # Not at bottom of range
        (df['VOLATILITY'] < 15) &  # Not too volatile
        (df['CLOSE'] > 1.0)  # Avoid penny stocks
    ].copy()
    
    # Score calculation for weekly plays
    screened['WEEKLY_SCORE'] = (
        screened['%CHANGE'] * 0.3 +
        screened['VOLUME_SURGE'] * 0.3 +
        screened['TREND_STRENGTH'] * 0.2 +
        (100 - screened['PRICE_POSITION']) * 0.1 +  # Favor stocks with room to grow
        (20 - screened['VOLATILITY']) * 0.1
    )
    
    return screened.sort_values('WEEKLY_SCORE', ascending=False)

def monthly_growth_strategy(df):
    """Value growth strategy for monthly cashouts"""
    screened = df[
        (df['CLOSE'] >= 5) &  # Established stocks
        (df['TREND_STRENGTH'] > 0) &  # Positive trend
        (df['VOLUME'] > df['AVG_VOLUME'] * 0.8) &  # Decent liquidity
        (df['PRICE_POSITION'] < 80) &  # Not overbought
        (df['VOLATILITY'] < 20)  # Reasonable volatility
    ].copy()
    
    # Score for monthly holds
    screened['MONTHLY_SCORE'] = (
        screened['TREND_STRENGTH'] * 0.4 +
        screened['%CHANGE'] * 0.2 +
        (100 - screened['PRICE_POSITION']) * 0.2 +  # Value potential
        screened['VOLUME_SURGE'] * 0.1 +
        (25 - screened['VOLATILITY']) * 0.1
    )
    
    return screened.sort_values('MONTHLY_SCORE', ascending=False)

def breakout_strategy(df):
    """Breakout strategy for explosive moves"""
    screened = df[
        (df['PRICE_POSITION'] > 85) &  # Near resistance
        (df['VOLUME_SURGE'] >= 2.0) &  # High volume
        (df['%CHANGE'] > 3) &  # Strong move
        (df['CLOSE'] > 2.0)  # Avoid micro-caps
    ].copy()
    
    screened['BREAKOUT_SCORE'] = (
        screened['PRICE_POSITION'] * 0.3 +
        screened['VOLUME_SURGE'] * 0.3 +
        screened['%CHANGE'] * 0.4
    )
    
    return screened.sort_values('BREAKOUT_SCORE', ascending=False)

def value_recovery_strategy(df):
    """Oversold recovery plays"""
    screened = df[
        (df['PRICE_POSITION'] < 25) &  # Near support
        (df['%CHANGE'] > -2) &  # Not crashing
        (df['VOLUME_SURGE'] >= 1.2) &  # Some interest
        (df['CLOSE'] >= 1.0) &  # Not penny stocks
        (df['TREND_STRENGTH'] > -5)  # Not in severe downtrend
    ].copy()
    
    screened['RECOVERY_SCORE'] = (
        (30 - screened['PRICE_POSITION']) * 0.4 +  # How oversold
        screened['VOLUME_SURGE'] * 0.3 +
        (screened['%CHANGE'] + 5) * 0.3  # Recent stability
    )
    
    return screened.sort_values('RECOVERY_SCORE', ascending=False)

# Streamlit App
st.set_page_config(page_title="NGX Smart Screener", page_icon="💰", layout="wide")

df = load_data()
st.title("💰 NGX Smart Stock Screener - Make Money Weekly & Monthly")

if df.empty:
    st.error("❌ No data found. Please run the parser first to create/update the CSV.")
    st.stop()

# Calculate indicators
with st.spinner("🔍 Analyzing stocks..."):
    analyzed_df = calculate_technical_indicators(df)

if analyzed_df.empty:
    st.error("❌ Not enough data for analysis. Need at least 2 days of data.")
    st.stop()

# Sidebar
st.sidebar.header("💡 Strategy Selection")
strategy = st.sidebar.selectbox(
    "Choose your money-making strategy:",
    ["🚀 Weekly Momentum (Quick Profits)", 
     "📈 Monthly Growth (Steady Gains)", 
     "💥 Breakout Hunter (Explosive Moves)",
     "🔄 Value Recovery (Oversold Bounce)",
     "📊 All Strategies Overview"]
)

st.sidebar.markdown("---")
max_results = st.sidebar.slider("Max stocks to show", 5, 20, 10)

# Main content
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📅 Latest Date", analyzed_df['DATE'].max().strftime('%Y-%m-%d'))
with col2:
    st.metric("📊 Stocks Analyzed", len(analyzed_df))
with col3:
    avg_change = analyzed_df['%CHANGE'].mean()
    st.metric("📈 Market Avg Change", f"{avg_change:.2f}%")
with col4:
    top_performer = analyzed_df.loc[analyzed_df['%CHANGE'].idxmax(), 'COMPANY']
    st.metric("🏆 Top Performer", top_performer)

# Strategy Implementation
if strategy == "🚀 Weekly Momentum (Quick Profits)":
    st.markdown("## 🚀 Weekly Momentum Strategy")
    st.markdown("**Target: 5-15% profits in 3-7 days**")
    
    weekly_picks = weekly_momentum_strategy(analyzed_df).head(max_results)
    
    if not weekly_picks.empty:
        st.markdown("### 💎 Top Weekly Picks")
        
        display_cols = ['COMPANY', 'CLOSE', '%CHANGE', 'WEEKLY_SCORE', 'VOLUME_SURGE', 'TREND_STRENGTH']
        styled_df = weekly_picks[display_cols].copy()
        styled_df['WEEKLY_SCORE'] = styled_df['WEEKLY_SCORE'].round(2)
        styled_df['VOLUME_SURGE'] = styled_df['VOLUME_SURGE'].round(2)
        styled_df['TREND_STRENGTH'] = styled_df['TREND_STRENGTH'].round(2)
        
        st.dataframe(styled_df, use_container_width=True)
        
        # Top 3 detailed analysis
        st.markdown("### 🎯 Detailed Analysis - Top 3 Picks")
        for i, (_, stock) in enumerate(weekly_picks.head(3).iterrows()):
            with st.expander(f"#{i+1} {stock['COMPANY']} - ₦{stock['CLOSE']:.2f}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Current Price:** ₦{stock['CLOSE']:.2f}")
                    st.write(f"**Daily Change:** {stock['%CHANGE']:.2f}%")
                    st.write(f"**Weekly Score:** {stock['WEEKLY_SCORE']:.2f}")
                    st.write(f"**Target (7 days):** ₦{stock['CLOSE'] * 1.08:.2f}")
                with col2:
                    st.write(f"**Volume Surge:** {stock['VOLUME_SURGE']:.1f}x")
                    st.write(f"**Trend Strength:** {stock['TREND_STRENGTH']:.1f}%")
                    st.write(f"**Support Level:** ₦{stock['SUPPORT']:.2f}")
                    st.write(f"**Risk Level:** {'Low' if stock['VOLATILITY'] < 10 else 'Medium'}")
    else:
        st.warning("⚠️ No stocks meet weekly momentum criteria today. Check tomorrow!")

elif strategy == "📈 Monthly Growth (Steady Gains)":
    st.markdown("## 📈 Monthly Growth Strategy")
    st.markdown("**Target: 15-40% profits in 20-30 days**")
    
    monthly_picks = monthly_growth_strategy(analyzed_df).head(max_results)
    
    if not monthly_picks.empty:
        st.markdown("### 🏦 Top Monthly Holdings")
        
        display_cols = ['COMPANY', 'CLOSE', '%CHANGE', 'MONTHLY_SCORE', 'TREND_STRENGTH', 'PRICE_POSITION']
        styled_df = monthly_picks[display_cols].copy()
        styled_df['MONTHLY_SCORE'] = styled_df['MONTHLY_SCORE'].round(2)
        styled_df['TREND_STRENGTH'] = styled_df['TREND_STRENGTH'].round(2)
        styled_df['PRICE_POSITION'] = styled_df['PRICE_POSITION'].round(1)
        
        st.dataframe(styled_df, use_container_width=True)
        
        # Portfolio allocation suggestion
        st.markdown("### 💼 Suggested Portfolio Allocation")
        total_score = monthly_picks['MONTHLY_SCORE'].sum()
        for i, (_, stock) in enumerate(monthly_picks.head(5).iterrows()):
            allocation = (stock['MONTHLY_SCORE'] / total_score) * 100
            st.write(f"**{stock['COMPANY']}:** {allocation:.1f}% - ₦{stock['CLOSE']:.2f}")

elif strategy == "💥 Breakout Hunter (Explosive Moves)":
    st.markdown("## 💥 Breakout Hunter Strategy")
    st.markdown("**Target: 20-50% profits in 1-10 days**")
    
    breakout_picks = breakout_strategy(analyzed_df).head(max_results)
    
    if not breakout_picks.empty:
        st.markdown("### 🚨 Breakout Alerts")
        
        for _, stock in breakout_picks.head(5).iterrows():
            st.success(f"🚨 **{stock['COMPANY']}** breaking out! Price: ₦{stock['CLOSE']:.2f} (+{stock['%CHANGE']:.1f}%) Volume: {stock['VOLUME_SURGE']:.1f}x")
        
        display_cols = ['COMPANY', 'CLOSE', '%CHANGE', 'BREAKOUT_SCORE', 'VOLUME_SURGE', 'PRICE_POSITION']
        styled_df = breakout_picks[display_cols].copy()
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.warning("⚠️ No breakouts detected today. Keep watching!")

elif strategy == "🔄 Value Recovery (Oversold Bounce)":
    st.markdown("## 🔄 Value Recovery Strategy")
    st.markdown("**Target: 10-25% profits in 5-15 days**")
    
    recovery_picks = value_recovery_strategy(analyzed_df).head(max_results)
    
    if not recovery_picks.empty:
        st.markdown("### 🔄 Oversold Recovery Candidates")
        
        display_cols = ['COMPANY', 'CLOSE', '%CHANGE', 'RECOVERY_SCORE', 'PRICE_POSITION', 'SUPPORT']
        styled_df = recovery_picks[display_cols].copy()
        st.dataframe(styled_df, use_container_width=True)
        
        st.markdown("### 💡 Recovery Trade Setup")
        for _, stock in recovery_picks.head(3).iterrows():
            risk_reward = (stock['RESISTANCE'] - stock['CLOSE']) / (stock['CLOSE'] - stock['SUPPORT'])
            st.write(f"**{stock['COMPANY']}:** Entry ₦{stock['CLOSE']:.2f}, Target ₦{stock['RESISTANCE']:.2f}, Stop ₦{stock['SUPPORT']:.2f} (R:R {risk_reward:.1f}:1)")
    else:
        st.info("ℹ️ No oversold opportunities today. Market might be strong!")

else:  # All Strategies Overview
    st.markdown("## 📊 All Strategies Overview")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Weekly Momentum", "Monthly Growth", "Breakout Hunter", "Value Recovery"])
    
    with tab1:
        weekly = weekly_momentum_strategy(analyzed_df).head(5)
        if not weekly.empty:
            st.dataframe(weekly[['COMPANY', 'CLOSE', '%CHANGE', 'WEEKLY_SCORE']])
        else:
            st.write("No weekly opportunities")
    
    with tab2:
        monthly = monthly_growth_strategy(analyzed_df).head(5)
        if not monthly.empty:
            st.dataframe(monthly[['COMPANY', 'CLOSE', '%CHANGE', 'MONTHLY_SCORE']])
        else:
            st.write("No monthly opportunities")
    
    with tab3:
        breakouts = breakout_strategy(analyzed_df).head(5)
        if not breakouts.empty:
            st.dataframe(breakouts[['COMPANY', 'CLOSE', '%CHANGE', 'BREAKOUT_SCORE']])
        else:
            st.write("No breakout opportunities")
    
    with tab4:
        recovery = value_recovery_strategy(analyzed_df).head(5)
        if not recovery.empty:
            st.dataframe(recovery[['COMPANY', 'CLOSE', '%CHANGE', 'RECOVERY_SCORE']])
        else:
            st.write("No recovery opportunities")

# Risk Management Tips
st.markdown("---")
st.markdown("## ⚠️ Risk Management Rules")
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **Weekly Trades:**
    - Never risk more than 2% per trade
    - Set stop loss at -5% to -8%
    - Take profits at +8% to +15%
    - Maximum 3-5 positions at once
    """)

with col2:
    st.markdown("""
    **Monthly Holds:**
    - Risk 3-5% per position
    - Stop loss at -12% to -15%
    - Target +20% to +40%
    - Diversify across 5-8 stocks
    """)

st.markdown("---")
st.caption("⚠️ **Disclaimer:** This is for educational purposes. Always do your own research and never invest more than you can afford to lose. Past performance doesn't guarantee future results.")