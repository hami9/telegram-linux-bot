from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from bot.i18n import language_name

logger = logging.getLogger(__name__)

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
REQUEST_TIMEOUT = 45
MAX_OUTPUT_TOKENS = 900
RETRY_STATUSES = {429, 500, 502, 503, 504}

PERSONA = (
    "You are the AI core of a Telegram group management bot styled as a Linux terminal. "
    "Answer with a witty but genuinely helpful technical tone. "
    "Keep answers under 250 words, plain text without markdown headings, and never invent Telegram admin actions you cannot perform. "
    "Write the whole answer in {language}."
)


class GeminiError(Exception):
    pass


class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        self.api_key = api_key
        self.model = model
        self._session: aiohttp.ClientSession | None = None
        self._lock = asyncio.Lock()

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def _get_session(self) -> aiohttp.ClientSession:
        async with self._lock:
            if self._session is None or self._session.closed:
                timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                self._session = aiohttp.ClientSession(timeout=timeout)
            return self._session

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    def _payload(self, prompt: str, lang: str, history: list[dict[str, str]] | None) -> dict[str, Any]:
        contents: list[dict[str, Any]] = []
        for item in history or []:
            contents.append({"role": item.get("role", "user"), "parts": [{"text": item.get("text", "")}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        return {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": PERSONA.format(language=language_name(lang))}]},
            "generationConfig": {
                "temperature": 0.8,
                "maxOutputTokens": MAX_OUTPUT_TOKENS,
            },
        }

    @staticmethod
    def _extract(data: dict[str, Any]) -> str:
        candidates = data.get("candidates") or []
        for candidate in candidates:
            parts = (candidate.get("content") or {}).get("parts") or []
            text = "".join(part.get("text", "") for part in parts).strip()
            if text:
                return text
        feedback = data.get("promptFeedback") or {}
        if feedback.get("blockReason"):
            raise GeminiError(f"blocked: {feedback['blockReason']}")
        raise GeminiError("empty response")

    async def ask(self, prompt: str, lang: str = "en", history: list[dict[str, str]] | None = None) -> str:
        if not self.configured:
            raise GeminiError("missing api key")

        session = await self._get_session()
        url = f"{API_ROOT}/{self.model}:generateContent"
        payload = self._payload(prompt, lang, history)
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status in RETRY_STATUSES:
                        last_error = GeminiError(f"http {response.status}")
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue
                    if response.status != 200:
                        body = await response.text()
                        raise GeminiError(f"http {response.status}: {body[:200]}")
                    return self._extract(await response.json())
            except (aiohttp.ClientError, asyncio.TimeoutError) as error:
                last_error = error
                await asyncio.sleep(1.5 * (attempt + 1))
        raise GeminiError(str(last_error or "request failed"))
