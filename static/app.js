// ====================================
// DATAPULSE — app.js
// Real-time WebSocket + Chart Logic
// ====================================

// ============ SOCKET SETUP ============
const socket = io({ transports: ['websocket', 'polling'] });

// ============ CHART INSTANCES ============
let categoryChartInst = null;
let monthChartInst    = null;

// ============ CHART DEFAULTS ============
Chart.defaults.font.family  = "'DM Sans', sans-serif";
Chart.defaults.font.size    = 12;
Chart.defaults.color        = '#6b7491';

// ============ CATEGORY CHART ============
function updateCategoryChart(labels, values) {
    const canvas = document.getElementById('categoryChart');
    const empty  = document.getElementById('categoryEmpty');
    if (!canvas) return;

    if (!labels || labels.length === 0) {
        canvas.style.display = 'none';
        if (empty) empty.style.display = 'flex';
        return;
    }

    canvas.style.display = 'block';
    if (empty) empty.style.display = 'none';

    const ctx = canvas.getContext('2d');
    if (categoryChartInst) categoryChartInst.destroy();

    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(26,86,240,0.85)');
    gradient.addColorStop(1, 'rgba(26,86,240,0.3)');

    categoryChartInst = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label          : 'Count',
                data           : values,
                backgroundColor: gradient,
                borderColor    : 'rgba(26,86,240,1)',
                borderWidth    : 0,
                borderRadius   : 6,
                borderSkipped  : false,
            }]
        },
        options: {
            responsive        : true,
            maintainAspectRatio: true,
            plugins: {
                legend : { display: false },
                tooltip: {
                    backgroundColor: '#0f1629',
                    padding        : 10,
                    cornerRadius   : 8,
                    titleColor     : '#ffffff',
                    bodyColor      : '#9ba3bf',
                }
            },
            scales: {
                x: {
                    grid : { display: false },
                    ticks: { maxRotation: 40 }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color      : 'rgba(0,0,0,0.04)',
                        borderDash : [4, 4]
                    }
                }
            }
        }
    });
}

// ============ MONTHLY CHART ============
function updateMonthChart(labels, values) {
    const canvas = document.getElementById('monthChart');
    const empty  = document.getElementById('monthEmpty');
    if (!canvas) return;

    if (!labels || labels.length === 0) {
        canvas.style.display = 'none';
        if (empty) empty.style.display = 'flex';
        return;
    }

    canvas.style.display = 'block';
    if (empty) empty.style.display = 'none';

    const ctx = canvas.getContext('2d');
    if (monthChartInst) monthChartInst.destroy();

    const gradient = ctx.createLinearGradient(0, 0, 0, 280);
    gradient.addColorStop(0, 'rgba(0,184,148,0.3)');
    gradient.addColorStop(1, 'rgba(0,184,148,0)');

    monthChartInst = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label          : 'Records',
                data           : values,
                borderColor    : '#00b894',
                backgroundColor: gradient,
                borderWidth    : 2.5,
                fill           : true,
                tension        : 0.4,
                pointRadius    : 4,
                pointHoverRadius: 7,
                pointBackgroundColor: '#00b894',
                pointBorderColor    : '#ffffff',
                pointBorderWidth    : 2,
            }]
        },
        options: {
            responsive        : true,
            maintainAspectRatio: true,
            plugins: {
                legend : { display: false },
                tooltip: {
                    backgroundColor: '#0f1629',
                    padding        : 10,
                    cornerRadius   : 8,
                    titleColor     : '#ffffff',
                    bodyColor      : '#9ba3bf',
                    mode           : 'index',
                    intersect      : false,
                }
            },
            scales: {
                x: {
                    grid : { display: false },
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color    : 'rgba(0,0,0,0.04)',
                        borderDash: [4, 4]
                    }
                }
            }
        }
    });
}

