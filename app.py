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
            continue # Skip invalid rows
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
        try:
            cost = float(row['Current Cost'])
            rul = int(row['Remaining Useful Life'])
            ul = int(row['Useful Life'])
            name = str(row['Component Name'])
            
            if ul > 0:
                replace_year = rul + 1
                while replace_year <= years_to_project:
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
    
    if percent_funded < 30:
        if min_bal < 0:
             # Critical AND cash flow failure
             suggestions.append("🔴 **CRITICAL DANGER:** Your fund is critically low, *and* your cash flow fails in Year " + str(failure_year) + ". Immediate corrective action is required.")
             suggestions.append("💡 **Strategy:** You must implement a large Special Assessment *and* increase ongoing contributions to address both the short-term cash crisis and the long-term deficit.")
        else:
             # Critical but cash flow safe (Addressing the contradiction)
             suggestions.append("🟡 **LONG-TERM DEFICIT:** Your Percent Funded is critically low (<30%), posing a risk for bank loans and compliance, even though current contributions cover bills.")
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
    pdf.multi_cell(0
