# SteamSearch 项目启动方案

## 1. 项目定位

SteamSearch 是一个面向 CS2 饰品倒买用户的快速查询与机会发现工具。

项目第一阶段的核心目标不是自动交易，而是帮助用户快速判断某个饰品是否值得买入、是否存在跨平台价差、当前价格是否具备利润空间。

本项目将采用“SteamDT 官方 API 为主、BUFF 数据增强为辅”的混合数据方案：

- SteamDT 提供稳定的饰品基础库、价格、K 线和历史趋势数据。
- BUFF 提供更贴近实际买入场景的当前挂单价格。
- 本地数据库负责缓存、搜索、监控和机会扫描。

## 2. 第一阶段目标

第一阶段先完成一个可用的查询型 MVP：

1. 配置 SteamDT API Key。
2. 同步 SteamDT 饰品基础数据到本地。
3. 支持本地快速搜索 CS2 饰品。
4. 查询单个饰品的 SteamDT 价格数据。
5. 可选启用 BUFF 单品价格增强。
6. 计算买入价、卖出价、手续费后利润、ROI。
7. 支持加入监控列表。
8. 展示数据来源、更新时间和基础风险提示。

第一阶段暂不做：

- 检视图。
- 自动购买。
- 自动发货。
- 自动上架。
- 批量全站爬取 BUFF。
- 绕过验证码、风控或登录限制。

## 3. 参考项目吸收点

### SkinsRadar

SkinsRadar 的价值主要在产品形态：

- Browser Mode：适合参考为“饰品查询页”。
- Radar Mode：适合参考为“机会扫描页”。
- 手续费、销量、价格区间、品类过滤：适合做成第一阶段配置项。
- 本地数据库和更新流程：适合参考为本地缓存设计。

SteamSearch 不照搬 SkinsRadar 的数据源，而是使用 SteamDT 和 BUFF 组合。

### oddish

oddish 的价值主要在 BUFF 爬取策略：

- 慢速少量。
- 使用价格区间缩小爬取范围。
- 使用品类白名单和黑名单。
- 本地缓存优先。
- 不频繁重复请求同一页面。

SteamSearch 不做 oddish 式全量爬取，而是只在用户查询、监控列表、机会确认时请求 BUFF。

### Steamauto

Steamauto 的价值主要在后期扩展架构：

- 多平台插件化。
- 通知系统。
- 自动化任务。
- 敏感配置管理。
- 日志脱敏。

SteamSearch 第一阶段只预留插件接口，不实现自动交易能力。

## 4. 技术选型

推荐使用 Python 桌面应用方案。

### 核心技术

- 语言：Python 3.11+
- UI：Flet 或 PySide6
- 数据库：SQLite
- HTTP 客户端：httpx
- 异步任务：asyncio
- 定时调度：APScheduler
- 配置管理：pydantic-settings
- 打包：PyInstaller 或 Nuitka

### 推荐首选

第一版建议选择 Flet：

- 开发速度快。
- 适合做桌面查询工具。
- UI 代码相对轻。
- 后期可尝试打包为桌面应用。

如果后续需要更原生、更复杂的桌面体验，再迁移到 PySide6。

## 5. 总体架构

```text
steamSearch/
  app/
    main.py
    ui/
      pages/
        dashboard.py
        browser.py
        radar.py
        watchlist.py
        settings.py
      components/
    core/
      config.py
      logger.py
      scheduler.py
      rate_limiter.py
    steamdt/
      client.py
      models.py
    buff/
      crawler.py
      parser.py
      models.py
    market/
      calculator.py
      scanner.py
      filters.py
      scoring.py
    storage/
      db.py
      repositories.py
      migrations/
    plugins/
      base.py
      notify/
      platforms/
    tests/
  config/
    config.example.toml
  data/
  docs/
  logs/
```

## 6. 核心模块设计

### SteamDTClient

负责访问 SteamDT API。

第一阶段需要封装：

- 基础饰品数据同步。
- 单品价格查询。
- 批量价格查询。
- K 线查询。

要求：

- 统一处理 Authorization。
- 统一处理限流。
- 统一处理错误码。
- 所有响应写入缓存。

### BuffCrawler

负责获取 BUFF 当前挂单价格。

第一阶段只支持：

- 按单个饰品查询当前最低挂单价。
- 获取在售数量。
- 获取数据更新时间。

要求：

- 默认关闭，由用户手动开启。
- 请求间隔默认 6-12 秒。
- 不允许低于 4 秒。
- 支持本地缓存，默认 5-15 分钟。
- 支持失败退避。
- 不做验证码绕过。
- cookie 不写入日志。

