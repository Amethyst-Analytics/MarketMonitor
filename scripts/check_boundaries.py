import ast
import sys
from pathlib import Path

FORBIDDEN_BY_PACKAGE: dict[str, list[str]] = {
    "market_monitor": ["amethyst_server", "amethyst_analytics", "amethyst_core_direct"],
    "amethyst_server": ["market_monitor", "amethyst_analytics"],
    "amethyst_analytics": ["market_monitor", "amethyst_server"],
    "amethyst_core": [],
    "amethyst_infrastructure": [],
}


def detect_package(src_dir: Path) -> str | None:
    for entry in sorted(src_dir.iterdir()):
        if entry.is_dir() and not entry.name.startswith("."):
            return entry.name.lower().replace("-", "_")
    return None


def collect_imports(filepath: Path) -> list[tuple[int, str]]:
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    results: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                results.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom) and node.module:
            results.append((node.lineno, node.module))
    return results


def main() -> int:
    src_dir = Path("src")
    if not src_dir.exists():
        print("No src/ directory found - skipping")
        return 0

    package = detect_package(src_dir)
    if package is None:
        print("No package found under src/ - skipping")
        return 0

    forbidden = FORBIDDEN_BY_PACKAGE.get(package, [])
    print(f"Repo package : {package}")
    if not forbidden:
        print("No boundary restrictions for this package. Clean.")
        return 0

    print(f"Forbidden    : {forbidden}")
    print()

    violations: list[tuple[Path, int, str, str]] = []
    for py_file in sorted(src_dir.rglob("*.py")):
        for lineno, module in collect_imports(py_file):
            for pkg in forbidden:
                if module == pkg or module.startswith(f"{pkg}."):
                    violations.append((py_file, lineno, module, pkg))

    if violations:
        print(f"FAIL: {len(violations)} boundary violation(s) found:")
        print()
        for filepath, lineno, module, pkg in violations:
            print(f"  {filepath}:{lineno}  imports '{module}'  (forbidden: '{pkg}')")
        print()
        print("Services must communicate via REST or Redis Pub/Sub only.")
        return 1

    print("PASS: Boundary check passed - no forbidden imports found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
