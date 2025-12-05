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
    Calculates 30-year projection AND the Percent Funded trajectory.
    """
    projection_data = []
    current_balance = start_balance
    current_contribution = annual_contribution
    
    # 1. Pre-calculate project expenses and replacement years
    expenditures_by_year = {year: 0 for year in range(1, years_to_project + 1)}
    projects_by_year = {year: [] for year in range(1, years_to_project + 1)}
    
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

    # 2. Cash flow loop
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
        
        # 3. Calculate Future Fully Funded Balance (FFB) for this specific year
        year_ffb_sum = 0
        for index, row in df.iterrows():
            try:
                ul = float(row['Useful Life'])
                start_rul = float(row['Remaining Useful Life'])
                base_cost = float(row['Current Cost'])
                
                if ul > 0:
                    # Adjust cost for inflation up to this year
                    future_component_cost = base_cost * ((1 + inflation_rate) ** year)
                    
                    # Calculate RUL at this specific future year
                    # Logic: Decrease RUL by years passed. If < 0, add UL (simulate replacement reset)
                    years_passed = year
                    current_rul_at_year = start_rul - years_passed
                    while current_rul_at_year < 0:
                        current_rul_at_year += ul
                    
                    # Effective Age now
                    eff_age_now = max(0, ul - current_rul_at_year)
                    
                    item_ffb = future_component_cost * (eff_age_now / ul)
                    year_ffb_sum += item_ffb
            except:
                continue
        
        # Calculate Percent Funded
        pct_funded = (end_of_year_balance / year_ffb_sum * 100) if year_ffb_sum > 0 else 100.0

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
            'Future FFB': year_ffb_sum,
            'Percent Funded': pct_funded,
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
    pdf.cell(200, 10, txt="1. Financial Snapshot", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Current Reserve Balance: ${starting_balance:,.2f}", ln=True)
    pdf.cell(200, 10, txt=f"Current Fully Funded Balance: ${ffb:,.2f}", ln=True)
    pdf.cell(200, 10, txt=f"Current Percent Funded: {percent_funded:.1f}%", ln=True)
    pdf.cell(200, 10, txt=f"Lowest Projected Balance (30 Years): ${min_bal:,.2f}", ln=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="2. AI-Generated Strategic Suggestions", ln=True)
    pdf.set_font("Arial", size=10)
    for suggestion in ai_suggestions:
        clean_text = suggestion.replace("**", "").replace("🔴", "").replace("🟡", "").replace("💡", "").replace("❌", "").replace("✅", "")
        pdf.multi_cell(0, 10, f"- {clean_text}")

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="3. Funding Trajectory (Years 1-10)", ln=True)
    pdf.set_font("Arial", size=9)
    
    # Funding Table Header
    pdf.cell(20, 8, "Year", 1)
    pdf.cell(45, 8, "Cash Balance", 1)
    pdf.cell(45, 8, "Ideal Goal (FFB)", 1)
    pdf.cell(30, 8, "% Funded", 1)
    pdf.ln()
    
    # Funding Table Rows (First 10 years to fit page)
    for index, row in proj_df.head(10).iterrows():
        pdf.cell(20, 8, str(int(row['Year'])), 1)
        pdf.cell(45, 8, f"${row['End Balance']:,.0f}", 1)
        pdf.cell(45, 8, f"${row['Future FFB']:,.0f}", 1)
        
        # Color code logic for text (simplified for FPDF black/white standard)
        pct = row['Percent Funded']
        status = "Crit." if pct < 30 else ("Risk" if pct < 70 else "Good")
        pdf.cell(30, 8, f"{pct:.1f}% ({status})", 1)
        pdf.ln()

    pdf.ln(10)
    pdf.set_font("Arial", 'I', 10)
    pdf.multi_cell(0, 10, "Disclaimer: This report is a mathematical simulation based on user inputs. It is not a substitute for a professional Reserve Study.")
    
    return pdf.output(dest='S').encode('latin-1')

# --- Initialization of Session State for Components ---
if 'component_df' not in st.session_state:
    # Default Starting Data
    default_data = {
        'Component Name': ['
