import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Configuration
st.set_page_config(page_title="Corporate Sentiment Dashboard", page_icon="📊", layout="wide")

# ==========================================
# 2. CUSTOM CSS
# ==========================================
st.markdown("""
<style>
    /* Light grey background for the whole app */
    .stApp {
        background-color: black;
    }
    
    /* Make all headers use the Petronas Teal */
    h1, h2, h3 {
        color: #00A19C !important; 
        font-family: 'Arial', sans-serif;
        font-weight: bold;
    }
    
    /* Style the Metric Cards to look like corporate widgets */
    div[data-testid="metric-container"] {
        background-color: #FFFFFF;
        border-left: 6px solid #00A19C; /* Teal accent line */
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.05);
    }
    
    /* Style the horizontal dividers */
    hr {
        border-bottom: 2px solid #00A19C;
        opacity: 0.2;
    }
</style>
""", unsafe_allow_html=True)
# ==========================================

# 3. Add Title and Description
st.title("📊 Social Media Sentiment Dashboard")
st.markdown("**Powered by Hugging Face AI.** Analyzing public reaction and sentiment distribution.")
st.divider() 

# 4. Load the Data
filename = "smart_analyzed_comments_OqEc_169ywY.csv" 

@st.cache_data 
def load_data():
    return pd.read_csv(filename)

try:
    df = load_data()

    # 5. Create Top-Level Metrics
    st.subheader("Executive Summary")
    col1, col2, col3, col4 = st.columns(4)
    
    total_comments = len(df)
    positive_count = len(df[df['Sentiment Label'] == 'POSITIVE'])
    negative_count = len(df[df['Sentiment Label'] == 'NEGATIVE'])
    neutral_count = len(df[df['Sentiment Label'] == 'NEUTRAL'])
    
    col1.metric("Total Comments", total_comments)
    col2.metric("Positive Reaction", positive_count)
    col3.metric("Negative Reaction", negative_count)
    col4.metric("Neutral / Unclear", neutral_count)

    st.divider()

    # 6. Create Interactive Charts
    st.subheader("Sentiment Distribution")
    
    sentiment_counts = df['Sentiment Label'].value_counts().reset_index()
    sentiment_counts.columns = ['Sentiment', 'Count']
    
    # Updated Plotly Chart with Corporate Colors
    fig = px.pie(
        sentiment_counts, 
        values='Count', 
        names='Sentiment', 
        color='Sentiment',
        color_discrete_map={
            'POSITIVE': '#00A19C', # Petronas Teal
            'NEGATIVE': '#E63946', # Corporate Red
            'NEUTRAL': '#8D99AE'   # Slate Grey
        },
        hole=0.4 
    )
    
    # Make the chart background transparent to blend with the app
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # 7. Display the Raw Data Table
    st.subheader("Raw Data & AI Confidence Log")
    display_df = df[['Author', 'Cleaned Text', 'Sentiment Label', 'Confidence Score']]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

except FileNotFoundError:
    st.error(f"Could not find the file: {filename}. Please make sure you ran the sentiment analyzer script first!")