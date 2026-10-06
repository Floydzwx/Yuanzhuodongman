/**
 * 圆桌动漫番剧归档 - Cloudflare Worker
 *
 * 职责：
 *  1) 定时抓取 B 站 UP 主「圆桌动漫」的粉丝量与各视频播放量
 *  2) 按 works_index.json 把视频播放量汇总成「作品播放量」
 *  3) 提供 /api/stats 接口给页面动态拉取，页面静态内容照旧可离线看
 *
 * 数据源：
 *   - 粉丝量：https://api.bilibili.com/x/relation/stat?vmid=654552
 *   - 播放量：https://api.bilibili.com/x/web-interface/view?bvid=xxx
 *     （取 data.stat.view；充电视频同样有播放量，无需特殊处理）
 *
 * 绑定：
 *   - KV 命名空间 STATS：存放最近一次抓取结果
 *   - Cron 触发器：每天一次
 */

//作品索引：由本地 export_works.py 生成后上传（作为静态资源）
// 也可以放在 KV 里，通过 PUT /api/works 更新

const KV_KEY_STATS = "stats:latest";
const KV_KEY_WORKS = "works:index";
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36";

/** 读取 works 索引：优先 KV，其次静态资源 */
async function loadWorks(env) {
  if (env.STATS) {
    const kv = await env.STATS.get(KV_KEY_WORKS, "json");
    if (kv && kv.works) return kv;
  }
  if (typeof WORKS !== "undefined") return WORKS;
  throw new Error("works index not found");
}

