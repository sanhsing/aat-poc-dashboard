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
        "yield_data": [round(row['avg_yield'], 2) for row in rows],
        "defect_data": [round(row['avg_defect'], 2) for row in rows],
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
            "data": [round(row['defect_rate'], 2) for row in rows],
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
        "yield_rate": [round(row['avg_yield'], 2) for row in rows]
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
                "yield": round(row['yield_rate'], 2),
                "defect": round(row['defect_rate'], 2)
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

# ============================================================
# 進階分析 API（XTF 拓展層）@織明 @理樞
# ============================================================

@app.route('/api/zw_maintenance_alert')
def api_zw_maintenance_alert():
    """300h 維護警示 - 運行時數臨界點分析"""
    conn = get_zw_db()
    cursor = conn.cursor()
    
    # 取得數據最大日期
    cursor.execute("SELECT MAX(timestamp) FROM production_log")
    max_date = cursor.fetchone()[0][:10]
    
    # 運行時數分段統計
    cursor.execute("""
        SELECT 
            CASE 
                WHEN runtime_hours < 100 THEN '0-100h'
                WHEN runtime_hours < 200 THEN '100-200h'
                WHEN runtime_hours < 300 THEN '200-300h'
                WHEN runtime_hours < 400 THEN '300-400h'
                ELSE '>400h'
            END as runtime_range,
            COUNT(*) as batch_count,
            ROUND(AVG(defect_rate) * 100, 2) as avg_defect_pct,
            ROUND(MIN(defect_rate) * 100, 2) as min_defect,
            ROUND(MAX(defect_rate) * 100, 2) as max_defect
        FROM production_log
        GROUP BY runtime_range
        ORDER BY 
            CASE runtime_range
                WHEN '0-100h' THEN 1
                WHEN '100-200h' THEN 2
                WHEN '200-300h' THEN 3
                WHEN '300-400h' THEN 4
                ELSE 5
            END
    """)
    
    runtime_data = []
    for row in cursor.fetchall():
        runtime_data.append({
            "range": row['runtime_range'],
            "batch_count": row['batch_count'],
            "defect_rate": row['avg_defect_pct'],
            "min": row['min_defect'],
            "max": row['max_defect']
        })
    
    # 當前需要維護的機台（>280h，最近7天）
    cursor.execute(f"""
        SELECT machine_id,
               MAX(runtime_hours) as current_hours,
               ROUND(AVG(defect_rate) * 100, 2) as recent_defect
        FROM production_log
        WHERE DATE(timestamp) >= DATE('{max_date}', '-7 days')
        GROUP BY machine_id
        HAVING MAX(runtime_hours) > 280
        ORDER BY current_hours DESC
    """)
    
    alerts = []
    for row in cursor.fetchall():
        alerts.append({
            "machine_id": row['machine_id'],
            "runtime_hours": round(row['current_hours'], 1),
            "recent_defect": row['recent_defect'],
            "urgency": "HIGH" if row['current_hours'] > 350 else "MEDIUM"
        })
    
    conn.close()
    
    return jsonify({
        "runtime_analysis": runtime_data,
        "maintenance_alerts": alerts,
        "threshold": 300,
        "insight": "300h 後不良率急升至 17.9%，建議在此前進行預防性維護"
    })

@app.route('/api/zw_temp_analysis')
def api_zw_temp_analysis():
    """溫度-不良率相關性分析"""
    conn = get_zw_db()
    cursor = conn.cursor()
    
    # 溫度分段
    cursor.execute("""
        SELECT 
            CASE 
                WHEN temperature < 62 THEN '<62°C'
                WHEN temperature < 64 THEN '62-64°C'
                WHEN temperature < 66 THEN '64-66°C'
                WHEN temperature < 68 THEN '66-68°C'
                ELSE '>68°C'
            END as temp_range,
            COUNT(*) as batch_count,
            ROUND(AVG(defect_rate) * 100, 2) as avg_defect_pct
        FROM production_log
        GROUP BY temp_range
        ORDER BY 
            CASE temp_range
                WHEN '<62°C' THEN 1
                WHEN '62-64°C' THEN 2
                WHEN '64-66°C' THEN 3
                WHEN '66-68°C' THEN 4
                ELSE 5
            END
    """)
    
    temp_data = [dict(row) for row in cursor.fetchall()]
    
    # 產線溫度分佈
    cursor.execute("""
        SELECT line_id,
               ROUND(AVG(temperature), 1) as avg_temp,
               ROUND(MIN(temperature), 1) as min_temp,
               ROUND(MAX(temperature), 1) as max_temp,
               ROUND(AVG(defect_rate) * 100, 2) as avg_defect
        FROM production_log
        GROUP BY line_id
        ORDER BY avg_temp
    """)
    
    line_temp = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        "temp_ranges": temp_data,
        "line_temperature": line_temp,
        "optimal_range": "62-66°C",
        "insight": "溫度>66°C 不良率急升至 15%+，建議強化冷卻系統"
    })

