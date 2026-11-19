"""Satu-satunya modul yang bicara ke penyedia AI. Logika agen hanya memakai antarmuka Provider,
jadi OpenRouter bisa diganti (mis. Anthropic langsung) tanpa mengubah agen.

API key tidak pernah ditulis ke log atau dikirim ke frontend."""
import json
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

import httpx

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
APP_REFERER = "http://localhost:5173"
APP_TITLE = "INAPROC Bulk Upload Assistant"


class AiError(Exception):
    """Galat pemanggilan AI yang aman ditampilkan ke pengguna (tanpa rahasia)."""


class AiQuotaExceeded(AiError):
    pass


@dataclass
class AiResult:
    content: str = ""
    tool_calls: list = field(default_factory=list)
    images: list = field(default_factory=list)       # data URL / base64 dari model gambar
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    model: str = ""                                    # model yang benar-benar dipakai
    provider: str = ""
    duration_ms: int = 0
    raw: dict = field(default_factory=dict)


class Provider(Protocol):
    def chat(self, **kw) -> AiResult: ...
    def list_models(self) -> list: ...
    def list_image_models(self) -> list: ...


def _sleep(s: float):  # dipisah supaya test bisa menggantinya
    time.sleep(s)


class OpenRouterProvider:
    def __init__(self, api_key: str, referer: str = APP_REFERER, title: str = APP_TITLE, base: str = OPENROUTER_BASE,
                 client: httpx.Client | None = None, sleep: Callable[[float], None] = _sleep, max_attempts: int = 4):
        self._key = api_key
        self._referer, self._title, self._base = referer, title, base
        self._http = client or httpx.Client(timeout=120)
        self._sleep = sleep
        self._max = max_attempts

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json",
                "HTTP-Referer": self._referer, "X-OpenRouter-Title": self._title}

    def _request(self, method: str, path: str, **kw) -> httpx.Response:
        """Backoff eksponensial + jitter untuk 429/5xx dan galat jaringan."""
        last = None
        for attempt in range(self._max):
            try:
                r = self._http.request(method, f"{self._base}{path}", headers=self._headers(), **kw)
            except (httpx.TimeoutException, httpx.TransportError) as e:
                last = f"koneksi: {type(e).__name__}"
            else:
                if r.status_code == 429 or r.status_code >= 500:
                    last = f"HTTP {r.status_code}"
                elif r.status_code == 401:
                    raise AiError("API key OpenRouter ditolak (401). Periksa key di Pengaturan AI.")
                elif r.status_code == 402:
                    raise AiError("Saldo OpenRouter tidak cukup (402).")
                elif r.status_code >= 400:
                    raise AiError(f"Permintaan ditolak OpenRouter (HTTP {r.status_code}): {_short(r)}")
                else:
                    return r
            if attempt < self._max - 1:
                self._sleep(min(30.0, (2 ** attempt) + random.uniform(0, 1)))
        raise AiError(f"OpenRouter tidak merespons dengan baik setelah {self._max} percobaan ({last}).")

    def chat(self, *, model: str, messages: list, fallbacks: list | None = None, response_format: dict | None = None,
             tools: list | None = None, tool_choice: Any = None, plugins: list | None = None,
             no_retention: bool = False, modalities: list | None = None, image_config: dict | None = None,
             max_tokens: int | None = None, temperature: float | None = 0.1) -> AiResult:
        body: dict = {"messages": messages, "usage": {"include": True}}
        if fallbacks:
            body["models"] = [model, *fallbacks]
        else:
            body["model"] = model
        provider: dict = {}
        if response_format or tools:
            provider["require_parameters"] = True      # hanya provider yang mendukung structured outputs/tools
        if no_retention:
            provider["data_collection"] = "deny"
        if provider:
            body["provider"] = provider
        if response_format:
            body["response_format"] = response_format
        if tools:
            body["tools"] = tools
            if tool_choice is not None:
                body["tool_choice"] = tool_choice
        if plugins:
            body["plugins"] = plugins
        if modalities:
            body["modalities"] = modalities
        if image_config:
            body["image_config"] = image_config
        if max_tokens:
            body["max_tokens"] = max_tokens
        if temperature is not None:
            body["temperature"] = temperature
        t0 = time.time()
        r = self._request("POST", "/chat/completions", json=body)
        data = r.json()
        if data.get("error"):
            raise AiError(f"Model gagal: {str(data['error'].get('message', data['error']))[:200]}")
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        u = data.get("usage") or {}
        imgs = []
        for im in msg.get("images") or []:
            url = (im.get("image_url") or {}).get("url") if isinstance(im, dict) else None
            if url:
                imgs.append(url)
        content = msg.get("content") or ""
        if isinstance(content, list):  # beberapa provider mengembalikan potongan
            content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
        return AiResult(
            content=content, tool_calls=msg.get("tool_calls") or [], images=imgs,
            prompt_tokens=int(u.get("prompt_tokens") or 0), completion_tokens=int(u.get("completion_tokens") or 0),
            cost_usd=float(u.get("cost") or 0.0), model=data.get("model") or model,
            provider=str(data.get("provider") or ""), duration_ms=int((time.time() - t0) * 1000), raw=data)

    def list_models(self) -> list:
        return self._request("GET", "/models").json().get("data", [])

    def list_image_models(self) -> list:
        return self._request("GET", "/images/models").json().get("data", [])


def _short(r: httpx.Response) -> str:
    try:
        j = r.json()
        return str(j.get("error", {}).get("message") or j)[:200]
    except Exception:  # noqa: BLE001
        return r.text[:200]


# --- pabrik provider (bisa diganti: test, atau penyedia lain nanti) ---
_factory: Callable[[str], Provider] = lambda key: OpenRouterProvider(key)  # noqa: E731


def make_provider(api_key: str) -> Provider:
    return _factory(api_key)


def set_provider_factory(fn: Callable[[str], Provider] | None):
    global _factory
    _factory = fn or (lambda key: OpenRouterProvider(key))


def json_schema_format(name: str, schema: dict) -> dict:
    return {"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": schema}}


def parse_json(text: str) -> Any:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t[t.find("\n") + 1:] if "\n" in t else t
        t = t.rsplit("```", 1)[0]
    return json.loads(t)
