from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import smtplib
from email.mime.text import MIMEText
from io import BytesIO
import random
import string
import pandas as pd
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)

users = {
    "DEPTCSE": "pksv"
}

attendance_data = {}

EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS", "vinaypydi85@gmail.com")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "pxbntsohbnbojhtw")  # use env vars for security

@app.route('/')
def home():
    return send_from_directory('static', 'frontend.html')

@app.route('/reset-password')
def reset_password():
    return "<h2>Password Reset Page - Feature under construction.</h2>"

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if username in users and users[username] == password:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid username or password"})

def generate_temp_password(length=8):
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(chars) for _ in range(length))

@app.route('/api/forgot_password', methods=['POST'])
def forgot_password():
    data = request.json
    username = data.get('username')
    if username in users:
        try:
            temp_password = generate_temp_password()
            users[username] = temp_password
            send_temp_password_email(temp_password)
            return jsonify({"success": True})
        except Exception:
            return jsonify({"success": False, "error": "Failed to send reset email"})
    return jsonify({"success": False, "error": "Username not found"})

def send_temp_password_email(temp_password):
    msg = MIMEText(f'Your temporary password is: {temp_password}\nPlease use this password to login and change it immediately.')
    msg['Subject'] = 'Your Temporary Password'
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = EMAIL_ADDRESS
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    server.send_message(msg)
    server.quit()

@app.route('/api/save', methods=['POST'])
def save_attendance():
    data = request.json
    date = data.get('date')
    attendance = data.get('attendance')
    if not date or not attendance:
        return jsonify({"success": False, "error": "Date or attendance missing"})
    attendance_data[date] = attendance
    return jsonify({"success": True})

@app.route('/api/check')
def check_attendance():
    regno = request.args.get('regno')
    date = request.args.get('date')
    if not regno or not date:
        return jsonify({"status": "Absent"})
    status = attendance_data.get(date, {}).get(regno, {}).get('status', "Absent")
    return jsonify({"status": status})

@app.route('/api/student_login', methods=['POST'])
def student_login():
    data = request.json
    regno = data.get('username')
    if not regno:
        return jsonify({"success": False, "error": "Registration number required"})
    # student exists if in any day's attendance data
    for day in attendance_data.values():
        if regno in day:
            return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid registration number"})

@app.route('/api/student/check_attendance')
def student_check_attendance():
    regno = request.args.get('regno')
    date = request.args.get('date')
    if not regno or not date:
        return jsonify({"status": "Absent"})
    status = attendance_data.get(date, {}).get(regno, {}).get('status', "Absent")
    return jsonify({"status": status})

@app.route('/api/export_absentees/')
def export_absentees():
    date = request.args.get('date')
    if not date or date not in attendance_data:
        return "No attendance data found for this date", 404
    absentees_dict = {}
    for regno, info in attendance_data[date].items():
        status = info.get('status')
        section = info.get('section', 'Unknown')
        if status in ['Absent', 'Permission']:
            absentees_dict.setdefault(section, []).append([regno, info.get('name'), status])
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        header_format = workbook.add_format({'bold': True, 'font_color': 'blue', 'font_size': 14})
        for section, rows in absentees_dict.items():
            df = pd.DataFrame(rows, columns=["Reg No", "Name", "Status"])
            df.to_excel(writer, sheet_name=f"Section {section}", startrow=2, index=False)
            worksheet = writer.sheets[f"Section {section}"]
            worksheet.write(0, 0, f"Attendance Date: {date}", header_format)
    output.seek(0)
    filename = "absentees_and_permissions.xlsx"
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/export_weekly_report/')
def export_weekly_report():
    start_date_str = request.args.get('start_date')
    if not start_date_str:
        return jsonify({"error": "start_date parameter is required"}), 400
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400
    week_dates = [(start_date + timedelta(days=i)).isoformat() for i in range(7)]
    all_students = {}
    for date in week_dates:
        for regno, info in attendance_data.get(date, {}).items():
            if regno not in all_students:
                all_students[regno] = info.get('name', '')
    report_rows = []
    for regno, name in sorted(all_students.items()):
        row = {'Reg No': regno, 'Name': name}
        for date in week_dates:
            day_data = attendance_data.get(date, {})
            info = day_data.get(regno)
            row[date] = info.get('status', 'Absent') if info else 'Absent'
        report_rows.append(row)
    if not report_rows:
        return "No attendance data found for this week", 404
    df = pd.DataFrame(report_rows)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Weekly Attendance', index=False)
        workbook = writer.book
        worksheet = writer.sheets['Weekly Attendance']
        header_format = workbook.add_format({'bold': True, 'font_color': 'blue', 'font_size': 14})
        week_range = f"{week_dates[0]} to {week_dates[-1]}"
        worksheet.write(0, 0, f"Weekly Attendance Breakdown: {week_range}", header_format)
    output.seek(0)
    filename = f"weekly_attendance_breakdown_{week_dates[0]}_to_{week_dates[-1]}.xlsx"
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
                
