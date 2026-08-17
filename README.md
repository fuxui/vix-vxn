# VIX · VXN 恐慌指数看板

每天自动更新 Cboe 官方发布的 **VIX**（标普 500 恐慌指数）和 **VXN**（纳斯达克 100 恐慌指数），一个网页随时看。

## 本地预览

```bash
python -m http.server 8000
# 浏览器打开 http://localhost:8000
```

（直接双击 index.html 会因浏览器本地文件限制读不到 JSON，用上面命令起个本地服务即可。）

## 部署到 GitHub Pages（一次性）

1. 在 github.com 新建仓库，名字随意（如 `vix-vxn`），**不要**勾选 "Add a README"
2. 把本目录推上去：

   ```bash
   git init
   git add .
   git commit -m "init"
   git branch -M main
   git remote add origin https://github.com/<你的用户名>/vix-vxn.git
   git push -u origin main
   ```

3. 仓库 **Settings → Pages** → Source 选 **Deploy from a branch** → 分支选 `main`、目录 `/ (root)` → **Save**
4. 等一两分钟，访问 `https://<你的用户名>.github.io/vix-vxn/`

## 自动更新

`.github/workflows/update.yml` 每天北京时间 06:00 自动抓取 Cboe 数据并提交，Pages 自动重新发布。
也可在仓库 **Actions** 页手动 **Run workflow** 立即刷新。

> 注：GitHub 对连续 60 天无活动的仓库会暂停定时任务。看板一直在访问就是有活动；若很久没更新，去 Actions 页手动跑一次即可。

## 数据来源

- VIX / VXN：Cboe 官方 CSV（`https://cdn.cboe.com/api/global/us_indices/daily_prices/{VIX,VXN}_History.csv`）
- SPX / NDX：FRED（`SP500` / `NASDAQ100`，美国站，GitHub Actions 上稳定）；失败时兜底东方财富（`100.SPX` / `100.NDX100`）

## 分析板块

页面包含：恐慌水平分位、均值回归偏离、价差/比值、短期动量、极值区间，以及情绪总览、大盘联动（负相关与相关系数）、成因解读。逻辑见 `index.html` 内 `renderAnalysis()` 及各 `renderXxx()` 函数。

## 调整恐慌阈值

编辑 `index.html` 顶部 `CONFIG.thresholds`：

- `calm`（平静 / 绿色）
- `elevated`（偏高 / 黄色）
- `fear`（恐慌 / 橙色，超过即红色“极端”）

默认：VIX 为 20 / 30 / 40；VXN 为 22 / 32 / 42（纳斯达克波动率结构性更高）。
