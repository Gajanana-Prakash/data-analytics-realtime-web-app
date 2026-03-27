// ===============================
// SOCKET CONNECTION
// ===============================
const socket = io();

// ===============================
// GLOBAL VARIABLES
// ===============================
let categoryChartInstance = null;
let monthChartInstance = null;

// ===============================
// CATEGORY CHART FUNCTION
// ===============================
function updateCategoryChart(labels, values) {

    const canvas = document.getElementById("categoryChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");

    if (categoryChartInstance) {
        categoryChartInstance.destroy();
    }

    // ❗ Prevent empty chart
    if (!labels || labels.length === 0 || !values || values.length === 0) {
        console.log("⚠️ No category data to display");
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        return;
    }

    categoryChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Category Distribution',
                data: values,
                borderWidth: 1,
                backgroundColor: 'rgba(54, 162, 235, 0.5)',
                borderColor: 'rgba(54, 162, 235, 1)'
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    enabled: true
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// ===============================
// MONTH CHART FUNCTION
// ===============================
function updateMonthChart(labels, values) {

    const canvas = document.getElementById("monthChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");

    if (monthChartInstance) {
        monthChartInstance.destroy();
    }

    // ❗ Prevent empty chart
    if (!labels || labels.length === 0 || !values || values.length === 0) {
        console.log("⚠️ No month data to display");
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        return;
    }

    monthChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Monthly Trend',
                data: values,
                borderWidth: 2,
                fill: false,
                borderColor: 'rgba(75, 192, 192, 1)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                tension: 0.3,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Month'
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Value'
                    },
                    beginAtZero: true
                }
            }
        }
    });
}

// ===============================
// SOCKET CONNECTION EVENTS
// ===============================
socket.on('connect', function() {
    console.log("✅ Connected to server");
});

// ===============================
// ERROR HANDLING
// ===============================
socket.on('upload_error', function(data) {

    const container = document.getElementById("progress-container");
    const text = document.getElementById("progress-text");

    if (container) container.style.display = "block";
    if (text) {
        text.innerText = "❌ " + data.message;
        text.style.color = "red";
    }
});

// ===============================
// PROGRESS UPDATE (REAL-TIME)
// ===============================
socket.on('progress', function(data) {

    const container = document.getElementById("progress-container");
    const bar = document.getElementById("progress-bar");
    const text = document.getElementById("progress-text");

    if (container) container.style.display = "block";
    if (bar) bar.style.width = data.percent + "%";
    if (text) {
        text.innerText = data.status + " (" + data.percent + "%)";
        text.style.color = "black";
    }

    if (data.percent === 100) {
        if (text) text.style.color = "green";

        setTimeout(() => {
            if (container) container.style.display = "none";
        }, 2000);
    }
});

// ===============================
// DASHBOARD REAL-TIME UPDATE
// ===============================
socket.on('dashboard_update', function(data) {

    console.log("🔥 Real-time data received:", data);

    // Update total records
    const total = document.getElementById("totalRecords");
    if (total) total.innerText = data.total_records;

    // Update summary
    const summaryBox = document.getElementById("summaryContent");
    if (summaryBox) {
        summaryBox.innerHTML = data.summary;
    }

    // Update charts
    updateCategoryChart(data.category_labels, data.category_values);
    updateMonthChart(data.month_labels, data.month_values);
});

// ===============================
// FILE UPLOAD (AJAX)
// ===============================
document.getElementById("uploadForm").addEventListener("submit", function(e) {

    e.preventDefault();

    const fileInput = document.getElementById("fileInput");
    const file = fileInput.files[0];

    if (!file) {
        alert("⚠️ Please select a file");
        return;
    }

    // Reset progress bar
    const bar = document.getElementById("progress-bar");
    const text = document.getElementById("progress-text");
    const container = document.getElementById("progress-container");

    if (bar) bar.style.width = "0%";
    if (text) {
        text.innerText = "Uploading...";
        text.style.color = "black";
    }
    if (container) container.style.display = "block";

    const formData = new FormData();
    formData.append("file", file);

    fetch("/upload-file", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        console.log("✅ Upload success:", data);
    })
    .catch(err => {
        console.error("❌ Upload failed:", err);
    });
});

// ===============================
// INITIAL CHART LOAD
// ===============================
window.onload = function () {

    console.log("Page Loaded → Initializing Charts...");

    // CATEGORY CHART
    const categoryCanvas = document.getElementById("categoryChart");
    if (categoryCanvas) {
        const labels = JSON.parse(categoryCanvas.dataset.labels || "[]");
        const values = JSON.parse(categoryCanvas.dataset.values || "[]");
        updateCategoryChart(labels, values);
    }

    // MONTH CHART
    const monthCanvas = document.getElementById("monthChart");
    if (monthCanvas) {
        const labels = JSON.parse(monthCanvas.dataset.labels || "[]");
        const values = JSON.parse(monthCanvas.dataset.values || "[]");
        updateMonthChart(labels, values);
    }
};