import json
import anthropic


class BaseAgent:
    """Gemeinsame Basis für alle Agenten – kapselt den Claude API Agentic Loop."""

    def __init__(
        self,
        system: str,
        tools: list[dict],
        tool_handlers: dict,
        model: str = "claude-sonnet-4-6",
        max_iterations: int = 25,
    ):
        self.system = system
        self.tools = tools
        self.tool_handlers = tool_handlers
        self.model = model
        self.max_iterations = max_iterations
        self.client = anthropic.Anthropic()

    def run(self, user_message: str) -> str:
        messages = [{"role": "user", "content": user_message}]

        for iteration in range(self.max_iterations):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8096,
                system=self.system,
                tools=self.tools if self.tools else [],
                messages=messages,
            )

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        return block.text
                return ""

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    handler = self.tool_handlers.get(block.name)
                    if handler:
                        try:
                            result = handler(**block.input)
                            content = json.dumps(result, ensure_ascii=False, default=str)
                        except Exception as e:
                            content = f"Fehler bei {block.name}: {str(e)}"
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": content,
                        })

            if tool_results:
                messages.append({"role": "user", "content": tool_results})
            elif response.stop_reason != "end_turn":
                break

        return "Maximale Iterationen erreicht."
