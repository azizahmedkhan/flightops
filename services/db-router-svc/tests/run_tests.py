#!/usr/bin/env python3
"""
Test runner for db-router-svc.

This script runs all tests for the db-router-svc service.
"""

import sys
import os
import subprocess
from pathlib import Path

# Add the service directory to the Python path
service_dir = Path(__file__).parent.parent
sys.path.insert(0, str(service_dir))

def run_tests():
    """Run all tests for the db-router-svc service."""
    print("Running db-router-svc tests...")
    print("=" * 50)
    
    # Change to the service directory
    os.chdir(service_dir)
    
    # Run pytest with verbose output
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--color=yes",
        "--durations=10"
    ]
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        return 0
    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 50)
        print(f"❌ Tests failed with exit code {e.returncode}")
        return e.returncode
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

def run_specific_test(test_file):
    """Run a specific test file."""
    print(f"Running test file: {test_file}")
    print("=" * 50)
    
    # Change to the service directory
    os.chdir(service_dir)
    
    # Run pytest for specific file
    cmd = [
        sys.executable, "-m", "pytest",
        f"tests/{test_file}",
        "-v",
        "--tb=short",
        "--color=yes"
    ]
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\n" + "=" * 50)
        print("✅ Test passed!")
        return 0
    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 50)
        print(f"❌ Test failed with exit code {e.returncode}")
        return e.returncode
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return 1

def run_coverage():
    """Run tests with coverage report."""
    print("Running tests with coverage...")
    print("=" * 50)
    
    # Change to the service directory
    os.chdir(service_dir)
    
    # Run pytest with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "--cov=.",
        "--cov-report=html",
        "--cov-report=term-missing",
        "-v"
    ]
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\n" + "=" * 50)
        print("✅ Coverage report generated!")
        print("HTML coverage report: htmlcov/index.html")
        return 0
    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 50)
        print(f"❌ Coverage test failed with exit code {e.returncode}")
        return e.returncode
    except Exception as e:
        print(f"❌ Error running coverage: {e}")
        return 1

def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "coverage":
            return run_coverage()
        elif command.startswith("test_"):
            return run_specific_test(command)
        else:
            print(f"Unknown command: {command}")
            print("Usage: python run_tests.py [coverage|test_filename]")
            return 1
    else:
        return run_tests()

if __name__ == "__main__":
    sys.exit(main())
