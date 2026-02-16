# 🚀 AAT PoC Dashboard 部署指南

## 一、上傳到 GitHub

### Step 1: 解壓縮
```bash
unzip aat_dashboard_deploy.zip
cd aat_dashboard_deploy
```

### Step 2: 初始化 Git
```bash
git init
git add .
git commit -m "Initial commit: AAT PoC Dashboard"
```

### Step 3: 連接 GitHub
```bash
# 在 GitHub 上創建新 repo: aat-poc-dashboard
git remote add origin https://github.com/YOUR_USERNAME/aat-poc-dashboard.git
git branch -M main
git push -u origin main
```

---

## 二、部署到 Render

### Step 1: 登入 Render
前往 https://render.com 並登入

### Step 2: 創建 Web Service
1. 點擊 **New** → **Web Service**
2. 連接你的 GitHub 帳號
3. 選擇剛上傳的 `aat-poc-dashboard` repo

### Step 3: 配置
| 設定項 | 值 |
|:-------|:---|
| Name | `aat-poc-dashboard` |
| Region | Singapore (or nearest) |
| Branch | `main` |
| Runtime | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app` |

### Step 4: 部署
點擊 **Create Web Service**，等待部署完成（約 2-3 分鐘）

### Step 5: 訪問
部署完成後，獲得 URL：
```
https://aat-poc-dashboard.onrender.com
```

---

## 三、本地測試

```bash
cd aat_dashboard_deploy
pip install -r requirements.txt
python app.py
# 訪問 http://localhost:5000
```

---

## 四、API 端點

| 端點 | 返回 |
|:-----|:-----|
| `/` | 儀表板頁面 |
| `/api/stats` | 總覽統計 JSON |
| `/api/daily_yield` | 良率趨勢 JSON |
| `/api/line_comparison` | 產線比較 JSON |
| `/api/defect_trend` | 不良率趨勢 JSON |
| `/api/capacity_distribution` | 產能分佈 JSON |
| `/api/scan_events` | 掃碼事件 JSON |
| `/api/qr_trace` | QR 追溯 JSON |
| `/api/lowest_yield` | 最低良率 JSON |
| `/health` | 健康檢查 |

---

## 五、注意事項

1. **Free Tier 限制**：Render 免費版會在閒置後休眠，首次訪問需等待 ~30 秒
2. **DB 只讀**：SQLite 在 Render 上為只讀，如需寫入請使用 PostgreSQL
3. **HTTPS**：Render 自動提供 HTTPS

---

**PYLIB v3.18** | @11星協作
