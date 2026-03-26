# Task

## 1. 初始化

- 创建目录：
  - `src/newsletter/fetchers/`
  - `src/newsletter/renderers/`
  - `src/newsletter/storage/`
  - `daily/`
- 创建文件：
  - `main.py`
  - `src/newsletter/config.py`
  - `src/newsletter/cli.py`
  - `src/newsletter/digest.py`
  - `pyproject.toml`

完成标准：

- `python main.py` 可以启动

状态：已完成

## 2. 实现 HN 抓取

- 接入 HN 官方 API
- 获取 Top Stories
- 获取详情并整理字段：
  - `title`
  - `url`
  - `rank`
  - `score`
  - `comments`
  - `hn_discussion_url`
  - `fetched_at`

完成标准：

- 返回 HN 条目列表

状态：已完成

## 3. 实现 GitHub Trending 抓取

- 抓 `https://github.com/trending?since=daily`
- 解析字段：
  - `repo_name`
  - `url`
  - `description`
  - `language`
  - `stars_today`
  - `rank`
  - `fetched_at`

完成标准：

- 返回 Trending 条目列表

状态：已完成

## 4. 实现 Markdown 渲染和写盘

- 生成固定 Markdown 模板
- 写入 `daily/YYYY-MM-DD.md`
- 同一天重复执行时覆盖同名文件

完成标准：

- 能看到当天的 Markdown 文件

状态：已完成

## 5. 串联主流程

- `main.py` 依次执行：
  - 抓 HN
  - 抓 Trending
  - 渲染 Markdown
  - 写文件
- 打印基础日志
- 失败时返回非零退出码

完成标准：

- 一条命令完成当天归档

状态：已完成

## 6. 第一版规则

- HN 摘要允许为空
- GitHub Trending 直接用 `description`
- 两个来源都失败时任务失败
- 只失败一个来源时允许先输出部分结果

状态：已完成
