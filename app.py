"""
AAT PoC Dashboard - DB 驅動圖表
================================
部署平台：Render
DB：SQLite (aat_poc_v2.db)
圖表：Chart.js

@11星協作：@光蘊 @典野 @理樞
"""

import os
import sqlite3
import json
from flask import Flask, render_template, jsonify, request
from datetime import datetime

app = Flask(__name__)

# DB 路徑
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'aat_poc_v2.db')

def get_db():
    """取得 DB 連線"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ============================================================
# API Routes - 數據端點
# ============================================================

@app.route('/api/stats')
def api_stats():
    """總覽統計"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 表數量
    cursor.execute("SELECT COUNT(*) FROM _table_catalog")
    table_count = cursor.fetchone()[0]
    
    # 總筆數
    cursor.execute("SELECT SUM(row_count) FROM _table_catalog")
    total_rows = cursor.fetchone()[0]
    
    # 產線數
    cursor.execute("SELECT COUNT(DISTINCT line_no) FROM daily_capacity")
    line_count = cursor.fetchone()[0]
    
    # 平均良率
    cursor.execute("SELECT AVG(yield_rate) FROM daily_capacity")
    avg_yield = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        "table_count": table_count,
        "total_rows": f"{total_rows:,}",
        "line_count": line_count,
        "avg_yield": round(avg_yield, 2) if avg_yield else 0
    })

@app.route('/api/daily_yield')
def api_daily_yield():
    """每日良率趨勢"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT date, AVG(yield_rate) as yield_rate
        FROM daily_capacity
        GROUP BY date
        ORDER BY date
        LIMIT 60
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify({
        "labels": [row['date'] for row in rows],
        "data": [round(row['yield_rate'], 4) for row in rows]
    })

@app.route('/api/line_comparison')
def api_line_comparison():
    """各產線比較"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT line_no, 
               AVG(yield_rate) as avg_yield,
               AVG(defect_rate) as avg_defect,
               SUM(total_good) as total_output
        FROM daily_capacity
        GROUP BY line_no
        ORDER BY line_no
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify({
        "labels": [row['line_no'] for row in rows],
        "yield_data": [round(row['avg_yield'] * 100, 2) for row in rows],
        "defect_data": [round(row['avg_defect'] * 100, 2) for row in rows],
        "output_data": [row['total_output'] for row in rows]
    })

@app.route('/api/defect_trend')
def api_defect_trend():
    """不良率趨勢（各產線）"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 取得所有產線
    cursor.execute("SELECT DISTINCT line_no FROM daily_capacity ORDER BY line_no")
    lines = [row['line_no'] for row in cursor.fetchall()]
    
    datasets = []
    colors = ['#4472C4', '#ED7D31', '#A5A5A5', '#FFC000']
    
    for i, line in enumerate(lines):
        cursor.execute("""
            SELECT date, defect_rate
            FROM daily_capacity
            WHERE line_no = ?
            ORDER BY date
            LIMIT 30
        """, (line,))
        rows = cursor.fetchall()
        
        datasets.append({
            "label": line,
            "data": [round(row['defect_rate'] * 100, 2) for row in rows],
            "borderColor": colors[i % len(colors)],
            "fill": False
        })
    
    # 取日期標籤
    cursor.execute("""
        SELECT DISTINCT date FROM daily_capacity 
        ORDER BY date LIMIT 30
    """)
    labels = [row['date'] for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        "labels": labels,
        "datasets": datasets
    })

@app.route('/api/capacity_distribution')
def api_capacity_distribution():
    """產能分佈（圓餅圖）"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT line_no, SUM(total_good) as capacity
        FROM daily_capacity
        GROUP BY line_no
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify({
        "labels": [row['line_no'] for row in rows],
        "data": [row['capacity'] for row in rows]
    })

@app.route('/api/scan_events')
def api_scan_events():
    """連續掃碼事件"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT line_no, COUNT(*) as event_count
        FROM scan_continuous_summary
        GROUP BY line_no
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify({
        "labels": [row['line_no'] for row in rows],
        "data": [row['event_count'] for row in rows]
    })

@app.route('/api/qr_trace')
def api_qr_trace():
    """QR 追溯統計"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT result, COUNT(*) as count
        FROM qr_trace_index
        GROUP BY result
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify({
        "labels": [row['result'] for row in rows],
        "data": [row['count'] for row in rows]
    })

@app.route('/api/hourly_pattern')
def api_hourly_pattern():
    """小時產能模式（熱力圖數據）"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT line_no, 
               AVG(hourly_output) as avg_hourly,
               AVG(yield_rate) as avg_yield
        FROM daily_capacity
        GROUP BY line_no
        ORDER BY line_no
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify({
        "lines": [row['line_no'] for row in rows],
        "hourly_output": [round(row['avg_hourly'], 0) for row in rows],
        "yield_rate": [round(row['avg_yield'] * 100, 2) for row in rows]
    })

@app.route('/api/lowest_yield')
def api_lowest_yield():
    """最低良率記錄"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT line_no, date, yield_rate, defect_rate
        FROM daily_capacity
        ORDER BY yield_rate ASC
        LIMIT 10
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify({
        "records": [
            {
                "line": row['line_no'],
                "date": row['date'],
                "yield": round(row['yield_rate'] * 100, 2),
                "defect": round(row['defect_rate'] * 100, 2)
            }
            for row in rows
        ]
    })

# ============================================================
# Page Routes
# ============================================================

@app.route('/')
def index():
    """主頁"""
    return render_template('index.html')

@app.route('/health')
def health():
    """健康檢查"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

# ============================================================
# Main
# ============================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
