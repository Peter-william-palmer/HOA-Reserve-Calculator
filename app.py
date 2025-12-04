import streamlit as st
import pandas as pd
import numpy as np
import io

# --- Configuration ---
st.set_page_config(layout="wide", page_title="MA HOA Reserve Calculator")

# --- Helper Functions ---

def calculate_fully_funded_balance(df):
    """
    Calculates the theoretical 'Fully Funded Balance' (FFB) at the current moment.
    FFB = Current Cost * (Effective Age / Useful Life)
    Effective Age = Useful Life - Remaining Useful Life
    """
    total_ffb = 0
    for index, row in df.iterrows():
        ul = row['Useful Life']
        rul = row['Remaining Useful Life']
        cost = row['Current Cost']
        
        # Avoid division by zero
        if ul > 0:
            effective_age = max(0, ul - rul)
            component_ffb = cost * (effective_age / ul)
            total_ffb += component_ffb
            
    return total_ffb

def calculate_projection(df, start_balance, annual_contribution, contribution_increase, inflation_rate, interest_rate, assessment_year, assessment_amount, years_to_project):
    """Calculates the 30-year cash flow projection with Special Assessments."""
    
    projection_data = []
    current_balance = start_balance
    current_contribution = annual_contribution
    
    # We expand the component list to track individual replacement years
    # Create a schedule of expenditures
    expenditures_by_year = {year: 0 for year in range(1, years_to_project + 1)}
    
    for index, row in df.iterrows():
        cost = row['Current Cost']
        rul = int(row['Remaining Useful Life'])
        ul = int(row['Useful Life'])
        
        # Calculate replacement years: RUL, then every UL after that
        if ul > 0:
            replace_year = rul + 1  # If RUL is 0, we replace in year 1
            while replace_year <= years_to_project:
                # Calculate future cost with inflation
                future_cost = cost * ((1 + inflation_rate) ** (replace_year - 1))
                expenditures_by_year[replace_year] += future_cost
                replace_year += ul

    # Run the yearly cash flow loop
    for year in range(1, years_to_project + 1):
        
        start_of_year_balance = current_balance
        
        # 1. Earnings (Interest on starting balance)
        interest_earned = start_of_year_balance * interest_rate
        
        # 2. Contributions (Income)
        # Apply annual increase to contribution
        if year > 1:
            current_contribution = current_contribution * (1 + contribution_increase)
        
        # Check for Special Assessment
        special_assessment = assessment_amount if year == assessment_year else 0
        
        total_income = current_contribution + special_assessment + interest_earned
        
        # 3. Expenditures
        yearly_expenditures = expenditures_by_year[year]
        
        # 4. End Balance
        end_of_year_balance = start_of_year_balance + total_income - yearly_expenditures
        current_balance = end_of_year_balance
        
        projection_data.append({
            'Year': year,
            'Start Balance': start_of_year_balance,
            'Annual Contribution': current_contribution,
            'Special Assessment': special_assessment,
            'Interest Earned': interest_earned,
            'Expenditures': yearly_expenditures,
            'End Balance': end_of_year_balance
        })

    return pd.DataFrame(projection_data)


# --- Streamlit App Layout ---

st.title("🏙️ Massachusetts HOA Reserve Calculator")
st.markdown("""
This tool helps Condominium Associations plan for long-term financial health. 
It calculates your **Percent Funded** status and projects cash flow for **30 years**.
""")

# --- Sidebar Inputs ---
st.sidebar.header("1. Financial Inputs")

starting_balance = st.sidebar.number_input(
    "Current Reserve Cash ($)", 
    min_value=0, 
    value=100000, 
    step=1000,
    help="The total cash currently sitting in your Reserve bank accounts."
)

annual_contribution = st.sidebar.number_input(
    "Annual Reserve Contribution ($)", 
    min_value=0, 
    value=25000, 
    step=500,
    help="How much you transfer to reserves from the operating budget each year."
)

contribution_increase = st.sidebar.slider(
    "Annual Dues Increase (%)", 
    min_value=0.0, max_value=10.0, 
    value=2.0, step=0.1,
    help="Percentage you plan to increase the reserve contribution each year."
) / 100

