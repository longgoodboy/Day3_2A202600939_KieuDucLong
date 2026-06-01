import json
import re
from typing import Any, Dict, List, Optional, Tuple

from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker

class ReActAgent:
    """
    A simple ReAct-style Agent that follows the Thought-Action-Observation loop.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 8):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []
        self.tool_map = {tool["name"]: tool["function"] for tool in tools}

    def get_system_prompt(self) -> str:
        """Return the system prompt with available tools and ReAct format."""
        tool_descriptions = "\n".join(
            [
                (
                    f"- {tool['name']}: {tool['description']}\n"
                    f"  input_schema: {json.dumps(tool.get('input_schema', {}))}"
                )
                for tool in self.tools
            ]
        )
        return f"""
You are an e-commerce assistant. Use tools when product, stock, coupon,
shipping, or order-total facts are needed. Do not invent catalog data.

Available tools:
{tool_descriptions}

Use exactly this format:
Thought: your line of reasoning.
Action: tool_name({{"arg": "value"}})
Observation: result of the tool call.
... repeat Thought/Action/Observation as needed.
Final Answer: your final response to the user.

Rules:
- Emit only one Action at a time.
- Stop immediately after the Action line.
- Never write Observation yourself; the runtime will provide it.
- Do not write Final Answer until you have received the needed Observations.
- Keep each response short.
- For shipping multiple units, use total_weight = unit weight * quantity.
"""

    def run(self, user_input: str) -> str:
        """
        Run the ReAct loop until the model emits Final Answer or max_steps is hit.
        """
        logger.log_event(
            "AGENT_START",
            {
                "input": user_input,
                "provider": getattr(self.llm, "provider_name", None),
                "model": self.llm.model_name,
                "max_steps": self.max_steps,
            },
        )
        
        current_prompt = f"User: {user_input}\n"

        for step in range(1, self.max_steps + 1):
            result = self.llm.generate(
                current_prompt,
                system_prompt=self.get_system_prompt(),
            )
            self._track_llm_metric(result)
            content = str(result.get("content", ""))
            self.history.append({"step": step, "llm_output": content})

            logger.log_event(
                "AGENT_STEP",
                {
                    "step": step,
                    "provider": result.get("provider", "unknown"),
                    "model": result.get("model", self.llm.model_name),
                    "output": content,
                },
            )

            actions = self._parse_actions(content)
            if actions:
                observations = []
                for tool_name, args in actions:
                    logger.log_event(
                        "TOOL_CALL",
                        {"step": step, "tool_name": tool_name, "arguments": args},
                    )
                    result_observation = self._execute_tool(tool_name, args)
                    logger.log_event(
                        "TOOL_RESULT",
                        {
                            "step": step,
                            "tool_name": tool_name,
                            "status": result_observation.get("status"),
                            "result": result_observation,
                        },
                    )
                    observations.append(
                        {
                            "tool_name": tool_name,
                            "arguments": args,
                            "result": result_observation,
                        }
                    )

                observation = {
                    "status": "success",
                    "data": {"observations": observations},
                    "error": None,
                }
                assistant_history = self._format_actions_for_history(actions)
            else:
                final_answer = self._extract_final_answer(content)
                if final_answer is not None:
                    logger.log_event(
                        "FINAL_ANSWER",
                        {"step": step, "answer": final_answer},
                    )
                    logger.log_event(
                        "AGENT_END",
                        {"steps": step, "termination_reason": "final_answer"},
                    )
                    return final_answer

                observation = {
                    "status": "error",
                    "data": None,
                    "error": {
                        "code": "PARSER_ERROR",
                        "message": "Expected Action: tool_name({...}) or Final Answer.",
                    },
                }
                logger.log_event(
                    "PARSER_ERROR",
                    {"step": step, "output": content, "observation": observation},
                )
                assistant_history = content

            observation_text = json.dumps(observation, ensure_ascii=False)
            current_prompt += (
                f"Assistant: {assistant_history}\n"
                f"Observation: {observation_text}\n"
            )
            
        logger.log_event(
            "MAX_STEPS_EXCEEDED",
            {"max_steps": self.max_steps, "input": user_input},
        )
        logger.log_event(
            "AGENT_END",
            {"steps": self.max_steps, "termination_reason": "max_steps_exceeded"},
        )
        return "I could not complete the request within the allowed steps."

    def _parse_action(self, content: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Parse Action: tool_name({...}) from the model output."""
        actions = self._parse_actions(content)
        if not actions:
            return None
        return actions[0]

    def _parse_actions(self, content: str) -> List[Tuple[str, Dict[str, Any]]]:
        """Parse all Action: tool_name({...}) occurrences from the model output."""
        actions = []
        for match in re.finditer(
            r"Action:\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*(\{.*?\})\s*\)",
            content,
            flags=re.DOTALL,
        ):
            tool_name = match.group(1)
            raw_args = match.group(2)
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                continue
            if isinstance(args, dict):
                actions.append((tool_name, args))
        return actions

    def _extract_final_answer(self, content: str) -> Optional[str]:
        """Return text after Final Answer if present."""
        match = re.search(r"Final Answer:\s*(.*)", content, flags=re.DOTALL)
        if match is None:
            return None
        return match.group(1).strip()

    def _format_actions_for_history(self, actions: List[Tuple[str, Dict[str, Any]]]) -> str:
        """Keep history grounded by excluding model-written observations."""
        lines = []
        for tool_name, args in actions:
            args_text = json.dumps(args, ensure_ascii=False)
            lines.append(f"Action: {tool_name}({args_text})")
        return "\n".join(lines)

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a registered tool by name and return a structured observation."""
        function = self.tool_map.get(tool_name)
        if function is None:
            logger.log_event(
                "UNKNOWN_TOOL",
                {"tool_name": tool_name, "arguments": args},
            )
            return {
                "status": "error",
                "data": None,
                "error": {
                    "code": "UNKNOWN_TOOL",
                    "message": f"Tool {tool_name} not found.",
                },
            }

        try:
            result = function(**args)
        except TypeError as exc:
            return {
                "status": "error",
                "data": None,
                "error": {
                    "code": "INVALID_ARGUMENTS",
                    "message": str(exc),
                },
            }
        except Exception as exc:
            return {
                "status": "error",
                "data": None,
                "error": {
                    "code": "TOOL_EXCEPTION",
                    "message": str(exc),
                },
            }

        if not isinstance(result, dict):
            return {
                "status": "error",
                "data": None,
                "error": {
                    "code": "INVALID_TOOL_RESPONSE",
                    "message": f"Tool {tool_name} did not return a dict.",
                },
            }
        return result

    def _track_llm_metric(self, result: Dict[str, Any]) -> None:
        tracker.track_request(
            provider=result.get("provider", "unknown"),
            model=result.get("model", self.llm.model_name),
            usage=result.get("usage", {}),
            latency_ms=result.get("latency_ms", 0),
        )
