"""将官方 AppWorld Python 交互式执行接到已有 OpenHands 工具桥接。"""

from typing import ClassVar

from openhands.sdk import Action, Observation, ToolDefinition
from openhands.sdk.tool import ToolExecutor
from pydantic import Field

from environment.appworld import AppWorldEnvironment
from .terminal import ShellAction


class CodeAction(Action):
    code: str = Field(min_length=1, description="Python code executed in the persistent AppWorld shell")


class CodeObservation(Observation):
    pass


class CodeExecutor(ToolExecutor):
    def __init__(self, channel):
        if channel is None or not isinstance(channel.environment, AppWorldEnvironment):
            raise TypeError("execute_code 需要本次 trial 的 AppWorldEnvironment")
        self.channel = channel

    def __call__(self, action: CodeAction, conversation=None) -> CodeObservation:
        command = self.channel.environment.code_command(action.code, timeout=self.channel.timeout)
        observation = self.channel.run_command(
            ShellAction(command=command, timeout_sec=self.channel.timeout), conversation,
            tool_name="execute_code", arguments=action.model_dump(mode="json"),
        )
        return CodeObservation.from_text(observation.text, is_error=observation.is_error)


class AppWorldCodeTool(ToolDefinition[CodeAction, CodeObservation]):
    name: ClassVar[str] = "execute_code"

    @classmethod
    def create(cls, conv_state=None, *, executor=None):
        return [cls(
            description=("Execute Python in this task's persistent AppWorld shell. Variables survive calls. "
                         "Use the provided apis object to discover documentation and operate simulated apps; "
                         "print results to inspect them. This tool does not accept Bash commands."),
            action_type=CodeAction, observation_type=CodeObservation,
            executor=CodeExecutor(executor),
        )]
