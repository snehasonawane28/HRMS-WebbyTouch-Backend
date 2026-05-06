"""
HRM CRM Backend - FastAPI
Salary, Attendance, Leaves, PDF, Email sab yahan manage hoga
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
import json, os, calendar, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from salary_slip_generator import generate_pdf_webbytouch

# PDF imports
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

app = FastAPI(title="HRM CRM API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("data", exist_ok=True)
os.makedirs("salary_slips", exist_ok=True)

# ─────────────────────────────────────────
# DATA FILES (JSON as simple DB)
# ─────────────────────────────────────────

def load(file): 
    if os.path.exists(f"data/{file}.json"):
        return json.load(open(f"data/{file}.json"))
    return []

def save(file, data): 
    json.dump(data, open(f"data/{file}.json", "w"), indent=2, default=str)

def load_dict(file):
    if os.path.exists(f"data/{file}.json"):
        return json.load(open(f"data/{file}.json"))
    return {}

# ─────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────

class Employee(BaseModel):
    emp_id: str
    name: str
    designation: str
    department: str
    email: str
    phone: str
    pan: str
    uan: str
    pf_account: str
    bank_account: str
    bank_name: str
    joining_date: str
    basic: float
    hra: float
    special_allowance: float
    travel_allowance: float
    medical_allowance: float
    pf_employee: float
    professional_tax: float
    income_tax: float
    status: str = "active"

class AttendanceRecord(BaseModel):
    emp_id: str
    date: str          # YYYY-MM-DD
    status: str        # present / absent / half_day / holiday / weekly_off

class LeaveRequest(BaseModel):
    emp_id: str
    leave_type: str    # sick / casual / earned / maternity / unpaid
    from_date: str
    to_date: str
    reason: str
    status: str = "pending"  # pending / approved / rejected

class LeaveAction(BaseModel):
    status: str        # approved / rejected
    remarks: str = ""

class SalaryConfig(BaseModel):
    company_name: str
    company_address: str
    company_phone: str
    company_email: str
    company_pan: str
    sender_email: str
    sender_password: str

# ─────────────────────────────────────────
# EMPLOYEES CRUD
# ─────────────────────────────────────────

@app.get("/api/employees")
def get_employees():
    return load("employees")

@app.post("/api/employees")
def add_employee(emp: Employee):
    employees = load("employees")
    # Check duplicate
    if any(e["emp_id"] == emp.emp_id for e in employees):
        raise HTTPException(400, "Employee ID already exists")
    employees.append(emp.dict())
    save("employees", employees)
    return {"message": "Employee added", "emp_id": emp.emp_id}

@app.put("/api/employees/{emp_id}")
def update_employee(emp_id: str, emp: Employee):
    employees = load("employees")
    for i, e in enumerate(employees):
        if e["emp_id"] == emp_id:
            employees[i] = emp.dict()
            save("employees", employees)
            return {"message": "Updated"}
    raise HTTPException(404, "Employee not found")

@app.delete("/api/employees/{emp_id}")
def delete_employee(emp_id: str):
    employees = load("employees")
    employees = [e for e in employees if e["emp_id"] != emp_id]
    save("employees", employees)
    return {"message": "Deleted"}

@app.get("/api/employees/{emp_id}")
def get_employee(emp_id: str):
    employees = load("employees")
    emp = next((e for e in employees if e["emp_id"] == emp_id), None)
    if not emp:
        raise HTTPException(404, "Not found")
    return emp

# ─────────────────────────────────────────
# ATTENDANCE
# ─────────────────────────────────────────

@app.post("/api/attendance")
def mark_attendance(rec: AttendanceRecord):
    attendance = load("attendance")
    # Update if exists
    for i, a in enumerate(attendance):
        if a["emp_id"] == rec.emp_id and a["date"] == rec.date:
            attendance[i] = rec.dict()
            save("attendance", attendance)
            return {"message": "Updated"}
    attendance.append(rec.dict())
    save("attendance", attendance)
    return {"message": "Marked"}

@app.get("/api/attendance/{emp_id}/{year}/{month}")
def get_attendance(emp_id: str, year: int, month: int):
    attendance = load("attendance")
    prefix = f"{year}-{month:02d}"
    records = [a for a in attendance if a["emp_id"] == emp_id and a["date"].startswith(prefix)]
    
    # Calculate summary
    total_days = calendar.monthrange(year, month)[1]
    present = sum(1 for r in records if r["status"] == "present")
    half_day = sum(1 for r in records if r["status"] == "half_day")
    absent = sum(1 for r in records if r["status"] == "absent")
    
    return {
        "records": records,
        "summary": {
            "total_days": total_days,
            "present": present,
            "half_day": half_day,
            "absent": absent,
            "working_days": present + (half_day * 0.5)
        }
    }

@app.get("/api/attendance/all/{year}/{month}")
def get_all_attendance(year: int, month: int):
    attendance = load("attendance")
    prefix = f"{year}-{month:02d}"
    return [a for a in attendance if a["date"].startswith(prefix)]

# ─────────────────────────────────────────
# LEAVES
# ─────────────────────────────────────────

def count_leave_days(from_date: str, to_date: str) -> int:
    d1 = datetime.strptime(from_date, "%Y-%m-%d").date()
    d2 = datetime.strptime(to_date, "%Y-%m-%d").date()
    return (d2 - d1).days + 1

@app.post("/api/leaves")
def apply_leave(leave: LeaveRequest):
    leaves = load("leaves")
    leave_data = leave.dict()
    leave_data["id"] = f"LV{len(leaves)+1:04d}"
    leave_data["days"] = count_leave_days(leave.from_date, leave.to_date)
    leave_data["applied_on"] = str(date.today())
    leaves.append(leave_data)
    save("leaves", leaves)
    return {"message": "Leave applied", "leave_id": leave_data["id"], "days": leave_data["days"]}

@app.get("/api/leaves/{emp_id}")
def get_leaves(emp_id: str):
    leaves = load("leaves")
    return [l for l in leaves if l["emp_id"] == emp_id]

@app.get("/api/leaves")
def get_all_leaves(status: str = None):
    leaves = load("leaves")
    if status:
        return [l for l in leaves if l["status"] == status]
    return leaves

@app.put("/api/leaves/{leave_id}/action")
def action_leave(leave_id: str, action: LeaveAction):
    leaves = load("leaves")
    for i, l in enumerate(leaves):
        if l["id"] == leave_id:
            leaves[i]["status"] = action.status
            leaves[i]["remarks"] = action.remarks
            leaves[i]["actioned_on"] = str(date.today())
            save("leaves", leaves)
            return {"message": f"Leave {action.status}"}
    raise HTTPException(404, "Leave not found")

@app.get("/api/leaves/{emp_id}/balance/{year}")
def leave_balance(emp_id: str, year: int):
    leaves = load("leaves")
    approved = [l for l in leaves 
                if l["emp_id"] == emp_id 
                and l["status"] == "approved"
                and l["from_date"].startswith(str(year))]
    
    balance = {
        "casual": {"total": 12, "used": 0, "balance": 12},
        "sick": {"total": 12, "used": 0, "balance": 12},
        "earned": {"total": 15, "used": 0, "balance": 15},
        "unpaid": {"total": 0, "used": 0, "balance": 0},
    }
    
    for l in approved:
        lt = l["leave_type"]
        if lt in balance:
            balance[lt]["used"] += l["days"]
            balance[lt]["balance"] = balance[lt]["total"] - balance[lt]["used"]
    
    return balance

# ─────────────────────────────────────────
# SALARY CALCULATION
# ─────────────────────────────────────────

@app.get("/api/salary/calculate/{emp_id}/{year}/{month}")
def calculate_salary(emp_id: str, year: int, month: int):
    employees = load("employees")
    emp = next((e for e in employees if e["emp_id"] == emp_id), None)
    if not emp:
        raise HTTPException(404, "Employee not found")

    # Get attendance
    attendance = load("attendance")
    prefix = f"{year}-{month:02d}"
    month_records = [a for a in attendance if a["emp_id"] == emp_id and a["date"].startswith(prefix)]

    total_days = calendar.monthrange(year, month)[1]
    working_days_in_month = total_days - sum(1 for a in month_records if a["status"] in ["holiday", "weekly_off"])
    if working_days_in_month == 0:
        working_days_in_month = 26  # default

    present_days = sum(1 for a in month_records if a["status"] == "present")
    half_days = sum(1 for a in month_records if a["status"] == "half_day")
    absent_days = sum(1 for a in month_records if a["status"] == "absent")
    
    # Get approved leaves this month
    leaves = load("leaves")
    month_leaves = [l for l in leaves 
                    if l["emp_id"] == emp_id 
                    and l["status"] == "approved"
                    and (l["from_date"].startswith(prefix) or l["to_date"].startswith(prefix))]
    
    paid_leave_days = sum(l["days"] for l in month_leaves if l["leave_type"] != "unpaid")
    unpaid_leave_days = sum(l["days"] for l in month_leaves if l["leave_type"] == "unpaid")
    
    # Effective working days
    effective_days = present_days + (half_days * 0.5) + paid_leave_days
    
    # LOP = absent days + unpaid leaves
    lop_days = absent_days + unpaid_leave_days
    
    # Per day salary
    per_day = emp["basic"] / working_days_in_month
    lop_deduction = round(per_day * lop_days, 2)
    
    basic_after_lop = emp["basic"] - lop_deduction
    gross = (basic_after_lop + emp["hra"] + emp["special_allowance"] 
             + emp["travel_allowance"] + emp["medical_allowance"])
    
    total_deductions = (emp["pf_employee"] + emp["professional_tax"] 
                        + emp["income_tax"])
    
    net_salary = gross - total_deductions

    return {
        "emp_id": emp_id,
        "employee": emp,
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month],
        "attendance": {
            "total_days": total_days,
            "working_days": working_days_in_month,
            "present": present_days,
            "half_day": half_days,
            "absent": absent_days,
            "paid_leaves": paid_leave_days,
            "unpaid_leaves": unpaid_leave_days,
            "effective_days": effective_days,
            "lop_days": lop_days,
        },
        "earnings": {
            "basic": round(basic_after_lop, 2),
            "hra": emp["hra"],
            "special_allowance": emp["special_allowance"],
            "travel_allowance": emp["travel_allowance"],
            "medical_allowance": emp["medical_allowance"],
            "gross": round(gross, 2),
        },
        "deductions": {
            "pf_employee": emp["pf_employee"],
            "professional_tax": emp["professional_tax"],
            "income_tax": emp["income_tax"],
            "lop_deduction": lop_deduction,
            "total": round(total_deductions + lop_deduction, 2),
        },
        "net_salary": round(net_salary - lop_deduction, 2),
        "employer_pf": emp["pf_employee"],
        "leaves_detail": month_leaves,
    }

# ─────────────────────────────────────────
# PDF GENERATION
# ─────────────────────────────────────────

def amount_to_words(amount: int) -> str:
    ones = ['','One','Two','Three','Four','Five','Six','Seven','Eight','Nine','Ten',
            'Eleven','Twelve','Thirteen','Fourteen','Fifteen','Sixteen','Seventeen','Eighteen','Nineteen']
    tens = ['','','Twenty','Thirty','Forty','Fifty','Sixty','Seventy','Eighty','Ninety']
    def two(n):
        return ones[n] if n < 20 else tens[n//10]+(' '+ones[n%10] if n%10 else '')
    def three(n):
        return (ones[n//100]+' Hundred'+(' '+two(n%100) if n%100 else '')) if n>=100 else two(n)
    if amount == 0: return 'Zero Rupees'
    parts, a = [], amount
    for label, div in [('Crore',10000000),('Lakh',100000),('Thousand',1000),('',1)]:
        v = a // div; a %= div
        if v: parts.append(three(v)+(' '+label if label else ''))
    return 'Rupees ' + ' '.join(parts)

def generate_pdf(salary_data: dict, config: dict) -> str:
    emp = salary_data["employee"]
    att = salary_data["attendance"]
    earn = salary_data["earnings"]
    ded = salary_data["deductions"]
    net = salary_data["net_salary"]
    month_name = salary_data["month_name"]
    year = salary_data["year"]

    filepath = f"salary_slips/{emp['emp_id']}_{month_name}_{year}.pdf"
    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            rightMargin=12*mm, leftMargin=12*mm,
                            topMargin=12*mm, bottomMargin=12*mm)

    styles = getSampleStyleSheet()
    def sty(name, **kw):
        return ParagraphStyle(name, parent=styles['Normal'], **kw)

    story = []

    # Header
    story.append(Paragraph(config.get("company_name","Company Name"),
        sty('h1', fontSize=15, fontName='Helvetica-Bold', alignment=TA_CENTER,
            textColor=colors.HexColor('#0d2b6e'), spaceAfter=2)))
    story.append(Paragraph(config.get("company_address",""),
        sty('h2', fontSize=8, fontName='Helvetica', alignment=TA_CENTER,
            textColor=colors.HexColor('#555'), spaceAfter=1)))
    story.append(Paragraph(
        f"Phone: {config.get('company_phone','')}  |  Email: {config.get('company_email','')}  |  PAN: {config.get('company_pan','')}",
        sty('h3', fontSize=7.5, alignment=TA_CENTER, textColor=colors.HexColor('#777'))))
    story.append(Spacer(1, 3*mm))

    # Title bar
    title_bar = Table([[Paragraph(f"SALARY SLIP — {month_name.upper()} {year}",
        sty('tb', fontSize=10, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_CENTER))]],
        colWidths=[186*mm])
    title_bar.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#0d2b6e')),
        ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
    ]))
    story.append(title_bar)
    story.append(Spacer(1, 4*mm))

    # Employee details
    def lbl(t): return Paragraph(t, sty('lbl', fontSize=8, fontName='Helvetica-Bold'))
    def val(t): return Paragraph(str(t), sty('val', fontSize=8, fontName='Helvetica'))

    emp_table = Table([
        [lbl("Employee ID"), val(emp["emp_id"]), lbl("Department"), val(emp["department"])],
        [lbl("Name"), val(emp["name"]), lbl("Designation"), val(emp["designation"])],
        [lbl("PAN Number"), val(emp["pan"]), lbl("UAN Number"), val(emp["uan"])],
        [lbl("PF Account"), val(emp["pf_account"]), lbl("Bank"), val(emp["bank_name"])],
        [lbl("A/C Number"), val(emp["bank_account"]), lbl("Joining Date"), val(emp["joining_date"])],
    ], colWidths=[35*mm, 58*mm, 35*mm, 58*mm])

    emp_table.setStyle(TableStyle([
        ('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#ddd')),
        ('BACKGROUND',(0,0),(0,-1),colors.HexColor('#eef2ff')),
        ('BACKGROUND',(2,0),(2,-1),colors.HexColor('#eef2ff')),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('LEFTPADDING',(0,0),(-1,-1),5),
    ]))
    story.append(emp_table)
    story.append(Spacer(1, 3*mm))

    # Attendance Summary
    att_data = [
        [lbl("Total Days"), val(att["total_days"]),
         lbl("Working Days"), val(att["working_days"]),
         lbl("Days Present"), val(f"{att['present']} + {att['half_day']} Half")],
        [lbl("Paid Leaves"), val(att["paid_leaves"]),
         lbl("LOP Days"), val(att["lop_days"]),
         lbl("Effective Days"), val(att["effective_days"])],
    ]
    att_table = Table(att_data, colWidths=[30*mm, 32*mm, 30*mm, 32*mm, 30*mm, 32*mm])
    att_table.setStyle(TableStyle([
        ('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#ddd')),
        ('BACKGROUND',(0,0),(0,-1),colors.HexColor('#fff8e1')),
        ('BACKGROUND',(2,0),(2,-1),colors.HexColor('#fff8e1')),
        ('BACKGROUND',(4,0),(4,-1),colors.HexColor('#fff8e1')),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('LEFTPADDING',(0,0),(-1,-1),5),
    ]))
    story.append(att_table)
    story.append(Spacer(1, 3*mm))

    # Earnings & Deductions
    def amt(v, bold=False):
        s = sty('a', fontSize=8, fontName='Helvetica-Bold' if bold else 'Helvetica', alignment=TA_RIGHT)
        return Paragraph(f"₹ {v:,.2f}", s)

    sec = sty('sec', fontSize=8.5, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_CENTER)

    salary_rows = [
        [Paragraph("EARNINGS", sec), Paragraph("Amount (₹)", sec),
         Paragraph("DEDUCTIONS", sec), Paragraph("Amount (₹)", sec)],
        [lbl("Basic Salary"), amt(earn["basic"]),
         lbl("Provident Fund (12%)"), amt(ded["pf_employee"])],
        [lbl("HRA"), amt(earn["hra"]),
         lbl("Professional Tax"), amt(ded["professional_tax"])],
        [lbl("Special Allowance"), amt(earn["special_allowance"]),
         lbl("Income Tax (TDS)"), amt(ded["income_tax"])],
        [lbl("Travel Allowance"), amt(earn["travel_allowance"]),
         lbl("LOP Deduction"), amt(ded["lop_deduction"])],
        [lbl("Medical Allowance"), amt(earn["medical_allowance"]),
         lbl(""), amt(0) if False else Paragraph("", styles["Normal"])],
        [lbl("GROSS EARNINGS"), amt(earn["gross"], True),
         lbl("TOTAL DEDUCTIONS"), amt(ded["total"], True)],
    ]

    sal_table = Table(salary_rows, colWidths=[55*mm, 38*mm, 55*mm, 38*mm])
    sal_table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(1,0),colors.HexColor('#1565c0')),
        ('BACKGROUND',(2,0),(3,0),colors.HexColor('#b71c1c')),
        ('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#ccc')),
        ('ROWBACKGROUNDS',(0,1),(-1,-2),[colors.white, colors.HexColor('#f8f9ff')]),
        ('BACKGROUND',(0,-1),(-1,-1),colors.HexColor('#e8eaf6')),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
    ]))
    story.append(sal_table)
    story.append(Spacer(1, 3*mm))

    # Net Salary
    net_row = Table([[
        Paragraph(f"NET SALARY PAYABLE: ₹ {net:,.2f}",
            sty('ns', fontSize=11, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_CENTER)),
        Paragraph(f"Employer PF: ₹ {salary_data['employer_pf']:,.2f}",
            sty('ep', fontSize=8.5, fontName='Helvetica', alignment=TA_CENTER, textColor=colors.HexColor('#1b5e20'))),
    ]], colWidths=[130*mm, 56*mm])
    net_row.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(0,0),colors.HexColor('#1b5e20')),
        ('BACKGROUND',(1,0),(1,0),colors.HexColor('#e8f5e9')),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('LEFTPADDING',(0,0),(-1,-1),6),
        ('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#ccc')),
    ]))
    story.append(net_row)
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(f"In Words: {amount_to_words(int(net))} Only",
        sty('iw', fontSize=8, fontName='Helvetica-Bold', textColor=colors.HexColor('#0d2b6e'))))
    story.append(Spacer(1, 5*mm))

    # Footer
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#ccc')))
    story.append(Spacer(1, 2*mm))
    footer = Table([[
        Paragraph("Employee Signature", sty('fs', fontSize=7.5, alignment=TA_CENTER, textColor=colors.HexColor('#888'))),
        Paragraph("This is a computer-generated salary slip.\nNo signature is required.",
            sty('fc', fontSize=7.5, alignment=TA_CENTER, textColor=colors.HexColor('#888'))),
        Paragraph("Authorized Signatory", sty('fa', fontSize=7.5, alignment=TA_CENTER, textColor=colors.HexColor('#888'))),
    ]], colWidths=[62*mm, 62*mm, 62*mm])
    footer.setStyle(TableStyle([
        ('TOPPADDING',(0,0),(-1,-1),12),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
    ]))
    story.append(footer)

    doc.build(story)
    return filepath

@app.get("/api/salary/generate-pdf/{emp_id}/{year}/{month}")
def generate_salary_pdf(emp_id: str, year: int, month: int):
    salary_data = calculate_salary(emp_id, year, month)
    config = load_dict("company_config")
    filepath = generate_pdf(salary_data, config)
    return FileResponse(filepath, media_type="application/pdf",
                        filename=f"Salary_{emp_id}_{calendar.month_name[month]}_{year}.pdf")

# ─────────────────────────────────────────
# SEND EMAIL
# ─────────────────────────────────────────

@app.post("/api/salary/send-email/{emp_id}/{year}/{month}")
def send_salary_email(emp_id: str, year: int, month: int):
    config = load_dict("company_config")
    if not config.get("sender_email") or not config.get("sender_password"):
        raise HTTPException(400, "Email config not set")

    salary_data = calculate_salary(emp_id, year, month)
    emp = salary_data["employee"]
    month_name = salary_data["month_name"]
    filepath = generate_pdf_webbytouch(salary_data, config)

    msg = MIMEMultipart()
    msg['From'] = config["sender_email"]
    msg['To'] = emp["email"]
    msg['Subject'] = f"Salary Slip — {month_name} {year} | {config.get('company_name','')}"

    body = f"""Priya {emp['name']} Ji,

