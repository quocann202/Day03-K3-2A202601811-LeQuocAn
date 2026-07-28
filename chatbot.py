"""Command-line baseline chatbot for Lab 3.

This baseline deliberately has no tools and no ReAct loop.  It is the control
case used later to compare ordinary LLM chat with the ReAct agent.
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from src.telemetry.metrics import tracker


SYSTEM_PROMPT = (
    "You are a helpful e-commerce assistant. Answer clearly and honestly. "
    "You cannot check live stock, coupon discounts, shipping fees, or prices. "
    "If a question requires those facts, say that tools would be needed."
)


def create_provider():
    """Create the provider selected by DEFAULT_PROVIDER in .env."""
    provider_name = os.getenv("DEFAULT_PROVIDER", "openai").lower()
    model_name = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")

    if provider_name == "openai":
        # Import lazily: users selecting OpenAI should not need optional
        # Gemini or llama-cpp packages installed.
        from src.core.openai_provider import OpenAIProvider

        return OpenAIProvider(model_name, os.getenv("OPENAI_API_KEY"))
    if provider_name in {"google", "gemini"}:
        from src.core.gemini_provider import GeminiProvider

        gemini_model = os.getenv("GEMINI_MODEL", model_name)
        return GeminiProvider(gemini_model, os.getenv("GEMINI_API_KEY"))
    if provider_name == "local":
        from src.core.local_provider import LocalProvider

        return LocalProvider(os.getenv("LOCAL_MODEL_PATH", ""))
    raise ValueError("DEFAULT_PROVIDER must be openai, google, gemini, or local.")


def ask(provider, question: str) -> str:
    result = provider.generate(question, system_prompt=SYSTEM_PROMPT)
    tracker.track_request(
        provider=result["provider"],
        model=provider.model_name,
        usage=result["usage"],
        latency_ms=result["latency_ms"],
    )
    return result["content"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Lab 3 chatbot baseline.")
    parser.add_argument("--message", "-m", help="Ask one question and exit.")
    args = parser.parse_args()

    load_dotenv()
    try:
        provider = create_provider()
    except Exception as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        return 2

    if args.message:
        try:
            print(ask(provider, args.message))
            return 0
        except Exception as error:
            print(f"Chatbot error: {error}", file=sys.stderr)
            return 1

    print("Chatbot baseline ready. Type 'exit' to quit.")
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if question.lower() in {"exit", "quit"}:
            return 0
        if question:
            try:
                print(f"Bot: {ask(provider, question)}")
            except Exception as error:
                print(f"Chatbot error: {error}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