// ============ CORRELATION COLOUR ============
function colorCorrelationCells() {
    document.querySelectorAll('.corr-cell').forEach(cell => {
        const val = parseFloat(cell.dataset.val);
        if (isNaN(val)) return;
        const abs = Math.abs(val);
        if (val === 1) {
            cell.style.background = '#1a56f0';
            cell.style.color      = '#ffffff';
        } else if (abs >= 0.7) {
            cell.style.background = `rgba(26,86,240,${abs * 0.6})`;
            cell.style.color      = abs > 0.85 ? '#ffffff' : '#0f1629';
        } else if (abs >= 0.4) {
            cell.style.background = `rgba(0,184,148,${abs * 0.5})`;
        } else if (abs >= 0.1) {
            cell.style.background = `rgba(253,150,68,${abs * 0.5})`;
        } else {
            cell.style.background = '#f7f8fc';
            cell.style.color      = '#9ba3bf';
        }
    });
}

// ============ TOAST HELPER ============
function showToast(message, type = 'success') {
    const toast     = document.getElementById('liveToast');
    const toastBody = document.getElementById('toastBody');
    if (!toast || !toastBody) return;
    toastBody.innerText = message;
    toast.className = `toast align-items-center text-bg-${type} border-0`;
    new bootstrap.Toast(toast, { delay: 4000 }).show();
}

// ============ PROGRESS ============
function setProgress(percent, status, type = 'normal') {
    const container = document.getElementById('progress-container');
    const bar       = document.getElementById('progress-bar');
    const text      = document.getElementById('progress-text');

    if (container) container.style.display = 'block';
    if (bar) bar.style.width = percent + '%';
    if (text) {
        text.innerText  = status + ' (' + percent + '%)';
        text.style.color = type === 'error' ? '#e74c3c'
                         : type === 'done'  ? '#00b894'
                         : '#6b7491';
    }

    if (percent >= 100) {
        setTimeout(() => {
            if (container) container.style.display = 'none';
            if (bar) bar.style.width = '0%';
        }, 2500);
    }
}

// ============ STAT COUNTER ANIMATION ============
function animateCount(el, target) {
    if (!el) return;
    const start    = parseInt(el.innerText) || 0;
    const duration = 600;
    const step     = Math.abs(target - start) / (duration / 16);
    let   current  = start;
    const inc      = target > start ? step : -step;
    const timer    = setInterval(() => {
        current += inc;
        if ((inc > 0 && current >= target) || (inc < 0 && current <= target)) {
            el.innerText = target.toLocaleString();
            clearInterval(timer);
        } else {
            el.innerText = Math.round(current).toLocaleString();
        }
    }, 16);
}

// ============ SOCKET EVENTS ============

socket.on('connect', () => {
    console.log('✅ Socket connected:', socket.id);
});

socket.on('disconnect', () => {
    console.log('❌ Socket disconnected');
});

socket.on('message', data => {
    console.log('📨 Server:', data.data);
});

// Real-time progress
socket.on('progress', data => {
    setProgress(data.percent, data.status);
});

// Upload error
socket.on('upload_error', data => {
    setProgress(0, '❌ ' + data.message, 'error');
    showToast('Upload failed: ' + data.message, 'danger');
    const btn = document.getElementById('uploadBtn');
    if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-upload"></i> Upload & Analyse'; }
});

// Dashboard live update
socket.on('dashboard_update', data => {
    console.log('🔥 Dashboard update received:', data);

    // Animate counters
    animateCount(document.getElementById('totalRecords'), data.total_records);
    const colEl = document.getElementById('totalColumns');
    if (colEl && data.preview_columns) {
        animateCount(colEl, data.preview_columns.length);
    }

    // Status badge
    const badge = document.getElementById('statusBadge');
    if (badge) badge.innerHTML = '<span class="badge bg-success">Ready ✅</span>';

    // Update column badges
    const catBadge  = document.getElementById('catColBadge');
    const dateBadge = document.getElementById('dateColBadge');
    if (catBadge) {
        catBadge.textContent = data.category_col
            ? data.category_col.toUpperCase()
            : (data.category_labels && data.category_labels.length ? data.category_labels.length + ' values' : '');
    }
    if (dateBadge) {
        dateBadge.textContent = data.date_col
            ? data.date_col.toUpperCase()
            : (data.month_labels && data.month_labels.length ? data.month_labels.length + ' months' : '');
    }

    // Charts
    updateCategoryChart(data.category_labels, data.category_values);
    updateMonthChart(data.month_labels, data.month_values);

    // Summary
    const summaryContent = document.getElementById('summaryContent');
    if (summaryContent && data.summary) {
        summaryContent.innerHTML = data.summary;
    }

    // Preview table
    if (data.preview_columns && data.preview_rows && data.preview_columns.length > 0) {
        updatePreviewTable(data.preview_columns, data.preview_rows);
    }

    showToast('Dashboard updated in real-time! 🚀', 'success');

    // Redirect to new dataset after processing — triggers pagination init
    if (data.dataset_id) {
        setTimeout(() => {
            window.location.href = '/dashboard?dataset=' + data.dataset_id;
        }, 1500);
    }
});

