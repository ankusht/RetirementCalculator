import streamlit as st
import numpy as np
import pandas as pd
import altair as alt

# Glide path function with multiple strategies
def get_equity_allocation(age, strategy, start_age=27, end_age=60, start_pct=0.85, end_pct=0.2):
    if strategy == "Aggressive":
        start_pct, end_pct = 0.9, 0.3
    elif strategy == "Balanced":
        start_pct, end_pct = 0.85, 0.2
    elif strategy == "Conservative":
        start_pct, end_pct = 0.7, 0.2

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
                          home_loan=None, strategy="Balanced",
                          custom_start=0.85, custom_end=0.2, custom_age=60):
    years = life_expectancy - current_age + 1
    ages = np.arange(current_age, current_age + years)

    data = []
    balance = current_savings
    contrib = monthly_contribution * 12
    emi_amount = -1

    for i, age in enumerate(ages):
        equity_allocation = get_equity_allocation(age, strategy, start_age=current_age, end_age=custom_age, start_pct=custom_start, end_pct=custom_end)
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

st.markdown("### 🎯 Basic Info")

# Info Inputs
current_age = st.number_input("Current Age", 20, 60, 27)
retirement_age = st.number_input("Retirement Age", current_age + 1, 70, 45)
life_expectancy = st.number_input("Life Expectancy", retirement_age + 1, 100, 90)

st.markdown("### 📈 Expected Returns")
equity_return = st.slider("Equity Return", 0.05, 0.20, 0.13)
fixed_income_return = st.slider("Fixed Income Return", 0.03, 0.10, 0.07)
exp_inflation_rate = st.slider("Inflation Rate", 0.02, 0.10, 0.06)

st.markdown("### 📉 Glide Path Preview")
# Add a collapsible section for Glide Path explanation
with st.expander("What is a Glide Path?"):
    st.markdown("""
        As you age, your investments gradually shift from higher-risk options like equity to safer options like fixed deposits or bonds. 
        This strategy helps protect your savings but also reduces your expected returns over time. Choose a return strategy below to see how your equity allocation changes with age.
    """)
strategy = st.radio(
    "Return Strategy",
    ["Aggressive", "Balanced", "Conservative", "Custom"],
    index=1,
    help="Glide path controls how much equity your investments have as you age. It starts high and decreases over time."
)

custom_start = custom_end = custom_age = None
if strategy == "Custom":
    custom_start = st.slider("Equity allocation at current age (%)", 0.0, 1.0, 0.85)
    custom_end = st.slider("Equity allocation by retirement/older age (%)", 0.0, 1.0, 0.2)
    custom_age = st.slider("Glide ends by age", 40, 70, 60)
else:
    custom_start, custom_end, custom_age = 0.85, 0.2, 60

preview_ages = list(range(25, 91))
preview_allocs = [get_equity_allocation(age, strategy, start_age=27, end_age=custom_age, start_pct=custom_start, end_pct=custom_end) * 100 for age in preview_ages]
glide_df = pd.DataFrame({"Age": preview_ages, "Equity Allocation (%)": preview_allocs})
st.line_chart(glide_df.set_index("Age"))


st.markdown("### 💰 Contributions")
current_savings = st.number_input("Current Savings (₹)", 0, 10_00_00_000, 2_40_00_000, step=10_00_000)
monthly_contribution = st.number_input("Monthly SIP (₹)", 0, 10_00_000, 2_00_000, step=10_000)
annual_contrib_increase = st.slider("Annual SIP Growth Rate", 0.0, 0.20, 0.10)

st.markdown("### 💸 Expenses")
annual_ret_expenses = st.number_input("Annual Retirement Expenses (₹)", 0, 1_00_00_000, 30_00_000, step = 10_000, help="Enter your expected annual expenses in today's value. Inflation will be applied automatically.")

st.markdown("### 🏡 One-Time Expenses")
input_exp = st.text_area(
    "One-Time Expenses (in today’s value, one per line as age,amount)",
    "28,2000000\n35,30000000\n50,30000000"
)
one_time_expenses = []
for line in input_exp.strip().split('\n'):
    try:
        age, amt = map(int, line.split(','))
        one_time_expenses.append((age, amt))
    except:
        pass

st.markdown("### 🏦 Home Loan")
include_loan = st.checkbox("Include Home Loan")
if include_loan:
    loan_age = st.number_input("Loan Start Age", current_age, retirement_age, 35)
    loan_amount = st.number_input("Loan Principal (₹)", 0, 10_00_00_000, 2_00_00_000)
    loan_years = st.slider("Loan Term (years)", 1, 30, 20)
    loan_rate = st.slider("Loan Interest Rate", 0.04, 0.12, 0.08)
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
        home_loan, strategy, custom_start, custom_end, custom_age
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
    highlight_years = set([current_age, retirement_age, life_expectancy] + [age for age, _ in one_time_expenses])
    df_filtered = df[df["Age"].apply(lambda x: x in highlight_years or x % 5 == 0)].reset_index(drop=True)
    st.dataframe(df_filtered.style.format({
        "Net Worth (Cr)": "{:.2f}", "Contribution (Cr)": "{:.2f}",
        "Expense (Cr)": "{:.2f}", "Return (Cr)": "{:.2f}", "Equity %": "{:.0f}"
    }))

    st.subheader("\U0001F4CA Summary")
    final_balance = df["Net Worth"].iloc[-1]
    peak_row = df.loc[df["Net Worth"].idxmax()]
    st.success(f"✅ Final Net Worth at age {life_expectancy}: ₹{final_balance:.2f} Cr")
    st.info(f"📈 Peak Net Worth: ₹{peak_row['Net Worth']:.2f} Cr at age {int(peak_row['Age'])}")
    if (df["Net Worth"] < 0).any():
        st.error("⚠️ Warning: Your savings run out before life expectancy!")
