#!/usr/bin/env python
"""
Integration Test Runner
========================
Convenient script to run integration tests with various options.

Usage:
    python run_integration_tests.py                    # Run all tests
    python run_integration_tests.py --fast             # Skip slow tests
    python run_integration_tests.py --coverage         # With coverage
    python run_integration_tests.py --api              # Only API tests
    python run_integration_tests.py --database         # Only DB tests

Author: Production Team
Version: 1.0.0
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str]) -> int:
    """Run command and return exit code."""
    print(f"\n🚀 Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)
    return result.returncode


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Run integration tests for AstroGeo AI")

    parser.add_argument("--fast", action="store_true", help="Skip slow tests")

    parser.add_argument("--coverage", action="store_true", help="Run with coverage report")

    parser.add_argument("--api", action="store_true", help="Run only API workflow tests")

    parser.add_argument("--database", action="store_true", help="Run only database tests")

    parser.add_argument("--agents", action="store_true", help="Run only agent workflow tests")

    parser.add_argument("--monitoring", action="store_true", help="Run only monitoring tests")

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    parser.add_argument("--debug", action="store_true", help="Drop into debugger on failure")

    args = parser.parse_args()

    # Base command
    cmd = ["pytest", "tests/integration/"]

    # Add verbose flag
    if args.verbose:
        cmd.append("-vv")
    else:
        cmd.append("-v")

    # Add coverage
    if args.coverage:
        cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term"])

    # Add debugger
    if args.debug:
        cmd.append("--pdb")

    # Filter by test type
    if args.api:
        cmd.append("tests/integration/test_api_workflows.py")
    elif args.database:
        cmd.append("tests/integration/test_database.py")
    elif args.agents:
        cmd.append("tests/integration/test_agent_workflows.py")
    elif args.monitoring:
        cmd.append("tests/integration/test_monitoring.py")

    # Skip slow tests
    if args.fast:
        cmd.extend(["-m", "not slow"])

    # Run tests
    exit_code = run_command(cmd)

    # Print summary
    if exit_code == 0:
        print("\n✅ All tests passed!")
        if args.coverage:
            print("\n📊 Coverage report generated: htmlcov/index.html")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
