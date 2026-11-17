import re
from typing import Optional
from urllib.parse import unquote, quote

from furl import furl

# http(s)://host followed by an optional path, query or fragment. The host is
# plain ASCII and nothing contains whitespace or control characters, so furl's
# result is known without parsing.
_SIMPLE_URL = re.compile(r"([A-Za-z]+)://([A-Za-z0-9.-]+)(?:[/?#][^\s\x00-\x1f\x7f]*)?")


def _normalize_simple_url(url: str) -> Optional[str]:
    """Return what furl-based normalization gives for a plain http(s) URL, else None."""
    match = _SIMPLE_URL.fullmatch(url)
    if not match or match.group(1).lower() not in ("http", "https"):
        return None
    host = match.group(2).lower()
    # Empty or over-long labels make furl or IDNA encoding fail; xn-- hosts are IDNA-decoded.
    if "xn--" in host or not all(0 < len(label) < 64 for label in host.split(".")):
        return None
    if host.startswith("www."):
        host = host[4:]
    return "//" + host


def normalize_url(url: str) -> Optional[str]:
    if not url or not url.strip():
        return None

    simple = _normalize_simple_url(url)
    if simple is not None:
        return simple

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


def normalize_wikipedia_url(url: str) -> Optional[str]:
    if not url or not url.startswith('https://'):
        return url
    base = url[:url.rfind('/') + 1]
    path = url[url.rfind('/') + 1:]
    normalized_path = quote(unquote(path))
    return base + normalized_path
