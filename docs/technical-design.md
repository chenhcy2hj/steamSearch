# SteamSearch 技术方案

## 1. 方案目标

本文档用于指导 SteamSearch 第一阶段开发。

第一阶段目标是实现一个可运行的桌面查询工具：

- 使用 SteamDT API 同步饰品基础数据。
- 使用本地 SQLite 实现快速搜索和缓存。
- 查询单个饰品价格并计算利润。
- 可选启用 BUFF 单品价格增强。
- 支持监控列表和 Radar 初版扫描。

技术方案坚持三个原则：

- SteamDT 优先，BUFF 增强。
- 缓存优先，请求克制。
- 先查询决策，后自动化扩展。
- 国内网络优先，Steam 官方源可选降级。

## 2. 技术栈

### 运行环境

- Python：3.11+
- 包管理：uv 或 pip-tools
- 操作系统：macOS、Windows 优先

### 应用框架

- UI：Flet
- HTTP：httpx
- 数据库：SQLite
- 数据校验：pydantic
- 配置：pydantic-settings
- 调度：APScheduler
- 日志：loguru
- 测试：pytest
- 打包：PyInstaller

### 首版依赖建议

```toml
[project]
dependencies = [
  "flet",
  "httpx",
  "pydantic",
  "pydantic-settings",
  "apscheduler",
  "loguru",
  "platformdirs",
]

[dependency-groups]
dev = [
  "pytest",
  "pytest-asyncio",
  "ruff",
]
```

BUFF 解析如果后续需要 HTML 解析，再加入：

```toml
"selectolax"
```

## 3. 项目结构

```text
steamSearch/
  app/
    __init__.py
    main.py
    bootstrap.py

    core/
      config.py
      constants.py
      errors.py
      logger.py
      rate_limiter.py
      scheduler.py
      security.py
      time.py

    ui/
      app.py
      routes.py
      state.py
      components/
        price_badge.py
        source_status.py
        search_box.py
      pages/
        dashboard.py
        browser.py
        radar.py
        watchlist.py
        settings.py

    steamdt/
      client.py
      dto.py
      service.py

    buff/
      client.py
      dto.py
      service.py
      parser.py

    market/
      calculator.py
      scanner.py
      filters.py
      scoring.py
      models.py

    storage/
      db.py
      migrations.py
      repositories/
        items.py
        prices.py
        watchlist.py
        settings.py
        source_health.py

    plugins/
      base.py
      notify/
      platforms/

  config/
    config.example.toml

  data/
    .gitkeep

  docs/
    project-start-plan.md
    technical-design.md

  logs/
    .gitkeep

  tests/
    test_calculator.py
    test_rate_limiter.py
    test_repositories.py
```

## 4. 分层设计

### UI 层

职责：

- 展示数据。
- 收集用户输入。
- 调用应用服务。
- 不直接访问外部 API。
- 不直接写 SQL。

页面：

- Dashboard：总览和数据源状态。
- Browser：单品搜索与查询。
- Radar：机会扫描。
- Watchlist：监控列表。
- Settings：配置管理。

### Service 层

职责：

- 编排业务流程。
- 调用 API Client。
- 调用 Repository。
- 执行缓存判断。
- 返回 UI 可直接使用的 ViewModel。

推荐服务：

- `SteamDTService`
- `BuffService`
- `MarketQueryService`
- `WatchlistService`
- `RadarService`
- `SettingsService`

### Client 层

职责：

- 封装外部 HTTP 请求。
- 处理请求头、认证、限流和错误。
- 返回结构化 DTO。
- 不做业务计算。

推荐 Client：

- `SteamDTClient`
- `BuffClient`

### Repository 层

职责：

- 只负责 SQLite 读写。
- 不调用外部 API。
- 不包含 UI 逻辑。

推荐 Repository：

- `ItemRepository`
- `PriceRepository`
- `WatchlistRepository`
- `SettingRepository`
- `SourceHealthRepository`

### Market 层

职责：

- 利润计算。
- 机会扫描。
- 风险评分。
- 过滤规则。

该层必须保持纯逻辑，优先写单元测试。

## 5. 启动流程

应用启动时执行：

```text
main.py
  -> bootstrap_app()
    -> load_settings()
    -> init_logger()
    -> init_database()
    -> run_migrations()
    -> build_services()
    -> start_scheduler()
    -> start_ui()
```

