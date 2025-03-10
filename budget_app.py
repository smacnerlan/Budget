import json
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load credentials from Streamlit secrets
credentials = st.secrets["GOOGLE_CLOUD_CREDENTIALS"]
creds = Credentials.from_service_account_info(dict(credentials))

def get_budget_data():
    client = gspread.authorize(creds)
    spreadsheet = client.open("Joint Budget")
    sheet = spreadsheet.worksheet("New Budget Format")
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    df.columns = df.columns.str.strip()
    
    if "Income/Expense" in df.columns:
        df["Income/Expense"] = df["Income/Expense"].astype(str).str.strip().str.lower()
    
    if "Amount" in df.columns:
        df["Amount"] = df["Amount"].astype(str).str.replace(',', '').str.replace('$', '').str.strip()
        df["Amount"] = pd.to_numeric(df["Amount"], errors='coerce').fillna(0)
    
    if "Item" in df.columns:
        df["Item"] = df["Item"].fillna("Unknown")
    
    return df, spreadsheet

def get_saved_distribution_settings(spreadsheet):
    try:
        pos_sheet = spreadsheet.worksheet("POS")
        values = pos_sheet.get("B3:D3")
        if values and len(values[0]) == 3:
            return [int(values[0][0]), int(values[0][1]), int(values[0][2])]
    except Exception as e:
        st.error(f"Error fetching saved settings: {e}")
    return [20, 60, 20]

def save_distribution_settings(spreadsheet, profit, opex, slush):
    pos_sheet = spreadsheet.worksheet("POS")
    pos_sheet.update_acell("B3", profit)
    pos_sheet.update_acell("C3", opex)
    pos_sheet.update_acell("D3", slush)

def delete_entry(sheet, row_index):
    sheet.delete_rows(row_index + 2)
    st.success("Entry deleted successfully!")

def add_new_entry(sheet, item, income_expense, amount, category, expense_type):
    sheet.append_row([item, income_expense, amount, category, expense_type])
    st.success("New entry added successfully!")

st.set_page_config(layout="wide")
st.title("Budget Management Dashboard")

df, spreadsheet = get_budget_data()
sheet = spreadsheet.worksheet("New Budget Format")

saved_percentages = get_saved_distribution_settings(spreadsheet)

st.sidebar.header("Income Distribution")
profit_percent = st.sidebar.slider("Profit %", 0, 100, saved_percentages[0])
opex_percent = st.sidebar.slider("OPEX %", 0, 100, saved_percentages[1])
slush_percent = st.sidebar.slider("Slush %", 0, 100, saved_percentages[2])

if st.sidebar.button("Save Distribution Settings"):
    save_distribution_settings(spreadsheet, profit_percent, opex_percent, slush_percent)
    st.sidebar.success("Distribution settings saved!")

df_income = df[df["Income/Expense"] == "income"]
df_expense = df[df["Income/Expense"] == "expense"]

total_income = df_income["Amount"].sum()
annualized_total_income = total_income * 12

distributed_income = {
    "Profit": (profit_percent / 100) * total_income,
    "OPEX": (opex_percent / 100) * total_income,
    "Slush": (slush_percent / 100) * total_income,
}

total_expenses = df_expense["Amount"].sum()
annualized_total_expenses = total_expenses * 12

expense_by_type = df_expense.groupby("Expense Type")["Amount"].sum()

st.sidebar.subheader("Distributed Income Calculator")
input_income = st.sidebar.number_input("Enter Income to Distribute", min_value=0.0, format="%.2f")
calculated_distribution = {
    "Profit": (profit_percent / 100) * input_income,
    "OPEX": (opex_percent / 100) * input_income,
    "Slush": (slush_percent / 100) * input_income,
}
for key, value in calculated_distribution.items():
    st.sidebar.text(f"{key}: ${value:.2f}")

st.sidebar.subheader("Distributed Income (Monthly)")
for key, value in distributed_income.items():
    st.sidebar.text(f"{key}: ${value:.2f}")

col1, col2, col3 = st.columns([2, 3, 2])

with col1:
    st.sidebar.header("Add New Entry")
    new_item = st.sidebar.text_input("Item Name")
    new_income_expense = st.sidebar.selectbox("Type", ["income", "expense"])
    new_amount = st.sidebar.number_input("Amount", min_value=0.0, format="%.2f")
    new_category = st.sidebar.text_input("Category")
    new_expense_type = st.sidebar.text_input("Expense Type")
    
    if st.sidebar.button("Add Entry"):
        add_new_entry(sheet, new_item, new_income_expense, new_amount, new_category, new_expense_type)

with col2:
    st.subheader("Income")
    df_income = st.data_editor(df_income, column_config={"Amount": st.column_config.NumberColumn("Amount", format="$%.2f", step=0.01)}, num_rows="dynamic", key='income_amount_editor')
    
    st.metric("Total Income (Monthly)", f"${total_income:.2f}")
    st.metric("Total Income (Annualized)", f"${annualized_total_income:.2f}")
    
    st.subheader("Expenses")
    df_expense = st.data_editor(df_expense, column_config={"Amount": st.column_config.NumberColumn("Amount", format="$%.2f", step=0.01)}, num_rows="dynamic", key='expense_amount_editor')
    
    st.metric("Total Expenses (Monthly)", f"${total_expenses:.2f}")
    st.metric("Total Expenses (Annualized)", f"${annualized_total_expenses:.2f}")
