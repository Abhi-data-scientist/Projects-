"""Create a safe ZIP archive from the final code-generation output."""
import json
from pathlib import PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile

from app.agents.base_agent import BaseAgent
from app.config import settings


class PackageAgent(BaseAgent):
    """Packages the Bug Fix output, which is the final version of every file."""

    name = "package"

    def run(self, context: dict) -> dict:
        final_code = context.get("bug_fix") or context.get("coding") or {}
        files = final_code.get("files") or []
        if not files:
            raise ValueError("No generated code files are available to package.")

        session_id = str(context.get("session_id", "session"))
        artifact = self.create_archive(session_id, "final_code", "code", files)

        return {
            "archive_name": artifact["filename"],
            "file_count": len(files),
            "files": sorted(file.get("path", "") for file in files),
            "downloads": [artifact],
        }

    @classmethod
    def create_archive(
        cls,
        session_id: str,
        artifact_id: str,
        suffix: str,
        files: list[dict],
        *,
        label: str | None = None,
        extra_files: dict[str, str] | None = None,
    ) -> dict:
        """Create a downloadable ZIP without exposing a filesystem path."""
        archive_name = f"{session_id}_{suffix}.zip"
        archive_path = settings.generated_path(archive_name)
        seen_paths: set[str] = set()
        prepared_files: list[tuple[str, str]] = []

        for file in files:
            archive_path_in_zip = cls._safe_archive_path(file.get("path"))
            if archive_path_in_zip in seen_paths:
                raise ValueError(f"Duplicate generated file path: {archive_path_in_zip}")
            seen_paths.add(archive_path_in_zip)

            content = file.get("content")
            if not isinstance(content, str):
                raise ValueError(f"Generated file '{archive_path_in_zip}' has no text content.")
            prepared_files.append((archive_path_in_zip, content))

        for path, content in (extra_files or {}).items():
            archive_path_in_zip = cls._safe_archive_path(path)
            if archive_path_in_zip in seen_paths:
                raise ValueError(f"Duplicate generated file path: {archive_path_in_zip}")
            seen_paths.add(archive_path_in_zip)
            prepared_files.append((archive_path_in_zip, content))

        with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
            for archive_path_in_zip, content in prepared_files:
                archive.writestr(archive_path_in_zip, content)

        return {
            "id": artifact_id,
            "label": label or f"Download {suffix.replace('_', ' ')} ZIP",
            "filename": archive_name,
            "kind": "zip",
        }

    @staticmethod
    def report_json(report: dict) -> str:
        return json.dumps(report, indent=2, ensure_ascii=False)

    @staticmethod
    def _safe_archive_path(value: object) -> str:
        """Reject absolute and traversal paths so the archive is safe to extract."""
        path = PurePosixPath(str(value or "").replace("\\", "/"))
        if not str(path) or path.is_absolute() or ".." in path.parts or "." in path.parts:
            raise ValueError(f"Unsafe generated file path: {value!r}")
        return path.as_posix()
