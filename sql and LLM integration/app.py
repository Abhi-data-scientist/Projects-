from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import os
import google.generativeai as genai
import mysql.connector

# -------------------------------
# MySQL Connection
# -------------------------------
db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
)

cursor = db.cursor(dictionary=True)

# -------------------------------
# Gemini Configuration
# -------------------------------
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Agar error aaye to "gemini-2.5-pro" try kar lena
model = genai.GenerativeModel("models/gemini-2.5-flash")

# -------------------------------
# Database Schema
# Apne database ke hisaab se update karna
# -------------------------------
SCHEMA = """
Table: employees
Columns:
- id
- name
- department
- salary
"""

# -------------------------------
# Gemini -> SQL -> MySQL
# -------------------------------
def myoutput(query):

    prompt = f"""
            You are an expert MySQL query generator.

            Database Schema:
            {SCHEMA}

            Rules:
            1. Return ONLY a valid MySQL SELECT query.
            2. Never generate INSERT, UPDATE, DELETE, DROP, CREATE, ALTER.
            3. No explanation.
            4. No markdown.
            5. No ```sql block.

            User Question:
            {query}
        """

    try:
        # SQL Generate
        response = model.generate_content(prompt)

        sql_query = response.text.strip()
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

        # Debugging ke liye SQL dikha do
        st.write("**Generated SQL:**")
        st.code(sql_query, language="sql")

        # Security Check
        if not sql_query.lower().startswith("select"):
            return "❌ Only SELECT queries are allowed."

        # Execute SQL
        cursor.execute(sql_query)
        result = cursor.fetchall()

        if not result:
            return "No matching records found."

        return result

    except Exception as e:
        return f"Error: {str(e)}"

# -------------------------------
# Streamlit UI
# -------------------------------
st.set_page_config(page_title="SMART_BOT")
st.header("SMART_BOT 🤖")

user_input = st.text_input(
    "Ask your database query:",
    key="input"
)

submit = st.button("Ask your query")

if submit:
    output = myoutput(user_input)

    st.subheader("Response:")

    if isinstance(output, list):
        st.dataframe(output, use_container_width=True)
    else:
        st.write(output)