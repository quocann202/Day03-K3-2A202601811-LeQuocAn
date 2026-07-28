"""Evaluate chatbot baseline against ReAct v1/v2 and write JSONL evidence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from chatbot import ask, create_provider
from src.agent.agent import ReActAgent
from src.tools.tools import get_default_tools


CASES = [
    {"id": "simple_qa", "prompt": "What is the capital of Vietnam?"},
    {"id": "purchase_success", "prompt": "I want to buy 2 iPhones using code WINNER and ship to Hanoi. What is the total price?"},
    {"id": "invalid_coupon", "prompt": "Buy 1 iPhone with coupon NOTREAL and ship to Hanoi. What is the total?"},
    {"id": "out_of_stock", "prompt": "Can I buy 1 MacBook Air and ship it to Hanoi?"},
]


def run() -> Path:
    load_dotenv()
    # A local GGUF model is large; load it once and reuse it sequentially.
    provider = create_provider()
    results = []
    for case in CASES:
        v1 = ReActAgent(provider, get_default_tools(), prompt_version="v1")
        v2 = ReActAgent(provider, get_default_tools(), prompt_version="v2")
        record = {"timestamp": datetime.now(timezone.utc).isoformat(), **case}
        for name, run_case in {
            "chatbot": lambda: ask(provider, case["prompt"]),
            "agent_v1": lambda: v1.run(case["prompt"]),
            "agent_v2": lambda: v2.run(case["prompt"]),
        }.items():
            try:
                record[name] = {"status": "success", "answer": run_case()}
            except Exception as error:
                record[name] = {"status": "error", "error": str(error)}
        results.append(record)

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    output = log_dir / f"evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    output.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in results) + "\n", encoding="utf-8")
    print(f"Saved evaluation evidence: {output}")
    return output


if __name__ == "__main__":
    run()
