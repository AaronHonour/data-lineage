"""
Runbook 1: Infrastructure Deployment

Deploys all Docker services required for the lineage system:
- PostgreSQL (lineage metadata DB)
- PostgreSQL (source operational DB)
- MySQL (source auxiliary DB)
- Backend API service
- dbt service
"""

import sys
import time
from pathlib import Path
from utils import (
    DockerClient,
    HTTPClient,
    print_header,
    print_success,
    print_error,
    print_info,
    print_warning,
    get_deployment_root,
    logger
)


def check_prerequisites() -> bool:
    """Check if all prerequisites are met."""
    print_header("Checking Prerequisites")

    # Check Docker availability
    print_info("Checking Docker availability...")
    if not DockerClient.is_available():
        print_error("Docker is not available. Please install Docker and ensure it's running.")
        return False
    print_success("Docker is available")

    # Check docker-compose.sample.yml exists
    compose_file = get_deployment_root() / "docker-compose.sample.yml"
    if not compose_file.exists():
        print_error(f"Docker Compose file not found: {compose_file}")
        return False
    print_success(f"Docker Compose file found: {compose_file}")

    return True


def start_services() -> bool:
    """Start all Docker services."""
    print_header("Starting Docker Services")

    compose_file = get_deployment_root() / "docker-compose.sample.yml"

    print_info("Starting services with docker compose...")
    if not DockerClient.compose_up(compose_file):
        print_error("Failed to start Docker services")
        return False

    print_success("Docker Compose started successfully")
    return True


def wait_for_services() -> bool:
    """Wait for all services to be healthy."""
    print_header("Waiting for Services to be Healthy")

    services_to_check = [
        ("lineage-db", 5432, 120),
        ("postgres-source", 5432, 120),
        ("mysql-source", 3306, 120),
    ]

    for container_name, port, max_wait in services_to_check:
        if not DockerClient.wait_for_port(container_name, port, max_wait):
            print_error(f"Service {container_name} did not become healthy")
            return False

    # Wait for API service
    print_info("Waiting for lineage API to be ready...")
    http_client = HTTPClient("http://localhost:8000")

    if not http_client.wait_for_api("/health", max_wait=180):
        print_error("Lineage API did not become ready")
        return False

    print_success("All services are healthy and ready")
    return True


def verify_deployment() -> bool:
    """Verify the deployment is working correctly."""
    print_header("Verifying Deployment")

    # Check all containers are running
    compose_file = get_deployment_root() / "docker-compose.sample.yml"
    services = DockerClient.compose_ps(compose_file)

    if not services:
        print_error("No services found running")
        return False

    print_info(f"Found {len(services)} running services:")
    for service in services:
        service_name = service.get('Service', service.get('Name', 'unknown'))
        state = service.get('State', service.get('Status', 'unknown'))
        print(f"  - {service_name}: {state}")

    # Verify API health endpoint
    http_client = HTTPClient("http://localhost:8000")
    response = http_client.get("/health")

    if response is None:
        print_error("Failed to connect to API health endpoint")
        return False

    print_success("API health check passed")

    # Verify database connectivity via API
    response = http_client.get("/api/v1/data-sources")

    if response is None:
        print_error("Failed to query data sources endpoint")
        return False

    print_success("Database connectivity verified")

    return True


def print_deployment_info():
    """Print deployment information and next steps."""
    print_header("Deployment Complete")

    print_success("Infrastructure deployment successful!\n")

    print("Service Endpoints:")
    print("  - Lineage API:        http://localhost:8000")
    print("  - API Documentation:  http://localhost:8000/docs")
    print("  - Lineage DB:         localhost:5432 (lineage/lineage_user)")
    print("  - PostgreSQL Source:  localhost:5433 (ecommerce/source_user)")
    print("  - MySQL Source:       localhost:3306 (auxiliary/mysql_user)")

    print("\nNext Steps:")
    print("  1. Run: python scripts/cli.py run sample-data")
    print("     This will register data sources and trigger sync")
    print("\n  2. Run: python scripts/cli.py run validation")
    print("     This will validate the lineage graph was built correctly")

    print("\nUseful Commands:")
    print("  - View logs:       docker compose -f docker-compose.sample.yml logs -f")
    print("  - Stop services:   python scripts/cli.py run teardown")
    print("  - Restart services: docker compose -f docker-compose.sample.yml restart")


def rollback():
    """Rollback deployment on failure."""
    print_warning("\nRolling back deployment...")

    compose_file = get_deployment_root() / "docker-compose.sample.yml"
    DockerClient.compose_down(compose_file, remove_volumes=False)

    print_info("Rollback complete. Services stopped but volumes preserved.")
    print_info("To clean up volumes, run: python scripts/cli.py run teardown --clean-volumes")


def main() -> int:
    """Main execution function."""
    print_header("Infrastructure Deployment - Runbook 1")

    try:
        # Step 1: Check prerequisites
        if not check_prerequisites():
            return 1

        # Step 2: Start services
        if not start_services():
            rollback()
            return 1

        # Step 3: Wait for services to be ready
        if not wait_for_services():
            rollback()
            return 1

        # Step 4: Verify deployment
        if not verify_deployment():
            rollback()
            return 1

        # Step 5: Print success info
        print_deployment_info()

        return 0

    except KeyboardInterrupt:
        print_warning("\nDeployment interrupted by user")
        rollback()
        return 1

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        logger.exception("Deployment failed with exception")
        rollback()
        return 1


if __name__ == "__main__":
    sys.exit(main())
