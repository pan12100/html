import os
import json
import hashlib
from collections import Counter
from datetime import datetime
from dateutil import parser
from flask import Flask, request, render_template, redirect, session, jsonify
from google.oauth2.service_account import Credentials
import gspread

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_default_secret_key")

# Global สำหรับให้ ESP32 ดึง username ล่าสุด
current_username = ""

# Google Sheets setup
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# โหลด credentials จาก Environment Variable (JSON string)
creds_json = os.getenv("GOOGLE_CREDS")
if not creds_json:
    print("⚠️ Warning: GOOGLE_CREDS environment variable is missing!")
    creds = None
else:
    try:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    except Exception as e:
        print(f"⚠️ Failed to load credentials: {e}")
        creds = None

# เปิด Google Sheets
if creds:
    try:
        client = gspread.authorize(creds)
        sheet_users = client.open("BMI_system").worksheet("users")
        sheet_bmi = client.open("BMI_system").worksheet("bmi_data")
    except Exception as e:
        print(f"⚠️ Failed to access Google Sheets: {e}")
        sheet_users = None
        sheet_bmi = None
else:
    sheet_users = None
    sheet_bmi = None

# ฟังก์ชันช่วย
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def most_common_value(lst):
    if not lst:
        return 0
    counter = Counter(lst)
    return counter.most_common(1)[0][0] or 0

# Routes
@app.route("/")
def home():
    if "username" in session:
        return redirect("/bmi_table")
    return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
def register():
    if not sheet_users:
        return "❌ ระบบยังไม่พร้อมใช้งาน (Google Sheets ไม่สามารถเข้าถึงได้)"

    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]
        dob = request.form.get("dob")
        gender = request.form.get("gender")

        hashed_pw = hash_password(password)
        try:
            users = sheet_users.get_all_records()
            if any(u.get("username", "").strip().lower() == username for u in users):
                return "ชื่อผู้ใช้นี้มีอยู่แล้ว กรุณาเปลี่ยนชื่อผู้ใช้"
            sheet_users.append_row([username, hashed_pw, dob, gender])
        except Exception as e:
            return f"เกิดข้อผิดพลาด: {e}"

        return redirect("/login")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    global current_username
    if not sheet_users:
        return "❌ ระบบยังไม่พร้อมใช้งาน (Google Sheets ไม่สามารถเข้าถึงได้)"

    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]
        hashed_pw = hash_password(password)
        try:
            users = sheet_users.get_all_records()
            for user in users:
                if user.get("username", "").strip().lower() == username and user.get("password") == hashed_pw:
                    session["username"] = username
                    current_username = username
                    return redirect("/bmi_table")
        except Exception as e:
            return f"เกิดข้อผิดพลาด: {e}"

        return "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"
    return render_template("login.html")

@app.route("/logout", methods=["GET", "POST"])
def logout():
    global current_username
    session.clear()
    current_username = ""
    return redirect("/login")

@app.route("/bmi_table")
def bmi_table():
    if "username" not in session:
        return redirect("/login")

    if not sheet_bmi:
        return "❌ ระบบยังไม่พร้อมใช้งาน (Google Sheets ไม่สามารถเข้าถึงได้)"

    username = session["username"]
    try:
        bmi_data = sheet_bmi.get_all_records()
    except Exception as e:
        return f"เกิดข้อผิดพลาด: {e}"

    cleaned_data = []
    for row in bmi_data:
        user = row.get("username", "").strip().lower()
        if user == username.strip().lower():
            try:
                height = float(row.get("height", 0))
                weight = float(row.get("weight", 0))
                bmi = float(row.get("bmi", 0))
                timestamp = row.get("timestamp", "")
                cleaned_data.append({
                    "height": height,
                    "weight": weight,
                    "bmi": bmi,
                    "timestamp": timestamp
                })
            except:
                continue

    cleaned_data = sorted(
        cleaned_data,
        key=lambda r: parser.parse(r["timestamp"]) if r["timestamp"] else datetime.min,
        reverse=True
    )

    daily_bmi = {}
    daily_weight = {}
    for item in cleaned_data:
        try:
            date_key = parser.parse(item["timestamp"]).date()
            daily_bmi.setdefault(date_key, []).append(item["bmi"])
            daily_weight.setdefault(date_key, []).append(item["weight"])
        except:
            continue

    graph_labels = sorted(daily_bmi.keys())
    graph_labels_str = [d.strftime("%Y-%m-%d") for d in graph_labels]
    graph_bmi = [round(most_common_value(daily_bmi[d]), 2) for d in graph_labels]
    graph_weight = [round(most_common_value(daily_weight[d]), 2) for d in graph_labels]

    per_page = 20
    page = int(request.args.get("page", 1))
    total_pages = (len(cleaned_data) + per_page - 1) // per_page

    start = (page - 1) * per_page
    end = start + per_page
    page_data = cleaned_data[start:end]

    return render_template(
        "bmi_table.html",
        username=username,
        bmi_data=page_data,
        page=page,
        total_pages=total_pages,
        graph_labels=graph_labels_str,
        graph_bmi=graph_bmi,
        graph_weight=graph_weight
    )

@app.route("/add_bmi", methods=["POST"])
def add_bmi():
    if "username" not in session:
        return redirect("/login")

    if not sheet_bmi:
        return "❌ ระบบยังไม่พร้อมใช้งาน (Google Sheets ไม่สามารถเข้าถึงได้)"

    username = session["username"]
    height = request.form.get("height")
    weight = request.form.get("weight")

    try:
        height = float(height)
        weight = float(weight)
        bmi = weight / ((height / 100) ** 2)
    except (ValueError, TypeError):
        return "ข้อมูลไม่ถูกต้อง"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        sheet_bmi.append_row([username, height, weight, round(bmi, 2), timestamp])
    except Exception as e:
        return f"เกิดข้อผิดพลาด: {e}"

    return redirect("/bmi_table")

@app.route("/api/bmi", methods=["POST"])
def api_bmi():
    if not sheet_users or not sheet_bmi:
        return jsonify({"status": "error", "message": "ระบบยังไม่พร้อมใช้งาน"}), 500

    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "ไม่มีข้อมูล"}), 400

    username = data.get("username")
    height = data.get("height")
    weight = data.get("weight")

    if not (username and height and weight):
        return jsonify({"status": "error", "message": "ข้อมูลไม่ครบ"}), 400

    try:
        height = float(height)
        weight = float(weight)
        bmi = weight / ((height / 100) ** 2)
    except ValueError:
        return jsonify({"status": "error", "message": "ข้อมูลผิดพลาด"}), 400

    try:
        users = sheet_users.get_all_records()
        if not any(u.get("username") == username for u in users):
            return jsonify({"status": "error", "message": "ไม่พบผู้ใช้"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": f"เกิดข้อผิดพลาด: {e}"}), 500

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        sheet_bmi.append_row([username, height, weight, round(bmi, 2), timestamp])
    except Exception as e:
        return jsonify({"status": "error", "message": f"เกิดข้อผิดพลาด: {e}"}), 500

    return jsonify({"status": "success", "bmi": round(bmi, 2)})

@app.route("/api/get_username", methods=["GET"])
def get_username():
    return current_username if current_username else ""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
