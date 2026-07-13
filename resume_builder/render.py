"""Render structured resume data into LaTeX via Jinja2.

Jinja delimiters are remapped so they never collide with LaTeX braces:
  blocks    ((* ... *))
  variables ((( ... )))
  comments  ((= ... =))
Every variable is passed through the |tex escape filter inside the template.
"""

import re
from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, StrictUndefined

TEMPLATE_DIR = Path(__file__).parent / "templates"

_LATEX_SPECIALS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}
_LATEX_RE = re.compile("|".join(re.escape(c) for c in _LATEX_SPECIALS))


def tex_escape(value: Any) -> str:
    if value is None:
        return ""
    return _LATEX_RE.sub(lambda m: _LATEX_SPECIALS[m.group()], str(value))


def strip_scheme(url: str) -> str:
    """Display form of a URL: no https://, no trailing slash."""
    return re.sub(r"^https?://(www\.)?", "", str(url)).rstrip("/")


def tex_url(url: str) -> str:
    """Escape only what breaks \\href's URL argument."""
    return str(url).replace("%", r"\%").replace("#", r"\#")


def make_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        block_start_string="((*",
        block_end_string="*))",
        variable_start_string="(((",
        variable_end_string=")))",
        comment_start_string="((=",
        comment_end_string="=))",
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
        autoescape=False,
    )
    env.filters["tex"] = tex_escape
    env.filters["noscheme"] = strip_scheme
    env.filters["texurl"] = tex_url
    return env


def render_resume(data: Dict[str, Any], template_name: str = "resume.tex.j2") -> str:
    template = make_env().get_template(template_name)
    return template.render(**data)
