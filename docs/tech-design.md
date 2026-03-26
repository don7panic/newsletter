# Tech Design

## 目标

每天在本地抓取两类内容：

- Hacker News
- GitHub Trending

将结果写入单个 Markdown 文件：

- `daily/YYYY-MM-DD.md`

## 设计决策

### GitHub Trending

- 主方案：Trending 页面 + GitHub repo API 补充详情
- 地址：`https://github.com/trending?since=daily`
- 详情接口：`https://api.github.com/repos/{owner}/{repo}`
- 实现：`requests` + `BeautifulSoup`

原因：

- 保留官方 Trending 排序和 `stars today`
- 用 repo API 补足更稳定的仓库详情字段
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
  src/
    newsletter/
      cli.py
      digest.py
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
  - `stars_total`
  - `forks`

## Markdown 输出

固定结构：

```md
# Newsletter - YYYY-MM-DD

## GitHub Trending

1. [owner/repo](URL)
   - Language: Python
   - Stars today: 1234
   - Description: ...

## Hacker News

1. [Title](URL)
   - 123 points, 45 comments
   - HN: ...
   - Summary: ...

---
Generated at: YYYY-MM-DD HH:MM:SS
```

规则：

- 一个文件包含两个 section
- 格式固定，方便后续解析
- HN 摘要第一版允许为空
- GitHub Trending 优先使用 repo API 的 `description`，页面字段作为回退

## 模块职责

- `main.py`：开发期入口包装器
- `src/newsletter/cli.py`：CLI 参数解析与命令分发
- `src/newsletter/digest.py`：主流程编排与日报检查
- `src/newsletter/fetchers/hn.py`：抓 HN
- `src/newsletter/fetchers/github_trending.py`：抓 Trending 页面
- `src/newsletter/renderers/markdown.py`：生成 Markdown
- `src/newsletter/storage/writer.py`：写文件

## 错误处理

- 请求失败要打印来源
- 解析失败要打印来源
- 两个来源都失败时退出非零
- 只失败一个来源时，允许先生成部分结果

## 约束

- 本地运行，不依赖 GitHub Actions
- Markdown 是最终落盘格式
- 同一天重复执行时覆盖同名文件
