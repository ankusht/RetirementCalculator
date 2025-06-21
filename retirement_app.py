import streamlit as st
import numpy as np
import pandas as pd
import altair as alt

# Glide path function
def get_equity_allocation(age, start_age=27, end_age=60, start_pct=0.85, end_pct=0.2):
    if age <= start_age:
        return start_pct
    elif age >= end_age:
        return end_pct
    else:
        return start_pct - ((age - start_age) / (end_age - start_age)) * (start_pct - end_pct)

def calculate_annual_emi(principal, annual_rate, years):
    monthly_rate = annual_rate / 12
    months = years * 12
    emi = (principal * monthly_rate * (1 + monthly_rate)**months) / ((1 + monthly_rate)**months - 1)
    return emi * 12

def retirement_calculator(current_age, retirement_age, life_expectancy,
                          current_savings, monthly_contribution,
                          equity_return, fixed_income_return,
                          annual_ret_expenses, exp_inflation_rate,
                          annual_contrib_increase, one_time_expenses,
                          home_loan=None):
    years = life_expectancy - current_age + 1
    ages = np.arange(current_age, current_age + years)

    data = []
    balance = current_savings
    contrib = monthly_contribution * 12
    emi_amount = -1

    for i, age in enumerate(ages):
        equity_allocation = get_equity_allocation(age)
        fixed_allocation = 1 - equity_allocation
        annual_return = equity_allocation * equity_return + fixed_allocation * fixed_income_return

        growth = balance * annual_return
        balance += growth

        # Contributions
        contribution = 0
        if age < retirement_age:
            contribution = contrib
            balance += contribution
            contrib *= (1 + annual_contrib_increase)

        # Retirement expenses
        expense = 0
        if age >= retirement_age:
            years_since_ret = age - current_age
            expense = annual_ret_expenses * ((1 + exp_inflation_rate) ** years_since_ret)
            balance -= expense

        # One-time expenses
        for exp_age, amount in one_time_expenses:
            if age == exp_age:
                inflated_amount = amount * ((1 + exp_inflation_rate) ** (age - current_age))
                balance -= inflated_amount
                expense += inflated_amount

        # Home loan EMI
        if home_loan:
            emi_start_age, emi_principal, emi_years, emi_rate = home_loan
            if age == emi_start_age and emi_amount < 0:
                effective_principal = emi_principal * ((1 + exp_inflation_rate) ** (age - current_age))
                emi_amount = calculate_annual_emi(effective_principal, emi_rate, emi_years)
            if emi_start_age <= age < emi_start_age + emi_years and emi_amount > 0:
                balance -= emi_amount
                expense += emi_amount

        data.append({
            "Age": age,
            "Net Worth": balance / 1e7,
            "Contribution": contribution / 1e7,
            "Expense": expense / 1e7,
            "Return": growth / 1e7,
            "Equity %": equity_allocation * 100
        })

    return pd.DataFrame(data)

# Streamlit App
st.title("\U0001F4CA Retirement Simulator with Glide Path")

# Sidebar Inputs
st.sidebar.header("Simulation Settings")
current_age = st.sidebar.number_input("Current Age", 20, 60, 27)
retirement_age = st.sidebar.number_input("Retirement Age", current_age+1, 70, 45)
life_expectancy = st.sidebar.number_input("Life Expectancy", retirement_age+1, 100, 90)
current_savings = st.sidebar.number_input("Current Savings (₹)", 0, 10_00_00_000, 2_40_00_000, step=10_00_000)
monthly_contribution = st.sidebar.number_input("Monthly SIP (₹)", 0, 10_00_000, 2_00_000, step=10_000)
equity_return = st.sidebar.slider("Equity Return", 0.05, 0.20, 0.13)
fixed_income_return = st.sidebar.slider("Fixed Income Return", 0.03, 0.10, 0.07)
annual_ret_expenses = st.sidebar.number_input("Annual Retirement Expenses (₹)", 1_00_000, 1_00_00_000, 30_00_000)
exp_inflation_rate = st.sidebar.slider("Inflation Rate", 0.02, 0.10, 0.06)
annual_contrib_increase = st.sidebar.slider("Annual SIP Growth Rate", 0.0, 0.20, 0.10)

# One-time expenses
st.sidebar.subheader("One-Time Expenses")
input_exp = st.sidebar.text_area("Format: age,amount", "28,2000000\n35,30000000\n50,30000000")
one_time_expenses = []
for line in input_exp.strip().split('\n'):
    try:
        age, amt = map(int, line.split(','))
        one_time_expenses.append((age, amt))
    except:
        pass

# Home loan
st.sidebar.subheader("Home Loan")
if st.sidebar.checkbox("Include Home Loan"):
    loan_age = st.sidebar.number_input("Loan Start Age", current_age, retirement_age, 35)
    loan_amount = st.sidebar.number_input("Loan Principal (₹)", 0, 10_00_00_000, 2_00_00_000)
    loan_years = st.sidebar.slider("Loan Term (years)", 1, 30, 20)
    loan_rate = st.sidebar.slider("Loan Interest Rate", 0.04, 0.12, 0.08)
    home_loan = (loan_age, loan_amount, loan_years, loan_rate)
else:
    home_loan = None

if st.button("Simulate"):
    df = retirement_calculator(
        current_age, retirement_age, life_expectancy,
        current_savings, monthly_contribution,
        equity_return, fixed_income_return,
        annual_ret_expenses, exp_inflation_rate,
        annual_contrib_increase, one_time_expenses,
        home_loan
    )

    st.subheader("Net Worth Over Time")
    line_chart = alt.Chart(df).mark_line().encode(
        x="Age",
        y=alt.Y("Net Worth", title="Net Worth (Cr)"),
        tooltip=["Age", "Net Worth"]
    ).properties(width=700, height=300)
    st.altair_chart(line_chart, use_container_width=True)

    st.subheader("Breakdown: Contributions, Returns & Expenses")
    area_chart = alt.Chart(df).transform_fold(
        ["Contribution", "Return", "Expense"],
        as_=["Type", "Amount"]
    ).mark_area(opacity=0.6).encode(
        x=alt.X("Age:Q", title="Age"),
        y=alt.Y("Amount:Q", title="Amount (Cr)"),
        color=alt.Color("Type:N", title="Flow Type"),
        tooltip=[alt.Tooltip("Age:Q"), alt.Tooltip("Type:N"), alt.Tooltip("Amount:Q", format=".2f")]
    ).properties(width=700, height=300)

    st.altair_chart(area_chart, use_container_width=True)

    st.subheader("Data Table")
    st.dataframe(df.style.format({"Net Worth": "{:.2f}", "Contribution": "{:.2f}", "Expense": "{:.2f}", "Return": "{:.2f}", "Equity %": "{:.0f}"}))
