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
        try:
            ul = float(row['Useful Life'])
            rul = float(row['Remaining Useful Life'])
            cost = float(row['Current Cost'])
            if ul > 0:
                effective_age = max(0, ul - rul)
                component_ffb = cost * (effective_age / ul)
                total_ffb += component_ffb
        except:
            continue
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
    
    # Pre-calculate project expenses and replacement years
    for index, row in df.iterrows():
        try:
            cost = float(row['Current Cost'])
            rul = int(row['Remaining Useful Life'])
            ul = int(row['Useful Life'])
            name = str(row['Component Name'])
            
            if ul > 0:
                replace_year = rul + 1
                while replace_year <= years_to_project:
                    # Future cost calculation based on inflation
                    future_cost = cost * ((1 + inflation_rate) ** (replace_year - 1))
                    expenditures_by_year[replace_year] += future_cost
                    projects_by_year[replace_year].append(f"{name} (${future_cost:,.0f})")
                    replace_year += ul
        except:
            continue

    # Cash flow loop
    for year in range(1, years_to_project + 1):
        start_of_year_balance = current_balance
        interest_earned = start_of_year_balance * interest_rate
        
        # Increase contribution after the first year
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

def generate_ai_suggestions(percent_funded, min_bal, failure_year):
    """Generates dynamic 'AI' suggestions based on financial health."""
    suggestions = []
    
    # Check Percent Funded Status
    if percent_funded < 30:
        if min_bal < 0:
             suggestions.append("🔴 **CRITICAL DANGER:** Fund is critically low and fails in Year " + str(failure_year) + ". Immediate Special Assessment and contribution increase required.")
             suggestions.append("💡 **Strategy:** Use the Minimizer tool to calculate the needed assessment, and the 70% Solver tool for long-term rate changes.")
        else:
             suggestions.append("🟡 **LONG-TERM DEFICIT:** Percent Funded is critically low (<30%), risking bank loans and compliance, even if cash flow is currently positive.")
             suggestions.append("💡 **Strategy:** Focus on long-term health. Use the Solver tool to find the contribution needed to reach a stable funding target (like 70%).")
    elif percent_funded < 70:
        suggestions.append("🟡 **WARNING:** You are in the 'High Risk' zone. Massachusetts lenders prefer >70% funded.")
        suggestions.append(f"💡 **Strategy:** Increase annual contributions aggressively (e.g., 5-8% annually) for the next 5 years to stabilize.")
    else:
        suggestions.append("✅ **Excellent Status:** Your fund is above the 70% threshold recommended by professionals.")
        
    # Always include cash flow check
    if min_bal < 0:
        suggestions.append(f"❌ **CASH FLOW FAILURE:** Your account runs out of money in **Year {failure_year}**.")
        suggestions.append(f"💡 **Fix:** You must levy a Special Assessment or increase contributions *before* Year {failure_year}.")
        
    return suggestions

def generate_pdf_report(proj_df, component_df, percent_funded, ffb, starting_balance, min_bal, ai_suggestions):
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
    pdf.cell(200, 10, txt="AI-Generated Strategic Suggestions", ln=True)
    pdf.set_font("Arial", size=10)
    for suggestion in ai_suggestions:
        # Strip markdown for PDF
        clean_text = suggestion.replace("**", "").replace("🔴", "").replace("🟡", "").replace("💡", "").replace("❌", "").replace("✅", "")
        pdf.multi_cell(0, 10, f"- {clean_text}")

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
        try:
            pdf.cell(col_width, 10, str(row['Component Name'])[:20], 1)
            pdf.cell(30, 10, f"${float(row['Current Cost']):,.0f}", 1)
            pdf.cell(20, 10, str(int(row['Useful Life'])), 1)
            pdf.cell(20, 10, str(int(row['Remaining Useful Life'])), 1)
            pdf.ln()
        except:
            continue

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
if num_units > 0:
    per_unit_monthly = annual_contribution / num_units / 12
    st.sidebar.markdown(f"<h2 style='text-align: center; color: #4CAF50;'>${per_unit_monthly:,.2f}</h2>", unsafe_allow_html=True)
    st.sidebar.markdown("<p style='text-align: center;'><b>per unit / per month</b></p>", unsafe_allow_html=True)

contribution_increase = st.sidebar.slider("Annual Dues Increase (%)", 0.0, 10.0, 2.0, 0.1) / 100

st.sidebar.header("3. Economic Assumptions")
# Hard-coded defaults
inflation_rate_default = 3.2
interest_rate_default = 1.8

