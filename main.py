from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        password = request.form["password"]
        dob = request.form["dob"]
        gender = request.form["gender"]

        return f"""
        <h2>ลงทะเบียนเรียบร้อย!</h2>
        <p>ชื่อ: {name}</p>
        <p>วันเกิด: {dob}</p>
        <p>เพศ: {gender}</p>
        """
    return render_template("register.html")

if __name__ == "__main__":
    app.run(debug=True)
