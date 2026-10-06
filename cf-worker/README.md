# Cloudflare 部署指南

圆桌动漫番剧归档的自动抓取方案：每天定时抓 B 站粉丝量与各视频播放量，
按作品汇总后由页面动态拉取。

## 文件说明

```
export_works.py        本地运行：导出 works_index.json（作品 → 视频 ID + 播放量）
works_index.json       作品索引，上传给 Worker
cf-worker/
  src/index.js         Worker 主逻辑（抓取 + 汇总 + API）
  wrangler.jsonc       配置（KV 绑定 + 定时触发器）
  package.json         依赖（wrangler）
```

## 一、准备（一次性）

### 1. 注册 Cloudflare 并安装 wrangler

```bash
cd cf-worker
npm install
npx wrangler login
```

### 2. 创建 KV 命名空间

```bash
npx wrangler kv namespace create STATS
```

命令会返回一段配置，把输出的 `id` 填进 `wrangler.jsonc`：

```jsonc
"kv_namespaces": [
  { "binding": "STATS", "id": "把这里换成刚拿到的 id" }
]
```

### 3. 部署

```bash
npx wrangler deploy
```

输出形如 `https://yuanshu-anime-archive.xxx.workers.dev` —— 这就是你的 Worker 地址。

## 二、首次抓取

部署后手动触发一次（Worker 里的定时器要等到下一个 cron 才跑）：

```bash
curl -X PUT https://你的worker地址/api/refresh
```

抓 740 个视频的播放量，按 6 并发算大约需要 2~4 分钟。
返回的 JSON 就是汇总结果。之后每天 UTC 11:17（北京时间 19:17）自动抓一次。

### 上传作品索引（可选）

如果作品有增减，重新跑 `python export_works.py` 后上传：

```bash
curl -X PUT https://你的worker地址/api/works \
  -H "Content-Type: application/json" \
  --data-binary @../works_index.json
```

## 三、让页面用上实时数据

拿到 Worker 地址后，在项目根目录执行：

```bash
set WORKER_API=https://你的worker地址
python build_page.py
```

或者直接改 `build_page.py` 里的默认值：

```python
WORKER_API = os.environ.get("WORKER_API", "https://你的worker地址")
```

页面会尝试从 `WORKER_API/api/stats` 拉取数据并更新：
- 页头的粉丝数、总播放量
- 每部作品的「总播放」

**拉不到也不影响使用** —— 页面会继续显示构建时的静态数据，
状态行会标注「静态数据（未配置或接口不可用）」。

## 四、接口一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/stats` | 读取最近一次抓取结果（客户端缓存 5 分钟） |
| PUT | `/api/refresh` | 立即抓取一次并更新 |
| PUT | `/api/works` | 上传作品索引 |

## 备注

- **B 站接口不需要登录**，用的是公开的 `x/web-interface/view` 和
  `x/relation/stat`，所以无需配置 cookie。
- 播放量抓取失败时会**沿用上一次的值**（存在 KV 里，保留 90 天），
  不会因为单次失败导致汇总值变 0。
- 免费版 Cron 是 UTC 时间，`17 11 * * *` 对应北京时间每天 19:17。
- KV 属于付费功能外的免费额度内（每天 1000 次写请求，抓取每天 1 次，
  远低于限制）。
