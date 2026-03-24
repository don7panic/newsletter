# Newsletter

一个本地运行的每日抓取项目：定时获取 Hacker News 和 GitHub Trending 信息，并将结果按天落盘为 Markdown 文档。

## 使用方式

项目使用 `uv` 管理依赖和运行环境。

初始化依赖：

```bash
uv sync
```

执行当天日报抓取：

```bash
uv run newsletter
```

也可以直接运行：

```bash
uv run python main.py
```

关于重复执行：

- 同一天可以重复运行多次。
- 输出路径固定为 `daily/YYYY-MM-DD.md`。
- 如果当天再次执行，会直接覆盖已有文件内容，而不是追加。
- 文件覆盖行为来自当前实现的直接写盘逻辑。

## 目标

- 在本地机器上定时执行，不依赖 GitHub Actions。
- 每天抓取两个数据源：
  - Hacker News
  - GitHub Trending
- 将当天结果写入一个 Markdown 文件，按日期归档。
- 输出格式稳定，方便后续继续做周报、月报、搜索或二次处理。

## 核心能力

### 1. 本地定时执行

- 项目本身提供一个可重复执行的单次任务入口。
- 调度由本机完成，可接入：
  - macOS `launchd`
  - `cron`
- 每次运行都应独立完成：
  - 抓取
  - 清洗
  - 渲染
  - 写盘

### 2. 抓取 Hacker News

- 使用 Hacker News 官方 API 获取热门内容。
- 需要抓取的核心字段：
  - 标题
  - 原始链接
  - 分数
  - 评论数
  - 排名
  - 抓取时间
- 对没有外链的条目，保留 HN discussion 链接。

### 3. 抓取 GitHub Trending

- 获取 GitHub Trending 当天的热门仓库信息。
- 需要抓取的核心字段：
  - 仓库名（`owner/repo`）
  - 仓库链接
  - 描述
  - 语言
  - 当日增长指标（如当天 star 增量，若可取）
  - 抓取时间

### 4. Markdown 落盘

- 最终产物必须是 Markdown。
- 每天生成一个日报文件，推荐命名：
  - `daily/YYYY-MM-DD.md`
- 单文件内同时包含两个来源的内容。
- 输出结构固定，后续可以被程序再次解析。
- 同一天重复执行时直接覆盖同名文件。

推荐示例：

```md
# Newsletter - 2026-03-24

## Hacker News

1. [Article Title](https://example.com)
   - 320 points, 120 comments
   - HN: https://news.ycombinator.com/item?id=123
   - Summary: ...

## GitHub Trending

1. [owner/repo](https://github.com/owner/repo)
   - Language: Python
   - Stars today: 2341
   - Description: ...

---
Generated at: 2026-03-24 09:00:00
```

### 5. 摘要策略

- 项目需要支持“摘要”这个概念，但两个来源的策略不同。

#### Hacker News

- HN 官方 API 通常不提供外链文章摘要。
- 第一版允许以下策略：
  - 外链条目默认不生成摘要，只保留标题和元数据
  - 对 `Ask HN` / `Show HN` 等包含正文的帖子，提取 `text` 作为简单摘要
- 如果后续需要更强摘要能力，可以在第二阶段增加：
  - 抓取目标网页后提取 `meta description`
  - 或对正文做自动摘要

#### GitHub Trending

- 仓库 `description` 可以直接作为短摘要。
- 如果描述为空，可保留为空，不强制补全。

结论：

- Markdown 输出需要预留 `Summary` / `Description` 位置。
- 第一版不要求为所有 HN 条目强行生成摘要。

### 6. 可扩展性

- 数据抓取和 Markdown 渲染要分离。
- 不应把 Markdown 拼接逻辑和抓取逻辑耦合在一起。
- 后续应可以自然扩展：
  - 周报
  - 月报
  - 搜索
  - 标签分类
  - 更多来源

## 建议的项目结构

```text
newsletter/
  README.md
  pyproject.toml
  main.py
  fetchers/
    hn.py
    github_trending.py
  renderers/
    markdown.py
  storage/
    writer.py
  daily/
```

## 第一阶段 MVP

- 实现本地单次任务入口。
- 抓取 Hacker News 当日热门内容。
- 抓取 GitHub Trending 当日热门仓库。
- 将两部分内容渲染到同一个 Markdown 文件。
- 按日期输出到 `daily/`。

## 暂不作为第一阶段目标

- Web 页面
- README 自动展示
- 在线数据库
- 复杂标签系统
- 所有来源都生成高质量自动摘要

## 设计约束

- 本地优先。
- Markdown 是最终落盘格式，不是可选导出格式。
- 输出格式必须稳定，便于后续机器读取。
- 每次任务失败时应尽量定位到具体来源，而不是整体静默失败。

## 下一步

- 基于这份说明初始化项目骨架。
- 先实现 `HN + GitHub Trending -> Markdown` 的最小可运行版本。
