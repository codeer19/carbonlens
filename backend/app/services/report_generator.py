"""
CarbonLens — ESG PDF Report Generator
Generates a professional ESG compliance report as a downloadable PDF.
Uses FPDF2 for PDF generation.
"""

import io
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from fpdf import FPDF


class CarbonLensReport(FPDF):
    """Custom FPDF class with CarbonLens branding."""
    
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)
    
    def header(self):
        """Page header with CarbonLens branding."""
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(34, 139, 34)  # Forest green
        self.cell(0, 8, 'CarbonLens ESG Report', align='L')
        self.set_font('Helvetica', '', 8)
        self.set_text_color(136, 136, 136)
        self.cell(0, 8, f'Generated: {datetime.now().strftime("%d %b %Y, %I:%M %p")}', align='R', new_x="LMARGIN", new_y="NEXT")
        # Separator line
        self.set_draw_color(232, 232, 228)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)
    
    def footer(self):
        """Page footer."""
        self.set_y(-15)
        self.set_font('Helvetica', '', 7)
        self.set_text_color(136, 136, 136)
        self.cell(0, 10, f'CarbonLens - India\'s SME Carbon Intelligence Platform  |  Page {self.page_no()}/{{nb}}', align='C')


def generate_esg_report(
    company_name: str = "Sample SME",
    industry: str = "Manufacturing",
    monthly_kwh: float = 8500,
    co2_kg: float = 6086,
    carbon_score: int = 75,
    grade: str = "B+",
    scan_history: Optional[List[Dict[str, Any]]] = None,
) -> bytes:
    """
    Generate a comprehensive ESG PDF report.
    
    Args:
        company_name: Company name
        industry: Industry sector
        monthly_kwh: Monthly energy consumption in kWh
        co2_kg: Monthly CO2 emissions in kg
        carbon_score: Carbon score (0-100)
        grade: Carbon grade (A/B+/B/C/D)
        scan_history: Optional list of previous scan results
        
    Returns:
        PDF bytes ready for download
    """
    pdf = CarbonLensReport()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # ── COVER / TITLE ──
    pdf.ln(15)
    pdf.set_font('Helvetica', 'B', 28)
    pdf.set_text_color(17, 17, 17)
    pdf.cell(0, 14, 'ESG Compliance Report', align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font('Helvetica', '', 12)
    pdf.set_text_color(136, 136, 136)
    pdf.cell(0, 8, 'Environmental, Social & Governance Assessment', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(34, 139, 34)
    pdf.cell(0, 10, company_name, align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(136, 136, 136)
    pdf.cell(0, 6, f'Industry: {industry}  |  Report Period: {datetime.now().strftime("%B %Y")}', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(15)
    
    # ── EXECUTIVE SUMMARY ──
    _section_header(pdf, '1. Executive Summary')
    
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(68, 68, 68)
    summary_text = (
        f"This report provides a comprehensive assessment of {company_name}'s environmental impact, "
        f"focusing on carbon emissions, energy consumption, and sustainability practices. "
        f"Based on the analysis of utility bills and energy data, the company currently emits approximately "
        f"{co2_kg:,.0f} kg of CO2 per month from an energy consumption of {monthly_kwh:,.0f} kWh/month. "
        f"The current Carbon Score is {carbon_score}/100 (Grade: {grade})."
    )
    pdf.multi_cell(0, 5.5, summary_text)
    pdf.ln(8)
    
    # ── KEY METRICS TABLE ──
    _section_header(pdf, '2. Key Environmental Metrics')
    
    # Metrics table
    metrics = [
        ('Metric', 'Value', 'Status'),
        ('Monthly Energy Consumption', f'{monthly_kwh:,.0f} kWh', _get_energy_status(monthly_kwh)),
        ('Monthly CO2 Emissions', f'{co2_kg:,.0f} kg', _get_co2_status(co2_kg)),
        ('Annual CO2 Projection', f'{co2_kg * 12:,.0f} kg', ''),
        ('Carbon Score', f'{carbon_score}/100', grade),
        ('Grid Emission Factor', '0.716 kg CO2/kWh', 'CEA 2024'),
        ('Estimated Monthly Cost', f'Rs {monthly_kwh * 8:,.0f}', ''),
        ('CO2 per Rs 1,000 spent', f'{(co2_kg / (monthly_kwh * 8) * 1000):.1f} kg', ''),
    ]
    
    _draw_table(pdf, metrics)
    pdf.ln(8)
    
    # ── EMISSIONS BREAKDOWN ──
    _section_header(pdf, '3. Emissions Breakdown')
    
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(68, 68, 68)
    
    scope1 = co2_kg * 0.15  # Estimate 15% from direct fuel
    scope2 = co2_kg * 0.85  # 85% from purchased electricity
    scope3 = co2_kg * 0.10  # Estimate 10% indirect
    
    breakdown = [
        ('Scope', 'Source', 'Estimated CO2 (kg/month)', '% of Total'),
        ('Scope 1', 'Direct fuel combustion', f'{scope1:,.0f}', '15%'),
        ('Scope 2', 'Purchased electricity', f'{scope2:,.0f}', '85%'),
        ('Scope 3*', 'Indirect (est.)', f'{scope3:,.0f}', '~10%'),
    ]
    
    _draw_table(pdf, breakdown)
    pdf.ln(3)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(136, 136, 136)
    pdf.cell(0, 5, '* Scope 3 is estimated based on industry averages and is not included in the total.', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    
    # ── CARBON SCORE ANALYSIS ──
    _section_header(pdf, '4. Carbon Score Analysis')
    
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(68, 68, 68)
    
    score_analysis = _get_score_analysis(carbon_score, grade, company_name)
    pdf.multi_cell(0, 5.5, score_analysis)
    pdf.ln(5)
    
    # Score scale
    scores = [
        ('Grade', 'Score Range', 'Description'),
        ('A', '90-100', 'Excellent - Industry leader in sustainability'),
        ('B+', '75-89', 'Good - Above average with room for improvement'),
        ('B', '60-74', 'Average - Meets basic standards'),
        ('C', '45-59', 'Below Average - Significant improvement needed'),
        ('D', '0-44', 'Poor - Urgent action required'),
    ]
    _draw_table(pdf, scores)
    pdf.ln(8)
    
    # ── RECOMMENDATIONS ──
    pdf.add_page()
    _section_header(pdf, '5. AI-Powered Recommendations')
    
    recommendations = [
        {
            'title': 'Solar Energy Transition',
            'detail': f'Installing rooftop solar panels for 20% of energy needs could save approximately {monthly_kwh * 0.20 * 0.716:,.0f} kg CO2/month and Rs {monthly_kwh * 0.20 * 8 * 0.70:,.0f}/month in electricity costs.',
            'impact': 'High',
            'timeline': '6-12 months'
        },
        {
            'title': 'Peak Hour Load Shifting',
            'detail': 'Moving heavy machinery operations to off-peak hours (10 PM - 6 AM) can reduce electricity cost by 15-20% due to Time-of-Day tariff benefits.',
            'impact': 'Medium',
            'timeline': '1-3 months'
        },
        {
            'title': 'LED Lighting Upgrade',
            'detail': 'Replacing conventional lighting with LED systems can reduce lighting energy consumption by 60-70%, saving approximately 200-500 kWh/month.',
            'impact': 'Medium',
            'timeline': '1-2 months'
        },
        {
            'title': 'Energy Audit & Monitoring',
            'detail': 'Implementing IoT-based energy monitoring can identify wastage points and optimize consumption. Typical savings: 10-15% of total energy bill.',
            'impact': 'High',
            'timeline': '3-6 months'
        },
        {
            'title': 'EV Fleet Transition',
            'detail': 'Transitioning 30% of the vehicle fleet to EVs could reduce transport-related emissions by approximately 40% and fuel costs by 60%.',
            'impact': 'High',
            'timeline': '12-24 months'
        },
    ]
    
    for i, rec in enumerate(recommendations, 1):
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(17, 17, 17)
        pdf.cell(0, 7, f'{i}. {rec["title"]}', new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(68, 68, 68)
        pdf.multi_cell(0, 5, rec['detail'])
        
        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(34, 139, 34)
        pdf.cell(0, 5, f'Impact: {rec["impact"]}  |  Timeline: {rec["timeline"]}', new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
    
    # ── POTENTIAL SAVINGS ──
    _section_header(pdf, '6. Potential Impact Summary')
    
    solar_save = monthly_kwh * 0.20 * 0.716
    led_save = 350 * 0.716
    peak_save = monthly_kwh * 0.05 * 0.716
    total_save = solar_save + led_save + peak_save
    
    savings = [
        ('Initiative', 'CO2 Saved (kg/mo)', 'Cost Saved (Rs/mo)', 'Priority'),
        ('20% Solar', f'{solar_save:,.0f}', f'{monthly_kwh * 0.20 * 8 * 0.70:,.0f}', 'High'),
        ('LED Upgrade', f'{led_save:,.0f}', f'{350 * 8:,.0f}', 'Medium'),
        ('Peak Shifting', f'{peak_save:,.0f}', f'{monthly_kwh * 0.05 * 8 * 0.15:,.0f}', 'Medium'),
        ('TOTAL', f'{total_save:,.0f}', f'{monthly_kwh * 0.20 * 8 * 0.70 + 350 * 8 + monthly_kwh * 0.05 * 8 * 0.15:,.0f}', ''),
    ]
    _draw_table(pdf, savings)
    pdf.ln(8)
    
    # ── REGULATORY CONTEXT ──
    _section_header(pdf, '7. Indian Regulatory Context')
    
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(68, 68, 68)
    regs = (
        "India's evolving ESG landscape includes several key frameworks relevant to SMEs:\n\n"
        "- BRSR (Business Responsibility and Sustainability Reporting): Mandatory for top 1000 listed companies, "
        "voluntary for SMEs. Early adoption demonstrates sustainability commitment.\n\n"
        "- PAT Scheme (Perform, Achieve and Trade): Bureau of Energy Efficiency scheme for energy-intensive industries. "
        "SMEs in designated sectors must comply with energy efficiency targets.\n\n"
        "- Carbon Credit Trading Scheme (CCTS): India's upcoming carbon market framework will create opportunities "
        "for SMEs to monetize emission reductions through carbon credit trading.\n\n"
        "- National Action Plan on Climate Change (NAPCC): Eight national missions including the National Solar "
        "Mission and National Mission for Enhanced Energy Efficiency provide policy support for green transitions."
    )
    pdf.multi_cell(0, 5.5, regs)
    pdf.ln(8)
    
    # ── DISCLAIMER ──
    pdf.ln(5)
    pdf.set_draw_color(232, 232, 228)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    pdf.set_font('Helvetica', 'I', 7)
    pdf.set_text_color(170, 170, 170)
    disclaimer = (
        "Disclaimer: This report is auto-generated by CarbonLens AI platform based on uploaded bill data and "
        "standard emission factors (CEA 2024). Scope 3 emissions are estimated. This report is for informational "
        "purposes only and does not constitute professional ESG audit or certification. For regulatory compliance, "
        "please consult a certified ESG auditor. Powered by Grok AI + Tesseract OCR."
    )
    pdf.multi_cell(0, 4, disclaimer)
    
    # Return PDF as bytes
    return pdf.output()


def _section_header(pdf: FPDF, title: str):
    """Draw a styled section header."""
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(17, 17, 17)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(34, 139, 34)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 60, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(5)


def _draw_table(pdf: FPDF, rows: list):
    """Draw a simple table."""
    if not rows:
        return
    
    col_count = len(rows[0])
    col_width = (190) / col_count
    
    for i, row in enumerate(rows):
        if i == 0:
            # Header row
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_fill_color(245, 245, 243)
            pdf.set_text_color(17, 17, 17)
        elif i == len(rows) - 1 and rows[-1][0] == 'TOTAL':
            # Total row
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_fill_color(240, 253, 244)
            pdf.set_text_color(22, 101, 52)
        else:
            pdf.set_font('Helvetica', '', 9)
            pdf.set_fill_color(255, 255, 255)
            pdf.set_text_color(68, 68, 68)
        
        for j, cell in enumerate(row):
            pdf.cell(col_width, 7, str(cell), border=0, fill=True,
                    align='L' if j == 0 else 'C')
        pdf.ln()


def _get_energy_status(kwh: float) -> str:
    if kwh < 3000: return 'Low'
    if kwh < 6000: return 'Moderate'
    if kwh < 10000: return 'High'
    return 'Very High'


def _get_co2_status(co2: float) -> str:
    if co2 < 2000: return 'Low'
    if co2 < 4500: return 'Moderate'
    if co2 < 7000: return 'High'
    return 'Very High'


def _get_score_analysis(score: int, grade: str, company: str) -> str:
    if score >= 90:
        return (f"{company} has achieved an excellent Carbon Score of {score}/100 (Grade {grade}). "
                "The company demonstrates strong environmental stewardship and is well-positioned "
                "for upcoming ESG regulatory requirements.")
    elif score >= 75:
        return (f"{company} has a good Carbon Score of {score}/100 (Grade {grade}). "
                "The company shows above-average environmental practices but has clear opportunities "
                "for further improvement, particularly in renewable energy adoption and energy efficiency.")
    elif score >= 60:
        return (f"{company} has an average Carbon Score of {score}/100 (Grade {grade}). "
                "The company meets basic environmental standards but should prioritize emission reduction "
                "initiatives to improve competitiveness and prepare for tightening regulations.")
    elif score >= 45:
        return (f"{company} has a below-average Carbon Score of {score}/100 (Grade {grade}). "
                "Significant improvements are needed across energy efficiency, renewable adoption, "
                "and emission monitoring to align with industry best practices.")
    else:
        return (f"{company} has a poor Carbon Score of {score}/100 (Grade {grade}). "
                "Urgent action is required to address high emissions and energy inefficiency. "
                "Immediate steps should include an energy audit, LED transition, and solar feasibility study.")
