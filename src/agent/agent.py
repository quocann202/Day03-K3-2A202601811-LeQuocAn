import json
import re
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker

class ReActAgent:
    """
    SKELETON: A ReAct-style Agent that follows the Thought-Action-Observation loop.
    Students should implement the core loop logic and tool execution.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5, prompt_version: str = "v2"):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.prompt_version = prompt_version
        self.history = []

    def get_system_prompt(self) -> str:
        """
        ReAct v2 prompt. The strict JSON action avoids ambiguous regex-only
        parsing and tells the model exactly when enough evidence is available.
        """
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        if self.prompt_version == "v1":
            return f"""You are an e-commerce assistant with tools:
{tool_descriptions}

Use this format:
Thought: reason briefly
Action: {{"tool": "tool_name", "args": {{}}}}
Final Answer: answer for the user
"""
        return f"""You are a careful e-commerce ReAct agent.
Available tools:
{tool_descriptions}

On every turn, choose exactly one of these formats and output no Markdown fence:
Thought: short reason for the next step
Action: {{"tool": "tool_name", "args": {{"argument": "value"}}}}

OR, only when observations contain all needed facts:
Final Answer: concise answer with calculation and VND amounts.

Rules:
1. Never invent stock, prices, discounts, weights, shipping costs, or tool results.
2. Return exactly ONE Action per response, then stop. Never include a future
   Action, placeholder such as `total_vnd`, or Final Answer in an Action response.
3. Before a purchase total, call check_stock. Check stock is enough for quantity.
4. If a coupon is supplied, call get_discount. For shipping, calculate total
   weight (quantity times weight_kg) before calling calc_shipping.
5. Before reporting a purchase total, call calculate_order_total using only
   values returned by prior observations plus the requested quantity.
6. If a tool observation says ok=false, explain the failure in Final Answer.
7. Do not repeat the same tool call with identical arguments.
"""

    def run(self, user_input: str) -> str:
        """
        Execute Thought -> Action -> Observation until final output or the
        bounded max_steps guard triggers.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        current_prompt = f"User request: {user_input}"
        steps = 0
        seen_actions = set()

        while steps < self.max_steps:
            result = self.llm.generate(current_prompt, system_prompt=self.get_system_prompt())
            content = result["content"].strip()
            tracker.track_request(result["provider"], self.llm.model_name, result["usage"], result["latency_ms"])
            logger.log_event("AGENT_STEP", {"step": steps + 1, "llm_output": content})

            action = self._parse_action(content)
            final_answer = self._extract_final_answer(content)
            # Some smaller local models emit a plan containing several future
            # actions and a placeholder Final Answer at once. A final response
            # is valid only when it contains no Action at all.
            if final_answer is not None and action is None and "action:" not in content.lower():
                logger.log_event("AGENT_END", {"steps": steps + 1, "status": "success"})
                return final_answer

            if action is None:
                observation = {"ok": False, "error": "Parser error: expected Action JSON or Final Answer."}
            else:
                tool_name, arguments = action
                action_key = (tool_name, json.dumps(arguments, sort_keys=True, ensure_ascii=False))
                if action_key in seen_actions:
                    observation = {"ok": False, "error": "Repeated identical action blocked."}
                else:
                    seen_actions.add(action_key)
                    observation = self._execute_tool(tool_name, arguments)

            steps += 1
            observation_text = json.dumps(observation, ensure_ascii=False)
            logger.log_event("TOOL_OBSERVATION", {"step": steps, "observation": observation})
            current_prompt += f"\n\nAssistant response:\n{content}\nObservation: {observation_text}\nContinue."
        logger.log_event("AGENT_END", {"steps": steps, "status": "max_steps"})
        return "I could not complete the request within the safety limit of tool calls."

    @staticmethod
    def _extract_final_answer(content: str) -> Optional[str]:
        match = re.search(r"Final\s*Answer\s*:\s*(.+)", content, flags=re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else None

    @staticmethod
    def _parse_action(content: str) -> Optional[tuple[str, Dict[str, Any]]]:
        """Extract and parse the first Action JSON object without greedy regex."""
        match = re.search(r"Action\s*:\s*", content, re.IGNORECASE)
        if not match:
            return None
        remainder = content[match.end():].lstrip()
        if remainder.startswith("```"):
            remainder = remainder.split("\n", 1)[-1].lstrip()
        object_start = remainder.find("{")
        if object_start < 0:
            return None
        raw_json = ReActAgent._first_json_object(remainder[object_start:])
        if raw_json is None:
            return None
        try:
            payload = json.loads(raw_json)
        except (TypeError, json.JSONDecodeError):
            return None
        tool = payload.get("tool")
        args = payload.get("args")
        if not isinstance(tool, str) or not isinstance(args, dict):
            return None
        return tool, args

    @staticmethod
    def _first_json_object(text: str) -> Optional[str]:
        """Return one balanced JSON object while respecting quoted strings."""
        depth = 0
        in_string = False
        escaped = False
        for index, char in enumerate(text):
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[: index + 1]
        return None

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Helper method to execute tools by name.
        """
        for tool in self.tools:
            if tool['name'] == tool_name:
                missing = [key for key in tool.get("required_args", []) if key not in args]
                if missing:
                    return {"ok": False, "error": f"Missing required arguments: {', '.join(missing)}."}
                try:
                    return tool["function"](**args)
                except (TypeError, ValueError) as error:
                    return {"ok": False, "error": f"Invalid arguments for {tool_name}: {error}"}
        return {"ok": False, "error": f"Tool '{tool_name}' was not found."}
