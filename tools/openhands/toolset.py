"""为共用工具名称导入 OpenHands 专用类并完成 SDK 注册。"""

from importlib import import_module
from uuid import uuid4

from openhands.sdk import ToolDefinition
from openhands.sdk.tool import Tool, register_tool

from tools.loader import REGISTRY_TOOLS

TOOL_CLASSES = {
    "search_skills": "tools.openhands.search_skills:SearchSkillsTool",
    "load_skill": "tools.openhands.load_skill:LoadSkillTool",
    "load_resource": "tools.openhands.load_resources:LoadResourceTool",
    "execute_resource": "tools.openhands.execute_resource:ExecuteResourceTool",
    "terminal": "tools.openhands.terminal:EnvironmentShellTool",
    "execute_code": "tools.openhands.appworld:AppWorldCodeTool",
    "read_file": "tools.openhands.file_editor:ReadFileTool",
    "write_file": "tools.openhands.file_editor:WriteFileTool",
    "replace_text": "tools.openhands.file_editor:ReplaceTextTool",
    "think": "tools.openhands.control:LocalThinkTool",
    "finish": "tools.openhands.control:LocalFinishTool",
}


def create_tools(selected: list[str], *, executor=None) -> tuple[list[Tool], set[str]]:
    """每个类实现 create(conv_state=None, *, executor=None, **params)。

    executor 是当前环境的命令通道；不使用环境的工具可传 None。
    仅导入配置中指定的类。
    """
    if unknown := set(selected) - TOOL_CLASSES.keys():
        raise ValueError(f"以下工具没有 OpenHands 实现：{sorted(unknown)}")
    registry = None
    if executor is not None and set(selected).intersection(REGISTRY_TOOLS):
        registry = executor.environment.executor.registry
        if registry is None:
            raise ValueError("环境中的注册中心工具需要配置环境的 registry_url")
    specs, names = [], set()
    for name in selected:
        reference = TOOL_CLASSES[name]
        module, separator, attribute = reference.partition(":")
        if not separator or not module or not attribute:
            raise ValueError(f"需要 module:Class 格式，实际收到 {reference!r}")
        tool_class = getattr(import_module(module), attribute)
        if not isinstance(tool_class, type) or not issubclass(tool_class, ToolDefinition):
            raise TypeError(f"配置的工具必须为 ToolDefinition 子类：{reference}")
        bindings = {"executor": executor}
        if name in REGISTRY_TOOLS:
            bindings["registry"] = registry
        definitions = tool_class.create(conv_state=None, **bindings)
        if not definitions:
            raise ValueError(f"配置的工具未创建任何定义：{reference}")
        for definition in definitions:
            if not isinstance(definition, ToolDefinition) or definition.executor is None:
                raise TypeError(f"工具必须包含定义和执行器：{reference}")
            if definition.name in names:
                raise ValueError(f"模型可见工具名称重复：{definition.name}")
            names.add(definition.name)
            # 不得覆盖 SDK 全局注册表中其他试验的绑定。
            binding = "custom_" + uuid4().hex
            register_tool(binding, definition)
            specs.append(Tool(name=binding))
    return specs, names
