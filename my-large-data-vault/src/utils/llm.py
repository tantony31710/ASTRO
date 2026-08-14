"""
Model Weight Loading & Inference (Phase 3).

Routing priority:
  1. Anthropic API, if ANTHROPIC_API_KEY is set.
  2. OpenAI API, if OPENAI_API_KEY is set.
  3. Local weights fallback — reports what's available in
     00_raw_data/model_weights, but does NOT attempt to run inference,
     because a .safetensors/.pt file alone doesn't tell us the model
     architecture or how to load it. Wiring that up (e.g. via
     transformers/llama.cpp) is a real follow-on step once you tell me
     which model family lives in that folder — faking it here would
     silently give you wrong or garbage responses.
  4. If nothing is configured at all, says so plainly.

Both SDKs are imported lazily so the vault doesn't hard-require either
one — only whichever env var is actually set needs the matching package
installed.
"""
import os
from src.pipelines.train_model import list_model_weights

SYSTEM_PROMPT = (
    "You are JARVIS, a local assistant for a personal data vault. "
    "Be concise — responses may be spoken aloud."
)


def _call_anthropic(prompt: str, api_key: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text").strip()


def _call_openai(prompt: str, api_key: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content.strip()


def _local_fallback_message() -> str:
    weights = list_model_weights()
    if not weights:
        return (
            "No API key is configured and no local model weights were found. "
            "Set ANTHROPIC_API_KEY or OPENAI_API_KEY, or add weights to "
            "00_raw_data/model_weights."
        )
    names = ", ".join(w["name"] for w in weights)
    return (
        f"No API key is configured. Local weights are present ({names}) but "
        "local inference isn't wired up yet — that needs a model-specific "
        "loader (e.g. transformers or llama.cpp) which depends on which "
        "model these weights are."
    )


def ask_llm(prompt: str) -> str:
    """Routes a prompt to whichever backend is available. Never raises — always returns text."""
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if anthropic_key:
        try:
            return _call_anthropic(prompt, anthropic_key)
        except ImportError:
            return "ANTHROPIC_API_KEY is set but the 'anthropic' package isn't installed (pip install anthropic)."
        except Exception as e:
            return f"Anthropic API call failed: {e}"

    if openai_key:
        try:
            return _call_openai(prompt, openai_key)
        except ImportError:
            return "OPENAI_API_KEY is set but the 'openai' package isn't installed (pip install openai)."
        except Exception as e:
            return f"OpenAI API call failed: {e}"

    return _local_fallback_message()
