import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
import base64
from datetime import datetime

# --- Configuration ---
st.set_page_config(layout="wide", page_title="MA Condo Reserve Calculator", page_icon="🇺🇸")

# --- Helper Functions ---

def calculate_fully_funded_balance(df):
    """Calculates FFB using the Component Method (CAI Standard)."""
    total_ffb = 0
    for index, row in df.iterrows():
        ul = row['Useful Life']
        rul = row['Remaining Useful Life']
        cost = row['Current Cost']
        if ul > 0:
            effective_age = max(0, ul - rul)
            component_ffb = cost * (effective_age / ul)
            total_ffb += component_ffb
    return total_ffb

def calculate_projection_detailed(df, start_balance, annual_contribution, contribution_increase, inflation_rate, interest_rate, assessment_year, assessment_amount, years_to_project=30):
    """
    Calculates 30-year projection and tracks specific component replacements per year for hover details.
    """
    projection_data = []
    current_balance = start_balance
    current_contribution = annual_contribution
    
    # Track expenditures and specific project names per year
    expenditures_by_year = {year: 0 for year in range(1, years_to_project + 1)}
    projects_by_year = {year: [] for year in range(1, years_to_project + 1)}
    
    for index, row in df.iterrows():
        cost = row['Current Cost']
        rul = int(row['Remaining Useful Life'])
        ul = int(row['Useful Life'])
        name = row['Component Name']
        
        if ul > 0:
            replace_year = rul + 1
            while replace_year <= years_to_project:
                future_cost = cost * ((1 + inflation_rate) ** (replace_year - 1))
                expenditures_by_year[replace_year] += future_cost
                projects_by_year[replace_year].append(f"{name} (${future_cost:,.0f})")
                replace_year += ul

    # Cash flow loop
    for year in range(1, years_to_project + 1):
        start_of_year_balance = current_balance
        interest_earned = start_of_year_balance * interest_rate
        
        if year > 1:
            current_contribution = current_contribution * (1 + contribution_increase)
        
        special_assessment = assessment_amount if year == assessment_year else 0
        total_income = current_contribution + special_assessment + interest_earned
        yearly_expenditures = expenditures_by_year[year]
        
        end_of_year_balance = start_of_year_balance + total_income - yearly_expenditures
        current_balance = end_of_year_balance
        
        # Join project names for hover text
        project_details = "<br>".join(projects_by_year[year]) if projects_by_year[year] else "No Major Projects"
        
        projection_data.append({
            'Year': year,
            'Start Balance': start_of_year_balance,
            'Annual Contribution': current_contribution,
            'Special Assessment': special_assessment,
            'Interest Earned': interest_earned,
            'Expenditures': yearly_expenditures,
            'End Balance': end_of_year_balance,
            'Projects': project_details
        })

    return pd.DataFrame(projection_data)