首次启动：

1. 创建本地数据目录。
2. 创建 SQLite 数据库。
3. 创建默认配置。
4. 进入 Settings 页面提示用户配置 SteamDT API Key。

非首次启动：

1. 加载配置。
2. 检查数据库版本。
3. 检查 SteamDT 基础库是否过期。
4. 可提醒用户同步基础数据。

## 6. 配置设计

配置文件建议位于用户数据目录，不直接放在仓库根目录。

开发环境可以读取：

```text
config/config.local.toml
```

示例配置：

```toml
[steamdt]
api_key = ""
base_url = "https://open.steamdt.com"
base_sync_ttl_hours = 24
price_cache_ttl_seconds = 60
kline_cache_ttl_seconds = 1800

[buff]
enabled = false
cookie = ""
min_interval_seconds = 6
max_interval_seconds = 12
cache_ttl_seconds = 600
max_items_per_scan = 30

[market]
steam_fee_rate = 0.15
wallet_discount_rate = 1.0
min_profit = 1.0
min_roi = 0.03

[app]
log_level = "INFO"
theme = "system"
```

敏感字段：

- `steamdt.api_key`
- `buff.cookie`

处理要求：

- UI 显示时脱敏。
- 日志输出时脱敏。
- 导出配置时默认排除。
- 后期接入系统 keyring。

## 7. 数据库设计

### schema_version

```sql
CREATE TABLE IF NOT EXISTS schema_version (
  version INTEGER NOT NULL,
  applied_at TEXT NOT NULL
);
```

### items

```sql
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  steamdt_item_id TEXT UNIQUE,
  market_hash_name TEXT NOT NULL UNIQUE,
  name_cn TEXT,
  name_en TEXT,
  category TEXT,
  rarity TEXT,
  icon_url TEXT,
  tradable INTEGER DEFAULT 1,
  updated_at TEXT NOT NULL
);
```

### items_fts

用于本地搜索。

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS items_fts
USING fts5(
  market_hash_name,
  name_cn,
  name_en,
  category,
  content='items',
  content_rowid='id'
);
```

### item_aliases

```sql
CREATE TABLE IF NOT EXISTS item_aliases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id INTEGER NOT NULL,
  source TEXT NOT NULL,
  source_item_id TEXT,
  source_name TEXT,
  updated_at TEXT NOT NULL,
  UNIQUE(source, source_item_id),
  FOREIGN KEY(item_id) REFERENCES items(id)
);
```

### price_snapshots

```sql
CREATE TABLE IF NOT EXISTS price_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id INTEGER NOT NULL,
  source TEXT NOT NULL,
  buy_price REAL,
  sell_price REAL,
  lowest_price REAL,
  sell_count INTEGER,
  currency TEXT NOT NULL DEFAULT 'CNY',
  raw_json TEXT,
  captured_at TEXT NOT NULL,
  FOREIGN KEY(item_id) REFERENCES items(id)
);
```

索引：

```sql
CREATE INDEX IF NOT EXISTS idx_price_snapshots_item_source_time
ON price_snapshots(item_id, source, captured_at);
```

### watchlist

```sql
CREATE TABLE IF NOT EXISTS watchlist (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id INTEGER NOT NULL,
  target_buy_price REAL,
  target_roi REAL,
  enabled INTEGER NOT NULL DEFAULT 1,
  note TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(item_id) REFERENCES items(id)
);
```

### scan_results

```sql
CREATE TABLE IF NOT EXISTS scan_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id INTEGER NOT NULL,
  buy_source TEXT NOT NULL,
  sell_source TEXT NOT NULL,
  buy_price REAL NOT NULL,
  sell_price REAL NOT NULL,
  net_sell_price REAL NOT NULL,
  profit REAL NOT NULL,
  roi REAL NOT NULL,
  risk_score REAL,
  captured_at TEXT NOT NULL,
  FOREIGN KEY(item_id) REFERENCES items(id)
);
```

### source_health

```sql
CREATE TABLE IF NOT EXISTS source_health (
  source TEXT PRIMARY KEY,
  enabled INTEGER NOT NULL DEFAULT 1,
  last_success_at TEXT,
  last_error TEXT,
  cooldown_until TEXT
);
```

## 8. 核心数据模型

### Item

```python
class Item(BaseModel):
    id: int | None = None
    steamdt_item_id: str | None = None
    market_hash_name: str
    name_cn: str | None = None
    name_en: str | None = None
    category: str | None = None
    rarity: str | None = None
