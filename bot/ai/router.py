"""
AI Router — Two-client multi-provider router with automatic failover.

Client 1: google-genai (Gemini) — primary with native structured output
Client 2: AsyncOpenAI — fallback chain (Groq → Cerebras → OpenRouter)
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from google import genai
from google.genai import types as genai_types
from openai import AsyncOpenAI, RateLimitError, APIError, APITimeoutError

from bot.ai.intents import MusicIntent, INTENT_SYSTEM_PROMPT, BANTER_SYSTEM_PROMPT, get_intent_schema
from bot.ai.sanitizer import sanitize_json
from bot.utils.rate_limiter import RateLimiter
from bot.utils.truncator import build_messages

logger = logging.getLogger(__name__)


class AllProvidersExhausted(Exception):
    """Raised when all LLM providers have failed."""
    pass


class AIRouter:
    """Two-client multi-provider router with automatic failover.
    
    Uses Gemini as the primary engine with native JSON schema enforcement,
    then falls back through Groq → Cerebras → OpenRouter via a single
    AsyncOpenAI client with dynamic base_url swapping.
    """

    def __init__(self, settings):
        # Client 1: Gemini (primary)
        self.gemini = genai.Client(api_key=settings.gemini_api_key)
        self.gemini_model = settings.gemini_model
        
        # Client 2: OpenAI-compatible (fallback chain)
        self.fallback_chain = [
            {
                "name": "groq",
                "base_url": "https://api.groq.com/openai/v1",
                "key": settings.groq_api_key,
                "model": "llama-3.3-70b-versatile",
            },
            {
                "name": "cerebras",
                "base_url": "https://api.cerebras.ai/v1",
                "key": settings.cerebras_api_key,
                "model": "gpt-oss-120b",
            },
            {
                "name": "openrouter",
                "base_url": "https://openrouter.ai/api/v1",
                "key": settings.openrouter_api_key,
                "model": "meta-llama/llama-3.3-70b-instruct:free",
            },
        ]
        
        self.rate_limiter = RateLimiter()

    # ── Intent Parsing ──

    async def parse_intent(self, user_message: str) -> MusicIntent:
        """Parse user message into a structured MusicIntent.
        
        Tries Gemini first (native JSON schema), then falls back
        through the OpenAI-compatible chain.
        
        Args:
            user_message: Raw text from the user.
            
        Returns:
            Parsed MusicIntent object.
            
        Raises:
            AllProvidersExhausted: If all providers fail.
        """
        # Attempt 1: Gemini (native structured output)
        if not self.rate_limiter.is_blocked("gemini"):
            try:
                result = await self._gemini_structured(user_message)
                self.rate_limiter.reset("gemini")
                return result
            except Exception as e:
                logger.warning(f"Gemini intent parsing failed: {e}")
                if "429" in str(e) or "quota" in str(e).lower():
                    self.rate_limiter.block("gemini", seconds=60)

        # Attempt 2-4: Fallback chain via AsyncOpenAI
        for provider in self.fallback_chain:
            if self.rate_limiter.is_blocked(provider["name"]):
                continue
            try:
                result = await self._openai_intent(provider, user_message)
                self.rate_limiter.reset(provider["name"])
                return result
            except RateLimitError:
                self.rate_limiter.block(provider["name"], seconds=60)
                logger.warning(f"{provider['name']} rate limited")
            except (APIError, APITimeoutError) as e:
                logger.warning(f"{provider['name']} API error: {e}")
            except Exception as e:
                logger.warning(f"{provider['name']} unexpected error: {e}")

        raise AllProvidersExhausted("All LLM providers failed for intent parsing")

    async def _gemini_structured(self, user_message: str) -> MusicIntent:
        """Use Gemini's native structured output for intent parsing."""
        response = await self.gemini.aio.models.generate_content(
            model=self.gemini_model,
            contents=user_message,
            config=genai_types.GenerateContentConfig(
                system_instruction=INTENT_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=MusicIntent,
                temperature=0.1,
            ),
        )
        raw = response.text
        logger.debug(f"Gemini raw intent: {raw}")
        return MusicIntent.model_validate_json(raw)

    async def _openai_intent(
        self, provider: dict, user_message: str
    ) -> MusicIntent:
        """Use an OpenAI-compatible provider for intent parsing."""
        client = AsyncOpenAI(
            base_url=provider["base_url"],
            api_key=provider["key"],
        )
        
        messages = build_messages(
            user_text=user_message,
            system_prompt=INTENT_SYSTEM_PROMPT,
            max_tokens=6000,
        )

        response = await client.chat.completions.create(
            model=provider["model"],
            messages=messages,
            temperature=0.1,
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        logger.debug(f"{provider['name']} raw intent: {raw}")
        cleaned = sanitize_json(raw)
        return MusicIntent.model_validate_json(cleaned)

    # ── Conversational Banter ──

    async def chat(self, user_message: str) -> str:
        """Generate a conversational response (non-music queries).
        
        Uses Gemini first, falls back through chain for personality responses.
        """
        # Try Gemini first
        if not self.rate_limiter.is_blocked("gemini"):
            try:
                response = await self.gemini.aio.models.generate_content(
                    model=self.gemini_model,
                    contents=user_message,
                    config=genai_types.GenerateContentConfig(
                        system_instruction=BANTER_SYSTEM_PROMPT,
                        temperature=0.8,
                        max_output_tokens=300,
                    ),
                )
                self.rate_limiter.reset("gemini")
                return response.text
            except Exception as e:
                logger.warning(f"Gemini chat failed: {e}")
                if "429" in str(e) or "quota" in str(e).lower():
                    self.rate_limiter.block("gemini", seconds=60)

        # Fallback chain
        for provider in self.fallback_chain:
            if self.rate_limiter.is_blocked(provider["name"]):
                continue
            try:
                client = AsyncOpenAI(
                    base_url=provider["base_url"],
                    api_key=provider["key"],
                )
                messages = build_messages(
                    user_text=user_message,
                    system_prompt=BANTER_SYSTEM_PROMPT,
                    max_tokens=6000,
                )
                response = await client.chat.completions.create(
                    model=provider["model"],
                    messages=messages,
                    temperature=0.8,
                    max_tokens=300,
                )
                self.rate_limiter.reset(provider["name"])
                return response.choices[0].message.content
            except RateLimitError:
                self.rate_limiter.block(provider["name"], seconds=60)
            except Exception as e:
                logger.warning(f"{provider['name']} chat failed: {e}")

        return "🐍 All my brain cells are napping right now. Try again in a minute!"

    def get_provider_status(self) -> dict[str, str]:
        """Get the current status of all providers."""
        blocked = self.rate_limiter.status()
        providers = ["gemini", "groq", "cerebras", "openrouter"]
        return {
            p: blocked.get(p, "✅ ok")
            for p in providers
        }