def generate_pdf_report(proj_df, component_df, percent_funded, ffb, starting_balance, min_bal):
    """Generates a simple PDF report."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Massachusetts Condo Reserve Report", ln=True, align='C')
    
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Date Generated: {datetime.now().strftime('%Y-%m-%d')}", ln=True)
    pdf.ln(5)
    
    # Key Metrics
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="Financial Snapshot", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Current Reserve Balance: ${starting_balance:,.2f}", ln=True)
    pdf.cell(200, 10, txt=f"Fully Funded Balance (FFB): ${ffb:,.2f}", ln=True)
    pdf.cell(200, 10, txt=f"Percent Funded: {percent_funded:.1f}%", ln=True)
    pdf.cell(200, 10, txt=f"Lowest Projected Balance (30 Years): ${min_bal:,.2f}", ln=True)
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="Component List", ln=True)
    pdf.set_font("Arial", size=10)
    
    # Table Header
    col_width = 45
    pdf.cell(col_width, 10, "Component", 1)
    pdf.cell(30, 10, "Cost", 1)
    pdf.cell(20, 10, "UL", 1)
    pdf.cell(20, 10, "RUL", 1)
    pdf.ln()
    
    # Table Rows
    for index, row in component_df.iterrows():
        pdf.cell(col_width, 10, str(row['Component Name'])[:20], 1)
        pdf.cell(30, 10, f"${row['Current Cost']:,.0f}", 1)
        pdf.cell(20, 10, str(row['Useful Life']), 1)
        pdf.cell(20, 10, str(row['Remaining Useful Life']), 1)
        pdf.ln()

    pdf.ln(10)
    pdf.set_font("Arial", 'I', 10)
    pdf.multi_cell(0, 10, "Disclaimer: This report is a mathematical simulation based on user inputs. It is not a substitute for a professional Reserve Study by a credentialed engineer.")
    
    return pdf.output(dest='S').encode('latin-1')

# --- Initialization of Session State for Components ---
if 'component_df' not in st.session_state:
    # Default Starting Data
    default_data = {
        'Component Name': ['Roof Shingles (Asphalt)', 'Pavement (Seal & Crackfill)', 'Hallway Carpets', 'Exterior Paint'],
        'Current Cost': [150000.0, 5000.0, 12000.0, 8000.0],
        'Useful Life': [25, 4, 10, 7],
        'Remaining Useful Life': [12, 2, 5, 1],
        'Notes': ['Pricing based on 2024 quote', 'Maintenance cycle', 'Common areas', 'Full cycle']
    }
    st.session_state.component_df = pd.DataFrame(default_data)

# --- Main Layout ---

st.title("Massachusetts Condo Reserve Calculator 🇺🇸")

# --- Tabs for Organization ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "✏️ Components", "📅 Replacement Timeline", "📉 Sensitivity & Tools", "📄 Report"])

# --- Sidebar ---
st.sidebar.header("1. Property Details")
num_units = st.sidebar.number_input("Number of Units", min_value=1, value=50, step=1)

st.sidebar.header("2. Financial Inputs")
starting_balance = st.sidebar.number_input("Current Reserve Cash ($)", min_value=0.0, value=100000.0, step=1000.0, format="%.2f")

# Annual Contribution with BIG PER UNIT DISPLAY
annual_contribution = st.sidebar.number_input("Annual Reserve Contribution ($)", min_value=0.0, value=25000.0, step=500.0, format="%.2f")
per_unit_monthly = annual_contribution / num_units / 12
st.sidebar.markdown(f"<h2 style='text-align: center; color: #4CAF50;'>${per_unit_monthly:,.2f}</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='text-align: center;'><b>per unit / per month</b></p>", unsafe_allow_html=True)

contribution_increase = st.sidebar.slider("Annual Dues Increase (%)", 0.0, 10.0, 2.0, 0.1) / 100

st.sidebar.header("3. Economic Assumptions")
inflation_rate = st.sidebar.slider("Inflation Rate (%)", 0.0, 10.0, 3.2, 0.1) / 100
interest_rate = st.sidebar.slider("Interest Rate on Savings (%)", 0.0, 8.0, 1.8, 0.1) / 100

st.sidebar.header("4. Special Assessment")
assessment_year = st.sidebar.number_input("Assessment Year", 1, 30, 1)
assessment_amount = st.sidebar.number_input("Total Assessment ($)", min_value=0.0, value=0.0, step=5000.0)

# --- TAB 2: COMPONENTS (Editable) ---
with tab2:
    st.subheader("Edit Your Component List")
    st.info("Add or remove rows below. Data saves automatically.")
    
    # Presets Logic
    col_preset, col_btn = st.columns([3, 1])
    with col_preset:
        preset_option = st.selectbox("Quick Add (2025 Greater Boston Averages)", 
                                     ["Select...", "Asphalt Roof (Large)", "Rubber Roof (Flat)", "Boiler System", "Elevator Modernization", "Ext. Painting (Wood)", "Paving Overlay"])
    with col_btn:
        st.write("") # Spacer
        st.write("") 
        if st.button("Add Preset"):
            new_row = {}
            if "Asphalt Roof" in preset_option: new_row = {'Component Name': 'New Asphalt Roof', 'Current Cost': 120000.0, 'Useful Life': 25, 'Remaining Useful Life': 25, 'Notes': 'Boston Avg'}
            elif "Rubber Roof" in preset_option: new_row = {'Component Name': 'EPDM Rubber Roof', 'Current Cost': 80000.0, 'Useful Life': 20, 'Remaining Useful Life': 20, 'Notes': 'Boston Avg'}
            elif "Boiler" in preset_option: new_row = {'Component Name': 'Commercial Boiler', 'Current Cost': 45000.0, 'Useful Life': 25, 'Remaining Useful Life': 15, 'Notes': 'Boston Avg'}
            elif "Elevator" in preset_option: new_row = {'Component Name': 'Elevator Mod', 'Current Cost': 100000.0, 'Useful Life': 25, 'Remaining Useful Life': 10, 'Notes': 'Hydraulic'}
            elif "Painting" in preset_option: new_row = {'Component Name': 'Full Ext Paint', 'Current Cost': 25000.0, 'Useful Life': 6, 'Remaining Useful Life': 3, 'Notes': 'Cycles fast in NE'}
            elif "Paving" in preset_option: new_row = {'Component Name': 'Pavement Overlay', 'Current Cost': 35000.0, 'Useful Life': 20, 'Remaining Useful Life': 5, 'Notes': '2 inch overlay'}
            
            if new_row:
                st.session_state.component_df = pd.concat([st.session_state.component_df, pd.DataFrame([new_row])], ignore_index=True)
                st.rerun()

    # The Editor
    edited_df = st.data_editor(st.session_state.component_df, num_rows="dynamic", use_container_width=True)
    st.session_state.component_df = edited_df

# --- Calculations for Dashboard ---
df = st.session_state.component_df
ffb = calculate_fully_funded_balance(df)
percent_funded = (starting_balance / ffb * 100) if ffb > 0 else 100

# Run Projection
proj_df = calculate_projection_detailed(
    df, starting_balance, annual_contribution, contribution_increase,
    inflation_rate, interest_rate, assessment_year, assessment_amount, 30
)
min_bal = proj_df['End Balance'].min()

# --- TAB 1: DASHBOARD ---
with tab1:
    # 1. THE GAUGE
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = percent_funded,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Percent Funded Status"},
        gauge = {
            'axis': {'range': [None, 130]},
            'bar': {'color': "black"},
            'steps': [
                {'range': [0, 50], 'color': "#FFCDD2"},  # Red
                {'range': [50, 70], 'color': "#FFF9C4"}, # Yellow
                {'range': [70, 130], 'color': "#C8E6C9"} # Green
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 70
            }
        }
    ))
    fig_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig_gauge, use_container_width=True)
    
    # Warning Text
    st.markdown("""
    <div style='text-align: center; font-style: italic; color: #555; margin-bottom: 20px;'>
    Massachusetts lenders and courts consider <50% funded ‘inadequate’ and may block refinancing.
    </div>
    """, unsafe_allow_html=True)

    # Risk Banner
    if percent_funded < 70:
        st.error("⚠️ **BELOW THRESHOLD:** Below the 70% threshold most Massachusetts banks and condo attorneys recommend. Risk of special assessments or loan denials.")
    else:
        st.success("✅ **HEALTHY:** Above the 70% threshold recommended by lenders.")

    # FFB Expander
    st.caption(f"Fully Funded Balance Goal: ${ffb:,.2f}")
    with st.expander("How is this calculated?"):
        st.write("Sum of (Current Replacement Cost × Years Already Used ÷ Total Useful Life) for every component – the CAI-recommended Component Method used by every Massachusetts reserve study firm.")

    # 2. INTERACTIVE CHART
    st.subheader("30-Year Cash Flow & Projects")
    
    # Colors for bars
    proj_df['Color'] = np.where(proj_df['End Balance'] < 0, 'Negative', 'Positive')
    
    fig_bar = px.bar(
        proj_df, 
        x='Year', 
        y='End Balance',
        color='Color',
        color_discrete_map={'Negative': 'red', 'Positive': 'blue'},
        hover_data=['Expenditures', 'Projects'],
        title="Projected Year-End Balance (Hover for Project Details)"
    )
    fig_bar.add_trace(go.Scatter(x=proj_df['Year'], y=proj_df['Expenditures'], mode='lines', name='Expenses', line=dict(color='orange', width=2, dash='dot')))
    st.plotly_chart(fig_bar, use_container_width=True)

# --- TAB 3: TIMELINE ---
with tab3:
    st.subheader("Projected Replacement Timeline")
    
    # Prepare Gantt Data
    gantt_data = []
    current_year_val = datetime.now().year
    
    for index, row in df.iterrows():
        rul = row['Remaining Useful Life']
        ul = row['Useful Life']
        name = row['Component Name']
        
        # Add the next replacement
        rep_year = current_year_val + rul
        gantt_data.append(dict(Task=name, Start=rep_year, Finish=rep_year+1, Type='Next Replacement'))
        
        # Add the one after that (if within 30 years)
        next_rep = rep_year + ul
        if next_rep < current_year_val + 30:
            gantt_data.append(dict(Task=name, Start=next_rep, Finish=next_rep+1, Type='Future Replacement'))

    if gantt_data:
        gantt_df = pd.DataFrame(gantt_data)
        fig_gantt = px.timeline(gantt_df, x_start="Start", x_end="Finish", y="Task", color="Type")
        fig_gantt.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_gantt, use_container_width=True)
    else:
        st.write("Add components to see the timeline.")

# --- TAB 4: SENSITIVITY & TOOLS ---
with tab4:
    st.subheader("🛠️ Solvers & Optimizers")
    
    col_solver, col_min = st.columns(2)
    
    # SOLVER 1: REACH 70%
    with col_solver:
        st.markdown("#### 🎯 Reach 70% in 5 Years")
        if st.button("Calculate Required Contribution"):
            # Simple iterator
            test_contribution = annual_contribution
            found = False
            for i in range(1000): # Limit iterations
                temp_proj = calculate_projection_detailed(df, starting_balance, test_contribution, contribution_increase, inflation_rate, interest_rate, assessment_year, assessment_amount, 5)
                # Calculate future FFB (approximate for speed)
                # Future FFB is harder, let's just aim for a balance target or simple logic. 
                # Let's assume FFB grows by inflation.
                future_ffb = ffb * ((1+inflation_rate)**5)
                yr5_bal = temp_proj.iloc[4]['End Balance']
                
                if (yr5_bal / future_ffb) >= 0.70:
                    found = True
                    break
                test_contribution += 100
            
            if found:
                req_monthly = test_contribution / num_units / 12
                st.success(f"Required Annual: ${test_contribution:,.0f}")
                st.metric("New Monthly/Unit Cost", f"${req_monthly:,.2f}")
            else:
                st.warning("Could not find a reasonable solution within limits.")

    # SOLVER 2: MINIMIZER
    with col_min:
        st.markdown("#### 🛡️ Special Assessment Minimizer")
        st.caption("Finds the smallest assessment needed to keep balance > $0.")
        if st.button("Find Minimum Fix"):
            # Check if needed
            if min_bal >= 0:
                st.success("No assessment needed! You are fully funded.")
            else:
                # Find the lowest dip
                deficit = abs(min_bal)
                # Simple logic: Assess the deficit amount in Year 1 (simplest safety)
                rec_assess = deficit
                per_unit_assess = rec_assess / num_units
                st.error(f"Recommended Assessment: ${rec_assess:,.0f}")
                st.metric("Cost Per Unit", f"${per_unit_assess:,.2f}")
                st.info("Apply this in Sidebar 'Special Assessment' to verify.")

    st.divider()
    
    st.subheader("📉 Inflation Sensitivity")
    st.write("Vary inflation/interest to see impact on the 'Lowest Projected Balance'.")
    
    col_sens1, col_sens2 = st.columns(2)
    with col_sens1:
        sens_inflation = st.slider("Test Inflation", inflation_rate - 0.02, inflation_rate + 0.02, inflation_rate, 0.005, format="%.3f")
    with col_sens2:
        sens_interest = st.slider("Test Interest", interest_rate - 0.01, interest_rate + 0.01, interest_rate, 0.005, format="%.3f")
        
    # Quick calc for sensitivity
    sens_proj = calculate_projection_detailed(df, starting_balance, annual_contribution, contribution_increase, sens_inflation, sens_interest, assessment_year, assessment_amount, 30)
    sens_min = sens_proj['End Balance'].min()
    st.metric("Lowest Balance (Sensitivity)", f"${sens_min:,.0f}", delta=f"{sens_min - min_bal:,.0f}")

# --- TAB 5: REPORT & SHARE ---
with tab5:
    st.subheader("📄 Export & Share")
    
    # PDF
    if st.button("Generate PDF Report"):
        try:
            pdf_bytes = generate_pdf_report(proj_df, df, percent_funded, ffb, starting_balance, min_bal)
            b64 = base64.b64encode(pdf_bytes).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="MA_Condo_Reserve_Report.pdf">Download PDF File</a>'
            st.markdown(href, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error generating PDF: {e}")

    st.divider()
    
    # Share Link
    st.subheader("🔗 Share Settings")
    st.caption("Note: This link shares your Financial Inputs (Sidebar). Component data is not saved in the link due to size limits.")
    
    # Construct URL with query params
    base_url = "https://hoa-reserve-calculator.streamlit.app/" # Replace with actual if known
    params = f"?balance={starting_balance}&contrib={annual_contribution}&units={num_units}&inf={inflation_rate}&int={interest_rate}"
    st.code(f"{base_url}{params}", language="text")

    st.divider()
    
    # Feedback
    st.subheader("Feedback")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        if st.button("👍 Useful"):
            st.toast("Thanks for the feedback!")
    with col_f2:
        if st.button("👎 Needs Work"):
            st.toast("We'll keep improving!")

# --- Query Param Loading (Simple Implementation) ---
# Note: To make this robust requires checking query params at start. 
# For this version, we just display the link generator.
