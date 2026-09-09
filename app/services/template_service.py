from pathlib import Path
from typing import Any

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, StrictUndefined, TemplateNotFound, select_autoescape


class TemplateServiceError(RuntimeError):
    pass


class TemplateService:
    def __init__(self, template_dir: Path) -> None:
        self._environment = Environment(
            loader=ChoiceLoader(
                [FileSystemLoader(str(template_dir)), FileSystemLoader(str(template_dir.parent))]
            ),
            autoescape=select_autoescape(["html", "xml"]),
            undefined=StrictUndefined,
        )

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        # Names come from EventService only; this guard also prevents accidental traversal.
        if Path(template_name).name != template_name or not template_name.endswith(".html"):
            raise TemplateServiceError("Invalid template name")
        try:
            template = self._environment.get_template(template_name)
        except TemplateNotFound as exc:
            raise TemplateServiceError(f"Template not found: {template_name}") from exc
        return template.render(**context)
