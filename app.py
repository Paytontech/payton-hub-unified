import os
import json
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS
from dotenv import load_dotenv
from utils.zoho_helper import ZohoHelper
from utils.sheets_helper import SheetsHelper
from models import db, User, Attendance, Case, BreakLog

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("HUB_SECRET_KEY", "payton-secret-key-2026")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///payton_hub.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)

db.init_app(app)

# Initialize Helpers
zoho = ZohoHelper()
sheets = SheetsHelper()

with app.app_context():
    db.create_all()
    # Add initial admin if not exists
    if not User.query.filter_by(email="rajeev4494@payton.com").first():
        admin = User(
            email="rajeev4494@payton.com",
            password="Rajeev@7619364493++",
            full_name="Rajeev (Admin)",
            role="Super Admin"
        )
        db.session.add(admin)
        db.session.commit()

# --- DATABASE / SHEET NAMES ---
SHEET_USERS = "00_User_Database"
SHEET_REQUESTS = "03_Hospital_Requests"
SHEET_PROCESSING = "04_Processing_Data"
SHEET_LOGS = "26_Call_Logs"
SHEET_WHATSAPP = "01_WhatsApp_Memory"
SHEET_TICKETS = "24_Support_Tickets"
SHEET_HOSP_MASTER = "01_Hospital_Master"

# --- CORE UTILITIES ---

def get_user_by_email(email):
    # Check DB first
    user = User.query.filter_by(email=email.lower()).first()
    if user:
        return {
            "Email": user.email,
            "Password": user.password,
            "Full_Name": user.full_name,
            "Role": user.role
        }
    
    # CRITICAL: Hardcoded admin fallback for Rajeev must be instantaneous
    if str(email).lower() == "rajeev4494@payton.com":
        return {
            "Email": "rajeev4494@payton.com",
            "Password": "Rajeev@7619364493++",
            "Full_Name": "Rajeev (Admin)",
            "Role": "Super Admin"
        }
    
    try:
        # This part might be slow if cache is empty
        users = sheets.get_sheet_data(SHEET_USERS)
        for u in users:
            if str(u.get("Email", "")).lower() == email.lower():
                return u
    except Exception as e:
        print(f"Error fetching users from sheet: {e}")
    return None

def get_safe_date(val):
    if not val or val == "-": return None
    try:
        return datetime.strptime(str(val).split('T')[0], "%Y-%m-%d").date()
    except:
        return None

# --- AUTH ROUTES ---

@app.route("/")
def index():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login_api():
    start_time = time.time()
    data = request.json
    email = data.get("email")
    password = data.get("password")
    
    print(f"Login attempt for: {email}")
    user = get_user_by_email(email)
    
    if user and str(user.get("Password")) == str(password):
        session["user"] = user
        print(f"Login success for {email} in {time.time() - start_time:.2f}s")
        return jsonify({"ok": True, "url": url_for("dashboard"), "user": user})
    
    print(f"Login failed for {email} in {time.time() - start_time:.2f}s")
    return jsonify({"ok": False, "message": "Invalid credentials"})

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("index"))
    return render_template("internal_dashboard.html", user=session["user"])

@app.route("/dashboard/internal")
def dashboard_internal():
    if "user" not in session: return redirect(url_for("index"))
    return render_template("internal_dashboard.html", user=session["user"])

@app.route("/dashboard/hospital")
def dashboard_hospital():
    if "user" not in session: return redirect(url_for("index"))
    return render_template("hospital_dashboard.html", user=session["user"])

@app.route("/dashboard/logistics")
def dashboard_logistics():
    if "user" not in session: return redirect(url_for("index"))
    return render_template("logistics_dashboard.html", user=session["user"])

@app.route("/dashboard/patient")
def dashboard_patient():
    # Patient area might not need a session if it's public upload
    return render_template("patient_upload.html")

# --- GAS COMPATIBILITY LAYER ---

@app.route("/api/gas", methods=["POST"])
def gas_proxy():
    data = request.json
    func_name = data.get("function")
    args = data.get("args", [])

    # CRITICAL: globalLogin must be allowed without a session as it is the auth trigger
    if func_name != "globalLogin" and "user" not in session:
        return jsonify({"ok": False, "message": "Unauthorized"}), 401
    
    start_time = time.time()
    print(f"GAS API Call: {func_name}")
    
    func_map = {
        "globalLogin": handle_global_login,
        "getTVMetrics": handle_get_tv_metrics,
        "getHospMaster_": handle_get_hosp_master,
        "internalSendEligChat": handle_send_elig_chat,
        "internalSubmitEligibility": handle_submit_eligibility,
        "internalSaveScrutinyDraft": handle_save_scrutiny_draft,
        "internalSubmitToAR": handle_submit_to_ar,
        "internalMarkQuery": handle_mark_query,
        "internalResolveQuery": handle_resolve_query,
        "internalSyncAttendance": handle_internal_sync_attendance,
    }
    
    if func_name in func_map:
        try:
            result = func_map[func_name](*args)
            print(f"GAS API {func_name} completed in {time.time() - start_time:.2f}s")
            return jsonify(result)
        except Exception as e:
            print(f"GAS API {func_name} failed: {e}")
            return jsonify({"ok": False, "message": str(e)}), 500
    
    return jsonify({"ok": False, "message": f"Function {func_name} not implemented"}), 404

# --- PORTED LOGIC HANDLERS ---

def handle_global_login(u, p, loginType="internal"):
    user = get_user_by_email(u)
    if user and str(user.get("Password")) == str(p):
        session["user"] = user
        url_map = {
            "internal": "/dashboard/internal",
            "hospital": "/dashboard/hospital",
            "logistics": "/dashboard/logistics",
            "patient": "/dashboard/patient"
        }
        return {"ok": True, "url": url_map.get(loginType, "/dashboard/internal")}
    return {"ok": False, "message": "Invalid Credentials"}

