import inspect
import json
from typing import Any, Dict, List, Optional, Tuple

from src.agent.parsers import ActionParseError, ParsedAction, parse_final_answer, parse_single_action
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


class ReActAgentV2:
    """A stricter ReAct agent with retry, validation, and graceful failure handling."""

    def __init__(
        self,
        llm: LLMProvider,
        tools: List[Dict[str, Any]],
        max_steps: int = 8,
        max_retries: int = 2,
    ):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.max_retries = max_retries
        self.history: List[Dict[str, Any]] = []
        self.tool_map = {tool["name"]: tool["function"] for tool in tools}
        self.action_counts: Dict[str, int] = {}
        self.observation_cache: Dict[str, Dict[str, Any]] = {}

    def get_system_prompt(self) -> str:
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
You are a careful e-commerce ReAct agent.

Available tools:
{tool_descriptions}

Use exactly one of these formats per response:
1. Action: tool_name({{"arg": "value"}})
2. Final Answer: answer to the user

Strict rules:
- Emit only one Action per response.
- Never write Observation; the runtime will provide observations.
- Never invent product price, stock, weight, coupon, shipping, or totals.
- If a tool returns an error, explain the limitation or choose a valid next action.
- Use total item weight for shipping: unit weight * quantity.
- Keep responses short.
"""

    def run(self, user_input: str) -> str:
        logger.log_event(
            "AGENT_START",
            {
                "version": "v2",
                "input": user_input,
                "provider": getattr(self.llm, "provider_name", None),
                "model": self.llm.model_name,
                "max_steps": self.max_steps,
                "max_retries": self.max_retries,
            },
        )

        current_prompt = f"User: {user_input}\n"

        for step in range(1, self.max_steps + 1):
            result = self._generate_with_retries(current_prompt, step)
            if result is None:
                return self._end(
                    step=step - 1,
                    reason="provider_error",
                    answer="I cannot complete the request right now because the model provider is unavailable or rate-limited. Please retry in a moment.",
                )

            content = str(result.get("content", ""))
            self.history.append({"step": step, "llm_output": content})
            logger.log_event(
                "AGENT_STEP",
                {
                    "version": "v2",
                    "step": step,
                    "provider": result.get("provider", "unknown"),
                    "model": result.get("model", self.llm.model_name),
                    "output": content,
                },
            )

            final_answer = parse_final_answer(content)
            if final_answer is not None and "Action:" not in content and "Observation:" not in content:
                logger.log_event("FINAL_ANSWER", {"step": step, "answer": final_answer})
                return self._end(step=step, reason="final_answer", answer=final_answer)

            action = self._parse_action_with_retries(content, current_prompt, step)
            if action is None:
                current_prompt += self._parser_feedback_history(
                    content,
                    "The output could not be parsed after retries. Use exactly one Action or Final Answer.",
                )
                continue

            repeated_answer = self._check_repeated_action(action, step)
            if repeated_answer is not None:
                if isinstance(repeated_answer, dict):
                    current_prompt += self._action_history(action, repeated_answer)
                    continue
                return repeated_answer

            invalid_observation = self._validate_action(action)
            if invalid_observation is not None:
                logger.log_event(
                    "INVALID_ARGUMENTS",
                    {
                        "step": step,
                        "tool_name": action.tool_name,
                        "arguments": action.arguments,
                        "result": invalid_observation,
                    },
                )
                observation = invalid_observation
            else:
                logger.log_event(
                    "TOOL_CALL",
                    {"step": step, "tool_name": action.tool_name, "arguments": action.arguments},
                )
                observation = self._execute_tool(action.tool_name, action.arguments)
                logger.log_event(
                    "TOOL_RESULT",
                    {
                        "step": step,
                        "tool_name": action.tool_name,
                        "status": observation.get("status"),
                        "result": observation,
                    },
                )
                self.observation_cache[self._action_signature(action)] = observation

            current_prompt += self._action_history(action, observation)

        logger.log_event("MAX_STEPS_EXCEEDED", {"max_steps": self.max_steps, "input": user_input})
        return self._end(
            step=self.max_steps,
            reason="max_steps_exceeded",
            answer="I could not complete the request within the allowed steps.",
        )

    def _generate_with_retries(self, prompt: str, step: int) -> Optional[Dict[str, Any]]:
        for attempt in range(0, self.max_retries + 1):
            try:
                result = self.llm.generate(prompt, system_prompt=self.get_system_prompt())
            except Exception as exc:
                logger.log_event(
                    "PROVIDER_ERROR",
                    {
                        "step": step,
                        "attempt": attempt + 1,
                        "provider": getattr(self.llm, "provider_name", None),
                        "model": self.llm.model_name,
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                    },
                )
                if attempt < self.max_retries:
                    logger.log_event(
                        "RETRY",
                        {
                            "step": step,
                            "attempt": attempt + 1,
                            "reason": "provider_error",
                        },
                    )
                    continue
                return None

            tracker.track_request(
                provider=result.get("provider", "unknown"),
                model=result.get("model", self.llm.model_name),
                usage=result.get("usage", {}),
                latency_ms=result.get("latency_ms", 0),
            )
            return result
        return None

    def _parse_action_with_retries(
        self,
        content: str,
        current_prompt: str,
        step: int,
    ) -> Optional[ParsedAction]:
        parse_content = content
        prompt = current_prompt
        for attempt in range(0, self.max_retries + 1):
            try:
                return parse_single_action(parse_content)
            except ActionParseError as exc:
                logger.log_event(
                    "PARSER_ERROR",
                    {
                        "step": step,
                        "attempt": attempt + 1,
                        "code": exc.code,
                        "message": str(exc),
                        "output": parse_content,
                    },
                )
                if attempt >= self.max_retries:
                    return None

                logger.log_event(
                    "RETRY",
                    {
                        "step": step,
                        "attempt": attempt + 1,
                        "reason": exc.code,
                    },
                )
                prompt += self._parser_feedback_history(parse_content, str(exc))
                retry_result = self._generate_with_retries(prompt, step)
                if retry_result is None:
                    return None
                parse_content = str(retry_result.get("content", ""))
                logger.log_event(
                    "AGENT_STEP",
                    {
                        "version": "v2",
                        "step": step,
                        "retry_output": True,
                        "output": parse_content,
                    },
                )
        return None

    def _validate_action(self, action: ParsedAction) -> Optional[Dict[str, Any]]:
        function = self.tool_map.get(action.tool_name)
        if function is None:
            logger.log_event(
                "UNKNOWN_TOOL",
                {"tool_name": action.tool_name, "arguments": action.arguments},
            )
            return self._error("UNKNOWN_TOOL", f"Tool {action.tool_name} not found.")

        signature = inspect.signature(function)
        parameters = signature.parameters
        required = [
            name
            for name, parameter in parameters.items()
            if parameter.default is inspect.Parameter.empty
        ]
        missing = [name for name in required if name not in action.arguments]
        unknown = [name for name in action.arguments if name not in parameters]
        if missing:
            return self._error("MISSING_ARGUMENT", f"Missing required argument(s): {', '.join(missing)}")
        if unknown:
            return self._error("UNKNOWN_ARGUMENT", f"Unknown argument(s): {', '.join(unknown)}")

        for name, value in action.arguments.items():
            validation_error = self._validate_value(name, value)
            if validation_error is not None:
                return validation_error
        return None

    def _validate_value(self, name: str, value: Any) -> Optional[Dict[str, Any]]:
        if name in {"item_name", "coupon_code", "destination"}:
            if not isinstance(value, str):
                return self._error("INVALID_ARGUMENT_TYPE", f"{name} must be a string.")
            if not value.strip():
                return self._error("INVALID_ARGUMENT_VALUE", f"{name} must be non-empty.")
        if name in {"query", "category"}:
            if value is not None and not isinstance(value, str):
                return self._error("INVALID_ARGUMENT_TYPE", f"{name} must be a string.")
        if name in {"requested_quantity", "quantity"}:
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                return self._error("INVALID_ARGUMENT_TYPE", f"{name} must be a positive integer.")
        if name in {"weight_kg", "max_price", "unit_price", "shipping_fee"}:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                return self._error("INVALID_ARGUMENT_TYPE", f"{name} must be a non-negative number.")
            if name == "weight_kg" and value <= 0:
                return self._error("INVALID_ARGUMENT_VALUE", "weight_kg must be positive.")
        if name == "discount_percent":
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 or value > 100:
                return self._error("INVALID_ARGUMENT_TYPE", "discount_percent must be between 0 and 100.")
        return None

    def _check_repeated_action(self, action: ParsedAction, step: int) -> Optional[str | Dict[str, Any]]:
        signature = self._action_signature(action)
        self.action_counts[signature] = self.action_counts.get(signature, 0) + 1
        if self.action_counts[signature] < 2:
            return None

        cached = self.observation_cache.get(signature)
        if cached is not None and self.action_counts[signature] == 2:
            logger.log_event(
                "REPEATED_ACTION",
                {
                    "step": step,
                    "tool_name": action.tool_name,
                    "arguments": action.arguments,
                    "resolution": "reuse_cached_observation",
                },
            )
            return {
                "status": "success",
                "data": {
                    "cached_observation": cached,
                    "instruction": (
                        "This action was already completed. Use the cached observation "
                        "and choose the next required action instead of repeating it."
                    ),
                },
                "error": None,
            }

        logger.log_event(
            "REPEATED_ACTION",
            {
                "step": step,
                "tool_name": action.tool_name,
                "arguments": action.arguments,
                "resolution": "stop",
            },
        )
        return self._end(
            step=step,
            reason="repeated_action",
            answer="I stopped because the same tool action repeated too many times without progress.",
        )

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        function = self.tool_map[tool_name]
        try:
            result = function(**args)
        except Exception as exc:
            return self._error("TOOL_EXCEPTION", str(exc))
        if not isinstance(result, dict):
            return self._error("INVALID_TOOL_RESPONSE", f"Tool {tool_name} did not return a dict.")
        return result

    def _action_history(self, action: ParsedAction, observation: Dict[str, Any]) -> str:
        args = json.dumps(action.arguments, ensure_ascii=False)
        observation_text = json.dumps(observation, ensure_ascii=False)
        return f"Assistant: Action: {action.tool_name}({args})\nObservation: {observation_text}\n"

    def _parser_feedback_history(self, output: str, message: str) -> str:
        observation = self._error("PARSER_ERROR", message)
        observation_text = json.dumps(observation, ensure_ascii=False)
        return f"Assistant: {output}\nObservation: {observation_text}\n"

    def _end(self, step: int, reason: str, answer: str) -> str:
        logger.log_event("AGENT_END", {"version": "v2", "steps": step, "termination_reason": reason})
        return answer

    def _error(self, code: str, message: str) -> Dict[str, Any]:
        return {"status": "error", "data": None, "error": {"code": code, "message": message}}

    def _action_signature(self, action: ParsedAction) -> str:
        return f"{action.tool_name}:{json.dumps(action.arguments, sort_keys=True)}"
