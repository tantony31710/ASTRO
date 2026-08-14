"""
Model Weight Loading & Inference (Phase 3).

Environment setup:
  A `.env` file in my-large-data-vault/ (or the repo root) is loaded
  automatically if python-dotenv is installed, so you never have to set
  env vars by hand each session. Commit a commented `.env.example` and
  keep `.env` in .gitignore.

Routing priority:
  1. Anthropic API, if ANTHROPIC_API_KEY is set.
  2. OpenAI API, if OPENAI_API_KEY is set.
  3. Local Llama-3 inference, if JARVIS_LLM_BACKEND=local and the model
     path resolves. Uses llama-cpp-python (CPU-native, no GPU needed),
     which only reads GGUF quantized weights. A loader branch for the
     raw .safetensors/.pt weights in 00_raw_data/model_weights follows
     once a GGUF copy exists — the raw files are loaded by
     transformers-style loaders that are heavy and model-family-
     specific, so they stay out of the default dependency set.
  4. If nothing is configured, says so plainly.

Both SDKs are imported lazily so the vault doesn't hard-require any of
them — only whichever env var is actually set needs the matching
package installed.
"""
import os
from pathlib import Path

# .env loading — no-op if python-dotenv isn't installed; values flow
# straight into os.environ so nothing else in the vault changes.
try:
    from dotenv import load_dotenv

    load_dotenv()
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except ImportError:
    pass

from src.pipelines.train_model import list_model_weights

SYSTEM_PROMPT = (
    "You are JARVIS, a local assistant for a personal data vault. "
    "Be concise — responses may be spoken aloud."
)

# Environment-controlled knobs for the local backend.
# Read fresh on every call so a changed .env / env var takes effect
# without restarting the process.
LOCAL_BACKEND = ""        # JARVIS_LLM_BACKEND — "local" enables local inference
LOCAL_MODEL_PATH = ""     # JARVIS_LOCAL_MODEL — path to a Llama-3 GGUF file


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


def _call_local_llama3(prompt: str, model_path: str) -> str:
    """
    Real local inference for a Llama-3 GGUF model via llama-cpp-python.
    CPU-native — no GPU, no CUDA toolchain needed. Kept behind
    JARVIS_LLM_BACKEND=local so the default dependency set stays light.
    """
    import llama_cpp

    llm = llama_cpp.Llama(
        model_path=model_path,
        n_ctx=2048,
        n_threads=max(1, (os.cpu_count() or 2) - 1),
        verbose=False,
    )
    response = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=512,
        temperature=0.3,
    )
    return response["choices"][0]["message"]["content"].strip()


def _local_fallback_message() -> str:
    weights = list_model_weights()
    # If the local backend is actively configured, lead with the actionable
    # local-backend hint regardless of what's in the weights folder — the
    # user asked for local inference, so tell them exactly what's missing.
    if LOCAL_BACKEND == "local":
        if not LOCAL_MODEL_PATH or not Path(LOCAL_MODEL_PATH).is_file():
            return (
                "JARVIS_LLM_BACKEND=local is set but JARVIS_LOCAL_MODEL does "
                "not point at an existing .gguf file."
            )
        return (
            f"Local backend is configured ({LOCAL_MODEL_PATH}) but "
            "'llama-cpp-python' isn't installed (pip install llama-cpp-python)."
        )
    if not weights:
        return (
            "No API key is configured and no local model weights were found. "
            "Set ANTHROPIC_API_KEY or OPENAI_API_KEY, or add weights to "
            "00_raw_data/model_weights."
        )
    names = ", ".join(w["name"] for w in weights)
    if LOCAL_BACKEND == "local" or any(w["extension"] == ".gguf" for w in weights):
        return (
            f"No API key is configured. Local Llama-3 weights are present "
            f"({names}) — set JARVIS_LLM_BACKEND=local and "
            f"JARVIS_LOCAL_MODEL=<path-to-gguf> in .env to enable real local "
            "inference, then `pip install llama-cpp-python`."
        )
    return (
        f"No API key is configured. Local weights are present ({names}) but "
        "local inference isn't wired up yet — that needs a model-specific "
        "loader (e.g. transformers or llama.cpp) which depends on which "
        "model these weights are."
    )


def ask_llm(prompt: str) -> str:
    """Routes a prompt to whichever backend is available. Never raises — always returns text."""
    global LOCAL_BACKEND, LOCAL_MODEL_PATH

    # Re-read config on every call so `.env` edits take effect live.
    LOCAL_BACKEND = os.environ.get("JARVIS_LLM_BACKEND", "")
    LOCAL_MODEL_PATH = os.environ.get("JARVIS_LOCAL_MODEL", "")

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

    if LOCAL_BACKEND == "local":
        if not LOCAL_MODEL_PATH:
            return _local_fallback_message()
        if not Path(LOCAL_MODEL_PATH).is_file():
            return _local_fallback_message()
        try:
            return _call_local_llama3(prompt, LOCAL_MODEL_PATH)
        except ImportError:
            return "JARVIS_LLM_BACKEND=local but 'llama-cpp-python' isn't installed (pip install llama-cpp-python)."
        except Exception as e:
            return f"Local Llama-3 inference failed: {e}"

    return _local_fallback_message()
