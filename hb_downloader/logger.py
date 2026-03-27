from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def make_log_paths(
    base_dir: Path, timestamped: bool = False, utc: bool = False
) -> tuple[Path, Path]:
    """Return (log_all_path, log_error_path) based on timestamped setting."""
    if timestamped:
        logs_dir = base_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        if utc:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S") + "Z"
        else:
            ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        return logs_dir / f"LOG-all-{ts}.txt", logs_dir / f"LOG-error-{ts}.txt"
    return base_dir / "LOG-all.txt", base_dir / "LOG-error.txt"


class Logger:
    def __init__(self, log_all: Path, log_error: Path) -> None:
        self._all = log_all
        self._err = log_error
        now = datetime.now().strftime("%Y-%m-%d %A %H:%M:%S")
        for path in (self._all, self._err):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{now}\n", encoding="utf-8")

    def _write(self, path: Path, text: str) -> None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text)

    def _write_all(self, text: str) -> None:
        self._write(self._all, text)

    def _write_err(self, text: str) -> None:
        self._write(self._err, text)

    def log_bundle_header(
        self, bundle_num: int, total: int, title: str, url: str
    ) -> None:
        block = (
            "\n==============================================================\n"
            f"{bundle_num} / {total} - {title}\n"
            f"{url}\n"
            "--------------------------------------------------------------\n"
        )
        self._write_all(block)
        self._write_err(block)

    def log_item_title(self, chunk_num: int, chunk_total: int, item_title: str) -> None:
        self._write_all(f"\n{chunk_num} / {chunk_total} - {item_title}\n")

    def log_item_error_title(
        self, chunk_num: int, chunk_total: int, item_title: str
    ) -> None:
        self._write_err(f"\n{chunk_num} / {chunk_total} - {item_title}\n")

    def log_item_ok(
        self, item_title: str, filename: str, label: str, md5: str
    ) -> None:
        self._write_all(
            f"{label} - {filename}\n"
            "   OK - File integrity (MD5) verified.\n"
            f"   MD5: {md5}\n"
        )

    def log_item_fail(
        self,
        item_title: str,
        filename: str,
        label: str,
        md5_file: str,
        md5_expected: str,
        reason: str,
    ) -> None:
        entry = (
            f"{label} - {filename}\n"
            f"   FAIL - {reason}\n"
            f"   File MD5: {md5_file}\n"
            f"   HB   MD5: {md5_expected}\n"
        )
        self._write_all(entry)
        self._write_err(entry)

    def log_item_skipped(
        self,
        item_title: str,
        filename: str,
        label: str,
        md5: str,
        ok: bool,
    ) -> None:
        self._write_all(
            f"{label} - {filename}\n"
            "   File downloaded already, skipping...\n"
        )
        if ok:
            self._write_all(
                "   OK - File integrity (MD5) verified.\n"
                f"   MD5: {md5}\n"
            )
        else:
            entry = (
                "   FAIL - File integrity (MD5) failed.\n"
                f"   MD5: {md5}\n"
            )
            self._write_all(entry)
            self._write_err(f"{label} - {filename}\n   File downloaded already, skipping...\n{entry}")

    def log_summary(self, md5_errors: int, not_found_errors: int) -> None:
        summary = (
            "\nError Summary:\n"
            "----------------------\n"
            f"Failed file integrity (MD5) checks: {md5_errors - not_found_errors}\n"
            f"Unsuccessful downloads (file not found): {not_found_errors}\n"
            f"Total: {md5_errors}\n"
        )
        self._write_all(summary)
        self._write_err(summary)

    def log_separator(self) -> None:
        sep = "==============================================================\n"
        self._write_all(sep)
        self._write_err(sep)
