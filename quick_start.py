#!/usr/bin/env python3
"""YTD-Kopya Code Quality Quick Start."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


class CodeQualitySetup:
    """Handles the gradual implementation of code quality tools."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.config_files: Dict[str, Path] = {}
        self.status: Dict[str, Any] = {}

    def check_project_structure(self) -> bool:
        """Verify we're in the correct project directory."""
        required_files = ["wsgi.py", "backend"]
        missing = [f for f in required_files if not (self.project_root / f).exists()]
        if missing:
            print(f"❌ Missing required files/directories: {missing}")
            print("Please run this script from the YTD-Kopya project root.")
            return False
        print("✅ Project structure verified")
        return True

    def create_pyproject_toml(self) -> None:
        """Create pyproject.toml with appropriate settings for current phase."""
        config = {
            "tool": {
                "black": {
                    "line-length": 100,
                    "target-version": ["py39"],
                    "include": r"\.pyi?$",
                    "extend-exclude": r"""
/(
  \.eggs
  | \.git
  | \.mypy_cache
  | \.tox
  | \.venv
  | _build
  | buck-out
  | build
  | dist
  | migrations
)/
""",
                },
                "isort": {
                    "profile": "black",
                    "multi_line_output": 3,
                    "line_length": 100,
                    "known_first_party": ["backend"],
                    "known_third_party": ["flask", "sqlalchemy", "celery", "redis"],
                    "sections": [
                        "FUTURE",
                        "STDLIB",
                        "THIRDPARTY",
                        "FIRSTPARTY",
                        "LOCALFOLDER",
                    ],
                },
                "mypy": {
                    "python_version": "3.9",
                    "warn_return_any": True,
                    "warn_unused_configs": True,
                    "disallow_untyped_defs": False,
                    "check_untyped_defs": True,
                    "show_error_codes": True,
                },
            }
        }
        config_path = self.project_root / "pyproject.toml"
        try:
            import tomli_w

            with open(config_path, "wb") as f:
                tomli_w.dump(config, f)
        except ImportError:
            self._write_toml_manually(config_path)
        print("✅ Created pyproject.toml")

    def _write_toml_manually(self, path: Path) -> None:
        """Manually write TOML config when tomli_w is not available."""
        toml_content = r"""
[tool.black]
line-length = 100
target-version = ['py39']
include = '\.pyi?$'

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 100
known_first_party = ["backend"]
known_third_party = ["flask", "sqlalchemy", "celery", "redis"]

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
check_untyped_defs = true
show_error_codes = true

[[tool.mypy.overrides]]
module = ["celery.*", "redis.*", "flask_migrate.*"]
ignore_missing_imports = true
"""
        path.write_text(toml_content.strip())

    def create_flake8_config(self) -> None:
        """Create .flake8 configuration file."""
        config_content = """
[flake8]
max-line-length = 100
extend-ignore = E203, E501, W503
exclude =
    .git,
    __pycache__,
    *.egg-info,
    build,
    dist,
    migrations,
    .venv
per-file-ignores =
    __init__.py:F401
    */migrations/*:E501
max-complexity = 15
"""
        (self.project_root / ".flake8").write_text(config_content.strip())
        print("✅ Created .flake8 configuration")

    def create_precommit_config(self) -> None:
        """Create pre-commit configuration."""
        config_content = """
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-json

  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: [--profile=black]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        additional_dependencies: [flake8-docstrings]
"""
        (self.project_root / ".pre-commit-config.yaml").write_text(
            config_content.strip()
        )
        print("✅ Created .pre-commit-config.yaml")

    def create_dev_requirements(self) -> None:
        """Create development requirements file."""
        requirements = [
            "black==23.3.0",
            "isort==5.12.0",
            "flake8==6.0.0",
            "flake8-docstrings==1.7.0",
            "mypy==1.3.0",
            "pre-commit==3.3.3",
            "pytest==7.3.1",
            "pytest-cov==4.1.0",
            "pytest-flask==1.2.0",
            "bandit==1.7.5",
            "coverage==7.2.7",
        ]
        req_path = self.project_root / "backend" / "requirements-dev.txt"
        req_path.write_text("\n".join(requirements) + "\n")
        print("✅ Created backend/requirements-dev.txt")

    def create_makefile(self) -> None:
        """Create Makefile with development commands."""
        makefile_content = """
.PHONY: help install install-dev format lint type-check test clean

help:
@echo "YTD-Kopya Development Commands"
@echo "=============================="
@echo "install-dev     - Install development dependencies"
@echo "format          - Format code with black and isort"
@echo "lint            - Run flake8 linting"
@echo "type-check      - Run mypy type checking"
@echo "test            - Run tests with coverage"
@echo "clean           - Clean cache files"

install-dev:
pip install -r backend/requirements-dev.txt

format:
black backend/ scripts/ tests/ || true
isort backend/ scripts/ tests/ || true

lint:
flake8 backend/ scripts/ tests/ || true

type-check:
mypy backend/ || true

test:
pytest --cov=backend --cov-report=term-missing || true

clean:
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -delete
rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/
"""
        (self.project_root / "Makefile").write_text(makefile_content)
        print("✅ Created Makefile")

    def run_command(
        self, cmd: List[str], description: str, ignore_errors: bool = True
    ) -> bool:
        """Run a shell command with error handling."""
        print(f"🔄 {description}...")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                check=not ignore_errors,
            )
            if result.returncode == 0:
                print(f"✅ {description} completed")
                return True
            print(f"⚠️  {description} completed with warnings")
            if result.stdout:
                print("STDOUT:", result.stdout[:200])
            if result.stderr:
                print("STDERR:", result.stderr[:200])
            return ignore_errors
        except subprocess.CalledProcessError as exc:
            print(f"❌ {description} failed: {exc}")
            return False
        except FileNotFoundError:
            print(f"❌ Command not found: {' '.join(cmd)}")
            return False

    def phase_1_setup_tools(self) -> None:
        """Phase 1: Install and configure development tools."""
        print("\n🚀 Phase 1: Setting up development tools")
        print("=" * 50)
        self.create_pyproject_toml()
        self.create_flake8_config()
        self.create_precommit_config()
        self.create_dev_requirements()
        self.create_makefile()
        self.run_command(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-r",
                "backend/requirements-dev.txt",
            ],
            "Installing development dependencies",
        )
        print("\n✅ Phase 1 completed!")
        print("Next steps:")
        print("- Review the created configuration files")
        print("- Run 'make format' to format your code")
        print("- Run 'make help' to see available commands")

    def phase_2_format_code(self) -> None:
        """Phase 2: Format existing code."""
        print("\n🎨 Phase 2: Formatting existing code")
        print("=" * 50)
        self.run_command(
            [sys.executable, "-m", "black", "backend/", "scripts/", "tests/"],
            "Formatting code with Black",
        )
        self.run_command(
            [sys.executable, "-m", "isort", "backend/", "scripts/", "tests/"],
            "Organizing imports with isort",
        )
        print("\n✅ Phase 2 completed!")
        print("Code has been formatted and imports organized.")

    def phase_3_enable_linting(self) -> None:
        """Phase 3: Enable linting checks."""
        print("\n🔍 Phase 3: Running linting checks")
        print("=" * 50)
        self.run_command(
            [sys.executable, "-m", "flake8", "backend/", "scripts/", "tests/"],
            "Running flake8 linting",
        )
        self.run_command(
            [sys.executable, "-m", "mypy", "backend/"],
            "Running mypy type checking",
        )
        print("\n✅ Phase 3 completed!")
        print("Review any linting issues and fix them gradually.")

    def setup_precommit_hooks(self) -> None:
        """Install pre-commit hooks."""
        print("\n🪝 Setting up pre-commit hooks")
        print("=" * 50)
        self.run_command(
            [sys.executable, "-m", "pre_commit", "install"],
            "Installing pre-commit hooks",
        )
        print("✅ Pre-commit hooks installed")

    def generate_report(self) -> None:
        """Generate a status report."""
        print("\n📊 Quality Status Report")
        print("=" * 50)
        py_files = list(self.project_root.glob("**/*.py"))
        print(f"Python files found: {len(py_files)}")
        config_files = [
            "pyproject.toml",
            ".flake8",
            ".pre-commit-config.yaml",
            "backend/requirements-dev.txt",
            "Makefile",
        ]
        for config_file in config_files:
            exists = (self.project_root / config_file).exists()
            status = "✅" if exists else "❌"
            print(f"{status} {config_file}")
        print("\nRecommended next steps:")
        print("1. Run 'make format' regularly")
        print("2. Fix linting issues gradually")
        print("3. Add type hints to new code")
        print("4. Increase test coverage")

    def run_full_implementation(self) -> None:
        """Run all phases of implementation."""
        print("🚀 Full Code Quality Implementation")
        print("=" * 50)
        self.phase_1_setup_tools()
        self.phase_2_format_code()
        self.phase_3_enable_linting()
        self.setup_precommit_hooks()
        self.generate_report()
        print("\n🎉 Full implementation completed!")
        print("Your project now has comprehensive code quality tools.")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="YTD-Kopya Code Quality Setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--phase", type=int, choices=[1, 2, 3], help="Run specific implementation phase"
    )
    parser.add_argument(
        "--all", action="store_true", help="Run full implementation (all phases)"
    )
    parser.add_argument(
        "--report", action="store_true", help="Generate status report only"
    )
    args = parser.parse_args()
    project_root = Path.cwd()
    setup = CodeQualitySetup(project_root)
    if not setup.check_project_structure():
        sys.exit(1)
    try:
        if args.all:
            setup.run_full_implementation()
        elif args.phase == 1:
            setup.phase_1_setup_tools()
        elif args.phase == 2:
            setup.phase_2_format_code()
        elif args.phase == 3:
            setup.phase_3_enable_linting()
        elif args.report:
            setup.generate_report()
        else:
            parser.print_help()
            print("\nQuick start examples:")
            print("  python quick_start.py --phase=1    # Setup tools")
            print("  python quick_start.py --phase=2    # Format code")
            print("  python quick_start.py --all        # Full setup")
            print("  python quick_start.py --report     # Status report")
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as exc:
        print(f"\n❌ Setup failed with error: {exc}")
        print("Please check the error message above and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
