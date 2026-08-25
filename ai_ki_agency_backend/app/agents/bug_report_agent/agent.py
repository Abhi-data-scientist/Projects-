"""
Bug Report Agent - deliberately has NO prompt.py and makes NO LLM call.

Runs the generated files through pure-Python static analysis, per
language, and returns a structured issue list. This stage is free.

Coverage (best-effort, static only - it will not catch runtime/logic bugs):
- python      -> ast.parse (syntax) + pyflakes (undefined names, unused imports/vars)
- javascript  -> esprima parser (syntax errors)
- css         -> tinycss2 (parse errors)
- html        -> BeautifulSoup + a few structural heuristics (unclosed-ish
                 tags, empty href/src, missing alt text, duplicate ids)
"""
import ast
import io

import esprima
import tinycss2
from bs4 import BeautifulSoup
from pyflakes.api import check as pyflakes_check
from pyflakes.reporter import Reporter

from app.agents.base_agent import BaseAgent

LANG_BY_EXT = {
    "py": "python",
    "js": "javascript",
    "mjs": "javascript",
    "css": "css",
    "html": "html",
    "htm": "html",
}

LANGUAGE_ALIASES = {
    "py": "python",
    "python3": "python",
    "js": "javascript",
    "node": "javascript",
    "nodejs": "javascript",
    "ts": "typescript",
    "html5": "html",
}


class BugReportAgent(BaseAgent):
    name = "bug_report"

    def run(self, context: dict) -> dict:
        files = (context.get("coding") or {}).get("files") or []
        issues: list[dict] = []

        for f in files:
            path = f.get("path", "")
            content = f.get("content", "")
            language = self._normalise_language(f.get("language"), path)

            if language == "python":
                issues.extend(self._check_python(path, content))
            elif language == "javascript":
                issues.extend(self._check_js(path, content))
            elif language == "css":
                issues.extend(self._check_css(path, content))
            elif language == "html":
                issues.extend(self._check_html(path, content))
            # unknown languages are skipped silently - no LLM guesswork here

        severity_counts = {"error": 0, "warning": 0}
        for issue in issues:
            severity_counts[issue["severity"]] = severity_counts.get(issue["severity"], 0) + 1

        return {
            "total_issues": len(issues),
            "severity_counts": severity_counts,
            "issues": issues,
            "clean": len(issues) == 0,
        }

    # -- per-language checks --------------------------------------------

    @staticmethod
    def _guess_language(path: str) -> str:
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        return LANG_BY_EXT.get(ext, "")

    @classmethod
    def _normalise_language(cls, language: object, path: str) -> str:
        """Accept the usual labels emitted by code generators as well as extensions."""
        value = str(language or "").strip().lower()
        if not value:
            return cls._guess_language(path)
        return LANGUAGE_ALIASES.get(value, value)

    @staticmethod
    def _check_python(path: str, content: str) -> list[dict]:
        issues = []
        try:
            ast.parse(content, filename=path or "<file>")
        except SyntaxError as e:
            issues.append(
                {
                    "file": path,
                    "line": e.lineno,
                    "severity": "error",
                    "tool": "ast",
                    "message": f"SyntaxError: {e.msg}",
                }
            )
            return issues  # pyflakes can't run on invalid syntax

        buf = io.StringIO()
        reporter = Reporter(buf, buf)
        pyflakes_check(content, path or "<file>", reporter)
        for line in buf.getvalue().splitlines():
            if not line.strip():
                continue
            issues.append(
                {
                    "file": path,
                    "line": None,
                    "severity": "warning",
                    "tool": "pyflakes",
                    "message": line.strip(),
                }
            )
        return issues

    @staticmethod
    def _check_js(path: str, content: str) -> list[dict]:
        issues = []
        try:
            esprima.parseScript(content, options={"tolerant": False})
        except esprima.Error as e:
            issues.append(
                {
                    "file": path,
                    "line": getattr(e, "lineNumber", None),
                    "severity": "error",
                    "tool": "esprima",
                    "message": str(e),
                }
            )
        return issues

    @staticmethod
    def _check_css(path: str, content: str) -> list[dict]:
        issues = []
        rules = tinycss2.parse_stylesheet(content, skip_comments=True, skip_whitespace=True)
        for rule in rules:
            if rule.type == "error":
                issues.append(
                    {
                        "file": path,
                        "line": getattr(rule, "source_line", None),
                        "severity": "error",
                        "tool": "tinycss2",
                        "message": rule.message,
                    }
                )
        return issues

    @staticmethod
    def _check_html(path: str, content: str) -> list[dict]:
        issues = []
        soup = BeautifulSoup(content, "html.parser")

        seen_ids: dict[str, int] = {}
        for tag in soup.find_all(True):
            tag_id = tag.get("id")
            if tag_id:
                seen_ids[tag_id] = seen_ids.get(tag_id, 0) + 1

            if tag.name in ("a",) and tag.get("href") == "":
                issues.append(
                    {
                        "file": path,
                        "line": None,
                        "severity": "warning",
                        "tool": "html-heuristics",
                        "message": f"<a> tag has empty href (element: {str(tag)[:80]})",
                    }
                )
            if tag.name == "img" and not tag.get("alt"):
                issues.append(
                    {
                        "file": path,
                        "line": None,
                        "severity": "warning",
                        "tool": "html-heuristics",
                        "message": f"<img> missing alt text (element: {str(tag)[:80]})",
                    }
                )
            if tag.name in ("script", "img") and tag.get("src") == "":
                issues.append(
                    {
                        "file": path,
                        "line": None,
                        "severity": "warning",
                        "tool": "html-heuristics",
                        "message": f"<{tag.name}> has empty src",
                    }
                )

        for dup_id, count in seen_ids.items():
            if count > 1:
                issues.append(
                    {
                        "file": path,
                        "line": None,
                        "severity": "error",
                        "tool": "html-heuristics",
                        "message": f"Duplicate id '{dup_id}' used {count} times",
                    }
                )

        return issues
