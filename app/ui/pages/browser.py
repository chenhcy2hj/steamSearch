from __future__ import annotations


def render_browser_page() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SteamSearch Browser</title>
  <style>
    :root {
      --bg: #f4f6f8;
      --surface: #ffffff;
      --line: #d8e0e7;
      --text: #17212b;
      --muted: #64717f;
      --green: #1f9d62;
      --red: #c64f4b;
      --blue: #2563a9;
      --blue-soft: #e5eff9;
      --green-soft: #e4f5ec;
      --shadow: 0 10px 28px rgba(23, 34, 45, 0.08);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      letter-spacing: 0;
    }

    .shell {
      min-height: 100vh;
      display: grid;
      grid-template-columns: 260px minmax(0, 1fr);
    }

    aside {
      background: #111820;
      color: #f7fafc;
      padding: 22px 16px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      padding-bottom: 18px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.12);
    }

    .mark {
      width: 38px;
      height: 38px;
      border-radius: 8px;
      display: grid;
      place-items: center;
      background: linear-gradient(135deg, #31a66a, #2b67ad);
      font-weight: 800;
    }

    .brand strong { display: block; }
    .brand span { color: #9fb0c0; font-size: 12px; }

    .nav {
      display: grid;
      gap: 8px;
      margin-top: 20px;
    }

    .nav div {
      min-height: 42px;
      display: flex;
      align-items: center;
      padding: 0 12px;
      border-radius: 8px;
      color: #c4cfda;
    }

    .nav .active {
      color: #fff;
      background: rgba(255, 255, 255, 0.11);
    }

    main {
      min-width: 0;
      padding: 26px;
    }

    .top {
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      gap: 18px;
      margin-bottom: 20px;
    }

    h1 {
      margin: 0 0 6px;
      font-size: 24px;
      line-height: 1.2;
    }

    .sub {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
    }

    .status {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    .pill {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 24px;
      padding: 0 9px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 650;
      white-space: nowrap;
    }

    .pill.blue { color: var(--blue); background: var(--blue-soft); }
    .pill.green { color: var(--green); background: var(--green-soft); }

    .grid {
      display: grid;
      grid-template-columns: minmax(320px, 0.9fr) minmax(0, 1.3fr);
      gap: 18px;
      align-items: start;
    }

    .panel {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }

    .panel-header {
      min-height: 56px;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }

    .panel-header h2 {
      margin: 0;
      font-size: 15px;
    }

    .search-row {
      padding: 14px 16px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 96px;
      gap: 10px;
      border-bottom: 1px solid var(--line);
    }

    input,
    button {
      font: inherit;
    }

    input {
      height: 40px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 0 12px;
      outline: none;
    }

    button {
      height: 40px;
      border: 0;
      border-radius: 8px;
      background: #111820;
      color: #fff;
      font-weight: 700;
      cursor: pointer;
    }

    .small-button {
      width: auto;
      height: 30px;
      padding: 0 10px;
      margin-right: 8px;
      font-size: 12px;
      background: #2563a9;
    }

    .results {
      display: grid;
      max-height: 560px;
      overflow: auto;
    }

    .result {
      padding: 13px 16px;
      display: grid;
      gap: 4px;
      border-bottom: 1px solid var(--line);
      cursor: pointer;
    }

    .result:hover,
    .result.active {
      background: #f7fafc;
    }

    .result strong {
      font-size: 13px;
      line-height: 1.3;
    }

    .result span {
      color: var(--muted);
      font-size: 12px;
    }

    .detail {
      padding: 18px;
      display: grid;
      gap: 16px;
    }

    .skin {
      min-height: 126px;
      padding: 18px;
      border-radius: 8px;
      background: linear-gradient(135deg, #eef4f3, #f7f3ec);
      border: 1px solid var(--line);
      display: grid;
      gap: 12px;
      align-content: center;
    }

    .skin h3 {
      margin: 0;
      font-size: 22px;
      line-height: 1.25;
    }

    .skin p {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
    }

    .prices {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }

    .price {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      min-height: 96px;
      background: #fbfcfd;
    }

    .price span {
      display: block;
      color: var(--muted);
      font-size: 12px;
    }

    .price strong {
      display: block;
      margin-top: 8px;
      font-size: 22px;
    }

    .profit strong { color: var(--green); }
    .warning {
      min-height: 42px;
      padding: 12px;
      border-radius: 8px;
      background: #f6ecd8;
      color: #895f1a;
      font-size: 13px;
    }

    .platforms {
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }

    .platform-row {
      display: grid;
      grid-template-columns: minmax(110px, 1fr) 100px 80px 100px 80px 150px;
      gap: 8px;
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      font-size: 13px;
      align-items: center;
    }

    .platform-row:last-child { border-bottom: 0; }

    .platform-row.header {
      color: var(--muted);
      background: #f7fafc;
      font-size: 12px;
      font-weight: 700;
    }

    .stack {
      display: grid;
      gap: 18px;
      margin-top: 18px;
    }

    .watchlist {
      display: grid;
    }

    .radar-controls {
      padding: 14px 16px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 120px 120px 90px;
      gap: 10px;
      border-bottom: 1px solid var(--line);
    }

    .watch-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto auto;
      gap: 10px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--line);
      align-items: center;
    }

    .watch-row:last-child { border-bottom: 0; }

    .radar-row {
      display: grid;
      grid-template-columns: minmax(0, 1.5fr) 90px 90px 90px 80px;
      gap: 10px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--line);
      align-items: center;
      font-size: 13px;
    }

    .radar-row.header {
      color: var(--muted);
      background: #f7fafc;
      font-size: 12px;
      font-weight: 700;
    }

    .radar-row:last-child { border-bottom: 0; }

    .watch-row strong {
      display: block;
      font-size: 13px;
      line-height: 1.3;
    }

    .watch-row span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-top: 3px;
    }

    .icon-button {
      width: 34px;
      height: 30px;
      padding: 0;
      font-size: 12px;
      background: #eef2f5;
      color: var(--text);
      border: 1px solid var(--line);
    }

    @media (max-width: 880px) {
      .shell { grid-template-columns: 1fr; }
      aside { padding: 14px; }
      .nav { grid-template-columns: repeat(4, minmax(0, 1fr)); }
      .grid,
      .prices { grid-template-columns: 1fr; }
      .radar-controls,
      .radar-row { grid-template-columns: 1fr; }
      .watch-row { grid-template-columns: 1fr auto; }
      .platform-row { grid-template-columns: 1fr 1fr; }
      .top { align-items: stretch; flex-direction: column; }
      .status { justify-content: flex-start; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <aside>
      <div class="brand">
        <div class="mark">SS</div>
        <div>
          <strong>SteamSearch</strong>
          <span>Browser MVP</span>
        </div>
      </div>
      <div class="nav">
        <div class="active">查询</div>
        <div>扫描</div>
        <div>监控</div>
        <div>设置</div>
      </div>
    </aside>
    <main>
      <div class="top">
        <div>
          <h1>饰品查询</h1>
          <p class="sub">本页已接入 SQLite 本地搜索、SteamDT 实时价格和利润计算。</p>
        </div>
        <div class="status">
          <span class="pill green">SQLite 已连接</span>
          <span class="pill blue" id="steamdtState">SteamDT 检查中</span>
          <span class="pill blue" id="buffState">BUFF 检查中</span>
          <span class="pill blue">FTS 搜索</span>
        </div>
      </div>
      <div class="grid">
        <section class="panel">
          <div class="panel-header">
            <h2>搜索结果</h2>
            <span>
              <button class="small-button" id="syncButton">同步 SteamDT 基础库</button>
              <span class="pill blue" id="resultCount">0 项</span>
            </span>
          </div>
          <div class="search-row">
            <input id="searchInput" value="AK" aria-label="搜索饰品">
            <button id="searchButton">搜索</button>
          </div>
          <div class="results" id="results"></div>
        </section>
        <section class="panel">
          <div class="panel-header">
            <h2>价格详情</h2>
            <span class="pill green" id="quoteState">等待选择</span>
          </div>
          <div class="detail" id="detail">
            <div class="skin">
              <h3>选择一个饰品</h3>
              <p>搜索结果会显示在左侧，点击后展示买入价、卖出估算和 ROI。</p>
            </div>
          </div>
        </section>
      </div>
      <div class="stack">
        <section class="panel">
          <div class="panel-header">
            <h2>Radar 扫描</h2>
            <span class="pill blue" id="radarCount">0 项</span>
          </div>
          <div class="radar-controls">
            <input id="radarQuery" value="" placeholder="关键词，可留空">
            <input id="radarProfit" value="0" placeholder="最低利润">
            <input id="radarRoi" value="0" placeholder="最低 ROI，例如 0.05">
            <button id="radarButton">扫描</button>
          </div>
          <div id="radarResults"></div>
        </section>
        <section class="panel">
          <div class="panel-header">
            <h2>监控列表</h2>
            <span class="pill blue" id="watchCount">0 项</span>
          </div>
          <div class="watchlist" id="watchlist"></div>
        </section>
      </div>
    </main>
  </div>
  <script>
    const searchInput = document.getElementById("searchInput");
    const searchButton = document.getElementById("searchButton");
    const syncButton = document.getElementById("syncButton");
    const results = document.getElementById("results");
    const resultCount = document.getElementById("resultCount");
    const detail = document.getElementById("detail");
    const quoteState = document.getElementById("quoteState");
    const steamdtState = document.getElementById("steamdtState");
    const buffState = document.getElementById("buffState");
    const watchlist = document.getElementById("watchlist");
    const watchCount = document.getElementById("watchCount");
    const radarButton = document.getElementById("radarButton");
    const radarQuery = document.getElementById("radarQuery");
    const radarProfit = document.getElementById("radarProfit");
    const radarRoi = document.getElementById("radarRoi");
    const radarResults = document.getElementById("radarResults");
    const radarCount = document.getElementById("radarCount");
    let activeMarketHashName = "";

    searchButton.addEventListener("click", runSearch);
    syncButton.addEventListener("click", syncSteamDTBase);
    radarButton.addEventListener("click", runRadar);
    searchInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") runSearch();
    });

    async function loadSourceStatus() {
      const response = await fetch("/api/source-status");
      const payload = await response.json();
      steamdtState.textContent = payload.steamdt.enabled ? "SteamDT 已启用" : "SteamDT 未配置";
      buffState.textContent = payload.buff.enabled ? "BUFF 已启用" : "BUFF 未启用";
    }

    async function syncSteamDTBase() {
      syncButton.disabled = true;
      syncButton.textContent = "同步中";
      const response = await fetch("/api/sync/steamdt/base");
      const payload = await response.json();
      if (!response.ok) {
        alert(payload.detail || payload.error || "同步失败");
      } else {
        alert(`同步完成：${payload.synced} 条，当前共 ${payload.total} 条`);
        await runSearch();
      }
      syncButton.textContent = "同步 SteamDT 基础库";
      syncButton.disabled = false;
    }

    async function runSearch() {
      const query = encodeURIComponent(searchInput.value.trim());
      const response = await fetch(`/api/search?q=${query}`);
      const payload = await response.json();
      renderResults(payload.items || []);
      if (payload.items && payload.items.length > 0) {
        await loadQuote(payload.items[0].market_hash_name);
      } else {
        activeMarketHashName = "";
      }
    }

    function renderResults(items) {
      resultCount.textContent = `${items.length} 项`;
      results.innerHTML = "";
      items.forEach((item, index) => {
        const row = document.createElement("div");
        row.className = `result${index === 0 ? " active" : ""}`;
        row.innerHTML = `
          <strong>${escapeHtml(item.market_hash_name)}</strong>
          <span>${escapeHtml(item.name_cn || "-")} · ${escapeHtml(item.category || "未分类")}</span>
        `;
        row.addEventListener("click", async () => {
          document.querySelectorAll(".result").forEach((node) => node.classList.remove("active"));
          row.classList.add("active");
          await loadQuote(item.market_hash_name);
        });
        results.appendChild(row);
      });
    }

    async function loadQuote(marketHashName) {
      activeMarketHashName = marketHashName;
      quoteState.textContent = "加载中";
      const response = await fetch(`/api/quote?market_hash_name=${encodeURIComponent(marketHashName)}`);
      const payload = await response.json();
      if (!response.ok) {
        if (payload.fallback) {
          renderQuote(payload.fallback, `${payload.error}: ${payload.detail || ""}`);
        } else {
          detail.innerHTML = `<div class="warning">${escapeHtml(payload.error || "加载失败")}</div>`;
        }
        quoteState.textContent = "失败";
        return;
      }
      quoteState.textContent = "已计算";
      renderQuote(payload);
    }

    function renderQuote(payload, errorMessage = "") {
      const profit = payload.profit || { roi: "-", profit: "-", net_sell_price: "-", spread: "-" };
      const platforms = payload.platform_prices || [];
      const capturedAt = formatTime(payload.captured_at);
      detail.innerHTML = `
        <div class="skin">
          <h3>${escapeHtml(payload.item.market_hash_name)}</h3>
          <p>${escapeHtml(payload.item.name_cn || "-")} · ${escapeHtml(payload.item.category || "未分类")} · ${escapeHtml(payload.item.rarity || "-")}</p>
          <div>
            <span class="pill green">ROI ${escapeHtml(profit.roi)}</span>
            <span class="pill blue">获取 ${escapeHtml(capturedAt)}</span>
            <button class="small-button" onclick="addActiveToWatchlist()">加入监控</button>
          </div>
        </div>
        <div class="prices">
          <div class="price">
            <span>${escapeHtml(payload.sources.buy.name)}</span>
            <strong>${escapeHtml(payload.sources.buy.price)}</strong>
            <span>${escapeHtml(payload.sources.buy.freshness)}</span>
          </div>
          <div class="price">
            <span>${escapeHtml(payload.sources.sell.name)}</span>
            <strong>${escapeHtml(payload.sources.sell.price)}</strong>
            <span>${escapeHtml(payload.sources.sell.freshness)}</span>
          </div>
          <div class="price profit">
            <span>预计利润</span>
            <strong>${escapeHtml(profit.profit)}</strong>
            <span>到手 ${escapeHtml(profit.net_sell_price)} · 价差 ${escapeHtml(profit.spread)}</span>
          </div>
        </div>
        ${renderPlatforms(platforms)}
        <div class="warning">${escapeHtml(errorMessage || payload.warning)}</div>
      `;
    }

    async function addActiveToWatchlist() {
      if (!activeMarketHashName) return;
      const response = await fetch("/api/watchlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ market_hash_name: activeMarketHashName })
      });
      if (!response.ok) {
        const payload = await response.json();
        alert(payload.error || "加入监控失败");
        return;
      }
      await loadWatchlist();
    }

    async function loadWatchlist() {
      const response = await fetch("/api/watchlist");
      const payload = await response.json();
      renderWatchlist(payload.items || []);
    }

    function renderWatchlist(items) {
      watchCount.textContent = `${items.length} 项`;
      if (!items.length) {
        watchlist.innerHTML = `<div class="watch-row"><div><strong>暂无监控项</strong><span>从价格详情中加入一个饰品</span></div></div>`;
        return;
      }
      watchlist.innerHTML = items.map((item) => `
        <div class="watch-row">
          <div>
            <strong>${escapeHtml(item.market_hash_name)}</strong>
            <span>${escapeHtml(item.name_cn || "-")} · ${item.enabled ? "已启用" : "已停用"}</span>
          </div>
          <button class="icon-button" title="启停" onclick="toggleWatch(${item.id}, ${item.enabled ? "false" : "true"})">${item.enabled ? "停" : "启"}</button>
          <button class="icon-button" title="删除" onclick="deleteWatch(${item.id})">删</button>
        </div>
      `).join("");
    }

    async function toggleWatch(id, enabled) {
      await fetch(`/api/watchlist/${id}/toggle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled })
      });
      await loadWatchlist();
    }

    async function deleteWatch(id) {
      await fetch(`/api/watchlist/${id}`, { method: "DELETE" });
      await loadWatchlist();
    }

    async function runRadar() {
      radarButton.disabled = true;
      radarButton.textContent = "扫描中";
      const params = new URLSearchParams({
        q: radarQuery.value.trim(),
        min_profit: radarProfit.value.trim() || "0",
        min_roi: radarRoi.value.trim() || "0",
        limit: "20"
      });
      const response = await fetch(`/api/radar?${params.toString()}`);
      const payload = await response.json();
      renderRadar(payload.items || [], payload.warning || "");
      radarButton.textContent = "扫描";
      radarButton.disabled = false;
    }

    function renderRadar(items, warning) {
      radarCount.textContent = `${items.length} 项`;
      if (!items.length) {
        radarResults.innerHTML = `<div class="watch-row"><div><strong>暂无候选</strong><span>${escapeHtml(warning || "降低筛选条件后再试")}</span></div></div>`;
        return;
      }
      radarResults.innerHTML = `
        <div class="radar-row header">
          <span>饰品</span><span>买入</span><span>卖出</span><span>利润</span><span>ROI</span>
        </div>
        ${items.map((item) => `
          <div class="radar-row">
            <span>${escapeHtml(item.market_hash_name)}</span>
            <span>${escapeHtml(item.buy_price)}</span>
            <span>${escapeHtml(item.sell_price)}</span>
            <span>${escapeHtml(item.profit)}</span>
            <span>${escapeHtml(item.roi)}</span>
          </div>
        `).join("")}
        <div class="warning">${escapeHtml(warning)}</div>
      `;
    }

    function renderPlatforms(platforms) {
      if (!platforms.length) return "";
      return `
        <div class="platforms">
          <div class="platform-row header">
            <span>平台</span><span>挂单价</span><span>在售</span><span>求购价</span><span>求购</span><span>获取时间</span>
          </div>
          ${platforms.map((item) => `
            <div class="platform-row">
              <span>${escapeHtml(item.platform)}</span>
              <span>${escapeHtml(item.sell_price)}</span>
              <span>${escapeHtml(item.sell_count)}</span>
              <span>${escapeHtml(item.bidding_price)}</span>
              <span>${escapeHtml(item.bidding_count)}</span>
              <span>${escapeHtml(formatTime(item.captured_at))}</span>
            </div>
          `).join("")}
        </div>
      `;
    }

    function formatTime(value) {
      if (!value) return "未记录";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return value;
      return date.toLocaleString("zh-CN", { hour12: false });
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    loadSourceStatus();
    runSearch();
    loadWatchlist();
    runRadar();
  </script>
</body>
</html>"""
