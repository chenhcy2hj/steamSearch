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

    @media (max-width: 880px) {
      .shell { grid-template-columns: 1fr; }
      aside { padding: 14px; }
      .nav { grid-template-columns: repeat(4, minmax(0, 1fr)); }
      .grid,
      .prices { grid-template-columns: 1fr; }
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
          <p class="sub">本页已接入 SQLite 本地搜索和利润计算，当前报价为演示数据。</p>
        </div>
        <div class="status">
          <span class="pill green">SQLite 已连接</span>
          <span class="pill blue">FTS 搜索</span>
          <span class="pill blue">Demo Quote</span>
        </div>
      </div>
      <div class="grid">
        <section class="panel">
          <div class="panel-header">
            <h2>搜索结果</h2>
            <span class="pill blue" id="resultCount">0 项</span>
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
    </main>
  </div>
  <script>
    const searchInput = document.getElementById("searchInput");
    const searchButton = document.getElementById("searchButton");
    const results = document.getElementById("results");
    const resultCount = document.getElementById("resultCount");
    const detail = document.getElementById("detail");
    const quoteState = document.getElementById("quoteState");

    searchButton.addEventListener("click", runSearch);
    searchInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") runSearch();
    });

    async function runSearch() {
      const query = encodeURIComponent(searchInput.value.trim());
      const response = await fetch(`/api/search?q=${query}`);
      const payload = await response.json();
      renderResults(payload.items || []);
      if (payload.items && payload.items.length > 0) {
        await loadQuote(payload.items[0].market_hash_name);
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
      quoteState.textContent = "加载中";
      const response = await fetch(`/api/quote?market_hash_name=${encodeURIComponent(marketHashName)}`);
      const payload = await response.json();
      if (!response.ok) {
        detail.innerHTML = `<div class="warning">${escapeHtml(payload.error || "加载失败")}</div>`;
        quoteState.textContent = "失败";
        return;
      }
      quoteState.textContent = "已计算";
      detail.innerHTML = `
        <div class="skin">
          <h3>${escapeHtml(payload.item.market_hash_name)}</h3>
          <p>${escapeHtml(payload.item.name_cn || "-")} · ${escapeHtml(payload.item.category || "未分类")} · ${escapeHtml(payload.item.rarity || "-")}</p>
          <div><span class="pill green">ROI ${escapeHtml(payload.profit.roi)}</span></div>
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
            <strong>${escapeHtml(payload.profit.profit)}</strong>
            <span>到手 ${escapeHtml(payload.profit.net_sell_price)} · 价差 ${escapeHtml(payload.profit.spread)}</span>
          </div>
        </div>
        <div class="warning">${escapeHtml(payload.warning)}</div>
      `;
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    runSearch();
  </script>
</body>
</html>"""