def handle_get_tv_metrics(token=None):
    try:
        # These will use the 1-minute cache from SheetsHelper
        req_data = sheets.get_sheet_data(SHEET_REQUESTS)
        proc_data = sheets.get_sheet_data(SHEET_PROCESSING)
        
        today = datetime.now().date()
        elig = {"pending": 0, "completedToday": 0}
        ap = {"pending": 0, "completedToday": 0}
        scr = {"pending": 0, "completedToday": 0}
        aud = {"pending": 0, "completedToday": 0}
        
        # Simple count logic
        for r in req_data:
            status = str(r.get("Request_Status", "")).lower()
            if "pending" in status: elig["pending"] += 1
            
        return {
            "ok": True,
            "elig": elig,
            "ap": ap,
            "scr": scr,
            "aud": aud,
            "ar": {"pending": 0},
            "scrTeam": [],
            "audTeam": [],
            "arTeam": [],
            "attendanceStats": []
        }
    except Exception as e:
        return {"ok": False, "message": str(e)}

def handle_get_hosp_master(token=None):
    data = sheets.get_sheet_data(SHEET_REQUESTS)
    return {"ok": True, "data": data}

def handle_send_elig_chat(cid, msg, agent):
    return {"ok": True, "message": "Message sent"}

def handle_submit_eligibility(data):
    return {"ok": True, "caseId": "NEW-CASE-ID"}

def handle_save_scrutiny_draft(cid, data):
    return {"ok": True}

def handle_submit_to_ar(cid, data):
    return {"ok": True}

def handle_mark_query(cid, data):
    return {"ok": True}

def handle_resolve_query(cid, data):
    return {"ok": True}

def handle_internal_sync_attendance(user_email, role, action, meta):
    try:
        email = f"{user_email}@payton.com" if "@" not in user_email else user_email
        
        if action == "PUNCH_IN":
            att = Attendance(
                user_email=email,
                role_at_time=role,
                status="PUNCHED_IN",
                punch_in=datetime.utcnow()
            )
            db.session.add(att)
            db.session.commit()
            return {"ok": True, "rowIdx": att.id, "message": "Punched in successfully"}
            
        elif action == "PUNCH_OUT":
            row_id = meta.get("rowIdx")
            active_mins = meta.get("activeMins", 0)
            att = db.session.get(Attendance, row_id)
            if att:
                att.punch_out = datetime.utcnow()
                att.status = "PUNCHED_OUT"
                att.active_mins = active_mins
                db.session.commit()
                return {"ok": True, "message": "Punched out successfully"}
            return {"ok": False, "message": "Attendance record not found"}
            
        elif action == "LOG_BREAK":
            row_id = meta.get("rowIdx")
            reason = meta.get("reason", "Break")
            duration = meta.get("durationMins", 0)
            
            log = BreakLog(attendance_id=row_id, reason=reason, duration_mins=duration)
            db.session.add(log)
            
            att = db.session.get(Attendance, row_id)
            if att:
                att.break_mins += duration
                
            db.session.commit()
            return {"ok": True}
            
        elif action == "RESOLVE_LOCK":
            row_id = meta.get("rowIdx")
            duration = meta.get("totalMins", 0)
            reason = meta.get("reason", "System Lock")
            
            log = BreakLog(attendance_id=row_id, reason=f"Unlocked: {reason}", duration_mins=duration)
            db.session.add(log)
            
            att = db.session.get(Attendance, row_id)
            if att:
                att.break_mins += duration
                
            db.session.commit()
            return {"ok": True}
            
        return {"ok": False, "message": f"Action {action} not recognized"}
    except Exception as e:
        print(f"Sync Attendance Error: {e}")
        return {"ok": False, "message": str(e)}

# --- WEBHOOKS ---

@app.route("/webhooks/ivr", methods=["POST"])
def ivr_webhook():
    return jsonify({"ok": True})

@app.route("/webhooks/whatsapp", methods=["POST"])
def whatsapp_webhook():
    return jsonify({"ok": True})

@app.route("/api/export/<table_name>")
def export_data(table_name):
    if "user" not in session:
        return jsonify({"ok": False, "message": "Unauthorized"}), 401
    
    try:
        import pandas as pd
        from io import BytesIO
        from flask import send_file
        
        if table_name == "attendance":
            data = Attendance.query.all()
            df = pd.DataFrame([{
                "ID": a.id,
                "Email": a.user_email,
                "Punch In": a.punch_in,
                "Punch Out": a.punch_out,
                "Active Mins": a.active_mins,
                "Break Mins": a.break_mins,
                "Role": a.role_at_time
            } for a in data])
        elif table_name == "users":
            data = User.query.all()
            df = pd.DataFrame([{
                "Email": u.email,
                "Name": u.full_name,
                "Role": u.role
            } for u in data])
        else:
            # Fallback to sheets if table not in DB
            sheet_data = sheets.get_sheet_data(table_name)
            df = pd.DataFrame(sheet_data)
            
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        output.seek(0)
        
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"Payton_{table_name}_Export_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        )
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500

@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "user" not in session:
        return jsonify({"ok": False, "message": "Unauthorized"}), 401
    
    if 'file' not in request.files:
        return jsonify({"ok": False, "message": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"ok": False, "message": "No selected file"}), 400
    
    # Save to a local 'uploads' directory for now
    upload_dir = "uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        
    file_path = os.path.join(upload_dir, file.filename)
    file.save(file_path)
    
    return jsonify({"ok": True, "message": f"File {file.filename} uploaded successfully", "path": file_path})

if __name__ == "__main__":
    app.run(port=os.getenv("PORT", 5000), debug=True)