st.sidebar.header("2. Economic Assumptions")
inflation_rate = st.sidebar.slider(
    "Inflation Rate (%)", 
    min_value=0.0, max_value=8.0, 
    value=3.0, step=0.1
) / 100

interest_rate = st.sidebar.slider(
    "Interest Rate on Savings (%)", 
    min_value=0.0, max_value=5.0, 
    value=1.5, step=0.1
) / 100

st.sidebar.header("3. Scenario Tools")
st.sidebar.markdown("**Special Assessment Tester**")
assessment_year = st.sidebar.number_input("Assessment Year (Example: 5)", min_value=1, max_value=30, value=1)
assessment_amount = st.sidebar.number_input("Assessment Amount ($)", min_value=0, value=0, step=5000)

st.sidebar.markdown("---")

# --- Data Upload ---
st.sidebar.header("4. Component Data")
uploaded_file = st.sidebar.file_uploader("Upload CSV File", type=['csv'])

# Template Download
if st.sidebar.button("Download Template CSV"):
    template_data = {
        'Component': ['Roof Shingles', 'Asphalt Paving', 'Hallway Carpets', 'Exterior Paint'],
        'Useful Life': [25, 20, 10, 7],
        'Remaining Useful Life': [12, 5, 2, 1],
        'Current Cost': [150000, 45000, 12000, 8000]
    }
    template_df = pd.DataFrame(template_data)
    csv = template_df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        "Download Template",
        csv,
        "ma_reserve_template.csv",
        "text/csv"
    )

# --- Main Calculation Logic ---

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        
        # Validation
        required_cols = ['Component', 'Useful Life', 'Remaining Useful Life', 'Current Cost']
        if not all(col in df.columns for col in required_cols):
            st.error(f"Error: CSV must contain these columns: {required_cols}")
        else:
            # 1. Calculate Current Percent Funded
            ffb = calculate_fully_funded_balance(df)
            percent_funded = (starting_balance / ffb * 100) if ffb > 0 else 100
            
            # 2. Run Projection
            proj_df = calculate_projection(
                df, starting_balance, annual_contribution, contribution_increase,
                inflation_rate, interest_rate, assessment_year, assessment_amount, 30
            )
            
            # --- DASHBOARD ---
            
            # Top Metrics
            st.subheader("Current Financial Health")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Starting Balance", f"${starting_balance:,.0f}")
            with col2:
                st.metric("Fully Funded Balance (FFB)", f"${ffb:,.0f}", help="How much you theoretically *should* have today based on component deterioration.")
            with col3:
                # Color code the Percent Funded
                pct_color = "normal"
                if percent_funded < 30: pct_color = "inverse" # Streamlit doesn't support red text directly in metric, but we can visualize it below
                st.metric("Percent Funded", f"{percent_funded:.1f}%")
            with col4:
                min_bal = proj_df['End Balance'].min()
                st.metric("Lowest Projected Balance", f"${min_bal:,.0f}", delta_color="off" if min_bal > 0 else "inverse")

            # Health Interpretation
            if percent_funded < 30:
                st.warning("⚠️ **High Risk (0-30% Funded):** Special assessments are highly likely. Immediate action recommended.")
            elif percent_funded < 70:
                st.info("⚠️ **Medium Risk (30-70% Funded):** Funding requires strengthening to avoid future cash flow issues.")
            else:
                st.success("✅ **Low Risk (70-100%+ Funded):** Financial health is strong.")

            st.markdown("---")

            # Charts
            st.subheader("30-Year Reserve Projection")
            
            chart_data = proj_df.set_index('Year')[['End Balance', 'Expenditures']]
            st.line_chart(chart_data)
            
            if min_bal < 0:
                failure_year = proj_df[proj_df['End Balance'] < 0].iloc[0]['Year']
                st.error(f"❌ **FUNDING FAILURE DETECTED:** Account runs out of money in Year {failure_year}. Use the 'Special Assessment' tool in the sidebar to test a fix.")

            # Detailed Data
            with st.expander("View Detailed Cash Flow Table"):
                st.dataframe(proj_df, use_container_width=True)

            with st.expander("View Component List"):
                st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error(f"An error occurred: {e}")
else:
    st.info("👈 **Start Here:** Download the template from the sidebar, fill in your component data, and upload it to see your results.")
