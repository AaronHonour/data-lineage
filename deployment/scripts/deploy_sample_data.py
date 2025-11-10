"""
Runbook 2: Sample Data Deployment

Registers all data sources with the lineage system and triggers synchronization:
1. Register PostgreSQL source
2. Register MySQL source
3. Register dbt project
4. Register Python jobs
5. Register Delta Lake
6. Trigger sync for each source
7. Wait for sync completion
8. Validate data was loaded
"""

import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID
from utils import (
    HTTPClient,
    print_header,
    print_success,
    print_error,
    print_info,
    print_warning,
    get_deployment_root,
    load_json_file,
    save_json_file,
    logger
)


class DataSourceDeployment:
    """Handles data source registration and synchronization."""

    def __init__(self, api_url: str = "http://localhost:8000"):
        self.http_client = HTTPClient(api_url)
        self.state_file = get_deployment_root() / "config" / "deployment-state.json"
        self.config_file = get_deployment_root() / "config" / "data-sources.json"

    def load_data_source_config(self) -> Optional[Dict]:
        """Load data source configuration."""
        return load_json_file(self.config_file)

    def save_deployment_state(self, state: Dict):
        """Save deployment state for tracking."""
        save_json_file(self.state_file, state)

    def load_deployment_state(self) -> Dict:
        """Load existing deployment state."""
        state = load_json_file(self.state_file)
        return state if state else {"data_sources": {}}

    def register_data_source(self, source_config: Dict) -> Optional[str]:
        """Register a single data source."""
        print_info(f"Registering: {source_config['name']}")

        response = self.http_client.post(
            "/api/v1/data-sources",
            json_data=source_config
        )

        if response is None:
            print_error(f"Failed to register {source_config['name']}")
            return None

        data = response.json()
        source_id = data.get('id')

        print_success(f"Registered: {source_config['name']} (ID: {source_id})")
        return source_id

    def trigger_sync(self, source_id: str, source_name: str) -> bool:
        """Trigger synchronization for a data source."""
        print_info(f"Triggering sync for: {source_name}")

        response = self.http_client.post(
            f"/api/v1/data-sources/{source_id}/sync"
        )

        if response is None:
            print_error(f"Failed to trigger sync for {source_name}")
            return False

        print_success(f"Sync triggered for: {source_name}")
        return True

    def wait_for_sync_completion(self, source_id: str, source_name: str, timeout: int = 300) -> bool:
        """Wait for sync to complete."""
        print_info(f"Waiting for sync completion: {source_name}")

        start_time = time.time()
        check_interval = 5

        while time.time() - start_time < timeout:
            # Get sync job status
            response = self.http_client.get(
                f"/api/v1/data-sources/{source_id}/sync-jobs",
                params={"limit": 1}
            )

            if response is None:
                time.sleep(check_interval)
                continue

            jobs = response.json()

            if not jobs:
                print_warning(f"No sync jobs found for {source_name}")
                return False

            latest_job = jobs[0]
            status = latest_job.get('status')

            if status == 'completed':
                stats = latest_job.get('statistics', {})
                print_success(f"Sync completed for {source_name}")
                print(f"  - Datasets: {stats.get('datasets_discovered', 0)}")
                print(f"  - Transformations: {stats.get('transformations_discovered', 0)}")
                print(f"  - Lineage edges: {stats.get('lineage_edges_created', 0)}")
                return True

            elif status == 'failed':
                error_msg = latest_job.get('error_message', 'Unknown error')
                print_error(f"Sync failed for {source_name}: {error_msg}")
                return False

            elif status in ['pending', 'running']:
                print(".", end="", flush=True)
                time.sleep(check_interval)

            else:
                print_warning(f"Unknown status '{status}' for {source_name}")
                time.sleep(check_interval)

        print()
        print_error(f"Sync timeout for {source_name} after {timeout} seconds")
        return False

    def deploy_all_sources(self) -> bool:
        """Deploy all data sources."""
        # Load configuration
        config = self.load_data_source_config()
        if not config:
            print_error("Failed to load data source configuration")
            return False

        # Load existing state
        state = self.load_deployment_state()

        sources_config = config.get('data_sources', [])
        print_info(f"Found {len(sources_config)} data sources to deploy")

        deployment_results = []

        # Register all sources
        print_header("Registering Data Sources")

        for source_config in sources_config:
            source_name = source_config['name']

            # Check if already registered
            if source_name in state.get('data_sources', {}):
                source_id = state['data_sources'][source_name]['id']
                print_info(f"Already registered: {source_name} (ID: {source_id})")
            else:
                source_id = self.register_data_source(source_config)
                if not source_id:
                    deployment_results.append((source_name, False))
                    continue

                # Save state
                if 'data_sources' not in state:
                    state['data_sources'] = {}
                state['data_sources'][source_name] = {
                    'id': source_id,
                    'type': source_config['source_type']
                }
                self.save_deployment_state(state)

            deployment_results.append((source_name, True, source_id))

        # Trigger syncs
        print_header("Triggering Synchronization")

        sync_results = []

        for result in deployment_results:
            if len(result) == 3:
                source_name, success, source_id = result
                if success:
                    sync_success = self.trigger_sync(source_id, source_name)
                    sync_results.append((source_name, source_id, sync_success))

        # Wait for sync completion
        print_header("Waiting for Sync Completion")

        final_results = []

        for source_name, source_id, sync_triggered in sync_results:
            if sync_triggered:
                completed = self.wait_for_sync_completion(source_id, source_name)
                final_results.append((source_name, completed))
            else:
                final_results.append((source_name, False))

        # Print summary
        print_header("Deployment Summary")

        successful = sum(1 for _, success in final_results if success)
        total = len(final_results)

        print(f"\nResults: {successful}/{total} sources deployed successfully\n")

        for source_name, success in final_results:
            if success:
                print_success(f"{source_name}")
            else:
                print_error(f"{source_name}")

        return successful == total


def check_prerequisites() -> bool:
    """Check if infrastructure is deployed."""
    print_header("Checking Prerequisites")

    print_info("Checking if API is available...")
    http_client = HTTPClient("http://localhost:8000")

    response = http_client.get("/health")
    if response is None:
        print_error("API is not available. Please run infrastructure deployment first:")
        print_error("  python scripts/cli.py run infrastructure")
        return False

    print_success("API is available")
    return True


def main() -> int:
    """Main execution function."""
    print_header("Sample Data Deployment - Runbook 2")

    try:
        # Check prerequisites
        if not check_prerequisites():
            return 1

        # Deploy all data sources
        deployer = DataSourceDeployment()

        if not deployer.deploy_all_sources():
            print_error("\nDeployment completed with errors")
            return 1

        print_success("\nSample data deployment successful!")
        print("\nNext Steps:")
        print("  - Run validation: python scripts/cli.py run validation")
        print("  - Query lineage: curl http://localhost:8000/api/v1/lineage/table/{dataset_id}")
        print("  - View API docs: http://localhost:8000/docs")

        return 0

    except KeyboardInterrupt:
        print_warning("\nDeployment interrupted by user")
        return 1

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        logger.exception("Deployment failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
