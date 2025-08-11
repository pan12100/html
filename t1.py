from flask import Flask, request, render_template, redirect, session, jsonify
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import gspread
import hashlib

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# Setup Google Sheets connection
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("C:/Users/acer/Desktop/HTMI/credentials.json", scope)
client = gspread.authorize(creds)

sheet_users = client.open("BMI_system").worksheet("users")
sheet_bmi = client.open("BMI_system").worksheet("bmi_data")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route("/")
def home():
    if "username" in session:
        return redirect("/bmi_table")
    return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip().lower()  # แปลงเป็น lowercase และตัดช่องว่าง
        password = request.form["password"]
        dob = request.form.get("dob")
        gender = request.form.get("gender")

        hashed_pw = hash_password(password)

        users = sheet_users.get_all_records()
        # เช็ค username ใน sheet โดยแปลง lowercase และ strip ช่องว่างเหมือนกัน
        if any(u.get("username", "").strip().lower() == username for u in users):
            return "ชื่อผู้ใช้นี้มีอยู่แล้ว กรุณาเปลี่ยนชื่อผู้ใช้"

        sheet_users.append_row([username, hashed_pw, dob, gender])
        return redirect("/login")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]
        hashed_pw = hash_password(password)

        users_raw = sheet_users.get_all_records()
        # ✅ ทำความสะอาด key และ value
        users = [
            {k.strip().lower(): v.strip() if isinstance(v, str) else v for k, v in u.items()}
            for u in users_raw
        ]

        print("DEBUG raw users:", users_raw)
        print("DEBUG cleaned users:", users)
        print("DEBUG: Username input:", username)
        print("DEBUG: Hashed password input:", hashed_pw)

        for u in users:
            user = u.get("username", "").strip().lower()
            pw = u.get("password", "").strip()

            print(f"Checking user: '{user}', password: '{pw}'")
            if user == username and pw == hashed_pw:
                session["username"] = username
                return redirect("/bmi_table")

        return "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"

    return render_template("login.html")



@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/bmi_table", methods=["GET", "POST"])
def bmi_table():
    if "username" not in session:
        return redirect("/login")

    username = session["username"]
    bmi_data = sheet_bmi.get_all_records()

    user_data = [row for row in bmi_data if row.get("username") == username]
    user_data = sorted(user_data, key=lambda r: r.get("timestamp", ""), reverse=True)[:20]

    return render_template("bmi_table.html", username=username, bmi_data=user_data)

@app.route("/add_bmi", methods=["POST"])
def add_bmi():
    if "username" not in session:
        return redirect("/login")

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
    sheet_bmi.append_row([username, height, weight, round(bmi, 2), timestamp])

    return redirect("/bmi_table")

@app.route("/api/bmi", methods=["POST"])
def api_bmi():
    data = request.json
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

    users = sheet_users.get_all_records()
    if not any(u.get("username") == username for u in users):
        return jsonify({"status": "error", "message": "ไม่พบผู้ใช้"}), 404

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet_bmi.append_row([username, height, weight, round(bmi, 2), timestamp])

    return jsonify({"status": "success", "bmi": round(bmi, 2)})

if __name__ == "__main__":
    app.run(debug=True)
