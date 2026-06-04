"""
Truncator — Token-aware message truncation for context window safety.

Gemini supports 1M+ tokens, but Llama models on Groq/Cerebras cap at 8K.
This module ensures messages fit within provider context limits.
"""

from __future__ import annotations


# Rough estimate: 1 token ≈ 4 chars for English text
CHARS_PER_TOKEN = 4


def truncate_for_provider(
    text: str,
    max_tokens: int = 6000,
) -> str:
    """Truncate text to fit within token limits.
    
    Keeps the most recent context (tail of the string) when truncating.
    """
    max_chars = max_tokens * CHARS_PER_TOKEN
    if len(text) > max_chars:
        text = text[-max_chars:]
    return text


def build_messages(
    user_text: str,
    system_prompt: str,
    max_tokens: int = 6000,
) -> list[dict[str, str]]:
    """Build OpenAI-compatible message list with truncation.
    
    Reserves tokens for the system prompt, truncates user text to fit.
    """
    # Reserve ~500 tokens for system prompt
    system_tokens = len(system_prompt) // CHARS_PER_TOKEN
    user_max = max(max_tokens - system_tokens - 200, 1000)
    
    truncated = truncate_for_provider(user_text, max_tokens=user_max)
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": truncated},
    ]
