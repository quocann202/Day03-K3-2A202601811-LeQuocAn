from src.agent.agent import ReActAgent
from src.tools.tools import get_default_tools


class ScriptedProvider:
    """Offline LLM double: proves the agent loop without an API/model."""
    model_name = "scripted-test-model"

    def __init__(self, responses):
        self.responses = iter(responses)

    def generate(self, prompt, system_prompt=None):
        return {
            "content": next(self.responses),
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            "latency_ms": 1,
            "provider": "test",
        }


def test_react_uses_observations_then_returns_answer():
    provider = ScriptedProvider([
        'Thought: Need the product facts.\nAction: {"tool":"check_stock","args":{"item_name":"iPhone"}}',
        'Thought: I have evidence.\nFinal Answer: iPhone is in stock.',
    ])
    agent = ReActAgent(provider, get_default_tools())
    assert agent.run("Check iPhone") == "iPhone is in stock."


def test_react_rejects_missing_argument():
    provider = ScriptedProvider([
        'Thought: Ship it.\nAction: {"tool":"calc_shipping","args":{"destination":"Hanoi"}}',
        'Final Answer: I need a weight before calculating shipping.',
    ])
    agent = ReActAgent(provider, get_default_tools())
    assert "need a weight" in agent.run("Ship it")


def test_react_does_not_accept_final_answer_when_action_is_present():
    provider = ScriptedProvider([
        'Thought: Plan everything.\nAction: {"tool":"check_stock","args":{"item_name":"iPhone"}}\n'
        'Action: {"tool":"get_discount","args":{"coupon_code":"WINNER"}}\n'
        'Final Answer: {total_vnd}',
        'Final Answer: Stock was checked before giving this answer.',
    ])
    agent = ReActAgent(provider, get_default_tools())
    assert agent.run("Check iPhone") == "Stock was checked before giving this answer."