@app.route('/api/zw_cost_analysis')
def api_zw_cost_analysis():
    """成本損失計算"""
    conn = get_zw_db()
    cursor = conn.cursor()
    
    # 產品成本表
    cursor.execute("SELECT product_id, unit_price, unit_cost, scrap_cost FROM cost_table")
    cost_map = {row['product_id']: dict(row) for row in cursor.fetchall()}
    
    # 各產線損失
    cursor.execute("""
        SELECT line_id, product_id,
               SUM(output_qty) as total_output,
               SUM(defect_qty) as total_defect
        FROM production_log
        GROUP BY line_id, product_id
    """)
    
    line_loss = {}
    total_loss = 0
    
    for row in cursor.fetchall():
        product_id = row['product_id']
        defect_qty = row['total_defect']
        
        if product_id in cost_map:
            scrap_cost = cost_map[product_id]['scrap_cost']
            loss = defect_qty * scrap_cost
            total_loss += loss
            
            if row['line_id'] not in line_loss:
                line_loss[row['line_id']] = 0
            line_loss[row['line_id']] += loss
    
    # 供應商造成的損失
    cursor.execute("""
        SELECT p.supplier_id,
               SUM(p.defect_qty) as total_defect,
               p.product_id
        FROM production_log p
        GROUP BY p.supplier_id, p.product_id
    """)
    
    supplier_loss = {}
    for row in cursor.fetchall():
        sid = row['supplier_id']
        pid = row['product_id']
        if pid in cost_map:
            loss = row['total_defect'] * cost_map[pid]['scrap_cost']
            if sid not in supplier_loss:
                supplier_loss[sid] = 0
            supplier_loss[sid] += loss
    
    conn.close()
    
    # 年化（60天數據 → 365天）
    annual_factor = 365 / 60
    
    return jsonify({
        "total_loss_60d": round(total_loss, 2),
        "total_loss_annual": round(total_loss * annual_factor, 2),
        "line_loss": [
            {"line_id": k, "loss_60d": round(v, 2), "loss_annual": round(v * annual_factor, 2)}
            for k, v in sorted(line_loss.items(), key=lambda x: -x[1])
        ],
        "supplier_loss": [
            {"supplier_id": k, "loss_60d": round(v, 2), "loss_annual": round(v * annual_factor, 2)}
            for k, v in sorted(supplier_loss.items(), key=lambda x: -x[1])
        ],
        "insight": f"60天總損失 ¥{total_loss:,.0f}，年化約 ¥{total_loss * annual_factor:,.0f}"
    })

