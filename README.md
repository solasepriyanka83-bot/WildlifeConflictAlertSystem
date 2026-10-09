# WildSense — Wildlife Conflict Alert System

AI-powered wildlife monitoring dashboard: Flask + SQLite + YOLOv8 + ESP32-CAM.

## 1. Setup

```bash
cd WildlifeConflictAlertSystem
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open **http://localhost:5000**

## 2. Default login

```
Email:    admin@wildsense.com
Password: admin123
```

Change this password (or create a new admin and disable this one) before any real deployment —
see "Security" below.

## 3. Demo mode vs real YOLOv8

The app runs in **mock detection mode** by default — no camera, no model download needed.
Click **"Simulate PIR Trigger + Capture"** on the Live Status page to generate a full,
realistic detection event (image, species, confidence, threat level) that flows through
every page: Dashboard → Live Status → Alerts → Records → Gallery → History → Reports.

To use **real YOLOv8 inference**:
```bash
pip install ultralytics
export USE_REAL_YOLO=1        # Windows: set USE_REAL_YOLO=1
python app.py
```
`ultralytics` will auto-download `yolov8n.pt` on first run (needs internet). Real frames
posted to `/api/detect` (e.g. from the ESP32-CAM) will then be run through actual YOLOv8
object detection instead of the simulator.

## 4. ESP32-CAM hardware

`esp32cam/esp32cam_wildlife.ino` is a ready-to-flash Arduino sketch:
- PIR sensor on GPIO 13 triggers a capture
- Captured JPEG is POSTed to `/api/detect` on your Flask server
- LED (GPIO 12) + buzzer (GPIO 15) pulse once the server accepts the frame

Before flashing, edit these constants at the top of the `.ino`:
```cpp
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* SERVER_IP     = "192.168.1.100";   // your PC's LAN IP running app.py
```
Your Flask server and the ESP32-CAM must be on the same network, and `app.py` must be run
with `host="0.0.0.0"` (already set) so it's reachable from other devices.

## 5. Security implemented

- Session-based authentication (Flask `session`, server-side secret key)
- Passwords hashed with Werkzeug's `generate_password_hash` / `check_password_hash` — never stored in plain text
- `/register` (create new users) is **admin-only**, enforced server-side, not just hidden in the UI
- All dashboard/API routes wrapped in `@login_required`
- Email format + minimum password length validated on registration
- Logout fully clears the session

**Before production use**, also add: HTTPS (reverse proxy / gunicorn + nginx), a real
`SECRET_KEY` from an environment variable (never hardcoded), rate limiting on `/login`,
and CSRF protection (e.g. `Flask-WTF`) on all forms.

## 6. Project structure

```
WildlifeConflictAlertSystem/
├── app.py                  # Flask routes
├── database.py              # SQLite schema + queries
├── detector.py               # YOLOv8 wrapper (real + mock modes)
├── report_generator.py       # PDF report builder
├── requirements.txt
├── esp32cam/
│   └── esp32cam_wildlife.ino
├── static/
│   ├── css/style.css
│   ├── js/main.js
│   └── images/detections/    # captured frames land here
├── templates/
│   ├── login.html / register.html / base.html
│   ├── dashboard.html / live_status.html / alerts.html
│   ├── records.html / gallery.html / history.html / reports.html
└── reports/                 # generated PDF reports land here
```

## 7. Notes on this build

- Built for demo/prototype purposes (final year project, hackathon, SIH, exhibition).
- The wildlife/forest background is done with CSS (gradients + subtle texture) rather than
  a stock photo, so there's nothing to swap out or license — drop your own image into
  `static/images/` and reference it in `style.css` under `body { background: ... }` if you'd
  like a photographic backdrop instead.
- SQLite is used for simplicity; swap `database.py` for PostgreSQL/MySQL if you need
  multi-device concurrent writes at scale.
