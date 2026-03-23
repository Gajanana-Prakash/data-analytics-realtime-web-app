# ==============================
# IMPORTS
# ==============================

import os
import uuid
import pandas as pd
from datetime import datetime

from flask import Flask, request, jsonify, redirect, render_template, session
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

                df.columns = df.columns.str.strip()

                total_records = len(df)

                preview_df = df.head(10)

                preview_columns = preview_df.columns.tolist()
                preview_rows = preview_df.values.tolist()

                if "category" in df.columns:

                    counts = df["category"].value_counts()

                    category_counts = counts.to_dict()

                if "date" in df.columns:

                    df["date"] = pd.to_datetime(df["date"], errors="coerce")

                    df["month"] = df["date"].dt.strftime("%b")

                    months = df["month"].value_counts()

                    month_order = [
                        "Jan","Feb","Mar","Apr","May","Jun",
                        "Jul","Aug","Sep","Oct","Nov","Dec"
                    ]

                    months = months.reindex(month_order).dropna()

                    monthly_counts = months.to_dict()

                corr_matrix = df.corr(numeric_only=True).round(2)

                if not corr_matrix.empty:

                    corr_labels = corr_matrix.columns.tolist()
                    corr_values = corr_matrix.values.tolist()

            except Exception as e:

                print("Error loading dataset:", e)

    return render_template(
    "dashboard.html",
    notification = session.pop("notification", None),   # ✅ ADD THIS
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
