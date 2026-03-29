# ==============================
# IMPORTS
# ==============================

import os
import io
import uuid
import time
import pandas as pd
from datetime import datetime

from flask import Flask, request, jsonify, redirect, render_template, session, url_for, flash, send_file, Response
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from socket_events import register_socket_events
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


# ==============================
# FLASK APP
# ==============================

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ── Performance settings ──────────────────────────────────
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 300   # Cache static files 5 min
app.config["JSON_SORT_KEYS"]            = False  # Faster JSON responses

# Register socket events
register_socket_events(socketio)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "supersecret123")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB max upload
ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls'}

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db = SQLAlchemy(app)

# ── In-memory dataset cache (avoids re-reading CSV on every page load) ──
_dataset_cache = {}   # { dataset_id: { 'df': df, 'time': timestamp } }
CACHE_TTL = 300       # seconds (5 minutes)

def get_cached_df(dataset_id, filepath, original_name):
    """Return cached DataFrame or read fresh and cache it."""
    import time as _time
    now = _time.time()
    if dataset_id in _dataset_cache:
        entry = _dataset_cache[dataset_id]
        if now - entry['time'] < CACHE_TTL:
            return entry['df']
    df = smart_read_file(filepath, original_name)
    _dataset_cache[dataset_id] = {'df': df, 'time': now}
    return df

def invalidate_cache(dataset_id):
    """Remove dataset from cache after delete or re-upload."""
    _dataset_cache.pop(dataset_id, None)


# ==============================
# DATABASE MODELS
# ==============================

