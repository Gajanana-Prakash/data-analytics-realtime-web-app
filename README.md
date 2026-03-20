# 📊 Data Analytics Dashboard Web Application

A **Flask-based Data Analytics Web Application** that allows users to upload CSV datasets and automatically generate interactive analytics dashboards using **Python, Pandas, and Chart.js**.

This project demonstrates **data processing, backend development, database integration, and interactive data visualization**.

---

# 🚀 Features

### 🔐 User Authentication

* Secure login system
* Session-based authentication
* User-specific dataset management

### 📂 Dataset Upload

* Upload CSV datasets through the web interface
* Files stored securely with **UUID-based filenames**
* Upload metadata saved in SQLite database

### 📊 Analytics Dashboard

After uploading a dataset, the dashboard automatically generates:

* ✔ **Total Records Card**
* ✔ **Dataset Preview (First 10 rows)**
* ✔ **Category Distribution Chart**
* ✔ **Monthly Trend Chart**
* ✔ **Correlation Matrix (Numeric Columns)**

### 📈 Data Visualization

Interactive charts powered by **Chart.js**:

* Bar Chart – Category distribution
* Line Chart – Monthly trend
* Correlation Matrix – Numeric relationships

### 📁 Dataset Management

* View all uploaded datasets
* Select dataset for analysis
* Data preview table

---

# 🛠️ Tech Stack

### Backend

* Python
* Flask
* Flask-SQLAlchemy
* Pandas

### Frontend

* HTML5
* CSS3
* JavaScript
* Chart.js

### Database

* SQLite

### Other Tools

* UUID (for secure file naming)
* Jinja2 Templates

---

# 📂 Project Structure

```
data-analytics-dashboard/
│
├── app.py
├── database.db
├── requirements.txt
│
├── uploads/
│   └── (CSV files stored with UUID names)
│
├── templates/
│   ├── login.html
│   ├── upload.html
│   └── dashboard.html
│
├── static/
│   └── style.css
│
└── README.md
```

---

# ⚙️ Installation

### 1️⃣ Clone the Repository

```
git clone https://github.com/yourusername/data-analytics-dashboard.git
cd data-analytics-dashboard
```

---

### 2️⃣ Create Virtual Environment

```
python -m venv venv
```

Activate it:

**Windows**

```
venv\Scripts\activate
```

**Mac / Linux**

```
source venv/bin/activate
```

---

### 3️⃣ Install Dependencies

```
pip install -r requirements.txt
```

---

### 4️⃣ Run the Application

```
python app.py
```

Open browser:

```
http://127.0.0.1:5000
```

---

# 📄 CSV Dataset Format

To generate correct dashboard charts, the CSV file should contain at least the following columns:

```
date,category
```

Recommended format:

```
date,category,sales,profit,quantity
2024-01-01,Electronics,200,50,2
2024-01-02,Clothing,150,40,3
2024-02-03,Food,120,20,5
```

### Required Columns

* **date** → Used for Monthly Trend Chart
* **category** → Used for Category Distribution Chart

### Numeric Columns

Used for correlation analysis:

* sales
* profit
* quantity

---

# 📸 Application Screenshots

### Login Page

User authentication interface.

### Upload Dataset Page

Upload CSV datasets for analysis.

### Dashboard Analytics

Displays:

* Total Records
* Dataset Preview
* Category Distribution Chart
* Monthly Trend Chart
* Correlation Matrix

---

# 🔒 Security

* Files saved using **UUID filenames**
* Prevents filename conflicts
* Protects against file overwrite attacks

Example stored file:

```
uploads/7d4f8a9c-91d3-4e5f-8a32-93a8e4f1d21c.csv
```

---

# 🎯 Use Cases

* Data Analyst Portfolio Project
* Data Visualization Demonstration
* CSV Data Exploration Tool
* Beginner Flask Data Analytics Project

---

# 📈 Future Improvements

Planned enhancements:

* Dataset delete feature
* Dataset rename option
* Advanced analytics (mean, median, variance)
* Interactive filtering
* File size validation
* Multi-user dataset isolation
* Deployment on cloud (AWS / Render / Heroku)

---

# 👨‍💻 Author

**Prakash Kumar**

Data Analytics & Python Enthusiast

Skills:

* Python
* Data Analysis
* SQL
* Power BI

---

# ⭐ If you like this project

Please consider giving it a **star ⭐ on GitHub**.
