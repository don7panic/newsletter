import os
from pathlib import Path


def _parse_dotenv_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    if stripped.startswith("export "):
        stripped = stripped[len("export ") :].lstrip()

    if "=" not in stripped:
        return None

    key, raw_value = stripped.split("=", 1)
    key = key.strip()
    value = raw_value.strip()
    if not key:
        return None

    if value and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    elif " #" in value:
        # Only treat inline comments specially for unquoted values.
        value = value.split(" #", 1)[0].rstrip()

    return key, value


def _load_dotenv_file(path: Path) -> None:
    if not path.is_file():
        return
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return

    for line in content.splitlines():
        parsed = _parse_dotenv_line(line)
        if parsed is None:
            continue
        key, value = parsed
        os.environ.setdefault(key, value)


_load_dotenv_file(Path(".env"))

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
X_COOKIES = os.getenv("X_COOKIES")
X_COOKIES_PATH = os.getenv("X_COOKIES_PATH") or "x.json"
X_WEB_BEARER_TOKEN = os.getenv("X_WEB_BEARER_TOKEN")
X_CLIENT_TRANSACTION_ID = os.getenv("X_CLIENT_TRANSACTION_ID")
X_USER_TWEETS_OPERATION = "x3B_xLqC0yZawOB7WQhaVQ/UserTweets"
X_AUTHOR_IDS = {
    "karpathy": "33836629",
    "sama": "1605",
    "joshwoodward": "206546319",
    "mattturck": "247785677",
    "trq212": "352806502"
}
X_LOOKBACK_HOURS = 24*2
X_POST_LIMIT_PER_AUTHOR = 3
X_AUTHOR_REQUEST_TIMEOUT = 20
X_AUTHOR_REQUEST_RETRIES = 4
X_AUTHORS = (
    "karpathy",
    "sama",
    "joshwoodward",
    "mattturck",
    "trq212",
)


def resolve_x_cookies_path() -> Path | None:
    if not X_COOKIES_PATH:
        return None
    return Path(X_COOKIES_PATH).expanduser()


def is_x_enabled() -> bool:
    if X_COOKIES and X_COOKIES.strip():
        return True
    cookies_path = resolve_x_cookies_path()
    return cookies_path is not None and cookies_path.is_file()


def get_x_author_ids() -> dict[str, str]:
    return dict(X_AUTHOR_IDS)


X_ENABLED = is_x_enabled()


# ---------------------------------------------------------------------------
# AI configuration — reads directly from .env, not system env vars
# ---------------------------------------------------------------------------

_DOTENV_CACHE: dict[str, str] | None = None


def _read_env(key: str, default: str = "") -> str:
    """Read a value directly from the project .env file.

    This avoids relying on ``os.environ`` so that system-level environment
    variables cannot accidentally override the project-local configuration.
    The .env file is parsed once and cached.
    """
    global _DOTENV_CACHE
    if _DOTENV_CACHE is None:
        _DOTENV_CACHE = {}
        dotenv_path = Path(".env")
        if dotenv_path.is_file():
            for line in dotenv_path.read_text(encoding="utf-8").splitlines():
                parsed = _parse_dotenv_line(line)
                if parsed is not None:
                    _DOTENV_CACHE[parsed[0]] = parsed[1]
    return _DOTENV_CACHE.get(key, default)


AI_API_KEY = _read_env("AI_API_KEY")
AI_BASE_URL = _read_env("AI_BASE_URL", "https://api.openai.com/v1")
AI_MODEL = _read_env("AI_MODEL", "glm-5")
try:
    AI_SCORE_THRESHOLD = float(_read_env("AI_SCORE_THRESHOLD", "6.0"))
except ValueError:
    AI_SCORE_THRESHOLD = 6.0
try:
    HN_MIN_ITEMS_AFTER_AI = max(0, int(_read_env("HN_MIN_ITEMS_AFTER_AI", "3")))
except ValueError:
    HN_MIN_ITEMS_AFTER_AI = 3
try:
    GITHUB_TRENDING_MIN_ITEMS_AFTER_AI = max(
        0,
        int(_read_env("GITHUB_TRENDING_MIN_ITEMS_AFTER_AI", "3")),
    )
except ValueError:
    GITHUB_TRENDING_MIN_ITEMS_AFTER_AI = 3
AI_ENABLED = bool(AI_API_KEY)