class User(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email    = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    datasets = db.relationship("Dataset", backref="owner", lazy=True)


class Dataset(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    filename    = db.Column(db.String(200), nullable=False)
    original_name = db.Column(db.String(200), nullable=False, default="")
    upload_date = db.Column(db.DateTime, default=datetime.now)
    total_rows  = db.Column(db.Integer, default=0)
    user_id     = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


# ==============================
# HELPERS
# ==============================

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def smart_read_csv(filepath):
    """Auto-detect CSV separator (comma, semicolon, tab, pipe)."""
    import csv
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        sample = f.read(4096)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
        sep = dialect.delimiter
    except Exception:
        sep = ','
    df = pd.read_csv(filepath, sep=sep, encoding='utf-8', encoding_errors='replace')
    if len(df.columns) == 1:
        df = pd.read_csv(filepath, sep=',', encoding='utf-8', encoding_errors='replace')
    df.columns = df.columns.str.strip().str.lower()
    print(f"✅ CSV: {len(df)} rows × {len(df.columns)} cols | sep='{sep}' | cols={df.columns.tolist()}")
    return df


def smart_read_file(filepath, original_name):
    """Read CSV or Excel file into a cleaned DataFrame."""
    ext = os.path.splitext(original_name)[1].lower()
    if ext in ('.xlsx', '.xls'):
        try:
            df = pd.read_excel(filepath, engine='openpyxl')
            df.columns = df.columns.str.strip().str.lower()
            print(f"✅ Excel: {len(df)} rows × {len(df.columns)} cols")
            return df
        except Exception as e:
            raise ValueError(f"Could not read Excel file: {e}")
    else:
        return smart_read_csv(filepath)


def find_category_col(df):
    """
    Find best categorical column for bar chart.
    Priority: exact or partial match on common category keywords.
    Falls back to any column with 2-50 unique string values.
    """
    skip_keywords = ['date', 'time', 'id', 'email', 'phone', 'address', 'url', 'uuid']
    priority      = ['category', 'type', 'region', 'status', 'department',
                     'segment', 'group', 'class', 'brand', 'customer_type',
                     'gender', 'city', 'country', 'state', 'product']

    # Step 1 — exact priority keyword match (any dtype, low cardinality)
    for keyword in priority:
        for col in df.columns:
            if keyword == col or keyword in col:
                if any(s in col for s in skip_keywords):
                    continue
                n = df[col].nunique()
                if 2 <= n <= 50:
                    print(f"  → category col via priority keyword: {col}")
                    return col

    # Step 2 — any object column with reasonable cardinality
    for col in df.columns:
        if any(s in col for s in skip_keywords):
            continue
        if df[col].dtype == object:
            n = df[col].nunique()
            if 2 <= n <= 50:
                print(f"  → category col via fallback: {col}")
                return col

    # Step 3 — numeric column with very low cardinality (encoded categories)
    for col in df.columns:
        if any(s in col for s in skip_keywords):
            continue
        n = df[col].nunique()
        if 2 <= n <= 15:
            print(f"  → category col via low-cardinality numeric: {col}")
            return col

    print("  ⚠️ No suitable category column found")
    return None


def find_date_col(df):
    """Find best date/time column."""
    priority = ['date', 'time', 'month', 'year', 'created', 'updated', 'order']
    for keyword in priority:
        for col in df.columns:
            if keyword in col:
                return col
    return None


def analyze_dataset(filepath):
    df = smart_read_csv(filepath)
    total_records = len(df)
    summary = df.describe().to_html(classes="table table-sm table-bordered", border=0)
    return total_records, summary


# ==============================
# REAL-TIME PROCESSING FUNCTION
# ==============================

def process_data(filepath, user_id, dataset_id, original_name=""):

    def emit(percent, status):
        socketio.emit('progress', {'percent': percent, 'status': status}, room=str(user_id))

    try:
        emit(10, 'Reading file...')

        df = smart_read_file(filepath, original_name or filepath)

        emit(30, 'Cleaning data...')

        # Summary stats
        summary = df.describe().to_html(classes="table table-sm table-bordered", border=0)
        total_records = len(df)

        emit(50, 'Calculating statistics...')

        # ── Category chart ──────────────────────────────────────
        category_labels, category_values = [], []
        cat_col = find_category_col(df)
        print(f"📊 Category column selected: {cat_col}")
        if cat_col:
            counts = df[cat_col].value_counts().head(15)
            category_labels = [str(x) for x in counts.index.tolist()]
            category_values = [int(x) for x in counts.values.tolist()]

        emit(70, 'Generating charts...')

        # ── Monthly trend ────────────────────────────────────────
        month_labels, month_values = [], []
        date_col = find_date_col(df)
        print(f"📅 Date column selected: {date_col}")
        if date_col:
            try:
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                valid_dates = df[date_col].dropna()
                if len(valid_dates) > 0:
                    tmp = valid_dates.dt.strftime('%b')
                    month_order = ["Jan","Feb","Mar","Apr","May","Jun",
                                   "Jul","Aug","Sep","Oct","Nov","Dec"]
                    m_counts = tmp.value_counts().reindex(month_order).dropna()
                    month_labels = [str(x) for x in m_counts.index.tolist()]
                    month_values = [int(x) for x in m_counts.values.tolist()]
            except Exception as e:
                print(f"WARNING date processing: {e}")

        # Correlation — convert NaN to None (JSON null)
        corr_labels, corr_values = [], []
        try:
            corr = df.corr(numeric_only=True).round(2)
            if not corr.empty:
                corr_labels = [str(x) for x in corr.columns.tolist()]
                corr_values = [
                    [None if (v != v) else float(v) for v in row]
                    for row in corr.values.tolist()
                ]
        except Exception as e:
            print(f"WARNING correlation: {e}")

        # Preview — stringify everything to avoid NaT/NaN serialization errors
        preview_columns = [str(c) for c in df.columns.tolist()]
        preview_rows = [
            ['' if str(cell) in ('NaT', 'nan', 'None', '<NA>') else str(cell)
             for cell in row]
            for row in df.head(10).values.tolist()
        ]

        # Update DB row count
        with app.app_context():
            ds = db.session.get(Dataset, dataset_id)
            if ds:
                ds.total_rows = total_records
                db.session.commit()

        emit(100, 'Done ✅')

        socketio.emit('dashboard_update', {
            'dataset_id'     : dataset_id,
            'total_records'  : total_records,
            'summary'        : summary,
            'category_labels': category_labels,
            'category_values': category_values,
            'category_col'   : cat_col or '',
            'month_labels'   : month_labels,
            'month_values'   : month_values,
            'date_col'       : date_col or '',
            'corr_labels'    : corr_labels,
            'corr_values'    : corr_values,
            'preview_columns': preview_columns,
            'preview_rows'   : preview_rows,
        }, room=str(user_id))

    except Exception as e:
        print(f"❌ process_data error: {e}")
        socketio.emit('upload_error', {'message': str(e)}, room=str(user_id))


# ==============================
# ROUTES — AUTH
# ==============================

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "danger")
            return render_template("register.html")

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return render_template("register.html")

        user = User(
            username=username,
            email=email,
            password=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash("Invalid email or password.", "danger")
            return render_template("login.html")

        session["user_id"]   = user.id
        session["username"]  = user.username
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ==============================
# ROUTES — DASHBOARD
# ==============================

@app.route("/dashboard")
@login_required
def dashboard():
    dataset_id = request.args.get("dataset", type=int)

    # Only show datasets belonging to current user
    datasets = Dataset.query.filter_by(
        user_id=session["user_id"]
    ).order_by(Dataset.upload_date.desc()).all()

    selected_dataset  = None
    total_records     = 0
    category_labels   = []
    category_values   = []
    month_labels      = []
    month_values      = []
    corr_labels       = []
    corr_values       = []
    preview_columns   = []
    preview_rows      = []
    summary           = ""

    if dataset_id:
        selected_dataset = Dataset.query.filter_by(
            id=dataset_id, user_id=session["user_id"]
        ).first()
    elif datasets:
        selected_dataset = datasets[0]

    if selected_dataset:
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], selected_dataset.filename)

        if os.path.exists(filepath):
            try:
                df = get_cached_df(selected_dataset.id, filepath, selected_dataset.original_name)
                total_records = len(df)
                summary = df.describe().to_html(classes="table table-sm table-bordered", border=0)
                print(f"✅ Summary generated: {len(summary)} chars")

                # Preview — safe stringify
                preview_columns = [str(c) for c in df.columns.tolist()]
                preview_rows = [
                    ['' if str(cell) in ('NaT','nan','None','<NA>') else str(cell)
                     for cell in row]
                    for row in df.head(10).values.tolist()
                ]
                print(f"✅ Preview: {len(preview_columns)} cols, {len(preview_rows)} rows")

                # Category — smart detection
                cat_col = find_category_col(df)
                print(f"📊 Dashboard category col: {cat_col}")
                if cat_col:
                    counts = df[cat_col].value_counts().head(15)
                    category_labels = [str(x) for x in counts.index.tolist()]
                    category_values = [int(x) for x in counts.values.tolist()]

                # Monthly — smart detection
                date_col = find_date_col(df)
                print(f"📅 Dashboard date col: {date_col}")
                if date_col:
                    try:
                        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                        valid = df[date_col].dropna()
                        if len(valid) > 0:
                            month_order = ["Jan","Feb","Mar","Apr","May","Jun",
                                           "Jul","Aug","Sep","Oct","Nov","Dec"]
                            m = valid.dt.strftime('%b').value_counts().reindex(month_order).dropna()
                            month_labels = [str(x) for x in m.index.tolist()]
                            month_values = [int(v) for v in m.values.tolist()]
                    except Exception as e:
                        print(f"WARNING monthly: {e}")

                # Correlation — safe NaN handling
                try:
                    corr = df.corr(numeric_only=True).round(2)
                    if not corr.empty:
                        corr_labels = [str(x) for x in corr.columns.tolist()]
                        corr_values = [
                            [None if (v != v) else float(v) for v in row]
                            for row in corr.values.tolist()
                        ]
                except Exception as e:
                    print(f"WARNING correlation: {e}")

                # Summary — ensure it's generated
                if not summary:
                    summary = df.describe().to_html(
                        classes="table table-sm table-bordered", border=0
                    )

            except Exception as e:
                print(f"❌ Dashboard load error: {e}")

    return render_template(
        "dashboard.html",
        datasets        = datasets,
        selected_dataset= selected_dataset.id if selected_dataset else None,
        selected_name   = selected_dataset.original_name if selected_dataset else "",
        total_records   = total_records,
        total_datasets  = len(datasets),
        summary         = summary,
        category_labels = category_labels,
        category_values = category_values,
        month_labels    = month_labels,
        month_values    = month_values,
        corr_labels     = corr_labels,
        corr_values     = corr_values,
        preview_columns = preview_columns,
        preview_rows    = preview_rows,
    )