```

### PriceSnapshot

```python
class PriceSnapshot(BaseModel):
    item_id: int
    source: str
    buy_price: Decimal | None = None
    sell_price: Decimal | None = None
    lowest_price: Decimal | None = None
    sell_count: int | None = None
    currency: str = "CNY"
    captured_at: datetime
```

### ProfitResult

```python
class ProfitResult(BaseModel):
    buy_price: Decimal
    sell_price: Decimal
    net_sell_price: Decimal
    profit: Decimal
    roi: Decimal
    spread: Decimal
```

金额字段在业务计算中使用 `Decimal`，落库时可以转为字符串或固定精度浮点。第一版如果使用 SQLite `REAL`，计算层仍应使用 `Decimal` 避免展示误差。

## 9. SteamDT 接入设计

### Client 接口

```python
class SteamDTClient:
    async def fetch_base_items(self) -> list[SteamDTBaseItem]: ...

    async def fetch_single_price(self, item_id: str) -> SteamDTPrice: ...

    async def fetch_batch_prices(self, item_ids: list[str]) -> list[SteamDTPrice]: ...

    async def fetch_kline(self, item_id: str, period: str) -> list[SteamDTKline]: ...
```

### 认证

所有请求统一加：

```text
Authorization: Bearer {api_key}
```

### 限流

按接口设置独立 bucket：

```text
steamdt.base        1/day
steamdt.price.single 60/min
steamdt.price.batch  1/min
steamdt.kline       120/min
```

限流器职责：

- 请求前等待令牌。
- 请求后记录结果。
- 收到 429 或限流错误时进入短冷却。

### 缓存

缓存策略：

- `base_items`：24 小时。
- `single_price`：60 秒。
- `batch_price`：60 秒。
- `kline`：30 分钟。

缓存命中时 Service 层直接返回本地数据，不调用 Client。

## 10. 国内网络与数据源降级设计

### 背景

SteamSearch 第一批用户默认位于中国境内。Steam 官方网站、Steam Community、Community Market 和部分市场接口可能无法稳定访问。

因此，系统不能把 Steam 官方源作为启动、查询、扫描或监控的必要条件。

### 数据源优先级

第一阶段采用以下优先级：

```text
基础饰品库：
  SteamDT -> 本地缓存

当前卖出估算价：
  SteamDT -> 第三方聚合 API -> Steam 官方源

当前买入参考价：
  BUFF -> 第三方聚合 API -> Skinport / CSFloat

历史趋势：
  SteamDT -> 第三方聚合 API -> 本地快照

Steam 官方市场：
  仅作为可选校验源
```

### Steam 官方源定位

Steam 官方源包括：

- `steamcommunity.com/market/priceoverview`
- `steamcommunity.com/market/itemordershistogram`
- `steamcommunity.com/market/pricehistory`
- `steamcommunity.com/market/listings/730/...`

这些接口只用于：

- 用户手动打开 Steam 校验。
- 单个饰品详情页辅助展示。
- 后台低频补充 `item_nameid` 映射。

不用于：

- 应用首次启动。
- 基础饰品库同步。
- Radar 全量扫描。
- 监控列表核心刷新。
- 阻塞用户查询流程。

### DataSource 抽象

所有价格源统一实现数据源接口。

```python
class PriceSource(Protocol):
    name: str
    priority: int
    region_hint: str

    async def health_check(self) -> SourceHealth: ...

    async def get_price(self, item: Item) -> PriceSnapshot | None: ...
```

推荐来源：

- `SteamDTPriceSource`
- `BuffPriceSource`
- `SteamOfficialPriceSource`
- `SkinportPriceSource`
- `CSFloatPriceSource`
- `AggregatorPriceSource`

### SourceHealth

每个数据源必须维护健康状态。

```python
class SourceHealth(BaseModel):
    source: str
    enabled: bool
    reachable: bool
    degraded: bool
    last_success_at: datetime | None
    last_error: str | None
    cooldown_until: datetime | None
