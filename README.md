# DataPulse — Real-Time Data Analytics Web Application

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0.3-green?style=flat-square&logo=flask)
![SocketIO](https://img.shields.io/badge/Flask--SocketIO-5.3.6-orange?style=flat-square)
![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey?style=flat-square&logo=sqlite)
![Bootstrap](https://img.shields.io/badge/UI-Bootstrap_5.3-purple?style=flat-square&logo=bootstrap)
![ChartJS](https://img.shields.io/badge/Charts-Chart.js-red?style=flat-square)

---

## 📌 Project Overview

**DataPulse** is a full-stack, production-grade **real-time data analytics dashboard** built from scratch using Python, Flask, WebSockets, Pandas, and Chart.js.

The core idea: Upload any CSV or Excel file → backend processes it instantly → dashboard updates **live without any page refresh** using WebSocket technology.

This project demonstrates end-to-end full-stack development skills including backend APIs, real-time communication, database management, data processing, authentication, and professional UI design.

---

## 🎯 Key Features

| Feature | Description |
|---|---|
| 🔐 User Authentication | Register, Login, Logout with hashed passwords (PBKDF2) |
| 📁 File Upload | Drag and drop or click to upload CSV and Excel (.xlsx/.xls) files |
| ⚡ Real-Time Processing | Live progress bar updates via WebSockets — no page refresh |
| 📊 Auto Chart Generation | Category Distribution (Bar) + Monthly Trend (Line) — auto-detects columns |
| 🔢 Statistical Summary | Mean, Std, Min, Max, Percentiles via Pandas describe() |
| 🔥 Correlation Heatmap | Color-coded correlation matrix for all numeric columns |
| 👁️ Paginated Data Preview | View 25, 50, or 100 rows at a time with Next/Prev navigation |
| 📥 Export Options | Download full data as Excel (3 sheets) or charts as PNG |
| 🗑️ Dataset Management | View, switch, and delete uploaded datasets per user |
| ⚡ In-Memory Caching | Datasets cached for 5 minutes — instant page switches |
| 📱 Responsive Design | Works on desktop, tablet, and mobile |

---

## 🏗️ Project Architecture

```
+-------------------------------------------------------------+
|                        USER BROWSER                         |
|                                                             |
|   HTML + Bootstrap 5   |   Chart.js   |  Socket.IO Client  |
|   (dashboard.html)     |   (app.js)   |  (app.js)          |
+----------------+-----------------------------+--------------+
                 |  HTTP Requests              | WebSocket
                 |  (REST API)                 | (Real-Time)
                 v                             v
+-------------------------------------------------------------+
|                     FLASK BACKEND                           |
|                                                             |
|   app.py                  |   socket_events.py             |
|   --------------------    |   -------------------          |
|   - Auth Routes           |   - connect handler            |
|   - Dashboard Route       |   - disconnect handler         |
|   - Upload Route          |   - room-based messaging       |
|   - Export Routes         |                                |
|   - Pagination API        |                                |
|   - Delete Route          |                                |
+----------------+-----------------------------+--------------+
                 |                             |
                 v                             v
+----------------------+       +------------------------------+
|   SQLite Database    |       |      Pandas Processing        |
|   ---------------    |       |      -----------------        |
|   - User table       |       |   - smart_read_csv()          |
|   - Dataset table    |       |   - smart_read_file()         |
|   (database.db)      |       |   - find_category_col()       |
+----------------------+       |   - find_date_col()           |
                               |   - In-memory cache           |
                               +------------------------------+
```

---

## 🔄 Application Flow

### 1. User Registration and Login
```
User fills Register form
       |
Flask hashes password (PBKDF2 via Werkzeug)
       |
User saved to SQLite database
       |
User logs in → session["user_id"] set
       |
Redirected to Dashboard
```

### 2. File Upload and Real-Time Processing
```
User selects CSV or Excel file
       |
JavaScript sends file via AJAX to /upload-file
       |
Flask saves file with UUID filename to /uploads folder
       |
Dataset record saved to SQLite database
       |
Background task started: process_data()
       |
+--------------------------------------------------+
|           BACKGROUND PROCESSING                   |
|                                                   |
|  emit(10%, "Reading file")                        |
|       |                                           |
|  smart_read_file() → DataFrame                    |
|       |                                           |
|  emit(30%, "Cleaning data")                       |
|       |                                           |
|  df.describe() → Statistical Summary              |
|       |                                           |
|  emit(50%, "Calculating statistics")              |
|       |                                           |
|  find_category_col() → Bar Chart data             |
|       |                                           |
|  emit(70%, "Generating charts")                   |
|       |                                           |
|  find_date_col() → Line Chart data                |
|  df.corr() → Correlation Matrix                   |
|       |                                           |
|  emit(100%, "Done")                               |
|       |                                           |
|  socketio.emit('dashboard_update', all_data)      |
+--------------------------------------------------+
       |
Frontend receives 'dashboard_update' event
       |
Charts update LIVE, stats animate, table refreshes
       |
Redirect to /dashboard?dataset=<id>
```

### 3. Dashboard Page Load with Cache
```
User visits /dashboard
       |
Flask checks session → login_required decorator
       |
Fetch datasets for this user from SQLite
       |
Check in-memory cache for selected dataset
       |
Cache HIT  → return cached DataFrame (instant)
Cache MISS → read file → cache it → return DataFrame
       |
Generate: charts, summary, preview, correlation
       |
Render dashboard.html with all data
       |
JavaScript initializes charts from server data
       |
Socket.IO connects → user joins their private room
```

### 4. Pagination Flow
```
User clicks Next/Prev or changes rows per page
       |
JavaScript calls /api/dataset-rows/<id>?page=2&per_page=25
       |
Flask fetches cached DataFrame (instant)
       |
Slices rows: df.iloc[25:50]
       |
Returns JSON: { columns, rows, page, pages, total }
       |
JavaScript rebuilds preview table instantly
```

### 5. Export Flow
```
Excel Export:
User clicks Export Excel
       |
Browser navigates to /export/excel/<dataset_id>
       |
Flask reads cached DataFrame
       |
Creates Excel with 3 sheets:
  Sheet 1 → Full Data
  Sheet 2 → Statistical Summary
  Sheet 3 → Category Counts
       |
Returns .xlsx file as download

PNG Export:
User clicks Export Chart PNG
       |
JavaScript calls canvas.toDataURL('image/png')
       |
Creates download link and triggers it instantly
(No server needed — runs 100% in browser)
```

---

## 🗄️ Database Schema

### User Table
```sql
CREATE TABLE user (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(100) UNIQUE NOT NULL,
    email    VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(200) NOT NULL  -- PBKDF2 hashed, never plain text
);
```

### Dataset Table
```sql
CREATE TABLE dataset (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    filename      VARCHAR(200) NOT NULL,  -- UUID_originalname.csv on disk
    original_name VARCHAR(200) NOT NULL,  -- shown in UI
    upload_date   DATETIME,
    total_rows    INTEGER DEFAULT 0,
    user_id       INTEGER REFERENCES user(id)
);
```

---

## 📁 Project Structure

```
data-analytics-realtime-web-app/
|
|-- app.py                  Main Flask app — routes, processing, exports
|-- socket_events.py        WebSocket connect/disconnect handlers
|-- requirements.txt        All Python dependencies
|-- README.md               This file
|-- pyrightconfig.json      VS Code type checking config
|
|-- .vscode/
|   |-- settings.json       VS Code Python interpreter settings
|
|-- instance/
|   |-- database.db         SQLite database (auto-created on first run)
|
|-- uploads/                Uploaded CSV/Excel files (auto-created)
|
|-- templates/
|   |-- base.html           Base layout — navbar, toast, Bootstrap links
|   |-- login.html          Login page with password show/hide toggle
|   |-- register.html       Registration page
|   |-- dashboard.html      Main analytics dashboard (all features)
|   |-- analytics.html      Dataset detail/summary page
|
|-- static/
    |-- app.js              Socket.IO client, Chart.js, pagination, export
    |-- style.css           Custom CSS — DM Sans font, CSS variables
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Language | Python 3.10+ | All backend logic |
| Web Framework | Flask 3.0.3 | HTTP routing, Jinja2 templating |
| Real-Time | Flask-SocketIO 5.3.6 | WebSocket server |
| Async | Threading (built-in) | Background task processing |
| Database ORM | Flask-SQLAlchemy 3.1.1 | Database models and queries |
| Database | SQLite | Lightweight file-based storage |
| Data Processing | Pandas 3.x | File reading, analysis, statistics |
| Excel Read/Write | OpenPyXL + XlsxWriter | .xlsx support |
| Auth Security | Werkzeug | PBKDF2 password hashing |
| Frontend | HTML5 + Bootstrap 5.3 | Responsive UI |
| Charts | Chart.js | Bar chart + Line chart |
| Icons | Bootstrap Icons | UI icons |
| Fonts | DM Sans + Syne (Google) | Custom typography |
| WS Client | Socket.IO JS 4.5.4 | Browser WebSocket |

---

## ⚙️ Installation and Setup

### Step 1 — Clone Repository
```bash
git clone https://github.com/Gajanana-Prakash/data-analytics-realtime-web-app.git
cd data-analytics-realtime-web-app
```

### Step 2 — Create Virtual Environment
```bash
# Windows
python -m venv venv_realtime
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv_realtime
source venv/bin/activate
```

### Step 3 — Install Dependencies
```bash
pip install -r requirements.txt
pip install openpyxl xlsxwriter
```

### Step 4 — Run Application
```bash
python app.py
```

### Step 5 — Open Browser
```
http://127.0.0.1:5000
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| GET | `/` | Redirect to login or dashboard | No |
| GET/POST | `/register` | User registration | No |
| GET/POST | `/login` | User login | No |
| GET | `/logout` | Clear session | Yes |
| GET | `/dashboard` | Main analytics dashboard | Yes |
| POST | `/upload-file` | Upload CSV or Excel file | Yes |
| POST | `/delete-dataset/<id>` | Delete dataset and file | Yes |
| GET | `/export/excel/<id>` | Download as Excel | Yes |
| GET | `/api/dataset-rows/<id>` | Paginated row data (JSON) | Yes |
| GET | `/analytics/<id>` | Dataset detail page | Yes |
| GET | `/api/datasets` | List all user datasets | Yes |

### WebSocket Events

| Direction | Event Name | Payload | Purpose |
|---|---|---|---|
| Server to Client | `progress` | `{percent, status}` | Upload progress bar |
| Server to Client | `dashboard_update` | All chart/stats data | Live dashboard refresh |
| Server to Client | `upload_error` | `{message}` | Show error to user |
| Server to Client | `message` | `{data}` | Connection confirmation |
| Client to Server | `ping_server` | none | Keep-alive check |

---

## 🔒 Security Features

| Feature | How it Works |
|---|---|
| Password Hashing | PBKDF2-SHA256 via Werkzeug — passwords never stored as plain text |
| Session Auth | Flask server-side sessions with a secret key |
| Data Isolation | All DB queries filter by `session['user_id']` |
| File Validation | Extension whitelist: `.csv`, `.xlsx`, `.xls` only |
| Safe Filenames | `secure_filename()` + UUID prefix prevents path traversal attacks |
| Upload Size | Max 50MB enforced at Flask config level |
| Route Protection | `@login_required` decorator on every private route |

---

## ⚡ Performance Optimizations

| Optimization | Result |
|---|---|
| In-memory DataFrame cache (5 min TTL) | Instant page switches after first load |
| `debug=False`, `use_reloader=False` | No file-scanning overhead |
| No `time.sleep()` in processing | Fastest possible processing pipeline |
| Static file caching (300s) | Browser caches CSS/JS between page loads |
| Client-side PNG export | Zero server load for chart image downloads |
| Pagination API (25/50/100 rows) | Never transfers full dataset to browser |

---

## 📊 Supported File Formats

| Format | Extension | Notes |
|---|---|---|
| CSV | `.csv` | Auto-detects separator: `,` `;` tab or pipe |
| Excel | `.xlsx` | Modern Excel — read with openpyxl |
| Excel Legacy | `.xls` | Older Excel format — also supported |

---



## 👨‍💻 Author

**Prakash Kumar**
GitHub: https://github.com/Gajanana-Prakash

---

## 📄 License

This project is open source and available under the MIT License.

---

*Built with Flask, WebSockets, Pandas, and Chart.js*