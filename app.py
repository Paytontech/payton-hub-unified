import os
import json
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS
from dotenv import load_dotenv
from utils.zoho_helper import ZohoHelper
from utils.sheets_helper import SheetsHelper

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("HUB_SECRET_KEY", "payton-secret-key-2026")
CORS(app)

# Initialize Helpers
zoho = ZohoHelper()
sheets = SheetsHelper()

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
    # Hardcoded admin fallback for initial setup
    if str(email).lower() == "rajeev4494@payton.com":
        return {
            "Email": "rajeev4494@payton.com",
            "Password": "Rajeev@7619364493++",
            "Full_Name": "Rajeev (Admin)",
            "Role": "Super Admin"
        }
    
    try:
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
    data = request.json
    email = data.get("email")
    password = data.get("password")
    
    user = get_user_by_email(email)
    if user and str(user.get("Password")) == str(password):
        session["user"] = user
        return jsonify({"ok": True, "url": url_for("dashboard"), "user": user})
    return jsonify({"ok": False, "message": "Invalid credentials"})

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("index"))
    return render_template("internal_dashboard.html", user=session["user"])

# --- GAS COMPATIBILITY LAYER ---

@app.route("/api/gas", methods=["POST"])
def gas_proxy():
    if "user" not in session:
        return jsonify({"ok": False, "message": "Unauthorized"}), 401
    
    data = request.json
    func_name = data.get("function")
    args = data.get("args", [])
    
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
    }
    
    if func_name in func_map:
        try:
            result = func_map[func_name](*args)
            return jsonify(result)
        except Exception as e:
            return jsonify({"ok": False, "message": str(e)}), 500
    
    return jsonify({"ok": False, "message": f"Function {func_name} not implemented"}), 404

# --- PORTED LOGIC HANDLERS ---

def handle_global_login(u, p):
    user = get_user_by_email(u)
    if user and str(user.get("Password")) == str(p):
        session["user"] = user
        return {"ok": True, "url": "/dashboard"}
    return {"ok": False, "message": "Invalid Credentials"}

def handle_get_tv_metrics(token=None):
    try:
        req_data = sheets.get_sheet_data(SHEET_REQUESTS)
        proc_data = sheets.get_sheet_data(SHEET_PROCESSING)
        
        today = datetime.now().date()
        elig = {"pending": 0, "completedToday": 0}
        ap = {"pending": 0, "completedToday": 0}
        scr = {"pending": 0, "completedToday": 0}
        aud = {"pending": 0, "completedToday": 0}
        
        for r in req_data:
            status = str(r.get("Request_Status", "")).lower()
            if "pending" in status: elig["pending"] += 1
            # Add more specific counting logic...
            
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
    # Ported from internalSendEligChat
    return {"ok": True, "message": "Message sent"}

def handle_submit_eligibility(data):
    # Logic to insert into SHEET_REQUESTS
    return {"ok": True, "caseId": "NEW-CASE-ID"}

def handle_save_scrutiny_draft(cid, data):
    # Logic to update SHEET_PROCESSING
    return {"ok": True}

def handle_submit_to_ar(cid, data):
    # Logic to update SHEET_PROCESSING status to "In Process"
    return {"ok": True}

def handle_mark_query(cid, data):
    # Logic to update SHEET_PROCESSING status to "Query"
    return {"ok": True}

def handle_resolve_query(cid, data):
    # Logic to update SHEET_PROCESSING status back to "In Process"
    return {"ok": True}

# --- WEBHOOKS ---

@app.route("/webhooks/ivr", methods=["POST"])
def ivr_webhook():
    data = request.json
    # Logic from Project 4 - IVR webhook/IVR Code.txt
    return jsonify({"ok": True})

@app.route("/webhooks/whatsapp", methods=["POST"])
def whatsapp_webhook():
    data = request.json
    # Logic from Project 3 - Whatsapp Inregration/Whatsapp Code.txt
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(port=os.getenv("PORT", 5000), debug=True)