Namaste! Aapki {month_name} {year} ki salary slip attached hai.

Net Salary: ₹ {salary_data['net_salary']:,.2f}
Days Present: {salary_data['attendance']['present']}
Paid Leaves: {salary_data['attendance']['paid_leaves']}
LOP Days: {salary_data['attendance']['lop_days']}

Dhanyavaad,
HR Department — {config.get('company_name','')}

(Yeh automated email hai. Reply na karen.)"""

    msg.attach(MIMEText(body, 'plain'))
    with open(filepath, 'rb') as f:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="Salary_{emp_id}_{month_name}_{year}.pdf"')
        msg.attach(part)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(config["sender_email"], config["sender_password"])
            server.send_message(msg)
        return {"message": f"Email sent to {emp['email']}"}
    except Exception as e:
        raise HTTPException(500, f"Email failed: {str(e)}")

@app.post("/api/salary/send-all/{year}/{month}")
def send_all_emails(year: int, month: int):
    employees = load("employees")
    active = [e for e in employees if e.get("status") == "active"]
    results = []
    for emp in active:
        try:
            send_salary_email(emp["emp_id"], year, month)
            results.append({"emp_id": emp["emp_id"], "status": "sent"})
        except Exception as e:
            results.append({"emp_id": emp["emp_id"], "status": "failed", "error": str(e)})
    return results

# ─────────────────────────────────────────
# COMPANY CONFIG
# ─────────────────────────────────────────

@app.get("/api/config")
def get_config():
    c = load_dict("company_config")
    # Don't expose password
    c.pop("sender_password", None)
    return c

@app.post("/api/config")
def save_config(cfg: SalaryConfig):
    save("company_config", cfg.dict())
    return {"message": "Config saved"}

# ─────────────────────────────────────────
# DASHBOARD STATS
# ─────────────────────────────────────────

@app.get("/api/dashboard")
def dashboard():
    employees = load("employees")
    leaves = load("leaves")
    now = datetime.now()
    
    total_emp = len(employees)
    active_emp = sum(1 for e in employees if e.get("status") == "active")
    pending_leaves = sum(1 for l in leaves if l["status"] == "pending")
    
    # This month attendance
    prefix = f"{now.year}-{now.month:02d}"
    attendance = load("attendance")
    today_present = sum(1 for a in attendance if a["date"] == str(date.today()) and a["status"] == "present")
    
    return {
        "total_employees": total_emp,
        "active_employees": active_emp,
        "pending_leaves": pending_leaves,
        "today_present": today_present,
        "current_month": now.strftime("%B %Y"),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
