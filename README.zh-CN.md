# Newsletter

[English README](README.md)

一个本地优先的命令行工具，用来抓取 GitHub Trending 和 Hacker News，并生成稳定的 Markdown 日报。

```text
daily/YYYY-MM-DD.md
```

## 项目作用

- 在你执行 CLI 的当前目录生成每日简报
- 输出顺序固定为 `GitHub Trending` 在前，`Hacker News` 在后
- 同一天重复执行会覆盖当日文件
- 单个数据源失败时，仍允许输出部分结果
- 只有两个数据源都失败时才会返回非零退出码

## 环境要求

- Python `3.10+`
- `uv`

## 安装

推荐作为本地命令安装：

```bash
uv tool install --force --editable .
```

安装完成后：

```bash
newsletter --help
```

如果你不想安装，也可以直接在仓库内通过 `uv run` 运行。

## 快速开始

生成今天的日报：

```bash
newsletter generate
```

检查今天的日报是否存在、是否完整：

```bash
newsletter status
```

打印今天的 Markdown 日报：

```bash
newsletter show
```

查看帮助或版本：

```bash
newsletter --help
newsletter --version
newsletter
```

不带参数执行 `newsletter`，会直接打印帮助信息。

## 命令列表

- `newsletter generate`：抓取数据并写入今天的日报
- `newsletter status`：检查今天的日报文件状态
- `newsletter show`：打印今天的日报内容
- `newsletter --help`：显示 CLI 帮助
- `newsletter --version`：显示已安装 CLI 的版本

## 输出示例

```md
# Newsletter - 2026-03-25

## GitHub Trending

1. [owner/repo](https://github.com/owner/repo)
   - Language: Python
   - ⭐ today: 2341
   - Description: ...

## Hacker News

1. [Article Title](https://example.com)
   - 320 points, 120 comments
   - HN: https://news.ycombinator.com/item?id=123
   - Summary: ...

---
Generated at: 2026-03-25 09:00:00
```

## 数据来源

- GitHub Trending 页面提供排名和当日 star 增长
- GitHub Repo API 提供仓库描述、语言等补充元数据
- Hacker News 官方 API 提供 top stories 和条目详情

只保留 `type == "story"` 的 Hacker News 条目。

## 运行说明

- 输出路径是当前工作目录下的 `daily/YYYY-MM-DD.md`
- Markdown 格式刻意保持稳定，便于后续解析和归档
- 未设置 GitHub token 时，可能会遇到 GitHub API 匿名访问限流

你可以设置 `GITHUB_TOKEN` 或 `GH_TOKEN`，降低匿名访问 GitHub API 时的限流风险。

## 开发

安装开发依赖：

```bash
uv sync
```

不做全局安装，直接在仓库内运行：

```bash
uv run newsletter generate
```

## 项目结构

```text
newsletter/
  README.md
  README.zh-CN.md
  pyproject.toml
  src/
    newsletter/
      cli.py
      digest.py
      config.py
      fetchers/
      renderers/
      storage/
  tests/
  docs/
```
