"""
Sanitizer — JSON fence stripper + Pydantic validator.

Open-source LLMs (Llama, Mistral) often wrap JSON output in
markdown code fences like ```json ... ```. This module strips
those fences and validates the raw JSON before parsing.
"""

from __future__ import annotations

import re
import json
import logging

logger = logging.getLogger(__name__)

# Pattern matches:  ```json\n{...}\n```  or  ```\n{...}\n```
_FENCE_PATTERN = re.compile(
    r"^```(?:json)?\s*\n?(.*?)\n?\s*```$",
    re.DOTALL,
)

# Also catch cases where the model wraps in single backticks
_SINGLE_FENCE = re.compile(r"^`(.*)`$", re.DOTALL)


def sanitize_json(raw: str) -> str:
    """Strip markdown fences and extract clean JSON.
    
    Args:
        raw: Raw LLM output that may contain markdown-wrapped JSON.
        
    Returns:
        Clean JSON string.
        
    Raises:
        ValueError: If the cleaned string isn't valid JSON.
    """
    cleaned = raw.strip()
    
    # Strip triple-backtick fences
    match = _FENCE_PATTERN.match(cleaned)
    if match:
        cleaned = match.group(1).strip()
    
    # Strip single-backtick wrapping
    match = _SINGLE_FENCE.match(cleaned)
    if match:
        cleaned = match.group(1).strip()
    
    # Remove any leading/trailing whitespace or newlines
    cleaned = cleaned.strip()
    
    # Handle cases where model outputs explanation before JSON
    # Look for the first { and last }
    if not cleaned.startswith("{"):
        brace_start = cleaned.find("{")
        if brace_start != -1:
            brace_end = cleaned.rfind("}")
            if brace_end != -1:
                cleaned = cleaned[brace_start : brace_end + 1]
                logger.debug("Extracted JSON from mixed output")
    
    # Validate it's parseable
    try:
        json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"JSON sanitization failed: {e}\nRaw: {raw[:200]}")
        raise ValueError(f"Cannot parse LLM output as JSON: {e}") from e
    
    return cleaned