@app.route('/api/zw_supplier_scorecard')
def api_zw_supplier_scorecard():
    """供應商評分卡"""
    conn = get_zw_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            p.supplier_id,
            s.supplier_name,
            s.quality_z,
            s.cost_multiplier,
            COUNT(*) as batch_count,
            SUM(p.output_qty) as total_output,
            SUM(p.defect_qty) as total_defect,
            ROUND(100.0 * (SUM(p.output_qty) - SUM(p.defect_qty)) / SUM(p.output_qty), 2) as yield_rate,
            ROUND(AVG(p.cycle_time), 3) as avg_cycle
        FROM production_log p
        JOIN supplier_master s ON p.supplier_id = s.supplier_id
        GROUP BY p.supplier_id
    """)
    
    scorecards = []
    for row in cursor.fetchall():
        # 計算綜合評分（品質60% + 成本20% + 交期20%）
        quality_score = min(100, row['yield_rate'])
        cost_score = 100 - (row['cost_multiplier'] - 1) * 100  # 成本係數越低越好
        delivery_score = 100 - (row['avg_cycle'] - 0.9) * 200  # 週期越短越好
        
        total_score = quality_score * 0.6 + cost_score * 0.2 + delivery_score * 0.2
        
        grade = 'A' if total_score >= 95 else 'B' if total_score >= 90 else 'C' if total_score >= 85 else 'D'
        
        scorecards.append({
            "supplier_id": row['supplier_id'],
            "supplier_name": row['supplier_name'],
            "quality_z": row['quality_z'],
            "batch_count": row['batch_count'],
            "yield_rate": row['yield_rate'],
            "cost_multiplier": row['cost_multiplier'],
            "avg_cycle": row['avg_cycle'],
            "quality_score": round(quality_score, 1),
            "cost_score": round(cost_score, 1),
            "delivery_score": round(delivery_score, 1),
            "total_score": round(total_score, 1),
            "grade": grade
        })
    
    # 按總分排序
    scorecards.sort(key=lambda x: -x['total_score'])
    
    conn.close()
    
    return jsonify({
        "scorecards": scorecards,
        "weights": {"quality": 60, "cost": 20, "delivery": 20},
        "insight": f"最佳供應商: {scorecards[0]['supplier_id']}（{scorecards[0]['grade']}級）"
    })

@app.route('/api/zw_predictive_score')
def api_zw_predictive_score():
    """預測性維護分數"""
    conn = get_zw_db()
    cursor = conn.cursor()
    
    # 取得數據最大日期（因為是歷史模擬數據）
    cursor.execute("SELECT MAX(timestamp) FROM machine_status")
    max_date = cursor.fetchone()[0][:10]  # 取日期部分
    
    # 每台機台的健康指標（最近7天）
    cursor.execute(f"""
        SELECT 
            m.machine_id,
            MAX(m.runtime_hours) as runtime_hours,
            AVG(m.temperature) as avg_temp,
            AVG(m.vibration) as avg_vibration,
            MAX(m.maintenance_flag) as needs_maintenance
        FROM machine_status m
        WHERE DATE(m.timestamp) >= DATE('{max_date}', '-7 days')
        GROUP BY m.machine_id
    """)
    
    machine_health = []
    for row in cursor.fetchall():
        # 計算健康分數（100分制，越低越需要維護）
        runtime_score = max(0, 100 - (row['runtime_hours'] / 5))  # 500h = 0分
        temp_score = max(0, 100 - (row['avg_temp'] - 60) * 5)  # 80°C = 0分
        vibration_score = max(0, 100 - (row['avg_vibration'] - 1) * 50)  # 3.0 = 0分
        
        health_score = runtime_score * 0.5 + temp_score * 0.3 + vibration_score * 0.2
        
        risk_level = 'CRITICAL' if health_score < 30 else 'HIGH' if health_score < 50 else 'MEDIUM' if health_score < 70 else 'LOW'
        
        machine_health.append({
            "machine_id": row['machine_id'],
            "runtime_hours": round(row['runtime_hours'], 1),
            "avg_temp": round(row['avg_temp'], 1),
            "avg_vibration": round(row['avg_vibration'], 2),
            "health_score": round(health_score, 1),
            "risk_level": risk_level,
            "recommendation": "立即維護" if risk_level == 'CRITICAL' else "排程維護" if risk_level == 'HIGH' else "監控中"
        })
    
    # 按健康分數排序（最差的在前）
    machine_health.sort(key=lambda x: x['health_score'])
    
    conn.close()
    
    return jsonify({
        "machine_health": machine_health[:20],  # Top 20 需要關注的
        "critical_count": len([m for m in machine_health if m['risk_level'] == 'CRITICAL']),
        "high_count": len([m for m in machine_health if m['risk_level'] == 'HIGH']),
        "weights": {"runtime": 50, "temperature": 30, "vibration": 20},
        "insight": f"{len([m for m in machine_health if m['risk_level'] in ['CRITICAL', 'HIGH']])} 台機台需要優先關注"
    })

@app.route('/api/zw_operator_machine_matrix')
def api_zw_operator_machine_matrix():
    """操作員-機台最佳配對矩陣"""
    conn = get_zw_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            operator_id,
            machine_id,
            COUNT(*) as batch_count,
            ROUND(100.0 * (SUM(output_qty) - SUM(defect_qty)) / SUM(output_qty), 2) as yield_rate
        FROM production_log
        GROUP BY operator_id, machine_id
        HAVING COUNT(*) >= 10
        ORDER BY yield_rate DESC
    """)
    
    matrix_data = [dict(row) for row in cursor.fetchall()]
    
    # 找出最佳配對
    best_pairs = matrix_data[:10]
    
    # 找出最差配對（需要調整）
    worst_pairs = sorted(matrix_data, key=lambda x: x['yield_rate'])[:10]
    
    conn.close()
    
    return jsonify({
        "best_pairs": best_pairs,
        "worst_pairs": worst_pairs,
        "insight": f"最佳配對 {best_pairs[0]['operator_id']}-{best_pairs[0]['machine_id']} 良率 {best_pairs[0]['yield_rate']}%"
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
