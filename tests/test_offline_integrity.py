"""Tests verifying offline integrity and local-only execution."""

from pathlib import Path
import re

ALLOWED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0"}
URL_REGEX = re.compile(r"https?://([a-zA-Z0-9.-]+)", re.IGNORECASE)


def test_no_external_hosts_in_app_code():
    """Fail if any application source code references an external host."""
    root_dir = Path(__file__).resolve().parent.parent

    # Check application directories and root entry points
    app_dirs = [root_dir / "engine", root_dir / "ui", root_dir / "eval"]
    py_files = [root_dir / "app.py"]

    for d in app_dirs:
        if d.exists():
            py_files.extend(d.rglob("*.py"))

    violations = []
    for fpath in py_files:
        content = fpath.read_text(encoding="utf-8")
        for line_num, line in enumerate(content.splitlines(), start=1):
            matches = URL_REGEX.findall(line)
            for host in matches:
                clean_host = host.split(":")[0].lower()
                if clean_host not in ALLOWED_HOSTS:
                    violations.append(
                        f"{fpath.relative_to(root_dir)}:{line_num} references external host '{clean_host}' in line: {line.strip()}"
                    )

    assert not violations, "Found external host references in app code:\n" + "\n".join(violations)