// ============ UPDATE PREVIEW TABLE ============
function updatePreviewTable(columns, rows) {
    const wrapper = document.getElementById('previewWrapper');
    if (!wrapper) return;

    // Build full table from scratch
    let html = '<div class="table-scroll"><table class="preview-table"><thead><tr>';
    columns.forEach(col => { html += `<th>${col}</th>`; });
    html += '</tr></thead><tbody>';
    rows.forEach(row => {
        html += '<tr>';
        row.forEach(cell => { html += `<td>${cell ?? ''}</td>`; });
        html += '</tr>';
    });
    html += '</tbody></table></div>';
    wrapper.innerHTML = html;
}

// ============ UPLOAD FORM ============
const ALLOWED_UPLOAD_EXTS = ['.csv', '.xlsx', '.xls'];

const uploadForm = document.getElementById('uploadForm');
if (uploadForm) {
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const fileInput = document.getElementById('fileInput');
        const file      = fileInput ? fileInput.files[0] : null;

        if (!file) {
            showToast('Please select a file', 'warning');
            return;
        }

        // Check allowed extension
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        if (!ALLOWED_UPLOAD_EXTS.includes(ext)) {
            showToast('Only CSV and Excel (.xlsx/.xls) files are supported', 'danger');
            return;
        }

        const btn = document.getElementById('uploadBtn');
        if (btn) {
            btn.disabled    = true;
            btn.innerHTML   = '<span class="spinner-border spinner-border-sm me-1"></span> Uploading...';
        }

        setProgress(5, 'Uploading file...');

        const formData = new FormData();
        formData.append('file', file);

        fetch('/upload-file', {
            method: 'POST',
            body  : formData
        })
        .then(r => {
            if (!r.ok) return r.json().then(e => Promise.reject(e));
            return r.json();
        })
        .then(data => {
            console.log('✅ Upload success:', data);
            showToast('File uploaded! Processing...', 'success');
            if (btn) {
                btn.disabled  = false;
                btn.innerHTML = '<i class="bi bi-upload"></i> Upload & Analyse';
            }
            // Reset file input
            fileInput.value = '';
            const label = document.getElementById('uploadLabel');
            if (label) label.textContent = 'CSV or Excel';
            const dropZone = document.getElementById('dropZone');
            if (dropZone) dropZone.classList.remove('has-file');
        })
        .catch(err => {
            console.error('❌ Upload error:', err);
            const msg = err.message || err.error || 'Upload failed';
            showToast(msg, 'danger');
            setProgress(0, '❌ ' + msg, 'error');
            if (btn) {
                btn.disabled  = false;
                btn.innerHTML = '<i class="bi bi-upload"></i> Upload & Analyse';
            }
        });
    });
}

// ============ INIT ON PAGE LOAD ============
window.addEventListener('DOMContentLoaded', () => {
    console.log('📊 DataPulse initialised');

    // Load charts from server-rendered data
    const categoryCanvas = document.getElementById('categoryChart');
    if (categoryCanvas) {
        try {
            const labels = JSON.parse(categoryCanvas.dataset.labels || '[]');
            const values = JSON.parse(categoryCanvas.dataset.values || '[]');
            updateCategoryChart(labels, values);
        } catch(e) { console.warn('Category data parse error', e); }
    }

    const monthCanvas = document.getElementById('monthChart');
    if (monthCanvas) {
        try {
            const labels = JSON.parse(monthCanvas.dataset.labels || '[]');
            const values = JSON.parse(monthCanvas.dataset.values || '[]');
            updateMonthChart(labels, values);
        } catch(e) { console.warn('Month data parse error', e); }
    }

    // Colour correlation cells
    colorCorrelationCells();
});