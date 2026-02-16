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
from flask import Flask, render_template, jsonify, request, request
from datetime import datetime

app = Flask(__name__)

# DB 路徑
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'aat_poc_v2.db')
ZW_DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'zw_poc_fake_60d.db')

def get_db():
    """取得 DB 連線（展示用）"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_zw_db():
    """取得正崴 DB 連線（深度分析）"""
    conn = sqlite3.connect(ZW_DB_PATH)
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

@app.route('/api/risk_check', methods=['POST', 'GET'])
def api_risk_check():
    """
    決策驗證 API - DVF Layer 2 核心
    輸入：變動參數
    輸出：風險分級 + 回滾建議
    """
    # GET 請求返回說明
    if request.method == 'GET':
        return jsonify({
            "endpoint": "/api/risk_check",
            "method": "POST",
            "description": "決策驗證 - 調整前風險評估",
            "input_example": {
                "change_type": "sampling_rate",
                "current_value": 5.0,
                "proposed_value": 3.0,
                "observation_days": 60
            },
            "output": ["risk_level", "risk_score", "recommendation", "rollback_threshold"]
        })
    
    # POST 請求處理
    data = request.get_json() or {}
    
    change_type = data.get('change_type', 'unknown')
    current = float(data.get('current_value', 5.0))
    proposed = float(data.get('proposed_value', 3.0))
    obs_days = int(data.get('observation_days', 60))
    
    # 簡易風險計算（DVF Layer 2 邏輯）
    change_pct = abs(proposed - current) / current * 100 if current > 0 else 0
    
    # 風險分級
    if change_pct < 10:
        risk_level = "LOW"
        risk_score = 15
        recommendation = "可執行，建議觀察 {obs_days} 天"
    elif change_pct < 30:
        risk_level = "MEDIUM"
        risk_score = 45
        recommendation = "謹慎執行，需設定回滾門檻"
    elif change_pct < 50:
        risk_level = "HIGH"
        risk_score = 70
        recommendation = "高風險，建議分階段調整"
    else:
        risk_level = "CRITICAL"
        risk_score = 90
        recommendation = "不建議執行，風險過高"
    
    # 回滾門檻建議
    rollback_threshold = round(current * 1.5 / 100, 3) if change_type == 'sampling_rate' else round(current * 0.02, 4)
    
    return jsonify({
        "change_type": change_type,
        "current_value": current,
        "proposed_value": proposed,
        "change_percentage": round(change_pct, 1),
        "risk_level": risk_level,
        "risk_score": risk_score,
        "recommendation": recommendation.format(obs_days=obs_days),
        "rollback_threshold": rollback_threshold,
        "observation_days": obs_days,
        "dvf_layer": "Layer 2 - Decision Validation"
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
    """主頁 - Dashboard"""
    return render_template('index.html')

@app.route('/query')
def query():
    """查詢頁面 - LLM 風格"""
    return render_template('query.html')

@app.route('/aoi')
def aoi():
    """AOI 門檻模擬頁面"""
    return render_template('aoi.html')

@app.route('/api/aoi_simulation')
def api_aoi_simulation():
    """
    AOI 門檻模擬數據
    基於 60天單線驗證設計
    """
    # DOE 模擬結果（基於簡報數據）
    scenarios = [
        {
            "name": "嚴格",
            "threshold": "240h",
            "false_reject_rate": 2.0,
            "escape_rate": 0.2,
            "annual_cost": 182000,
            "risk_level": "安全",
            "risk_color": "#28a745"
        },
        {
            "name": "標準",
            "threshold": "250h",
            "false_reject_rate": 1.0,
            "escape_rate": 0.4,
            "annual_cost": 168000,
            "risk_level": "安全",
            "risk_color": "#28a745"
        },
        {
            "name": "微調",
            "threshold": "260h",
            "false_reject_rate": 0.7,
            "escape_rate": 0.5,
            "annual_cost": 158000,
            "risk_level": "注意",
            "risk_color": "#ffc107"
        },
        {
            "name": "最佳點",
            "threshold": "265h",
            "false_reject_rate": 0.55,
            "escape_rate": 0.55,
            "annual_cost": 152000,
            "risk_level": "注意",
            "risk_color": "#ffc107",
            "recommended": True
        },
        {
            "name": "寬鬆",
            "threshold": "270h",
            "false_reject_rate": 0.4,
            "escape_rate": 0.8,
            "annual_cost": 151000,
            "risk_level": "中等",
            "risk_color": "#fd7e14"
        },
        {
            "name": "激進",
            "threshold": "280h",
            "false_reject_rate": 0.25,
            "escape_rate": 1.2,
            "annual_cost": 156000,
            "risk_level": "高",
            "risk_color": "#dc3545"
        }
    ]
    
    # 計算節省金額
    baseline_cost = scenarios[0]["annual_cost"]
    for s in scenarios:
        s["savings"] = baseline_cost - s["annual_cost"]
        s["savings_pct"] = round((baseline_cost - s["annual_cost"]) / baseline_cost * 100, 1)
    
    # 回滾條件
    rollback_rules = {
        "trigger": "7 天內有 2 天 escape ≥ 2",
        "action": "立即恢復原設定",
        "notify": ["製造部", "品保", "管理層"]
    }
    
    # 試驗參數
    trial_params = {
        "duration_days": 60,
        "daily_output": 5000,
        "scope": "單條產線",
        "control_group": "其他產線維持原設定"
    }
    
    return jsonify({
        "scenarios": scenarios,
        "rollback_rules": rollback_rules,
        "trial_params": trial_params,
        "recommended_scenario": "265h",
        "recommendation": "微調至 265h，年省約 ¥3萬，外流風險可控"
    })

# ============================================================
# 正崴深度分析 API（PYLIB: 複用現有模式）
# ============================================================

@app.route('/api/zw_stats')
def api_zw_stats():
    """正崴數據總覽"""
    conn = get_zw_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM production_log")
    batch_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT line_id) FROM production_log")
    line_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(output_qty), SUM(defect_qty) FROM production_log")
    row = cursor.fetchone()
    total_output = row[0] or 0
    total_defect = row[1] or 0
    yield_rate = (total_output - total_defect) / total_output * 100 if total_output > 0 else 0
    
    cursor.execute("SELECT COUNT(DISTINCT DATE(timestamp)) FROM production_log")
    day_count = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        "batch_count": f"{batch_count:,}",
        "line_count": line_count,
        "total_output": f"{total_output:,}",
        "yield_rate": round(yield_rate, 2),
        "day_count": day_count
    })

@app.route('/api/zw_yield_trend')
def api_zw_yield_trend():
    """正崴良率趨勢（日維度）"""
    conn = get_zw_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DATE(timestamp) as date,
               SUM(output_qty) as output,
               SUM(defect_qty) as defect,
               ROUND(100.0 * (SUM(output_qty) - SUM(defect_qty)) / SUM(output_qty), 2) as yield_rate
        FROM production_log
        GROUP BY DATE(timestamp)
        ORDER BY date
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify({
        "labels": [row['date'] for row in rows],
        "yield_data": [row['yield_rate'] for row in rows],
        "output_data": [row['output'] for row in rows]
    })

@app.route('/api/zw_line_performance')
def api_zw_line_performance():
    """正崴產線績效"""
    conn = get_zw_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT line_id,
               COUNT(*) as batch_count,
               SUM(output_qty) as total_output,
               ROUND(100.0 * (SUM(output_qty) - SUM(defect_qty)) / SUM(output_qty), 2) as yield_rate,
               ROUND(AVG(cycle_time), 3) as avg_cycle_time
        FROM production_log
        GROUP BY line_id
        ORDER BY line_id
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify({
        "labels": [row['line_id'] for row in rows],
        "yield_data": [row['yield_rate'] for row in rows],
        "output_data": [row['total_output'] for row in rows],
        "cycle_data": [row['avg_cycle_time'] for row in rows]
    })

@app.route('/api/zw_operator_ranking')
def api_zw_operator_ranking():
    """正崴操作員績效排名"""
    conn = get_zw_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT p.operator_id,
               COUNT(*) as batch_count,
               ROUND(100.0 * (SUM(p.output_qty) - SUM(p.defect_qty)) / SUM(p.output_qty), 2) as yield_rate,
               ROUND(AVG(p.cycle_time), 3) as avg_cycle_time
        FROM production_log p
        GROUP BY p.operator_id
        ORDER BY yield_rate DESC
        LIMIT 10
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify({
        "top": [
            {
                "operator_id": row['operator_id'],
                "batch_count": row['batch_count'],
                "yield_rate": row['yield_rate'],
                "cycle_time": row['avg_cycle_time']
            }
            for row in rows
        ]
    })

@app.route('/api/zw_supplier_quality')
def api_zw_supplier_quality():
    """正崴供應商品質"""
    conn = get_zw_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT p.supplier_id,
               s.supplier_name,
               COUNT(*) as batch_count,
               ROUND(100.0 * (SUM(p.output_qty) - SUM(p.defect_qty)) / SUM(p.output_qty), 2) as yield_rate
        FROM production_log p
        LEFT JOIN supplier_master s ON p.supplier_id = s.supplier_id
        GROUP BY p.supplier_id
        ORDER BY yield_rate DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify({
        "labels": [row['supplier_id'] for row in rows],
        "names": [row['supplier_name'] for row in rows],
        "yield_data": [row['yield_rate'] for row in rows],
        "batch_data": [row['batch_count'] for row in rows]
    })

@app.route('/api/zw_defect_heatmap')
def api_zw_defect_heatmap():
    """正崴不良率熱力圖（產線×班次）"""
    conn = get_zw_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT line_id, shift,
               ROUND(AVG(defect_rate) * 100, 2) as avg_defect_rate
        FROM production_log
        GROUP BY line_id, shift
        ORDER BY line_id, shift
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    # 整理為熱力圖格式
    lines = sorted(set(row['line_id'] for row in rows))
    shifts = sorted(set(row['shift'] for row in rows))
    
    data = []
    for row in rows:
        data.append({
            "line": row['line_id'],
            "shift": row['shift'],
            "defect_rate": row['avg_defect_rate']
        })
    
    return jsonify({
        "lines": lines,
        "shifts": shifts,
        "data": data
    })

@app.route('/analysis')
def analysis():
    """深度分析頁面"""
    return render_template('analysis.html')

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
