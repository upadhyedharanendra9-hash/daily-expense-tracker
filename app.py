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

# Initialize database
database.init_db()

# --- SIDEBAR: USER INSTRUCTIONS & FILTERS ---
st.sidebar.title("🎮 App Control Center")

with st.sidebar.expander("📖 Quick Start Guide & Instructions", expanded=True):
    st.markdown("""
    **Welcome to your AI Expense Tracker!**
    This app uses Google Gemini to read natural language and break down your spending automatically.
    
    ### 🚀 How to Use It:
    1. **Type like you talk:** Describe your day's spending in the text box on the right.
    2. **Be specific with amounts:** Include the numbers and currency (e.g., *Rs 500* or *$12*).
    3. **Let the AI judge:** The AI automatically categorizes items into:
        * 🟢 **Good:** Necessary/Smart choices (Rent, Groceries, Utilities).
        * 🔴 **Bad:** Impulsive/Wasteful spending (Late night snacks, games, luxury splurges).
    4. **Analyze:** Check the charts to see your net outflow performance.
    """)

st.sidebar.divider()
st.sidebar.header("🗓️ Dashboard Filters")
selected_date = st.sidebar.date_input("Select Analysis Date", datetime.now())
date_str = selected_date.strftime("%Y-%m-%d")

# --- MAIN INTERFACE ---
st.title("💸 AI Personal Expense Tracker")
st.markdown("Log your spending using conversational language. Let artificial intelligence structure your financial health.")

# --- QUICK COPY EXAMPLES ---
with st.expander("💡 Need an example? Click here to see what you can type", expanded=False):
    st.markdown("""
    Copy and paste any of these lines into the box below to test how the AI processes data:
    
    * **Example 1 (Mixed Day):** 
      `Paid Rs 12000 for house rent today morning. Later, ordered a gourmet burger on Swiggy for Rs 450 because I was lazy to cook.`
    * **Example 2 (Multiple Items):** 
      `Spent $50 on weekly groceries, then blew $120 on an impulse purchase for a video game skin.`
    * **Example 3 (Simple Entry):** 
      `Bought petrol for my vehicle for 1000 INR.`
    """)

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

# --- AI PARSING LOGIC ---
def parse_expenses_with_ai(user_comment: str) -> DailyLog:
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

# --- USER INPUT ENTRY ---
st.subheader("🖊️ Log New Transactions")
user_comment = st.text_area(
    "What did you spend money on today?", 
    placeholder="e.g., I spent Rs 800 on fresh fruits and vegetables, and Rs 1200 on a shirt I didn't really need..."
)

if st.button("Analyze & Record Expenses", type="primary"):
    if not user_comment.strip():
        st.warning("Please type your expense comments before sending.")
    else:
        with st.spinner("🤖 AI is analyzing financial context..."):
            try:
                parsed_data = parse_expenses_with_ai(user_comment)
                database.save_expenses(parsed_data.expenses)
                st.success(f"Recorded {len(parsed_data.expenses)} items successfully!")
                st.rerun() 
            except Exception as e:
                st.error(f"Failed to process log: {e}")

st.divider()

# --- ANALYTICS DASHBOARD LAYER ---
st.subheader(f"📊 Financial Performance Summary: {date_str}")
raw_records = database.get_daily_summary(date_str)

if not raw_records:
    st.info("No transaction entries logged for this date yet. Try using one of the examples above!")
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