inflation_rate = st.sidebar.slider("Inflation Rate (%)", 0.0, 10.0, inflation_rate_default, 0.1) / 100
interest_rate = st.sidebar.slider("Interest Rate on Savings (%)", 0.0, 8.0, interest_rate_default, 0.1) / 100

st.sidebar.header("4. Special Assessment")
assessment_year = st.sidebar.number_input("Assessment Year", 1, 30, 1)
assessment_amount = st.sidebar.number_input("Total Assessment ($)", min_value=0.0, value=0.0, step=5000.0, format="%.2f")

# Show the impact per unit immediately
if assessment_amount > 0 and num_units > 0:
    cost_per_unit = assessment_amount / num_units
    st.sidebar.warning(f"⚠️ Cost Per Unit: **${cost_per_unit:,.2f}**")

# --- TAB 2: COMPONENTS (Editable & Upload) ---
with tab2:
    st.subheader("Manage Component Inventory")
    
    # --- FILE UPLOADER SECTION ---
    st.markdown("#### 📂 Upload Existing Study")
    uploaded_file = st.file_uploader("Upload a CSV file to automatically populate this table", type=['csv'])
    
    if uploaded_file is not None:
        try:
            # Read CSV
            new_data = pd.read_csv(uploaded_file)
            
            # Simple column mapping to standardize inputs
            col_map = {
                'Component': 'Component Name', 'Item': 'Component Name', 'Name': 'Component Name',
                'Cost': 'Current Cost', 'Replacement Cost': 'Current Cost',
                'UL': 'Useful Life', 'Life': 'Useful Life',
                'RUL': 'Remaining Useful Life', 'Remaining': 'Remaining Useful Life'
            }
            new_data.rename(columns=col_map, inplace=True)
            
            # Check for required columns
            required = ['Component Name', 'Current Cost', 'Useful Life', 'Remaining Useful Life']
            if all(col in new_data.columns for col in required):
                # Ensure numeric types
                new_data['Current Cost'] = pd.to_numeric(new_data['Current Cost'], errors='coerce').fillna(0)
                new_data['Useful Life'] = pd.to_numeric(new_data['Useful Life'], errors='coerce').fillna(0)
                new_data['Remaining Useful Life'] = pd.to_numeric(new_data['Remaining Useful Life'], errors='coerce').fillna(0)
                
                # Update Session State
                st.session_state.component_df = new_data
                st.success("✅ Reserve Study Loaded Successfully! Reloading component list...")
                st.rerun()
            else:
                st.error(f"❌ CSV is missing required columns. It needs: {required}")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    st.divider()
    
    # --- MANUAL EDIT SECTION ---
    st.markdown("#### ✏️ Manual Edit")
    st.info("Add, edit, or delete rows below. Data saves automatically.")
    
    # Presets Logic
    BOSTON_PRESETS = {
        "Asphalt Roof (Large)": {'Component Name': 'New Asphalt Roof', 'Current Cost': 120000.0, 'Useful Life': 25, 'Remaining Useful Life': 25, 'Notes': 'Boston Avg'},
        "Rubber Roof (Flat)": {'Component Name': 'EPDM Rubber Roof', 'Current Cost': 80000.0, 'Useful Life': 20, 'Remaining Useful Life': 20, 'Notes': 'Boston Avg'},
        "Boiler System": {'Component Name': 'Commercial Boiler', 'Current Cost': 45000.0, 'Useful Life': 25, 'Remaining Useful Life': 15, 'Notes': 'Boston Avg'},
        "Elevator Modernization": {'Component Name': 'Elevator Mod', 'Current Cost': 100000.0, 'Useful Life': 25, 'Remaining Useful Life': 10, 'Notes': 'Hydraulic'},
        "Ext. Painting (Wood)": {'Component Name': 'Full Ext Paint', 'Current Cost': 25000.0, 'Useful Life': 6, 'Remaining Useful Life': 3, 'Notes': 'Cycles fast in NE'},
        "Paving Overlay": {'Component Name': 'Pavement Overlay', 'Current Cost': 35000.0, 'Useful Life': 20, 'Remaining Useful Life': 5, 'Notes': '2 inch overlay'}
    }
    
    col_preset, col_btn = st.columns([3, 1])
    with col_preset:
        preset_option = st.selectbox("Quick Add (2025 Greater Boston Averages)", ["Select..."] + list(BOSTON_PRESETS.keys()))
    with col_btn:
        st.write("") 
        st.write("") 
        if st.button("Add Preset"):
            if preset_option != "Select...":
                new_row = BOSTON_PRESETS[preset_option]
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
# NOTE TO USER: This is the line your error pointed to (Line 308). The syntax is now double-checked.
proj_df = calculate_projection_detailed(
    df, starting_balance, annual_contribution, contribution_increase,
    inflation_rate, interest_rate, assessment_year, assessment_amount, 30
)
min_bal = proj_df['End Balance'].min()
failure_year = proj_df[proj_df['End Balance'] < 0].iloc[0]['Year'] if min_bal < 0 else None

