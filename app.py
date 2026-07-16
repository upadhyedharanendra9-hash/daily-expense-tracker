import streamlit as st
import database
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from datetime import datetime
import pandas as pd
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(page_title="Premium Wealth Tracker", page_icon="💸", layout="wide")
database.init_db()

st.title("💸 AI Personal Expense Tracker")
st.markdown("Log your spending using natural language. Configured for premium execution.")

# --- PYDANTIC SCHEMAS ---
class ExpenseItem(BaseModel):
    item: str = Field(description="Name of the item or service purchased.")
    amount: float = Field(description="The exact cost numerical value.")
    currency: str = Field(description="Currency code used (e.g., INR, USD).")
    category: str = Field(description="Must strictly be 'Good' (essential) or 'Bad' (impulsive/wasteful).")
    reasoning: str = Field(description="Brief explanation of the category selection.")

class DailyLog(BaseModel):
    expenses: list[ExpenseItem]
    total_spent: float

def parse_expenses_with_ai(user_comment: str) -> DailyLog:
    # Pulls directly from Streamlit Secrets system
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    prompt = f"""
    You are a professional financial advisor. Analyze the text log provided by the user below.
    Extract every single purchase entry, separate the amount, and decide whether it represents a 'Good' or 'Bad' financial choice.
    User Log: "{user_comment}"
    """
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=DailyLog,
            temperature=0.1,
        ),
    )
    return DailyLog.model_validate_json(response.text)

# --- SIDEBAR FILTERS ---
st.sidebar.header("🗓️ Dashboard Filters")
selected_date = st.sidebar.date_input("Select Analysis Date", datetime.now())
date_str = selected_date.strftime("%Y-%m-%d")

# --- USER INPUT ENTRY ---
st.subheader("🖊️ Log New Transactions")
user_comment = st.text_area("Tell the AI what you spent money on today:")

if st.button("Analyze & Record Expenses", type="primary"):
    if not user_comment.strip():
        st.warning("Please type your expense comments before sending.")
    else:
        with st.spinner("🤖 AI is analyzing financial context..."):
            try:
                parsed_data = parse_expenses_with_ai(user_comment)
                database.save_expenses(parsed_data.expenses)
                st.success(f"Recorded {len(parsed_data.expenses)} items successfully!")
            except Exception as e:
                st.error(f"Failed to process log: {e}")

st.divider()

# --- ANALYTICS DASHBOARD LAYER ---
st.subheader(f"📊 Financial Performance Summary: {date_str}")
raw_records = database.get_daily_summary(date_str)

if not raw_records:
    st.info("No transaction entries logged for this date yet.")
else:
    df = pd.DataFrame(raw_records)
    good_total = df[df['category'] == 'Good']['amount'].sum()
    bad_total = df[df['category'] == 'Bad']['amount'].sum()
    grand_total = df['amount'].sum()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Essential Spend (Good)", f"{good_total:.2f} {df['currency'].iloc[0]}")
    col2.metric("Impulsive Spend (Bad)", f"{bad_total:.2f} {df['currency'].iloc[0]}")
    col3.metric("Net Outflow Today", f"{grand_total:.2f} {df['currency'].iloc[0]}")
    
    st.write("")
    col_chart, col_table = st.columns([1, 1.2])
    
    with col_chart:
        fig = px.pie(df, values='amount', names='category', color='category',
                     color_discrete_map={'Good': '#2ecc71', 'Bad': '#e74c3c'}, hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
        
    with col_table:
        for idx, row in df.iterrows():
            marker = "🟢 [GOOD]" if row['category'] == 'Good' else "🔴 [BAD]"
            with st.container(border=True):
                st.markdown(f"**{marker} {row['item']}** — `{row['amount']} {row['currency']}`")
                st.caption(f"💡 *AI Analysis:* {row['reasoning']}")
