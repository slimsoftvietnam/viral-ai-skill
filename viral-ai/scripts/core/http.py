"""HTTP client tối giản (chỉ thư viện chuẩn): có giãn cách, thử lại, lùi khi bị giới hạn, đếm thống kê."""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


class Http:
    def __init__(self, cfg: dict):
        self.delay = cfg.get("delay_seconds", 0.25)
        self.timeout = cfg.get("timeout_seconds", 20)
        self.retries = cfg.get("retries", 3)
        self.stats = {"requests": 0, "ok": 0, "empty": 0, "failed": 0, "rate_limited": 0}
        self._lock = threading.Lock()

    def _bump(self, key: str) -> None:
        with self._lock:
            self.stats[key] += 1

    def get(self, url: str, headers: dict | None = None, data: bytes | None = None, retries: int | None = None):
        """Trả về (status, text). status=0 nếu lỗi mạng."""
        tries = self.retries if retries is None else retries
        last = (0, "")
        for attempt in range(tries):
            time.sleep(self.delay)
            self._bump("requests")
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept": "application/json,text/html,*/*", **(headers or {})})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    body = r.read().decode("utf-8", "replace")
                    self._bump("ok")
                    return r.status, body
            except urllib.error.HTTPError as e:
                body = ""
                try:
                    body = e.read().decode("utf-8", "replace")
                except Exception:
                    pass
                last = (e.code, body)
                if e.code == 429:
                    self._bump("rate_limited")
                    time.sleep(4 * (attempt + 1))
                    continue
                if e.code in (500, 502, 503, 504, 520, 522, 524):
                    time.sleep(1.5 * (attempt + 1))
                    continue
                if e.code == 404:
                    # Một số nguồn trả 404 tạm thời khi phía sau trống: thử lại 1 lần.
                    if attempt == 0 and tries > 1:
                        time.sleep(1.0)
                        continue
                    self._bump("empty")
                    return last
                self._bump("failed")
                return last
            except Exception as e:  # timeout, DNS, reset...
                last = (0, str(e))
                time.sleep(1.5 * (attempt + 1))
        self._bump("failed")
        return last

    def get_json(self, url: str, **kw):
        status, body = self.get(url, **kw)
        if status != 200 or not body:
            return status, None
        try:
            return status, json.loads(body)
        except json.JSONDecodeError:
            return status, None
