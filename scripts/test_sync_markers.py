"""Dependency-free regression tests for marker-managed project templates."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync  # noqa: E402


BODY = "<!-- AI-CONFIG-LUCHDOM:START -->\r\n# Template\r\n<!-- AI-CONFIG-LUCHDOM:END -->\r\n"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as file:
        file.write(content)


def read(path: Path) -> str:
    with open(path, "r", encoding="utf-8", newline="") as file:
        return file.read()


def source(root: Path, content: str = BODY) -> Path:
    path = root / "template.md"
    write(path, content)
    return path


def test_fresh_write_and_splice() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        src, dest = source(root), root / "target.md"
        assert sync.write_or_splice_template(src, dest, False) == "new"
        external = "\r\n@RTK.md\r\n<!-- CODEGRAPH_START -->\r\n<!-- CODEGRAPH_END -->\r\n"
        write(dest, read(dest).rstrip("\r\n") + external)
        write(src, BODY.replace("# Template", "# Updated"))
        assert sync.write_or_splice_template(src, dest, False) == "spliced"
        result = read(dest)
        assert "# Updated" in result and result.endswith(external)


def test_legacy_and_force() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        src, dest = source(root), root / "target.md"
        write(dest, "# Hand-written\n")
        assert sync.write_or_splice_template(src, dest, False) == "skipped"
        assert sync.write_or_splice_template(src, dest, True) == "overwrote"


def test_malformed_and_newline_preservation() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        src, dest = source(root), root / "target.md"
        write(dest, "<!-- AI-CONFIG-LUCHDOM:START -->\n")
        assert sync.write_or_splice_template(src, dest, False) == "warning"
        write(dest, BODY.rstrip("\r\n") + "\n@RTK.md\n")
        assert sync.write_or_splice_template(src, dest, False) == "spliced"
        assert read(dest).endswith("\n@RTK.md\n")


def main() -> int:
    tests = (test_fresh_write_and_splice, test_legacy_and_force, test_malformed_and_newline_preservation)
    for test in tests:
        test()
        print(f"{test.__name__}: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
