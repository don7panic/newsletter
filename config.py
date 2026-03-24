import os

HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL_TEMPLATE = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
GITHUB_TRENDING_URL = "https://github.com/trending?since=daily"
GITHUB_REPO_API_URL_TEMPLATE = "https://api.github.com/repos/{repo_name}"
GITHUB_API_VERSION = "2022-11-28"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")

DEFAULT_ITEM_LIMIT = 10
REQUEST_TIMEOUT = 20
OUTPUT_DIR = "daily"
USER_AGENT = "Mozilla/5.0 (compatible; newsletter-bot/0.1)"