### ItemResolver

负责统一饰品标识。

需要维护：

- SteamDT item id。
- Steam market_hash_name。
- BUFF goods id。
- 中文名。
- 英文名。
- 品类。

第一阶段可以先基于 SteamDT 基础数据建立主索引，再在用户查询 BUFF 时逐步补全 BUFF goods id。

### ProfitCalculator

负责利润计算。

基础公式：

```text
steam_net = steam_sell_price * (1 - steam_fee_rate)
profit = steam_net - buy_price
roi = profit / buy_price
spread = sell_price / buy_price - 1
```

第一阶段配置项：

- Steam 手续费率。
- 平台买入手续费。
- 钱包余额折价。
- 最小利润。
- 最小 ROI。

### OpportunityScanner

负责机会扫描。

第一阶段扫描流程：

1. 从本地饰品库按品类、价格区间、关键词筛候选。
2. 使用 SteamDT 批量价格粗筛。
3. 对候选中可能有利润的饰品慢速请求 BUFF。
4. 计算利润和 ROI。
5. 输出排序后的机会列表。

## 7. 数据库设计

### items

存储饰品基础信息。

字段建议：

- id
- steamdt_item_id
- market_hash_name
- name_cn
- name_en
- category
- rarity
- icon_url
- updated_at

### item_aliases

存储不同平台的映射关系。

字段建议：

- id
- item_id
- source
- source_item_id
- source_name
- updated_at

### price_snapshots

存储价格快照。

字段建议：

- id
- item_id
- source
- buy_price
- sell_price
- lowest_price
- sell_count
- currency
- captured_at

### watchlist

存储用户监控项。

字段建议：

- id
- item_id
- target_buy_price
- target_roi
- enabled
- note
- created_at
- updated_at

### scan_results

存储机会扫描结果。

字段建议：

- id
- item_id
- buy_source
- sell_source
- buy_price
- sell_price
- profit
- roi
- risk_score
- captured_at

### source_health

存储数据源状态。

字段建议：

- source
- enabled
- last_success_at
- last_error
- cooldown_until

## 8. 页面设计

### Dashboard

展示：

- 今日监控命中数量。
- 当前最高 ROI 饰品。
- 数据源状态。
- SteamDT API 使用状态。
- BUFF 是否启用。

### Browser

核心查询页。

功能：

- 搜索饰品。
- 展示 SteamDT 价格。
- 展示 BUFF 增强价格。
- 展示利润、ROI、价差。
- 加入监控。
- 查看简单 K 线趋势。

### Radar

机会扫描页。

功能：

- 设置价格区间。
- 设置品类。
- 设置最小利润。
- 设置最小 ROI。
- 设置最大扫描数量。
- 启动扫描。
- 输出机会列表。

### Watchlist

监控列表页。

功能：

- 查看关注饰品。
- 设置目标买入价。
- 设置目标 ROI。
- 手动刷新。
- 启用或停用监控。

### Settings

设置页。

功能：

- SteamDT API Key。
- BUFF cookie。
- Steam 手续费率。
- 钱包折价。
- 请求间隔。
- 缓存时间。
- 日志级别。

## 9. 请求与缓存策略

### 国内网络环境

SteamSearch 默认面向中国境内用户使用，因此不能假设 Steam 官方网站、Steam Community Market 或相关接口始终可达。

第一阶段的数据源优先级调整为：

1. SteamDT：主数据源。
2. BUFF：买入价增强数据源。
3. 国内可访问的第三方聚合 API：备用价格源。
4. Skinport、CSFloat 等海外官方 API：可选参考源。
5. Steam 官方市场接口：可选校验源，不作为核心依赖。

应用必须支持“Steam 官方源不可用”的正常运行模式。

要求：

- 首次启动不依赖 Steam 官方网站。
- 基础饰品库优先来自 SteamDT。
- 单品查询优先使用 SteamDT 和 BUFF。
- Steam 官方市场数据只在用户启用后尝试请求。
- Steam 官方源请求失败时不影响主流程。
- UI 明确展示数据源可达状态。
- 不在应用内内置或引导绕过网络限制的能力。

### SteamDT

- 基础饰品数据：每日同步一次。
- 单品价格：手动查询优先，短 TTL 缓存。
- 批量价格：监控和 Radar 使用，进入队列。
- K 线：只在详情页或监控项中拉取。

### BUFF

- 默认不开启。
- 只查用户明确查询的饰品。
- 只查监控列表中的饰品。
- 只查 Radar 粗筛后的候选。
- 默认缓存 5-15 分钟。
- 失败后进入冷却。

