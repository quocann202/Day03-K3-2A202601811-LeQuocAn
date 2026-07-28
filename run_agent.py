"""Run the Lab 3 ReAct agent with the provider selected in .env."""

import argparse

from dotenv import load_dotenv

from chatbot import create_provider
from src.agent.agent import ReActAgent
from src.tools.tools import get_tools


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", "-m", required=True)
    parser.add_argument("--max-steps", type=int, default=5)
    parser.add_argument("--version", choices=["v1", "v2"], default="v2", help="Prompt version for ablation.")
    args = parser.parse_args()
    load_dotenv()
    agent = ReActAgent(
        create_provider(),
        get_tools(args.version),
        max_steps=args.max_steps,
        prompt_version=args.version,
    )
    print(agent.run(args.message))


if __name__ == "__main__":
    main()
