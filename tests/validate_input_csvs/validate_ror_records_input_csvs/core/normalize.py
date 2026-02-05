import re
from typing import Optional

from furl import furl


def normalize_url(url: str) -> Optional[str]:
    if not url or not url.strip():
        return None

    try:
        f = furl(url)
        f.path.normalize()
        f.path = ""
        f.remove(args=True, fragment=True)

        host = f.host
        if not host:
            return None

        if host.startswith("www."):
            f.host = host[4:]

        f.scheme = None

        return f.url.lower()
    except Exception:
        return None


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)

    return text


def normalize_whitespace(text: str) -> str:
    if not text:
        return ""

    text = re.sub(r"\s+", " ", text.strip())

    return text