## 10. 风险控制

### Steam 官方源不可达风险

中国境内访问 Steam Community、社区市场和部分市场接口可能不稳定或不可达。

控制措施：

- Steam 官方源默认关闭。
- Steam 官方源只作为校验源。
- 所有 Steam 官方源请求必须经过超时、限流和失败冷却。
- 连续失败后自动降级，不重复打扰用户。
- Radar 扫描不得依赖 Steam 官方源。
- 监控列表不得依赖 Steam 官方源。

### BUFF 账号风险

BUFF 存在反爬和账号冷却风险。

控制措施：

- 默认关闭 BUFF 数据源。
- 明确展示风险提示。
- 请求间隔不低于 4 秒。
- 默认使用 6-12 秒随机间隔。
- 限制单次扫描数量。
- 支持手动暂停。
- 不绕过验证码。

### 数据准确性风险

不同数据源更新时间不同，价格可能不一致。

控制措施：

- 所有价格展示数据来源。
- 所有价格展示更新时间。
- 利润结果标记为估算。
- 高利润但数据过旧时降低评分。

### 敏感信息风险

API Key 和 cookie 属于敏感信息。

控制措施：

- 本地保存。
- 日志脱敏。
- 导出配置时默认排除。
- 后续接入系统 keyring。

## 11. 第一阶段里程碑

### Milestone 1：项目骨架

目标：

- 建立 Python 项目结构。
- 建立配置系统。
- 建立 SQLite 初始化。
- 建立日志系统。

验收：

- 应用可以启动。
- 可以读取配置。
- 可以创建本地数据库。

### Milestone 2：SteamDT 基础能力

目标：

- 封装 SteamDTClient。
- 支持 API Key 配置。
- 支持同步基础饰品。
- 支持单品价格查询。

验收：

- 可以搜索本地饰品。
- 可以查询单品价格。

### Milestone 3：查询页 MVP

目标：

- 建立 Browser 页面。
- 展示饰品基础信息。
- 展示价格和利润计算。

验收：

- 用户可以输入关键词并得到结果。
- 用户可以看到利润和 ROI。

### Milestone 4：BUFF 单品增强

目标：

- 支持配置 BUFF cookie。
- 支持单品最低挂单价查询。
- 支持 BUFF 缓存和限流。

验收：

- 开启 BUFF 后，单品页可显示 BUFF 价格。
- 关闭 BUFF 后，应用仍可正常使用。

### Milestone 5：监控列表

目标：

- 支持加入监控。
- 支持手动刷新。
- 支持目标价和 ROI。

验收：

- 用户可以维护关注列表。
- 达到目标时有明显提示。

### Milestone 6：Radar 初版

目标：

- 支持按价格、品类、ROI 扫描。
- SteamDT 粗筛。
- BUFF 慢速确认。

验收：

- 可以输出按 ROI 排序的机会列表。
- 可以查看每条机会的数据来源和更新时间。

## 12. MVP 验收标准

MVP 完成时应满足：

1. 不依赖 BUFF 也能正常查询。
2. SteamDT API Key 配置后可以拉取基础数据。
3. 本地搜索响应足够快。
4. 单品页能展示利润和 ROI。
5. BUFF 增强可以手动启用或关闭。
6. BUFF 请求有缓存、限流和失败冷却。
7. 监控列表可以保存和刷新。
8. Radar 可以输出第一版机会列表。
9. 日志中不出现 API Key 和 cookie。

## 13. 后续扩展方向

后续可以逐步扩展：

- 通知：Telegram、飞书、钉钉、WxPusher。
- 更多平台价格：悠悠有品、C5、IGXE、CSFloat。
- 历史回测：验证某类策略是否稳定。
- 风险评分：成交量、波动率、价格异常、数据新鲜度。
- 自动化插件：自动改价、自动上架、自动发货。
- 多账号配置：不同平台账号隔离。

自动化交易能力必须作为高级插件，并默认关闭。

## 14. 当前推荐结论

项目第一步应先实现 SteamDT-only 的稳定查询闭环，再加入 BUFF 单品增强。

推荐顺序：

1. 项目骨架。
2. SteamDT 基础数据同步。
3. 本地搜索。
4. 单品价格查询。
5. 利润计算。
6. BUFF 单品价格增强。
7. 监控列表。
8. Radar 扫描。

这样既能尽快做出可用软件，也能避免一开始就被 BUFF 风控、验证码、自动交易等复杂问题拖住。
