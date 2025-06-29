#!/usr/bin/env python3
"""
Test runner script for Brum Brum Tracker
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n{'=' * 60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('=' * 60)
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode != 0:
        print(f"\n❌ {description} failed with exit code {result.returncode}")
        return False
    
    print(f"\n✅ {description} passed")
    return True


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description='Run tests for Brum Brum Tracker')
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests only')
    parser.add_argument('--coverage', action='store_true', help='Generate coverage report')
    parser.add_argument('--lint', action='store_true', help='Run linting checks')
    parser.add_argument('--security', action='store_true', help='Run security checks')
    parser.add_argument('--all', action='store_true', help='Run all checks')
    parser.add_argument('--install', action='store_true', help='Install test dependencies')
    
    args = parser.parse_args()
    
    # If no specific option, run unit tests by default
    if not any([args.unit, args.integration, args.coverage, args.lint, args.security, args.all]):
        args.unit = True
    
    # Install dependencies if requested
    if args.install:
        print("Installing test dependencies...")
        if not run_command([sys.executable, '-m', 'pip', 'install', '-r', 'requirements-test.txt'], 
                          'Install test dependencies'):
            return 1
    
    success = True
    
    # Run unit tests
    if args.unit or args.all:
        cmd = [sys.executable, '-m', 'pytest', 'tests/unit', '-v', '-m', 'unit']
        if args.coverage or args.all:
            cmd.extend(['--cov=backend', '--cov-report=html', '--cov-report=term'])
        success &= run_command(cmd, 'Unit Tests')
    
    # Run integration tests
    if args.integration or args.all:
        cmd = [sys.executable, '-m', 'pytest', 'tests/integration', '-v', '-m', 'integration']
        success &= run_command(cmd, 'Integration Tests')
    
    # Run linting
    if args.lint or args.all:
        # Black formatting check
        success &= run_command(
            [sys.executable, '-m', 'black', '--check', 'backend/', 'tests/'],
            'Black Formatting Check'
        )
        
        # isort import sorting check
        success &= run_command(
            [sys.executable, '-m', 'isort', '--check-only', 'backend/', 'tests/'],
            'Import Sorting Check'
        )
        
        # Flake8 linting
        success &= run_command(
            [sys.executable, '-m', 'flake8', 'backend/', 'tests/', '--max-line-length=100'],
            'Flake8 Linting'
        )
        
        # MyPy type checking
        success &= run_command(
            [sys.executable, '-m', 'mypy', 'backend/', '--ignore-missing-imports'],
            'MyPy Type Checking'
        )
    
    # Run security checks
    if args.security or args.all:
        # Bandit security scanning
        success &= run_command(
            [sys.executable, '-m', 'bandit', '-r', 'backend/', '-ll'],
            'Bandit Security Scan'
        )
        
        # Safety dependency check
        success &= run_command(
            [sys.executable, '-m', 'safety', 'check'],
            'Safety Dependency Check'
        )
    
    # Summary
    print(f"\n{'=' * 60}")
    if success:
        print("✅ All tests passed!")
        if args.coverage or args.all:
            print("\n📊 Coverage report generated in htmlcov/index.html")
    else:
        print("❌ Some tests failed!")
    print('=' * 60)
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())