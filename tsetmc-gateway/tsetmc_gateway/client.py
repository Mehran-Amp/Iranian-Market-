import gzip
import urllib.request
import zlib


def http_get(url: str, timeout: float = 20.0, user_agent: str = "") -> str:
    """GET a URL and return its text. Honors HTTP(S)_PROXY environment variables."""
    req = urllib.request.Request(url, headers={
        "User-Agent": user_agent or "Mozilla/5.0",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} from {url}")
        raw = resp.read()
        enc = (resp.headers.get("Content-Encoding") or "").lower()
    if enc == "gzip":
        raw = gzip.decompress(raw)
    elif enc == "deflate":
        try:
            raw = zlib.decompress(raw)
        except zlib.error:
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
    return raw.decode("utf-8", errors="replace")