# Generate AI Suggestions
ai_suggestions = generate_ai_suggestions(percent_funded, min_bal, failure_year)

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
                {'range': [0, 50], 'color': "#FFCDD2"},  # Red < 50%
                {'range': [50, 70], 'color': "#FFF9C4"}, # Yellow 50-69%
                {'range': [70, 130], 'color': "#C8E6C9"} # Green >= 70%
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

    # Key Metrics
    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    with col_k1: st.metric("Starting Balance", f"${starting_balance:,.2f}")
    with col_k2: 
        st.metric("Fully Funded Balance", f"${ffb:,.2f}")
        with st.expander("How this is calculated"):
             st.write("Sum of (Current Replacement Cost × Years Already Used ÷ Total Useful Life) for every component – the CAI-recommended Component Method used by every Massachusetts reserve study firm.")
    with col_k3: st.metric("Annual Contribution", f"${annual_contribution:,.2f}")
    with col_k4: st.metric("Lowest Projected Balance", f"${min_bal:,.2f}", delta_color="off" if min_bal > 0 else "inverse")
    
    # AI Analysis Box
    st.markdown("### 🤖 AI Financial Analyst")
    for suggestion in ai_suggestions:
        st.markdown(suggestion)

    st.divider()

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
        hover_data={'Year': True, 'End Balance': ':$.2f', 'Expenditures': ':$.2f', 'Projects': True},
        title="Projected Year-End Balance (Hover for Project Details)"
    )
    fig_bar.add_trace(go.Scatter(x=proj_df['Year'], y=proj_df['Expenditures'], mode='lines', name='Expenses', line=dict(color='orange', width=2, dash='dot')))
    st.plotly_chart(fig_bar, use_container_width=True)

# --- TAB 3: TIMELINE (Gantt Chart) ---
with tab3:
    st.subheader("Projected Replacement Timeline")
    
    # Prepare Gantt Data
    gantt_data = []
    current_year_val = datetime.now().year
    
    for index, row in df.iterrows():
        try:
            rul = int(row['Remaining Useful Life'])
            ul = int(row['Useful Life'])
            name = row['Component Name']
            cost = float(row['Current Cost'])
            
            if ul > 0:
                last_rep_year = current_year_val - rul
                
                i = 0
                while True:
                    replacement_year = last_rep_year + (ul * i)
                    
                    if replacement_year > current_year_val and replacement_year <= current_year_val + 30:
                        year_offset = replacement_year - current_year_val
                        future_cost = cost * ((1 + inflation_rate) ** year_offset)
                        
                        gantt_data.append(dict(
                            Task=name, 
                            Start=datetime(replacement_year, 1, 1), 
                            Finish=datetime(replacement_year, 12, 31),
                            Cost=f"${future_cost:,.0f}"
                        ))
                    
                    if replacement_year > current_year_val + 30:
                        break
                    
                    i += 1
        except:
            continue

    if gantt_data:
        gantt_df = pd.DataFrame(gantt_data)
        
        fig_gantt = px.timeline(
            gantt_df, 
            x_start="Start", 
            x_end="Finish", 
            y="Task", 
            color="Task", 
            color_discrete_sequence=px.colors.qualitative.Pastel,
            hover_data={"Start": "|%Y", "Finish": "|%Y", "Task": False, "Cost": True}
        )
        fig_gantt.update_yaxes(autorange="reversed")
        fig_gantt.update_layout(
            title="Component Replacement Schedule (30 Years)",
            xaxis_title="Year",
            height=600 
        )
        st.plotly_chart(fig_gantt, use_container_width=True)
    else:
        st.write("Please add components in the 'Components' tab to see the timeline.")