```

健康状态用于：

- UI 展示。
- 请求调度。
- Radar 是否跳过某数据源。
- 失败后自动降级。

### 超时与冷却

Steam 官方源必须使用更保守的策略：

```text
connect_timeout = 3s
read_timeout = 6s
max_retries = 0
cooldown_after_failure = 10m
cooldown_after_429 = 30m
```

SteamDT 和国内可访问数据源可以使用更短冷却：

```text
connect_timeout = 5s
read_timeout = 15s
max_retries = 1
cooldown_after_failure = 2m
```

BUFF 继续使用慢速请求策略，不和 Steam 官方源共享队列。

### 查询降级流程

```text
用户查询饰品
  -> 本地搜索
  -> 读取 SteamDT 缓存
  -> SteamDT 可用则刷新
  -> BUFF 启用则尝试增强
  -> 如果 Steam 官方源启用且健康，再异步校验
  -> UI 先展示主结果
  -> Steam 校验结果稍后补充
```

Steam 官方源失败时：

- 不阻塞 UI。
- 不影响利润计算主结果。
- 标记 `Steam 官方源不可达`。
- 进入冷却。

### Radar 降级流程

```text
Radar 扫描
  -> SteamDT 粗筛
  -> BUFF 慢速确认
  -> 可选聚合 API 补充
  -> 不请求 Steam 官方源
```

Radar 不直接访问 Steam 官方源，避免扫描过程因网络不可达或限流整体失败。

### UI 展示

数据源状态要清晰展示：

```text
SteamDT：正常
BUFF：启用，8 秒后可请求
Steam 官方：未启用 / 不可达 / 冷却中
聚合 API：未配置
```

单品价格旁必须展示来源：

```text
卖出估算：SteamDT，1 分钟前
买入参考：BUFF，8 分钟前
Steam 校验：不可达
```

### 合规边界

应用不内置代理、VPN、加速或绕过访问限制的能力。

用户如自行配置系统网络环境，应用只按普通 HTTP 客户端工作。

## 11. BUFF 接入设计

### 设计边界

BUFF 只作为增强数据源，不作为主数据源。

第一阶段只做：

- 单个饰品最低挂单价。
- 在售数量。
- 数据更新时间。

不做：

- 全站爬取。
- 高频扫描。
- 自动下单。
- 验证码绕过。

### Client 接口

```python
class BuffClient:
    async def fetch_listing_summary(
        self,
        market_hash_name: str,
        buff_goods_id: str | None = None,
    ) -> BuffListingSummary: ...
```

### 请求策略

默认策略：

```text
min_interval_seconds = 6
max_interval_seconds = 12
cache_ttl_seconds = 600
max_items_per_scan = 30
```

同一个饰品在缓存有效期内不重复请求。

失败处理：

- 网络失败：指数退避。
- 401/403：禁用 BUFF 数据源并提示 cookie 失效。
- 429/风控提示：进入冷却，不继续请求。
- 解析失败：记录原始响应摘要，不记录 cookie。

## 12. 业务流程

### 单品查询流程

```text
用户输入关键词
  -> ItemRepository.search()
  -> 用户选择饰品
  -> MarketQueryService.query_item()
    -> 读取 SteamDT 价格缓存
    -> 缓存失效时调用 SteamDTService
    -> 如果 BUFF 启用，读取 BUFF 缓存
    -> BUFF 缓存失效时调用 BuffService
    -> ProfitCalculator.calculate()
    -> 返回 ItemQuoteViewModel
```

### 加入监控流程

```text
Browser 页面点击加入监控
  -> WatchlistService.add_item()
  -> 写入 watchlist
  -> 触发一次手动刷新
```

### 监控刷新流程

```text
Scheduler 定时触发
  -> WatchlistService.refresh_enabled_items()
  -> 按优先级队列刷新 SteamDT
  -> 如启用 BUFF，低频刷新 BUFF
  -> 重新计算利润
  -> 写入 price_snapshots
  -> 标记命中项
```

### Radar 扫描流程

```text
用户设置过滤条件
  -> ItemRepository.search_by_filters()
  -> SteamDTService.fetch_batch_prices()
  -> ProfitCalculator 粗筛
  -> 取 Top N 候选
  -> BuffService 慢速确认
  -> ScoringService 打分
  -> 写入 scan_results
  -> UI 展示机会列表
