#!/bin/bash
# ============================================================
# AAT PoC Dashboard - GitHub 上傳腳本
# ============================================================
# 使用方式：
# 1. 下載 aat_dashboard_deploy.zip
# 2. 解壓縮
# 3. 修改此腳本中的 YOUR_USERNAME
# 4. 執行 bash github_upload.sh
# ============================================================

# ⚠️ 請先修改這裡 ⚠️
GITHUB_USERNAME="YOUR_USERNAME"
REPO_NAME="aat-poc-dashboard"

# ============================================================
# Step 0: 檢查
# ============================================================
echo "================================================"
echo "  AAT PoC Dashboard - GitHub 上傳"
echo "================================================"

if [ "$GITHUB_USERNAME" = "YOUR_USERNAME" ]; then
    echo "❌ 錯誤：請先修改 GITHUB_USERNAME"
    echo "   打開此腳本，將 YOUR_USERNAME 改為你的 GitHub 帳號"
    exit 1
fi

# ============================================================
# Step 1: Git 初始化
# ============================================================
echo ""
echo "📦 Step 1: Git 初始化..."

git init
git add .
git commit -m "Initial commit: AAT PoC Dashboard

- Flask Web App with Chart.js
- SQLite DB driven charts
- 8 API endpoints
- Render ready

@11星協作 | PYLIB v3.18"

echo "✅ Git 初始化完成"

# ============================================================
# Step 2: 連接 GitHub
# ============================================================
echo ""
echo "🔗 Step 2: 連接 GitHub..."
echo ""
echo "⚠️  請先在 GitHub 上手動建立 repo："
echo "    https://github.com/new"
echo "    Repository name: $REPO_NAME"
echo "    選擇 Public 或 Private"
echo "    ❌ 不要勾選 Add README"
echo "    ❌ 不要勾選 Add .gitignore"
echo ""
read -p "已建立 repo？按 Enter 繼續..."

git remote add origin "https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"
git branch -M main

echo "✅ 已連接 GitHub"

# ============================================================
# Step 3: 推送
# ============================================================
echo ""
echo "🚀 Step 3: 推送到 GitHub..."

git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "================================================"
    echo "  ✅ 上傳成功！"
    echo "================================================"
    echo ""
    echo "📍 GitHub Repo:"
    echo "   https://github.com/${GITHUB_USERNAME}/${REPO_NAME}"
    echo ""
    echo "🚀 下一步：部署到 Render"
    echo "   1. 前往 https://render.com"
    echo "   2. New → Web Service"
    echo "   3. 連接此 GitHub repo"
    echo "   4. Build: pip install -r requirements.txt"
    echo "   5. Start: gunicorn app:app"
    echo ""
else
    echo ""
    echo "❌ 推送失敗，請檢查："
    echo "   1. GitHub 帳號是否正確"
    echo "   2. Repo 是否已建立"
    echo "   3. 是否有權限"
fi
