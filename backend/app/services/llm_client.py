import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class GeminiClient:
    """
    Resilient Google Gemini LLM Client with quota enforcement,
    in-memory response caching, rate limiting, and structured JSON parsing.
    """
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else ""
        self.model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"
        self._client = None
        self._cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}  # cache_key -> (timestamp, data)
        self._cache_ttl = 3600.0  # 1 hour
        self._call_timestamps: List[float] = []
        self._daily_calls_count = 0
        self._current_day_utc = datetime.now(timezone.utc).date()
        self._daily_limit = 1500  # Conservative limit for free-tier protection
        self._rate_limit_per_minute = 15

        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info(f"GeminiClient initialized with model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize google.genai Client: {e}")
                self._client = None

    @property
    def is_configured(self) -> bool:
        return bool(self._client and self.api_key)

    def _check_and_update_quota(self) -> bool:
        """Enforces daily call budget and per-minute rate limit."""
        now = time.time()
        today = datetime.now(timezone.utc).date()

        # Reset daily counter on UTC date change
        if today != self._current_day_utc:
            self._current_day_utc = today
            self._daily_calls_count = 0

        # Check daily ceiling
        if self._daily_calls_count >= self._daily_limit:
            logger.warning(f"Gemini daily quota exceeded ({self._daily_calls_count}/{self._daily_limit})")
            return False

        # Check per-minute rate limit
        one_min_ago = now - 60.0
        self._call_timestamps = [ts for ts in self._call_timestamps if ts > one_min_ago]
        if len(self._call_timestamps) >= self._rate_limit_per_minute:
            logger.warning(f"Gemini per-minute rate limit reached ({len(self._call_timestamps)}/min)")
            return False

        self._call_timestamps.append(now)
        self._daily_calls_count += 1
        return True

    def get_quota_status(self) -> Dict[str, Any]:
        today = datetime.now(timezone.utc).date()
        if today != self._current_day_utc:
            self._current_day_utc = today
            self._daily_calls_count = 0

        status = "active" if self.is_configured else "unconfigured"
        if self._daily_calls_count >= self._daily_limit:
            status = "daily_quota_exceeded"

        return {
            "gemini_configured": self.is_configured,
            "model_name": self.model_name,
            "total_calls_today": self._daily_calls_count,
            "daily_limit": self._daily_limit,
            "status": status,
        }

    def generate_json(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.2,
    ) -> Optional[Dict[str, Any]]:
        """
        Sends prompt to Gemini model requesting JSON response.
        Returns parsed dictionary or None if unavailable/failed.
        """
        if not self.is_configured:
            return None

        # Check cache
        cache_key = f"{system_instruction}::{prompt}"
        now = time.time()
        if cache_key in self._cache:
            ts, cached_data = self._cache[cache_key]
            if now - ts < self._cache_ttl:
                return cached_data

        if not self._check_and_update_quota():
            return None

        try:
            from google.genai import types

            full_prompt = prompt
            if system_instruction:
                full_prompt = f"System Instruction: {system_instruction}\n\nTask:\n{prompt}"

            config = types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type="application/json",
            )

            # Generate with model
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config=config,
            )

            if not response or not response.text:
                return None

            raw_text = response.text.strip()
            # Handle markdown code block wrappers if any
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]

            parsed = json.loads(raw_text.strip())
            # Cache valid response
            self._cache[cache_key] = (now, parsed)
            return parsed

        except Exception as e:
            logger.error(f"Error during Gemini generation: {e}")
            return None

gemini_client = GeminiClient()