# ==============================
# ROUTES — UPLOAD
# ==============================

@app.route("/upload", methods=["GET"])
@login_required
def upload_page():
    return redirect(url_for("dashboard"))


@app.route("/upload-file", methods=["POST"])
@login_required
def upload_file():
    file = request.files.get("file")

    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"Only CSV, Excel (.xlsx/.xls), and PDF files are allowed"}), 400

    try:
        original_name   = secure_filename(file.filename)
        unique_filename = str(uuid.uuid4()) + "_" + original_name
        filepath        = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
        file.save(filepath)

        dataset = Dataset(
            filename      = unique_filename,
            original_name = original_name,
            upload_date   = datetime.now(),
            user_id       = session["user_id"]
        )
        db.session.add(dataset)
        db.session.commit()

        socketio.start_background_task(
            process_data,
            filepath,
            session["user_id"],
            dataset.id,
            original_name
        )

        return jsonify({
            "message"   : "File uploaded! Processing started...",
            "status"    : "success",
            "dataset_id": dataset.id
        })

    except Exception as e:
        print(f"❌ Upload error: {e}")
        socketio.emit('upload_error', {'message': str(e)}, room=str(session.get("user_id")))
        return jsonify({"status": "error", "message": str(e)}), 500


# ==============================
# ROUTES — DELETE DATASET
# ==============================