```

## 13. 利润计算

基础输入：

- `buy_price`：买入价，优先 BUFF 最低挂单价。
- `sell_price`：卖出估算价，优先 SteamDT 的目标卖出价。
- `steam_fee_rate`：Steam 手续费率，默认 0.15。
- `wallet_discount_rate`：Steam 钱包折价，默认 1.0。

公式：

```text
net_sell_price = sell_price * (1 - steam_fee_rate) * wallet_discount_rate
profit = net_sell_price - buy_price
roi = profit / buy_price
spread = sell_price / buy_price - 1
```

处理规则：

- `buy_price <= 0` 时不计算。
- `sell_price <= 0` 时不计算。
- 利润和 ROI 都保留原始值，UI 再做格式化。
- 数据过期时仍可显示，但需要标记为 stale。

## 14. 风险评分

第一版风险评分可以简单实现：

```text
risk_score = 100
  - 数据过期扣分
  - BUFF 在售数量太少扣分
  - ROI 过高异常扣分
  - 缺少 BUFF 数据扣分
  - 缺少历史 K 线扣分
```

建议等级：

- 80-100：低风险。
- 60-79：中风险。
- 0-59：高风险。

风险评分只用于排序和提示，不作为交易建议。

## 15. UI 状态模型

### ItemQuoteViewModel

```python
class ItemQuoteViewModel(BaseModel):
    item: Item
    steamdt_price: PriceSnapshot | None
    buff_price: PriceSnapshot | None
    profit: ProfitResult | None
    source_warnings: list[str]
    is_stale: bool
```

### ScanResultViewModel

```python
class ScanResultViewModel(BaseModel):
    item: Item
    buy_source: str
    sell_source: str
    buy_price: Decimal
    sell_price: Decimal
    profit: Decimal
    roi: Decimal
    risk_score: Decimal
    captured_at: datetime
