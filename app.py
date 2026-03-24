# ==============================
# IMPORTS
# ==============================

import os
import uuid
import time
import pandas as pd
from datetime import datetime

from flask import Flask, request, jsonify, redirect, render_template, session
# type: ignore yellow error
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


# ==============================
# FLASK APP
# ==============================

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

app.config["SECRET_KEY"] = "secretkey"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Upload folder
app.config["UPLOAD_FOLDER"] = "uploads"

# Create uploads folder automatically
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Initialize DB
db = SQLAlchemy(app)


# ==============================
# DATABASE MODELS
# ==============================

class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), unique=True)

    email = db.Column(db.String(100), unique=True)

    password = db.Column(db.String(200))


class Dataset(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    filename = db.Column(db.String(200))

    upload_date = db.Column(db.DateTime)

    user_id = db.Column(db.Integer)


# ==============================
# ANALYTICS FUNCTION
# ==============================

def analyze_dataset(filepath):

    df = pd.read_csv(filepath)

    total_records = len(df)

    summary = df.describe().to_html()

    return total_records, summary


# ==============================
# REAL-TIME PROCESSING FUNCTION
# ==============================

import time  # ✅ add this at top also (important)

def process_data(filepath):

    socketio.emit('progress', {'status': 'Processing started'})
    time.sleep(1)

    df = pd.read_csv(filepath)

    # ✅ FIX: standardize column names
    df.columns = df.columns.str.strip().str.lower()

    socketio.emit('progress', {'status': 'Calculating summary'})
    time.sleep(1)

    summary = df.describe().to_json()

    socketio.emit('progress', {'status': 'Generating insights'})
    time.sleep(1)

    total_records = len(df)

    # ===============================
    # 🔥 CREATE CHART DATA
    # ===============================

    # Example (adjust column names as per your dataset)

    # Category Chart
    if 'category' in df.columns:
        category_data = df['category'].value_counts()
        category_labels = category_data.index.tolist()
        category_values = category_data.values.tolist()
    else:
        category_labels = []
        category_values = []

    # Monthly Chart
    if 'order date' in df.columns:
        df['order date'] = pd.to_datetime(df['order date'], errors='coerce')

        # Convert to datetime
        df['order date'] = pd.to_datetime(df['order date'], errors='coerce')

        # Extract month name
        df['month'] = df['order date'].dt.strftime('%b')

        # Count values
        month_data = df['month'].value_counts()

        # Sort months properly
        month_order = [
            "Jan","Feb","Mar","Apr","May","Jun",
            "Jul","Aug","Sep","Oct","Nov","Dec"
        ]

        month_data = month_data.reindex(month_order).dropna()

        # Final labels and values
        month_labels = month_data.index.tolist()
        month_values = month_data.values.tolist()
    else:
        month_labels = []
        month_values = []

    socketio.emit('progress', {'status': 'Completed ✅'})

    # 🔥 SEND EVERYTHING
    socketio.emit('dashboard_update', {
        'total_records': total_records,
        'summary': summary,
        'category_labels': category_labels,
        'category_values': category_values,
        'month_labels': month_labels,
        'month_values': month_values
    })

    return total_records, summary


# ==============================
# SOCKET.IO EVENTS
# ==============================

@socketio.on('connect')
def handle_connect():
    print("Client connected")
    socketio.emit('message', {'data': 'Connected successfully'})


# ==============================
# HOME ROUTE
# ==============================

@app.route("/")
def home():
    return redirect("/login")


# ==============================
# REGISTER PAGE
# ==============================

@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        user = User(
            username=username,
            email=email,
            password=hashed_password
        )

        db.session.add(user)
        db.session.commit()

        return redirect("/login")

    return render_template("register.html")


# ==============================
# LOGIN PAGE
# ==============================

@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if not user:
            return "User not registered"

        if not check_password_hash(user.password, password):
            return "Incorrect password"

        session["user_id"] = user.id

        return redirect("/upload")

    return render_template("login.html")


# ==============================
# LOGOUT
# ==============================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# ==============================
# UPLOAD PAGE
# ==============================

@app.route("/upload", methods=["GET","POST"])
def upload():

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        file = request.files.get("file")

        if not file:
            return "No file uploaded"

        if file.filename == "":
            return "No file selected"

        if not file.filename.lower().endswith(".csv"):
            return "Only CSV files allowed"

        try:
            print("Step 1: Upload started")

            filename = secure_filename(file.filename)
            unique_filename = str(uuid.uuid4()) + "_" + filename

            filepath = os.path.join(
                app.config["UPLOAD_FOLDER"],
                unique_filename
            )

            file.save(filepath)
            print("Step 2: File saved")

            # 🔥 CALL REAL-TIME PROCESS FUNCTION
            total_records, summary = process_data(filepath)

            dataset = Dataset(
                filename=unique_filename,
                upload_date=datetime.now(),
                user_id=session["user_id"]
            )

            db.session.add(dataset)
            db.session.commit()
            print("Step 3: Database saved")

            # 🔥 SEND NOTIFICATION
            session["notification"] = "Dataset uploaded successfully"

            print("Step 4: Notification sent")

            return redirect("/dashboard")

        except Exception as e:

            print("Upload Error:", e)

            return "Upload failed"

    return render_template("upload.html")


# ==============================
# DATASET ANALYTICS PAGE
# ==============================

@app.route("/analytics/<filename>")
def analytics(filename):

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    total_records, summary = analyze_dataset(filepath)

    return render_template(
        "analytics.html",
        total_records=total_records,
        summary=summary
    )


# ==============================
# DASHBOARD
# ==============================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    dataset_id = request.args.get("dataset", type=int)

    datasets = Dataset.query.order_by(Dataset.upload_date.desc()).all()

    selected_dataset = None

    total_records = 0
    category_counts = {}
    monthly_counts = {}

    corr_labels = []
    corr_values = []

    preview_columns = []
    preview_rows = []

    if not dataset_id and datasets:
        selected_dataset = datasets[0]
    elif dataset_id:
        selected_dataset = Dataset.query.get(dataset_id)

    if selected_dataset:

        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"],
            selected_dataset.filename
        )

        if os.path.exists(filepath):

          
            try:

                df = pd.read_csv(filepath)

                # ✅ CLEAN COLUMN NAMES
                df.columns = df.columns.str.strip().str.lower()

                total_records = len(df)

                # ===============================
                # PREVIEW DATA
                # ===============================

                preview_df = df.head(10)

                preview_columns = preview_df.columns.tolist()
                preview_rows = preview_df.values.tolist()

                # ===============================
                # CATEGORY CHART
                # ===============================

                if "category" in df.columns:

                    counts = df["category"].value_counts()

                    category_counts = counts.to_dict()

                
                # ===============================
                # MONTHLY CHART (FIXED)
                # ===============================

                if "order date" in df.columns:

                    # ✅ Step 1: Convert column to datetime
                    df["order date"] = pd.to_datetime(df["order date"], errors="coerce")

                    # ✅ Step 2: Extract month (Jan, Feb, etc.)
                    df["month"] = df["order date"].dt.strftime("%b")

                    # ✅ Step 3: Count records per month
                    months = df["month"].value_counts()

                    # ✅ Step 4: Define correct month order
                    month_order = [
                        "Jan","Feb","Mar","Apr","May","Jun",
                        "Jul","Aug","Sep","Oct","Nov","Dec"
                    ]

                    # ✅ Step 5: Arrange months properly
                    months = months.reindex(month_order).dropna()

                    # ✅ Step 6: Convert to dictionary
                    monthly_counts = months.to_dict()

                # ===============================
                # CORRELATION
                # ===============================

                corr_matrix = df.corr(numeric_only=True).round(2)

                if not corr_matrix.empty:

                    corr_labels = corr_matrix.columns.tolist()
                    corr_values = corr_matrix.values.tolist()

            except Exception as e:

                print("Error loading dataset:", e)

    notification = session.pop("notification", None)

    return render_template(
    "dashboard.html",
    notification=notification,   # ✅ ADD THIS
    datasets=datasets,
    selected_dataset=selected_dataset.id if selected_dataset else None,
    total_records=total_records,
    total_datasets=len(datasets),
    category_labels=list(category_counts.keys()),
    category_values=list(category_counts.values()),
    month_labels=list(monthly_counts.keys()),
    month_values=list(monthly_counts.values()),
    corr_labels=corr_labels,
    corr_values=corr_values,
    preview_columns=preview_columns,
    preview_rows=preview_rows
    )


# ==============================
# API ROUTES
# ==============================

@app.route("/api/register", methods=["POST"])
def register_api():

    data = request.get_json()

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"error":"Missing fields"}),400

    if User.query.filter_by(username=username).first():
        return jsonify({"error":"Username exists"}),400

    if User.query.filter_by(email=email).first():
        return jsonify({"error":"Email exists"}),400

    hashed_password = generate_password_hash(password)

    user = User(
        username=username,
        email=email,
        password=hashed_password
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({"message":"User registered"})


@app.route("/api/login", methods=["POST"])
def login_api():

    data = request.get_json()

    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password,password):

        return jsonify({
            "message":"Login successful",
            "user_id":user.id
        })

    return jsonify({"error":"Invalid credentials"}),401


# ==============================
# RUN APP
# ==============================

if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    socketio.run(app, debug=True)


   