/** 带超时与重试的 fetch */
async function fetchJson(url, tries = 3, timeoutMs = 15000) {
  let lastErr = null;
  for (let i = 0; i < tries; i++) {
    const ac = new AbortController();
    const timer = setTimeout(() => ac.abort(), timeoutMs);
    try {
      const r = await fetch(url, {
        headers: { "User-Agent": UA, Referer: "https://www.bilibili.com/" },
        signal: ac.signal,
      });
      clearTimeout(timer);
      if (!r.ok) throw new Error("HTTP " + r.status);
      return await r.json();
    } catch (e) {
      clearTimeout(timer);
      lastErr = e;
      if (i < tries - 1) await sleep(600 * (i + 1));
    }
  }
  throw lastErr;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** 抓 UP 主粉丝量 */
async function fetchFollower(mid) {
  const d = await fetchJson(
    `https://api.bilibili.com/x/relation/stat?vmid=${mid}`);
  if (d.code !== 0) throw new Error("relation/stat code=" + d.code);
  return d.data.follower;
}

/** 抓单个视频播放量（返回 null 表示失败，调用方决定是否沿用旧值） */
async function fetchVideoView(bvid) {
  const d = await fetchJson(
    `https://api.bilibili.com/x/web-interface/view?bvid=${bvid}`);
  if (d.code !== 0) return null;
  const v = d.data?.stat?.view;
  return typeof v === "number" ? v : null;
}

/** 并发池：同时最多 CONCURRENCY 个请求，避免把 B 站接口打爆 */
async function mapPool(items, worker, CONCURRENCY = 6) {
  const out = new Array(items.length);
  let idx = 0;
  async function run() {
    for (;;) {
      const i = idx++;
      if (i >= items.length) return;
      try {
        out[i] = await worker(items[i], i);
      } catch (e) {
        out[i] = null;
      }
    }
  }
  await Promise.all(
    Array.from({ length: Math.min(CONCURRENCY, items.length) }, run));
  return out;
}

/**
 * 主抓取逻辑：粉丝量 + 所有视频播放量 + 按作品汇总
 */
async function refreshStats(env) {
  const works = await loadWorks(env);
  const mid = works.mid;
  const allBvids = [...new Set(works.works.flatMap((w) => w.bvids))];

  // 1) 粉丝量
  let follower = null;
  try {
    follower = await fetchFollower(mid);
  } catch (e) {
    console.error("抓粉丝量失败:", e.message);
  }

  // 2) 上一次结果（用于失败时沿用旧值）
  const prev = (await env.STATS?.get(KV_KEY_STATS, "json")) || {};
  const prevView = prev.views || {};
  const prevFollower = prev.follower ?? null;

  // 3) 逐个抓播放量
  console.log(`开始抓取 ${allBvids.length} 个视频的播放量…`);
  const views = await mapPool(allBvids, async (bvid) => {
    const v = await fetchVideoView(bvid);
    return v === null ? (prevView[bvid] ?? null) : v;
  });

  const viewMap = {};
  let ok = 0;
  allBvids.forEach((b, i) => {
    if (views[i] !== null && views[i] !== undefined) {
      viewMap[b] = views[i];
      ok++;
    }
  });
  console.log(`播放量抓取成功 ${ok}/${allBvids.length}`);

  // 4) 按作品汇总播放量
  const outWorks = works.works.map((w) => {
    const bvids = w.bvids.filter((b) => b in viewMap);
    const view = bvids.reduce((s, b) => s + viewMap[b], 0);
    return { ...w, bvids, view };
  });

  const totalView = Object.values(viewMap).reduce((s, v) => s + v, 0);

  const result = {
    updatedAt: new Date().toISOString(),
    up: works.up,
    mid,
    follower: follower ?? prevFollower,
    totalView,
    totalVideos: Object.keys(viewMap).length,
    views: viewMap,
    works: outWorks,
  };

  if (env.STATS) {
    await env.STATS.put(KV_KEY_STATS, JSON.stringify(result), {
      expirationTtl: 60 * 60 * 24 * 90, // 90 天后自动清理
    });
  }
  console.log(`汇总完成：${outWorks.length} 部作品，总播放 ${totalView}`);
  return result;
}

/** 返回给页面的精简数据（不含逐视频明细，减小体积） */
function toPublicJSON(result) {
  return JSON.stringify({
    updatedAt: result.updatedAt,
    up: result.up,
    follower: result.follower,
    totalView: result.totalView,
    totalVideos: result.totalVideos,
    works: result.works.map((w) => ({
      key: w.key,
      view: w.view,
      n: w.bvids.length,
    })),
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // CORS + 缓存头
    const cors = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, PUT, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors });
    }

    try {
      // 手动触发抓取：PUT /api/refresh
      if (url.pathname === "/api/refresh" && request.method === "PUT") {
        const r = await refreshStats(env);
        return new Response(toPublicJSON(r), {
          headers: { ...cors, "Content-Type": "application/json; charset=utf-8" },
        });
      }

      // 读取现有统计：GET /api/stats
      if (url.pathname === "/api/stats") {
        const cached = await env.STATS?.get(KV_KEY_STATS, "json");
        if (!cached) {
          return new Response(
            JSON.stringify({ error: "暂无数据，请先访问 PUT /api/refresh 触发首次抓取" }),
            { status: 404, headers: { ...cors, "Content-Type": "application/json" } });
        }
        return new Response(toPublicJSON(cached), {
          headers: {
            ...cors,
            "Content-Type": "application/json; charset=utf-8",
            // 客户端 5 分钟内可复用，避免频繁回源
            "Cache-Control": "public, max-age=300",
          },
        });
      }

      // 上传/更新作品索引：PUT /api/works
      if (url.pathname === "/api/works" && request.method === "PUT") {
        const data = await request.json();
        if (!data || !Array.isArray(data.works)) {
          return new Response(JSON.stringify({ error: "缺少 works 数组" }),
            { status: 400, headers: cors });
        }
        await env.STATS.put(KV_KEY_WORKS, JSON.stringify(data));
        return new Response(JSON.stringify({ ok: true, works: data.works.length }),
          { headers: { ...cors, "Content-Type": "application/json" } });
      }

      return new Response("圆桌动漫归档 Worker\n\n" +
        "GET  /api/stats    读取统计\n" +
        "PUT  /api/refresh  立即抓取一次\n" +
        "PUT  /api/works    上传作品索引\n", {
        headers: { ...cors, "Content-Type": "text/plain; charset=utf-8" },
      });
    } catch (e) {
      return new Response(JSON.stringify({ error: String(e && e.message || e) }), {
        status: 500, headers: { ...cors, "Content-Type": "application/json" },
      });
    }
  },

  // 每天 03:17（UTC+8 = 19:17）自动抓取一次
  async scheduled(event, env, ctx) {
    ctx.waitUntil(refreshStats(env).catch((e) =>
      console.error("定时抓取失败:", e.message)));
  },
};