```

UI 只消费 ViewModel，避免页面里到处拼业务逻辑。

## 16. 错误处理

定义统一异常：

```python
class SteamSearchError(Exception): ...
class ConfigError(SteamSearchError): ...
class ExternalApiError(SteamSearchError): ...
class RateLimitError(ExternalApiError): ...
class AuthError(ExternalApiError): ...
class DataParseError(ExternalApiError): ...
```

UI 展示规则：

- 配置错误：引导用户去 Settings。
- 认证失败：提示 API Key 或 cookie 失效。
- 限流：显示冷却时间。
- 数据解析失败：显示数据源异常。
- 网络失败：允许重试。
- Steam 官方源不可达：提示已降级，不影响主查询。

日志规则：

- ERROR 记录异常类型和上下文。
- DEBUG 可记录响应摘要。
- 永不记录完整 API Key、cookie。

## 17. 调度与队列

第一版可以使用 APScheduler 加简单内存队列。

任务类型：

- `sync_steamdt_base_items`
- `refresh_watchlist_prices`
- `run_radar_scan`
- `cleanup_old_snapshots`

优先级：

1. 用户手动查询。
2. 用户手动刷新监控。
3. Radar 扫描。
4. 后台定时刷新。

同一数据源同一时间只允许一个请求 worker，避免 BUFF 并发触发风险。

Steam 官方源和 BUFF 使用独立队列：

- Steam 官方源队列：只处理手动校验和低频补充。
- BUFF 队列：只处理单品增强和候选确认。
- SteamDT 队列：处理主查询、监控和 Radar 粗筛。

## 18. 安全设计

### 敏感信息脱敏

脱敏函数：

```python
def mask_secret(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"
```

所有日志、错误提示、配置预览都必须使用脱敏后的值。

### 本地文件

建议使用 `platformdirs` 获取用户数据目录：

```text
macOS: ~/Library/Application Support/SteamSearch
Windows: %APPDATA%/SteamSearch
```

仓库内 `data/` 仅用于开发。

## 19. 测试策略

### 单元测试

必须覆盖：

- `ProfitCalculator`
- `RateLimiter`
- `Settings` 校验
- Repository 基础读写
- BUFF 请求间隔策略

### 集成测试

使用 mock HTTP：

- SteamDTClient 正常响应。
- SteamDTClient 认证失败。
- SteamDTClient 限流。
- BuffClient cookie 失效。
- BuffClient 解析失败。
- SteamOfficialPriceSource 不可达。
- SteamOfficialPriceSource 冷却降级。

### UI 手工验收

第一版至少验证：

- 无 API Key 时能进入设置页。
- 配置 API Key 后能同步基础数据。
- 搜索框输入中文和英文都能匹配。
- 单品页能显示价格和利润。
- 关闭 BUFF 时不影响查询。
- BUFF 失败时页面不崩溃。
- Steam 官方源不可达时主查询仍可完成。

## 20. 开发顺序

### Step 1：项目骨架

交付：

- `pyproject.toml`
- 基础目录结构。
- `app/main.py`
- 配置加载。
- 日志初始化。
- SQLite 初始化。

验收：

- `python -m app.main` 可以启动。
- 本地数据库能创建。

### Step 2：市场计算核心

交付：

- `market/calculator.py`
- `market/models.py`
- 单元测试。

验收：

- 能正确计算手续费后利润和 ROI。

### Step 3：SteamDT Client

交付：

- `steamdt/client.py`
- `steamdt/dto.py`
- SteamDT 错误处理。
- 限流器。

验收：

- 能用配置中的 API Key 请求单品价格。
- 认证失败有明确错误。

### Step 4：基础库同步和搜索

交付：

- `ItemRepository`
- `items` 和 `items_fts`
- 基础数据同步服务。

验收：

- 能搜索饰品。
- 能从搜索结果进入详情。

### Step 5：Browser 页面

交付：

- 搜索框。
- 搜索结果列表。
- 饰品详情。
- 利润展示。

验收：

- 用户可以完成一次完整查询。

### Step 6：BUFF 增强

交付：

- `BuffClient`
- `BuffService`
- BUFF 缓存。
- BUFF 限流。
- 设置页开关。

验收：

- 开启 BUFF 后可以显示最低挂单价。
- BUFF 错误不会影响 SteamDT 查询。

### Step 7：Watchlist

交付：

- 监控列表 Repository。
- Watchlist 页面。
- 定时刷新。

验收：

- 能加入、删除、启用、停用监控项。

### Step 8：Radar 初版

交付：

- 过滤条件。
- SteamDT 粗筛。
- BUFF 慢速确认。
- 机会结果排序。

验收：

- 能产出按 ROI 排序的候选列表。

## 21. 代码规范

### 命名

- 外部数据 DTO 使用来源前缀，例如 `SteamDTPriceDTO`。
- 业务模型不带来源前缀，例如 `PriceSnapshot`。
- Repository 方法名使用明确动作，例如 `find_by_market_hash_name`。

### 类型

- 新代码必须加类型注解。
- 金额计算使用 `Decimal`。
- API DTO 使用 pydantic model。

### 日志

- Service 层记录关键业务事件。
- Client 层记录请求失败。
- Repository 层默认不记录 SQL。

### 异步

- 外部 HTTP 请求使用 async。
- UI 层避免直接执行长任务。
- 长任务交给 Service 或 Scheduler。

## 22. 交付标准

第一阶段技术交付完成时，应满足：

1. 应用可启动。
2. 配置系统可用。
3. SQLite schema 可迁移。
4. SteamDT 查询闭环可用。
5. BUFF 增强可开关。
6. 利润计算有单元测试。
7. 本地搜索可用。
8. 监控列表可保存。
9. Radar 初版可运行。
10. 日志不泄露敏感信息。
11. Steam 官方源不可达时应用仍可正常查询。

## 23. 后期技术预留

### 插件接口

后期平台能力统一实现：

```python
class PlatformPlugin(Protocol):
    name: str

    async def get_price(self, item: Item) -> PriceSnapshot: ...

    async def health_check(self) -> SourceHealth: ...
```

### 通知接口

```python
class NotifyPlugin(Protocol):
    name: str

    async def send(self, title: str, content: str) -> None: ...
```

### 自动化接口

自动化交易必须独立插件化，并默认关闭。

```python
class TradePlugin(Protocol):
    name: str

    async def list_item(self, item: Item, price: Decimal) -> None: ...

    async def cancel_listing(self, listing_id: str) -> None: ...
```

自动化插件启用前必须具备：

- 明确风险提示。
- 操作确认。
- 日志脱敏。
- 单独配置。
- 可一键停用。

## 24. 近期建议

下一步建议直接开始 Step 1：

1. 初始化 Python 项目。
2. 建立目录结构。
3. 加入配置和日志。
4. 创建 SQLite migration。
5. 先写 `ProfitCalculator` 测试。

这样可以最快形成一个可靠的工程底座，然后再接 SteamDT API。
