from pathlib import Path
import yaml
from services.api.config import ROOT


def catalog():
    roles = yaml.safe_load((ROOT / "profiles/roles/roles.yaml").read_text(encoding="utf-8"))
    industries = yaml.safe_load((ROOT / "profiles/industries/industries.yaml").read_text(encoding="utf-8"))
    return {**roles, "industries": industries["industries"]}


class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, name, tool):
        if name in self.tools:
            raise ValueError("Duplicate tool")
        self.tools[name] = tool

    def call(self, name, allowed, **kwargs):
        if name not in allowed or name not in self.tools:
            raise PermissionError("Tool not granted")
        return self.tools[name](**kwargs)


class MCPAdapter:
    """External adapters must register explicit validated callables; no arbitrary tool dispatch."""
    def install(self, registry, tools):
        for name, tool in tools.items():
            registry.register("mcp:" + name, tool)


def skills():
    output = []
    for file in sorted((ROOT / "skills").glob("*/SKILL.md")):
        header = file.read_text(encoding="utf-8").split("---", 2)
        meta = yaml.safe_load(header[1])
        if meta.get("version") != 1 or not isinstance(meta.get("tools"), list):
            raise ValueError("Invalid skill registry")
        output.append({**meta, "instructions": header[2].strip()})
    return output
