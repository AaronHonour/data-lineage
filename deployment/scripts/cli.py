#!/usr/bin/env python3
"""
Data Lineage Deployment CLI

A cross-platform command-line interface for deploying and managing
the data lineage system.

Usage:
    python cli.py                              # Interactive mode
    python cli.py list                         # List available runbooks
    python cli.py run <runbook>               # Run a specific runbook
    python cli.py run teardown --clean-volumes # Run with options

Available Runbooks:
    - infrastructure: Deploy Docker services
    - sample-data:    Register data sources and sync
    - validation:     Validate deployment
    - teardown:       Stop services and cleanup
"""

import sys
import subprocess
from pathlib import Path
from typing import List, Optional
from utils import (
    print_header,
    print_success,
    print_error,
    print_info,
    Colors
)


class Runbook:
    """Represents a deployment runbook."""

    def __init__(self, name: str, title: str, script: str, description: str, order: int):
        self.name = name
        self.title = title
        self.script = script
        self.description = description
        self.order = order


# Define available runbooks
RUNBOOKS = [
    Runbook(
        name="infrastructure",
        title="Infrastructure Deployment",
        script="deploy_infrastructure.py",
        description="Deploy all Docker services (databases, API, dbt)",
        order=1
    ),
    Runbook(
        name="sample-data",
        title="Sample Data Deployment",
        script="deploy_sample_data.py",
        description="Register data sources and trigger synchronization",
        order=2
    ),
    Runbook(
        name="validation",
        title="Deployment Validation",
        script="validate_deployment.py",
        description="Validate that the lineage system is working correctly",
        order=3
    ),
    Runbook(
        name="teardown",
        title="Teardown",
        script="teardown.py",
        description="Stop services and clean up deployment",
        order=4
    ),
]


class DeploymentCLI:
    """Main CLI interface for deployment operations."""

    def __init__(self):
        self.scripts_dir = Path(__file__).parent
        self.runbooks = {rb.name: rb for rb in RUNBOOKS}

    def list_runbooks(self):
        """List all available runbooks."""
        print_header("Available Deployment Runbooks")

        print("Runbooks are executed in the following order for full deployment:\n")

        for runbook in sorted(RUNBOOKS, key=lambda x: x.order):
            print(f"{Colors.BOLD}{runbook.order}. {runbook.name}{Colors.ENDC}")
            print(f"   {runbook.title}")
            print(f"   {runbook.description}\n")

        print("Usage:")
        print(f"  python cli.py run <runbook-name>")
        print(f"\nExample:")
        print(f"  python cli.py run infrastructure")

    def run_runbook(self, runbook_name: str, extra_args: List[str] = None) -> int:
        """Execute a specific runbook."""
        if runbook_name not in self.runbooks:
            print_error(f"Unknown runbook: {runbook_name}")
            print_info("Run 'python cli.py list' to see available runbooks")
            return 1

        runbook = self.runbooks[runbook_name]
        script_path = self.scripts_dir / runbook.script

        if not script_path.exists():
            print_error(f"Script not found: {script_path}")
            return 1

        print_header(f"Executing: {runbook.title}")

        # Build command
        cmd = [sys.executable, str(script_path)]

        if extra_args:
            cmd.extend(extra_args)

        # Execute script
        try:
            result = subprocess.run(cmd, check=False)
            return result.returncode

        except KeyboardInterrupt:
            print_error("\n\nExecution interrupted by user")
            return 1

        except Exception as e:
            print_error(f"Failed to execute runbook: {e}")
            return 1

    def run_full_deployment(self) -> int:
        """Run complete deployment sequence."""
        print_header("Full Deployment Sequence")

        print("This will execute all runbooks in order:")
        print("  1. Infrastructure deployment")
        print("  2. Sample data deployment")
        print("  3. Validation")

        response = input("\nContinue? [y/N]: ").strip().lower()

        if response not in ['y', 'yes']:
            print_info("Deployment cancelled")
            return 0

        # Execute runbooks in order
        for runbook in sorted(RUNBOOKS, key=lambda x: x.order):
            if runbook.name == "teardown":
                continue  # Skip teardown in full deployment

            result = self.run_runbook(runbook.name)

            if result != 0:
                print_error(f"\nDeployment failed at: {runbook.title}")
                print_info("You can retry this step with:")
                print_info(f"  python cli.py run {runbook.name}")
                return result

        print_success("\n🎉 Full deployment completed successfully!")
        return 0

    def interactive_mode(self):
        """Run CLI in interactive mode."""
        print_header("Data Lineage Deployment CLI")

        print("Select an operation:\n")
        print("1. Run full deployment (infrastructure + data + validation)")
        print("2. Run individual runbook")
        print("3. List available runbooks")
        print("4. Exit")

        while True:
            try:
                choice = input("\nEnter your choice (1-4): ").strip()

                if choice == "1":
                    return self.run_full_deployment()

                elif choice == "2":
                    self.list_runbooks()
                    runbook_name = input("\nEnter runbook name: ").strip()
                    return self.run_runbook(runbook_name)

                elif choice == "3":
                    self.list_runbooks()
                    continue

                elif choice == "4":
                    print_info("Exiting...")
                    return 0

                else:
                    print_error("Invalid choice. Please enter 1-4.")

            except KeyboardInterrupt:
                print_info("\n\nExiting...")
                return 0

    def show_help(self):
        """Show help message."""
        print(__doc__)


def main():
    """Main entry point."""
    cli = DeploymentCLI()

    # Parse command line arguments
    if len(sys.argv) == 1:
        # No arguments - interactive mode
        return cli.interactive_mode()

    command = sys.argv[1]

    if command in ['help', '--help', '-h']:
        cli.show_help()
        return 0

    elif command == 'list':
        cli.list_runbooks()
        return 0

    elif command == 'run':
        if len(sys.argv) < 3:
            print_error("Missing runbook name")
            print_info("Usage: python cli.py run <runbook-name>")
            return 1

        runbook_name = sys.argv[2]
        extra_args = sys.argv[3:] if len(sys.argv) > 3 else None

        return cli.run_runbook(runbook_name, extra_args)

    elif command == 'deploy':
        # Full deployment shortcut
        return cli.run_full_deployment()

    else:
        print_error(f"Unknown command: {command}")
        cli.show_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
