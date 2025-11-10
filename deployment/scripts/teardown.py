"""
Runbook 4: Teardown

Tears down the deployment and optionally cleans up data:
1. Stop all Docker services
2. Optionally remove volumes (data cleanup)
3. Optionally remove deployment state
4. Verify cleanup
"""

import sys
import argparse
from pathlib import Path
from utils import (
    DockerClient,
    print_header,
    print_success,
    print_error,
    print_info,
    print_warning,
    get_deployment_root,
    logger
)


def confirm_action(message: str, default: bool = False) -> bool:
    """Ask user for confirmation."""
    prompt = f"{message} [y/N]: " if not default else f"{message} [Y/n]: "
    response = input(prompt).strip().lower()

    if not response:
        return default

    return response in ['y', 'yes']


def stop_services(remove_volumes: bool = False) -> bool:
    """Stop Docker services."""
    print_header("Stopping Docker Services")

    compose_file = get_deployment_root() / "docker-compose.sample.yml"

    if not compose_file.exists():
        print_error(f"Docker Compose file not found: {compose_file}")
        return False

    print_info("Stopping services...")

    if not DockerClient.compose_down(compose_file, remove_volumes=remove_volumes):
        print_error("Failed to stop Docker services")
        return False

    if remove_volumes:
        print_success("Docker services stopped and volumes removed")
    else:
        print_success("Docker services stopped (volumes preserved)")

    return True


def clean_deployment_state() -> bool:
    """Remove deployment state file."""
    print_header("Cleaning Deployment State")

    state_file = get_deployment_root() / "config" / "deployment-state.json"

    if not state_file.exists():
        print_info("No deployment state file found")
        return True

    try:
        state_file.unlink()
        print_success("Deployment state file removed")
        return True
    except Exception as e:
        print_error(f"Failed to remove state file: {e}")
        return False


def clean_generated_data() -> bool:
    """Remove generated data files."""
    print_header("Cleaning Generated Data")

    delta_path = get_deployment_root() / "sample-data" / "delta-lake"

    if not delta_path.exists():
        print_info("No delta-lake directory found")
        return True

    # Remove parquet files
    removed_count = 0
    try:
        for file in delta_path.rglob("*.parquet"):
            file.unlink()
            removed_count += 1

        if removed_count > 0:
            print_success(f"Removed {removed_count} generated data file(s)")
        else:
            print_info("No generated data files found")

        return True

    except Exception as e:
        print_error(f"Failed to clean generated data: {e}")
        return False


def verify_cleanup() -> bool:
    """Verify cleanup was successful."""
    print_header("Verifying Cleanup")

    compose_file = get_deployment_root() / "docker-compose.sample.yml"
    services = DockerClient.compose_ps(compose_file)

    if services:
        print_warning(f"Warning: {len(services)} service(s) still running")
        for service in services:
            service_name = service.get('Service', service.get('Name', 'unknown'))
            print(f"  - {service_name}")
        return False
    else:
        print_success("All services stopped")

    return True


def print_cleanup_info(removed_volumes: bool, removed_state: bool, removed_data: bool):
    """Print cleanup summary."""
    print_header("Teardown Complete")

    print("Cleanup Summary:")
    print(f"  ✓ Docker services stopped")

    if removed_volumes:
        print(f"  ✓ Docker volumes removed")
    else:
        print(f"  - Docker volumes preserved")

    if removed_state:
        print(f"  ✓ Deployment state cleaned")
    else:
        print(f"  - Deployment state preserved")

    if removed_data:
        print(f"  ✓ Generated data files cleaned")
    else:
        print(f"  - Generated data files preserved")

    print("\nTo redeploy:")
    print("  1. python scripts/cli.py run infrastructure")
    print("  2. python scripts/cli.py run sample-data")
    print("  3. python scripts/cli.py run validation")

    if not removed_volumes:
        print("\nTo perform a complete cleanup:")
        print("  python scripts/cli.py run teardown --clean-volumes")


def main() -> int:
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Teardown deployment")
    parser.add_argument(
        '--clean-volumes',
        action='store_true',
        help='Remove Docker volumes (deletes all data)'
    )
    parser.add_argument(
        '--clean-state',
        action='store_true',
        help='Remove deployment state file'
    )
    parser.add_argument(
        '--clean-data',
        action='store_true',
        help='Remove generated data files'
    )
    parser.add_argument(
        '--yes',
        '-y',
        action='store_true',
        help='Skip confirmation prompts'
    )

    args = parser.parse_args()

    print_header("Teardown - Runbook 4")

    try:
        # Confirm destructive actions
        if args.clean_volumes and not args.yes:
            if not confirm_action("⚠️  This will delete all database data. Continue?"):
                print_info("Teardown cancelled")
                return 0

        # Stop services
        if not stop_services(remove_volumes=args.clean_volumes):
            return 1

        # Clean state if requested
        if args.clean_state:
            clean_deployment_state()

        # Clean generated data if requested
        if args.clean_data:
            clean_generated_data()

        # Verify cleanup
        verify_cleanup()

        # Print summary
        print_cleanup_info(
            removed_volumes=args.clean_volumes,
            removed_state=args.clean_state,
            removed_data=args.clean_data
        )

        return 0

    except KeyboardInterrupt:
        print_warning("\nTeardown interrupted by user")
        return 1

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        logger.exception("Teardown failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