# --- TAB 4: SENSITIVITY & TOOLS ---
with tab4:
    st.subheader("🛠️ Solvers & Optimizers")
    
    col_solver, col_min = st.columns(2)
    
    # SOLVER 1: REACH 70% 
    with col_solver:
        st.markdown("#### 🎯 Contribution to Reach 70% Funded in 5 Years")
        if st.button("Calculate Minimum Contribution"):
            
            test_contribution = max(1.0, annual_contribution + 1.0)
            
            found = False
            for i in range(1000): 
                temp_proj = calculate_projection_detailed(df, starting_balance, test_contribution, contribution_increase, inflation_rate, interest_rate, assessment_year, assessment_amount, 5)
                
                future_ffb = ffb * ((1+inflation_rate)**5)
                yr5_bal = temp_proj.iloc[4]['End Balance']
                
                if (yr5_bal / future_ffb) >= 0.70:
                    found = True
                    break
                    
                test_contribution += 100
            
            if found:
                if test_contribution - annual_contribution <= 100:
                    st.success(f"You already meet the 70% target in 5 years with the current ${annual_contribution:,.0f} contribution!")
                else:
                    req_monthly = test_contribution / num_units / 12
                    st.success(f"Required Annual Contribution: ${test_contribution:,.0f}")
                    st.metric("New Monthly/Unit Cost", f"${req_monthly:,.2f}")
            else:
                st.warning("Could not find a reasonable solution within limits ($100,000 increase) to reach 70% funded.")

    # SOLVER 2: MINIMIZER
    with col_min:
        st.markdown("#### 🛡️ Special Assessment Minimizer")
        st.caption("Finds the smallest assessment needed to keep balance > $0.")
        if st.button("Find Minimum Assessment"):
            if min_bal >= 0:
                st.success("No assessment needed! You are fully funded.")
            else:
                deficit = abs(min_bal)
                rec_assess = deficit
                per_unit_assess = rec_assess / num_units
                st.error(f"Recommended Assessment (Total): ${rec_assess:,.0f}")
                st.metric("Cost Per Unit", f"${per_unit_assess:,.2f}")
                st.info("Apply this in Sidebar 'Special Assessment' to verify the fix.")

    st.divider()
    
    st.subheader("📉 Inflation Sensitivity Analysis")
    st.write("Vary assumptions to instantly see the impact on the lowest balance.")
    
    col_sens1, col_sens2 = st.columns(2)
    with col_sens1:
        sens_inflation = st.slider("Test Inflation (%)", inflation_rate_default - 2.0, inflation_rate_default + 2.0, inflation_rate_default, 0.1, format="%.1f") / 100
    with col_sens2:
        sens_interest = st.slider("Test Interest (%)", interest_rate_default - 1.0, interest_rate_default + 1.0, interest_rate_default, 0.1, format="%.1f") / 100
        
    sens_proj = calculate_projection_detailed(df, starting_balance, annual_contribution, contribution_increase, sens_inflation, sens_interest, assessment_year, assessment_amount, 30)
    sens_min = sens_proj['End Balance'].min()
    st.metric("Lowest Balance (Sensitivity)", f"${sens_min:,.2f}", delta=f"{sens_min - min_bal:,.2f}", delta_color="inverse" if sens_min < min_bal else "normal")


# --- TAB 5: REPORT & SHARE ---
with tab5:
    st.subheader("📄 Export & Share")
    
    # PDF
    if st.button("Download PDF Report"):
        try:
            pdf_bytes = generate_pdf_report(proj_df, df, percent_funded, ffb, starting_balance, min_bal, ai_suggestions)
            # Ensure encoding matches FPDF output
            b64 = base64.b64encode(pdf_bytes).decode('latin-1') 
            href = f'<a href="data:application/pdf;base64,{b64}" download="MA_Condo_Reserve_Report.pdf">Click here to download the PDF report.</a>'
            st.markdown(href, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error generating PDF: {e}. Ensure the 'fpdf' library is installed correctly.")

    st.divider()
    
    st.subheader("🔗 Share Settings")
    st.caption("The link below encodes your financial assumptions. Component data must be re-uploaded or manually entered by the recipient.")
    
    # Construct URL with query params
    # NOTE: In a live environment, replace this with your deployed URL
    base_url = "https://hoa-reserve-calculator.streamlit.app/" 
    params = f"balance={starting_balance}&contrib={annual_contribution}&units={num_units}&inf={inflation_rate*100}&int={interest_rate*100}"
    
    st.code(f"Your custom view link: {base_url}?{params}", language="text")
    st.button("Copy Results Link") 

    st.divider()
    
    st.subheader("Feedback")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.button("👍 Useful")
    with col_f2:
        st.button("👎 Needs Work")
