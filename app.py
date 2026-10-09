"""
app.py
Wildlife Conflict Alert System - Flask backend.
"""

import os
import csv
import io
from functools import wraps
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, send_file, Response
)
from werkzeug.security import generate_password_hash, check_password_hash

import database as db
import detector
from report_generator import generate_pdf_report

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-in-production")

db.init_db()


# ---------------- AUTH DECORATOR ----------------

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return wrapper


# ---------------- AUTH ROUTES ----------------

@app.route("/", methods=["GET"])
def root():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = db.get_user_by_email(email)
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["fullname"] = user["fullname"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['fullname']}.", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    # Only an already-logged-in admin can create new users
    if "user_id" not in session or session.get("role") != "admin":
        flash("Only an admin can register new users. Please log in as admin first.", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        fullname = request.form.get("fullname", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        role = request.form.get("role", "user")

        if not fullname or not email or not password:
            flash("All fields are required.", "error")
        elif "@" not in email or "." not in email.split("@")[-1]:
            flash("Enter a valid email address.", "error")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        elif db.get_user_by_email(email):
            flash("An account with that email already exists.", "error")
        else:
            db.create_user(fullname, email, generate_password_hash(password), role)
            flash("User created successfully.", "success")
            return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
@login_required
def dashboard():
    stats = db.get_stats()
    latest = db.get_latest_detection()
    return render_template("dashboard.html", stats=stats, latest=latest, active="dashboard")


# ---------------- LIVE STATUS ----------------

@app.route("/live-status")
@login_required
def live_status():
    latest = db.get_latest_detection()
    return render_template("live_status.html", latest=latest, active="live_status")


@app.route("/api/latest-detection")
@login_required
def api_latest_detection():
    latest = db.get_latest_detection()
    if not latest:
        return jsonify({"exists": False})
    return jsonify({
        "exists": True,
        "animal_name": latest["animal_name"],
        "confidence": latest["confidence"],
        "date_time": latest["date_time"],
        "location": latest["location"],
        "threat_level": latest["threat_level"],
        "image_name": latest["image_name"],
    })


# ---------------- DETECTION INGEST (ESP32-CAM posts here) ----------------

@app.route("/api/detect", methods=["POST"])
def api_detect():
    """
    ESP32-CAM (or any client / the 'Simulate Detection' button) POSTs
    an image here. We run YOLO (real or mock), store the result, and
    the dashboard/alerts pages auto-refresh to show it.
    """
    location = request.form.get("location", "Main Gate - Zone A")

    if "image" in request.files and request.files["image"].filename:
        source = request.files["image"]
    else:
        # No image supplied (e.g. simulate button) -> mock still works
        source = None

    if source:
        result = detector.process_and_detect(source, location=location)
    else:
        # Generate a mock result without a real uploaded file
        detections = detector.run_detection_mock()
        animal_name, confidence = detections[0]
        # create a placeholder filename since there's no real image
        filename = detector.save_incoming_image_placeholder() if hasattr(
            detector, "save_incoming_image_placeholder") else None
        result = {
            "animal_name": animal_name,
            "confidence": confidence,
            "image_name": filename or "no_image.jpg",
            "location": location,
        }

    if not result:
        return jsonify({"success": False, "message": "No recognizable animal detected."}), 200

    new_id = db.add_detection(
        result["animal_name"], result["confidence"],
        result["image_name"], result["location"]
    )
    return jsonify({"success": True, "id": new_id, **result})


# ---------------- RECORDS ----------------

@app.route("/records")
@login_required
def records():
    all_rows = db.get_all_detections()

    search = request.args.get("q", "").strip().lower()
    animal_filter = request.args.get("animal", "")
    page = int(request.args.get("page", 1))
    per_page = 10

    filtered = [r for r in all_rows if
                (not search or search in r["animal_name"].lower() or search in r["location"].lower()) and
                (not animal_filter or r["animal_name"] == animal_filter)]

    total = len(filtered)
    start = (page - 1) * per_page
    end = start + per_page
    page_rows = filtered[start:end]
    total_pages = max(1, (total + per_page - 1) // per_page)

    animals = sorted(set(r["animal_name"] for r in all_rows))

    return render_template(
        "records.html", rows=page_rows, page=page, total_pages=total_pages,
        search=search, animal_filter=animal_filter, animals=animals, active="records"
    )


@app.route("/records/export-csv")
@login_required
def export_csv():
    rows = db.get_all_detections()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Animal", "Confidence", "Date Time", "Location", "Threat Level", "Image"])
    for r in rows:
        writer.writerow([r["id"], r["animal_name"], r["confidence"], r["date_time"],
                          r["location"], r["threat_level"], r["image_name"]])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=detection_records.csv"}
    )


# ---------------- GALLERY ----------------

@app.route("/gallery")
@login_required
def gallery():
    rows = db.get_all_detections()
    return render_template("gallery.html", rows=rows, active="gallery")


@app.route("/gallery/delete/<image_name>", methods=["POST"])
@login_required
def gallery_delete(image_name):
    img_path = os.path.join("static", "images", "detections", image_name)
    if os.path.exists(img_path):
        os.remove(img_path)
    db.delete_detection_image(image_name)
    flash("Image deleted.", "success")
    return redirect(url_for("gallery"))


# ---------------- HISTORY ----------------

@app.route("/history")
@login_required
def history():
    rows = db.get_all_detections()
    search = request.args.get("q", "").strip().lower()
    if search:
        rows = [r for r in rows if search in r["animal_name"].lower() or search in r["location"].lower()]
    return render_template("history.html", rows=rows, search=search, active="history")


# ---------------- ALERTS ----------------

@app.route("/alerts")
@login_required
def alerts():
    latest = db.get_latest_detection()
    return render_template("alerts.html", latest=latest, active="alerts")


# ---------------- REPORTS ----------------

@app.route("/reports")
@login_required
def reports():
    stats = db.get_stats()
    animal_freq = db.get_animal_frequency()
    daily_trend = db.get_daily_trend()
    threat_dist = db.get_threat_distribution()
    return render_template(
        "reports.html", stats=stats, animal_freq=animal_freq,
        daily_trend=daily_trend, threat_dist=threat_dist, active="reports"
    )


@app.route("/reports/download-pdf")
@login_required
def download_pdf():
    stats = db.get_stats()
    animal_freq = db.get_animal_frequency()
    threat_dist = db.get_threat_distribution()
    recent = db.get_all_detections()
    filepath = generate_pdf_report(stats, animal_freq, threat_dist, recent)
    return send_file(filepath, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