@app.route("/delete-dataset/<int:dataset_id>", methods=["POST"])
@login_required
def delete_dataset(dataset_id):
    ds = Dataset.query.filter_by(id=dataset_id, user_id=session["user_id"]).first()
    if not ds:
        return jsonify({"error": "Not found"}), 404
    try:
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], ds.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        db.session.delete(ds)
        db.session.commit()
        invalidate_cache(dataset_id)
        return jsonify({"message": "Dataset deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==============================
# ROUTES — EXPORT EXCEL SUMMARY
# ==============================

@app.route("/export/excel/<int:dataset_id>")
@login_required
def export_excel(dataset_id):
    ds = Dataset.query.filter_by(id=dataset_id, user_id=session["user_id"]).first()
    if not ds:
        return jsonify({"error": "Not found"}), 404

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], ds.filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404

    try:
        df = smart_read_file(filepath, ds.original_name)

        output = io.BytesIO()

        # Auto-detect best available Excel engine
        try:
            import openpyxl
            engine = 'openpyxl'
        except ImportError:
            try:
                import xlsxwriter
                engine = 'xlsxwriter'
            except ImportError:
                engine = None

        if engine:
            with pd.ExcelWriter(output, engine=engine) as writer:
                # Sheet 1 — Full Data
                df.to_excel(writer, sheet_name='Data', index=False)
                # Sheet 2 — Statistical Summary
                summary_df = df.describe().round(2)
                summary_df.to_excel(writer, sheet_name='Summary')
                # Sheet 3 — Category counts if available
                cat_col = find_category_col(df)
                if cat_col:
                    cat_df = df[cat_col].value_counts().reset_index()
                    cat_df.columns = [cat_col, 'count']
                    cat_df.to_excel(writer, sheet_name='Category', index=False)

            output.seek(0)
            export_name = os.path.splitext(ds.original_name)[0] + '_export.xlsx'
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=export_name
            )
        else:
            # Fallback — export as CSV if no Excel engine available
            csv_output = io.StringIO()
            df.to_csv(csv_output, index=False)
            csv_bytes = io.BytesIO(csv_output.getvalue().encode('utf-8'))
            export_name = os.path.splitext(ds.original_name)[0] + '_export.csv'
            return send_file(
                csv_bytes,
                mimetype='text/csv',
                as_attachment=True,
                download_name=export_name
            )
    except Exception as e:
        print(f"❌ Export error: {e}")
        return jsonify({"error": str(e)}), 500


# ==============================
# ROUTES — PAGINATED DATA API
# ==============================

@app.route("/api/dataset-rows/<int:dataset_id>")
@login_required
def dataset_rows(dataset_id):
    ds = Dataset.query.filter_by(id=dataset_id, user_id=session["user_id"]).first()
    if not ds:
        return jsonify({"error": "Not found"}), 404

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], ds.filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404

    try:
        page     = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        per_page = min(per_page, 100)  # cap at 100

        df      = get_cached_df(ds.id, filepath, ds.original_name)
        total   = len(df)
        pages   = (total + per_page - 1) // per_page

        start   = (page - 1) * per_page
        end     = start + per_page
        chunk   = df.iloc[start:end]

        columns = [str(c) for c in chunk.columns.tolist()]
        rows    = [
            ['' if str(cell) in ('NaT','nan','None','<NA>') else str(cell)
             for cell in row]
            for row in chunk.values.tolist()
        ]

        return jsonify({
            "columns"  : columns,
            "rows"     : rows,
            "page"     : page,
            "per_page" : per_page,
            "total"    : total,
            "pages"    : pages,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==============================
# ROUTES — ANALYTICS
# ==============================

@app.route("/analytics/<int:dataset_id>")
@login_required
def analytics(dataset_id):
    ds = Dataset.query.filter_by(id=dataset_id, user_id=session["user_id"]).first()
    if not ds:
        flash("Dataset not found.", "danger")
        return redirect(url_for("dashboard"))

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], ds.filename)
    total_records, summary = analyze_dataset(filepath)

    return render_template(
        "analytics.html",
        dataset=ds,
        total_records=total_records,
        summary=summary
    )


# ==============================
# API ROUTES
# ==============================

@app.route("/api/datasets")
@login_required
def api_datasets():
    datasets = Dataset.query.filter_by(user_id=session["user_id"]).all()
    return jsonify([{
        "id"          : d.id,
        "filename"    : d.original_name,
        "upload_date" : d.upload_date.strftime("%Y-%m-%d %H:%M"),
        "total_rows"  : d.total_rows
    } for d in datasets])


# ==============================
# RUN APP
# ==============================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    socketio.run(
        app,
        debug=False,
        host="127.0.0.1",
        port=5000,
        use_reloader=False,
        log_output=False
    )