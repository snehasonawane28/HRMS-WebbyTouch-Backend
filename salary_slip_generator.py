"""
Salary Slip Generator - WebbyTouch Infotech Format
Exact same format as the uploaded PDF
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import io, os

# ── Brand Colors (matching the PDF) ──
MAROON      = colors.HexColor("#6B1226")
LIGHT_BG    = colors.HexColor("#F5F0EB")   # warm cream background
TABLE_BG    = colors.HexColor("#FFFFFF")
HEADER_TEXT = colors.HexColor("#6B1226")
LABEL_COL   = colors.HexColor("#F5F0EB")   # left label cells
WHITE       = colors.white
BLACK       = colors.HexColor("#1A1A1A")

W, H = A4   # 595 x 842 pts


def draw_salary_slip(salary_data: dict, output_path: str):
    c = canvas.Canvas(output_path, pagesize=A4)

    # ── Background ──
    c.setFillColor(LIGHT_BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # ── Top decorative diagonal shape (maroon) ──
    c.setFillColor(MAROON)
    p = c.beginPath()
    p.moveTo(0, H)
    p.lineTo(0, H - 110*mm)
    p.lineTo(55*mm, H)
    p.close()
    c.drawPath(p, fill=1, stroke=0)

    # ── Small accent triangle ──
    c.setFillColor(colors.HexColor("#8B1A2E"))
    p2 = c.beginPath()
    p2.moveTo(0, H)
    p2.lineTo(0, H - 60*mm)
    p2.lineTo(25*mm, H)
    p2.close()
    c.drawPath(p2, fill=1, stroke=0)

    # ── Company Logo Area (top right) ──
    # Logo box
    logo_x, logo_y = W - 55*mm, H - 28*mm
    c.setFillColor(WHITE)
    c.roundRect(logo_x - 2*mm, logo_y - 8*mm, 52*mm, 22*mm, 4, fill=1, stroke=0)

    # "wt" logo circle
    c.setFillColor(MAROON)
    c.circle(logo_x + 8*mm, logo_y + 3*mm, 7*mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(logo_x + 8*mm, logo_y + 0.5*mm, "wt")

    # Company name
    c.setFillColor(MAROON)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(logo_x + 17*mm, logo_y + 5*mm, "WebbyTouch")
    c.setFont("Helvetica", 8)
    c.setFillColor(BLACK)
    c.drawString(logo_x + 17*mm, logo_y - 1*mm, "infotech")

    # ── Header Text (center) ──
    c.setFillColor(MAROON)
    c.setFont("Helvetica-Bold", 13)
    emp_name = salary_data.get("name", "Employee")
    c.drawCentredString(W/2, H - 20*mm, f"Hi, {emp_name}")

    c.setFont("Helvetica-Bold", 13)
    month_year = salary_data.get("month_year", "April 2026")
    c.drawCentredString(W/2, H - 28*mm, f"Payslip for the month {month_year}")

    # Date (right side below logo)
    c.setFillColor(BLACK)
    c.setFont("Helvetica", 9)
    slip_date = salary_data.get("date", "5/05/2026")
    c.drawRightString(W - 12*mm, H - 38*mm, f"Date: {slip_date}")

    # ── Separator Line ──
    c.setStrokeColor(MAROON)
    c.setLineWidth(1.2)
    c.line(12*mm, H - 42*mm, W - 12*mm, H - 42*mm)

    # ══════════════════════════════════════
    # EMPLOYEE INFO TABLE (top section)
    # ══════════════════════════════════════
    def bold_label(text):
        return Paragraph(f"<b>{text}</b>",
            ParagraphStyle("lbl", fontName="Helvetica-Bold", fontSize=8.5,
                           textColor=HEADER_TEXT, leading=12))

    def value_cell(text):
        return Paragraph(str(text),
            ParagraphStyle("val", fontName="Helvetica", fontSize=8.5,
                           textColor=BLACK, leading=12))

    col_w = [38*mm, 42*mm, 45*mm, 50*mm]

    info_data = [
        [bold_label("Name"),           value_cell(salary_data.get("name","")),
         bold_label("Employee No.:"),  value_cell(salary_data.get("emp_id",""))],
        [bold_label("Joining Date"),   value_cell(salary_data.get("joining_date","")),
         bold_label("Bank Name:"),     value_cell(salary_data.get("bank_name",""))],
        [bold_label("Designation"),    value_cell(salary_data.get("designation","")),
         bold_label("Bank Account No.:"), value_cell(salary_data.get("bank_account",""))],
        [bold_label("Department"),     value_cell(salary_data.get("department","")),
         bold_label("PAN No.:"),       value_cell(salary_data.get("pan",""))],
        [bold_label("Location"),       value_cell(salary_data.get("location","Surat")),
         bold_label("UAN No.:"),       value_cell(salary_data.get("uan","-"))],
        [bold_label("Effective Work Days"), value_cell(salary_data.get("effective_days","22")),
         bold_label("LOP:"),           value_cell(salary_data.get("lop","0.0"))],
    ]

    info_table = Table(info_data, colWidths=col_w)
    info_table.setStyle(TableStyle([
        # Alternating row backgrounds
        ('BACKGROUND', (0,0), (0,-1), LABEL_COL),
        ('BACKGROUND', (2,0), (2,-1), LABEL_COL),
        ('BACKGROUND', (1,0), (1,-1), WHITE),
        ('BACKGROUND', (3,0), (3,-1), WHITE),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))

    table_x = 12*mm
    table_top = H - 45*mm
    info_table.wrapOn(c, W - 24*mm, 200)
    info_h = info_table._height
    info_table.drawOn(c, table_x, table_top - info_h)

    # ══════════════════════════════════════
    # EARNINGS & DEDUCTIONS TABLE
    # ══════════════════════════════════════
    salary = salary_data.get("salary", {})

    def col_header(text):
        return Paragraph(f"<b>{text}</b>",
            ParagraphStyle("ch", fontName="Helvetica-Bold", fontSize=9,
                           textColor=WHITE, alignment=TA_LEFT, leading=12))

    def earn_label(text, bold=False):
        fn = "Helvetica-Bold" if bold else "Helvetica"
        return Paragraph(f"<b>{text}</b>" if bold else text,
            ParagraphStyle("el", fontName=fn, fontSize=8.5,
                           textColor=HEADER_TEXT if bold else BLACK, leading=12))

    def num_cell(val, bold=False, red=False):
        color = colors.HexColor("#CC0000") if red else BLACK
        fn = "Helvetica-Bold" if bold else "Helvetica"
        return Paragraph(str(val),
            ParagraphStyle("nc", fontName=fn, fontSize=8.5,
                           textColor=color, alignment=TA_RIGHT, leading=12))

    def num_plain(val):
        return Paragraph(str(val),
            ParagraphStyle("np", fontName="Helvetica", fontSize=8.5,
                           textColor=BLACK, alignment=TA_RIGHT, leading=12))

    # Earnings data
    basic_full   = salary.get("basic_full", 0)
    basic_actual = salary.get("basic_actual", 0)
    hra_full     = salary.get("hra_full", 0)
    hra_actual   = salary.get("hra_actual", 0)
    conv_full    = salary.get("conveyance_full", 0)
    conv_actual  = salary.get("conveyance_actual", 0)
    other_full   = salary.get("other_allowance_full", 0)
    other_actual = salary.get("other_allowance_actual", 0)
    lta_full     = salary.get("lta_full", 0)
    lta_actual   = salary.get("lta_actual", 0)
    leave_enc_full   = salary.get("leave_encashment_full", 0)
    leave_enc_actual = salary.get("leave_encashment_actual", 0)
    total_earn_full   = salary.get("total_earning_full", 0)
    total_earn_actual = salary.get("total_earning_actual", 0)

    # Deductions data
    pf          = salary.get("pf", 0)
    prof_tax    = salary.get("prof_tax", 0)
    income_tax  = salary.get("income_tax", 0)
    other_ded   = salary.get("other_deduction", 0)
    total_ded   = salary.get("total_deduction", 0)
    net_payable = salary.get("net_payable", 0)

    # col widths: Earning | Full | Actual | Deduction | Actual
    sal_col_w = [42*mm, 28*mm, 28*mm, 52*mm, 25*mm]

    sal_data = [
        # Header row
        [col_header("Earning"), col_header("Full"), col_header("Actual"),
         col_header("Deduction"), col_header("Actual")],
        # Data rows
        [earn_label("Basic"), num_plain(basic_full), num_plain(basic_actual),
         earn_label("PF"), num_plain(pf)],
        [earn_label("HRA"), num_plain(hra_full), num_plain(hra_actual),
         earn_label("Prof Tax"), num_plain(prof_tax)],
        [earn_label("Conveyance"), num_plain(conv_full), num_plain(conv_actual),
         earn_label("Income Tax"), num_plain(income_tax)],
        [earn_label("Other Allowance"), num_plain(other_full), num_plain(other_actual),
         earn_label("Other Deduction"), num_plain(other_ded)],
        [earn_label("LTA"), num_plain(lta_full), num_plain(lta_actual),
         earn_label("Total Deduction (INR)", bold=True), num_cell(total_ded, bold=True)],
        [earn_label("Leave Encashment"), num_plain(leave_enc_full), num_plain(leave_enc_actual),
         earn_label("Total Payable Amount", bold=True), num_cell(net_payable, bold=True)],
        # Total row
        [earn_label("Total Earning (INR)", bold=True),
         num_cell(total_earn_full, bold=True),
         num_cell(total_earn_actual, bold=True),
         "", ""],
    ]

    sal_table = Table(sal_data, colWidths=sal_col_w)
    sal_table.setStyle(TableStyle([
        # Header row - maroon background
        ('BACKGROUND', (0,0), (-1,0), MAROON),
        ('TEXTCOLOR', (0,0), (-1,0), WHITE),
        # Alternating row colors
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, colors.HexColor("#FAF8F5")]),
        # Grid
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#DDDDDD")),
        ('LINEBELOW', (0,0), (-1,0), 1, MAROON),
        # Vertical separator between earn and deduction
        ('LINEAFTER', (2,0), (2,-1), 1.2, MAROON),
        # Padding
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        # Total row styling
        ('BACKGROUND', (0,-1), (2,-1), colors.HexColor("#F0E8E0")),
        ('FONTNAME', (0,-1), (2,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,-1), (2,-1), MAROON),
        # Total Deduction & Payable styling
        ('BACKGROUND', (3,5), (-1,6), colors.HexColor("#F0E8E0")),
    ]))

    sal_y = table_top - info_h - 6*mm
    sal_table.wrapOn(c, W - 24*mm, 400)
    sal_h = sal_table._height
    sal_table.drawOn(c, table_x, sal_y - sal_h)

    # ══════════════════════════════════════
    # FOOTER
    # ══════════════════════════════════════
    footer_y = sal_y - sal_h - 10*mm

    # Separator line
    c.setStrokeColor(colors.HexColor("#CCCCCC"))
    c.setLineWidth(0.8)
    c.line(12*mm, footer_y, W - 12*mm, footer_y)

    footer_y -= 8*mm

    # Icons + text
    icon_y = footer_y

    # Globe icon circle
    c.setFillColor(colors.HexColor("#CCCCCC"))
    c.circle(20*mm, icon_y, 3.5*mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 6)
    c.drawCentredString(20*mm, icon_y - 2, "www")

    c.setFillColor(BLACK)
    c.setFont("Helvetica", 8.5)
    c.drawString(25*mm, icon_y - 3, "www.webbytouch.com")

    # Email icon
    c.setFillColor(colors.HexColor("#CCCCCC"))
    c.rect(W/2 - 15*mm, icon_y - 4, 7*mm, 7*mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 5)
    c.drawCentredString(W/2 - 11.5*mm, icon_y - 2, "@")

    c.setFillColor(BLACK)
    c.setFont("Helvetica", 8.5)
    c.drawString(W/2 - 6*mm, icon_y - 3, "webbytouch.infotech@gmail.com")

    # Phone icon (below)
    phone_y = icon_y - 10*mm
    c.setFillColor(colors.HexColor("#CCCCCC"))
    c.circle(W/2, phone_y, 3.5*mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 6)
    c.drawCentredString(W/2, phone_y - 2, "ph")

    c.setFillColor(BLACK)
    c.setFont("Helvetica", 8.5)
    c.drawCentredString(W/2 + 20*mm, phone_y - 3, "+91 63522 03006")

    c.save()
    print(f"[✓] Salary slip generated: {output_path}")


# ══════════════════════════════════════
# UPDATED generate_pdf IN backend
# (Replace the old generate_pdf function)
# ══════════════════════════════════════

def generate_pdf_webbytouch(salary_data_from_api: dict, config: dict) -> str:
    """
    Converts API salary data to WebbyTouch format and generates PDF.
    salary_data_from_api = output of /api/salary/calculate endpoint
    """
    emp   = salary_data_from_api["employee"]
    att   = salary_data_from_api["attendance"]
    earn  = salary_data_from_api["earnings"]
    ded   = salary_data_from_api["deductions"]
    net   = salary_data_from_api["net_salary"]
    month_name = salary_data_from_api["month_name"]
    year  = salary_data_from_api["year"]

    from datetime import date
    slip_data = {
        "name":           emp["name"],
        "emp_id":         emp["emp_id"],
        "joining_date":   emp.get("joining_date", ""),
        "designation":    emp["designation"],
        "department":     emp["department"],
        "location":       emp.get("location", "Surat"),
        "bank_name":      emp["bank_name"],
        "bank_account":   emp["bank_account"],
        "pan":            emp["pan"],
        "uan":            emp.get("uan", "-"),
        "effective_days": att["effective_days"],
        "lop":            att["lop_days"],
        "month_year":     f"{month_name} {year}",
        "date":           date.today().strftime("%-d/%m/%Y"),
        "salary": {
            "basic_full":             emp["basic"],
            "basic_actual":           earn["basic"],
            "hra_full":               emp["hra"],
            "hra_actual":             earn["hra"],
            "conveyance_full":        emp.get("travel_allowance", 0),
            "conveyance_actual":      earn.get("travel_allowance", 0),
            "other_allowance_full":   emp.get("special_allowance", 0),
            "other_allowance_actual": earn.get("special_allowance", 0),
            "lta_full":               emp.get("medical_allowance", 0),
            "lta_actual":             earn.get("medical_allowance", 0),
            "leave_encashment_full":  0,
            "leave_encashment_actual":0,
            "total_earning_full":     emp["basic"]+emp["hra"]+emp.get("travel_allowance",0)+emp.get("special_allowance",0)+emp.get("medical_allowance",0),
            "total_earning_actual":   earn["gross"],
            "pf":                     ded["pf_employee"],
            "prof_tax":               ded["professional_tax"],
            "income_tax":             ded["income_tax"],
            "other_deduction":        0,
            "total_deduction":        ded["total"],
            "net_payable":            net,
        }
    }

    os.makedirs("salary_slips", exist_ok=True)
    filepath = f"salary_slips/{emp['emp_id']}_{month_name}_{year}.pdf"
    draw_salary_slip(slip_data, filepath)
    return filepath


# ══════════════════════════════════════
# DEMO - Test with sample data
# ══════════════════════════════════════
if __name__ == "__main__":
    sample = {
        "name":         "Undaviya Raj",
        "emp_id":       "WTI-000-0002",
        "joining_date": "10th March 2026",
        "designation":  "Developer",
        "department":   "Python",
        "location":     "Surat",
        "bank_name":    "HDFC Bank",
        "bank_account": "50100842433216",
        "pan":          "AEUPU0688N",
        "uan":          "-",
        "effective_days": 22,
        "lop":          "0.0",
        "month_year":   "April 2026",
        "date":         "5/05/2026",
        "salary": {
            "basic_full": 25000.0,    "basic_actual": 25000.0,
            "hra_full": 12000.0,      "hra_actual": 10000.0,
            "conveyance_full": 5000.0,"conveyance_actual": 5000.0,
            "other_allowance_full": 3000.0, "other_allowance_actual": 3200.0,
            "lta_full": 5000.0,       "lta_actual": 5000.0,
            "leave_encashment_full": 0, "leave_encashment_actual": 0,
            "total_earning_full": 50000.0, "total_earning_actual": 50200.0,
            "pf": 0.0,
            "prof_tax": 200.0,
            "income_tax": 0.0,
            "other_deduction": 0.0,
            "total_deduction": 200.0,
            "net_payable": 50000.0,
        }
    }
    os.makedirs("/mnt/user-data/outputs", exist_ok=True)
    draw_salary_slip(sample, "/mnt/user-data/outputs/Salary_Slip_WebbyTouch_Format.pdf")