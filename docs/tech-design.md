# Tech Design

## 目标

每天在本地抓取两类内容：

- Hacker News
- GitHub Trending

将结果写入单个 Markdown 文件：

- `daily/YYYY-MM-DD.md`

## 设计决策

### GitHub Trending

- 主方案：直接抓 GitHub 官方 Trending 页面
- 地址：`https://github.com/trending?since=daily`
- 实现：`requests` + `BeautifulSoup`

原因：

- 最简单
- 最可控
- 适合本地定时任务

不使用第三方预生成 API 作为主数据源。

### Hacker News

- 使用官方 API
- 先抓 Top Stories ID
- 再抓每条详情

## 执行流程

1. 获取当天日期
2. 抓取 HN
3. 抓取 GitHub Trending
4. 渲染 Markdown
5. 写入 `daily/YYYY-MM-DD.md`

## 目录

```text
newsletter/
  pyproject.toml
  main.py
  config.py
  fetchers/
    hn.py
    github_trending.py
  renderers/
    markdown.py
  storage/
    writer.py
  daily/
  docs/
```

## 数据结构

内部统一用简单 `dict`，避免过度建模。

公共字段：

- `source`
- `title`
- `url`
- `rank`
- `summary`
- `fetched_at`
- `meta`

`meta` 字段：

- HN
  - `score`
  - `comments`
  - `hn_discussion_url`
- GitHub Trending
  - `repo_name`
  - `language`
  - `stars_today`
  - `description`

## Markdown 输出

固定结构：

```md
# Newsletter - YYYY-MM-DD

## Hacker News

1. [Title](URL)
   - 123 points, 45 comments
   - HN: ...
   - Summary: ...

## GitHub Trending

1. [owner/repo](URL)
   - Language: Python
   - Stars today: 1234
   - Description: ...

---
Generated at: YYYY-MM-DD HH:MM:SS
```

规则：

- 一个文件包含两个 section
- 格式固定，方便后续解析
- HN 摘要第一版允许为空
- GitHub Trending 直接使用 `description`

## 模块职责

- `main.py`：串联流程
- `fetchers/hn.py`：抓 HN
- `fetchers/github_trending.py`：抓 Trending 页面
- `renderers/markdown.py`：生成 Markdown
- `storage/writer.py`：写文件

## 错误处理

- 请求失败要打印来源
- 解析失败要打印来源
- 两个来源都失败时退出非零
- 只失败一个来源时，允许先生成部分结果

## 约束

- 本地运行，不依赖 GitHub Actions
- Markdown 是最终落盘格式
- 同一天重复执行时覆盖同名文件
