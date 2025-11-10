"""Utility functions for deployment scripts.

Provides cross-platform utilities for:
- Docker operations (start, stop, health checks)
- HTTP client with retries
- Logging and progress indication
- File operations
"""

import subprocess
import time
import sys
import json
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from urllib.parse import urljoin

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("ERROR: requests library not installed. Please run: pip install requests")
    sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class Colors:
    """ANSI color codes for cross-platform terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def disable():
        """Disable colors for Windows compatibility if needed."""
        Colors.HEADER = ''
        Colors.OKBLUE = ''
        Colors.OKCYAN = ''
        Colors.OKGREEN = ''
        Colors.WARNING = ''
        Colors.FAIL = ''
        Colors.ENDC = ''
        Colors.BOLD = ''
        Colors.UNDERLINE = ''


def print_header(message: str):
    """Print a formatted header message."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")


def print_success(message: str):
    """Print a success message."""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")


def print_error(message: str):
    """Print an error message."""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")


def print_warning(message: str):
    """Print a warning message."""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")


def print_info(message: str):
    """Print an info message."""
    print(f"{Colors.OKCYAN}ℹ {message}{Colors.ENDC}")


class DockerClient:
    """Cross-platform Docker client wrapper."""

    @staticmethod
    def is_available() -> bool:
        """Check if Docker is available."""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    @staticmethod
    def compose_up(compose_file: Path, detach: bool = True) -> bool:
        """Start Docker Compose services."""
        try:
            cmd = ["docker", "compose", "-f", str(compose_file), "up"]
            if detach:
                cmd.append("-d")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                logger.error(f"Docker compose up failed: {result.stderr}")
                return False

            return True
        except subprocess.TimeoutExpired:
            logger.error("Docker compose up timed out after 5 minutes")
            return False
        except Exception as e:
            logger.error(f"Docker compose up error: {e}")
            return False

    @staticmethod
    def compose_down(compose_file: Path, remove_volumes: bool = False) -> bool:
        """Stop Docker Compose services."""
        try:
            cmd = ["docker", "compose", "-f", str(compose_file), "down"]
            if remove_volumes:
                cmd.append("-v")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                logger.error(f"Docker compose down failed: {result.stderr}")
                return False

            return True
        except Exception as e:
            logger.error(f"Docker compose down error: {e}")
            return False

    @staticmethod
    def compose_ps(compose_file: Path) -> List[Dict[str, str]]:
        """Get status of Docker Compose services."""
        try:
            result = subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "ps", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return []

            # Parse JSON output (each line is a JSON object)
            services = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    services.append(json.loads(line))
            return services
        except Exception as e:
            logger.error(f"Docker compose ps error: {e}")
            return []

    @staticmethod
    def exec_command(container_name: str, command: List[str], timeout: int = 60) -> Optional[str]:
        """Execute a command in a running container."""
        try:
            cmd = ["docker", "exec", container_name] + command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode != 0:
                logger.error(f"Command failed in {container_name}: {result.stderr}")
                return None

            return result.stdout
        except Exception as e:
            logger.error(f"Docker exec error: {e}")
            return None

    @staticmethod
    def wait_for_health(container_name: str, max_wait: int = 120, check_interval: int = 5) -> bool:
        """Wait for a container to be healthy."""
        print_info(f"Waiting for {container_name} to be healthy...")

        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                result = subprocess.run(
                    ["docker", "inspect", "--format", "{{.State.Health.Status}}", container_name],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    status = result.stdout.strip()
                    if status == "healthy":
                        print_success(f"{container_name} is healthy")
                        return True
                    elif status == "unhealthy":
                        print_error(f"{container_name} is unhealthy")
                        return False

            except Exception as e:
                logger.debug(f"Health check error: {e}")

            time.sleep(check_interval)
            print(".", end="", flush=True)

        print()
        print_error(f"{container_name} did not become healthy within {max_wait} seconds")
        return False

    @staticmethod
    def wait_for_port(container_name: str, port: int, max_wait: int = 120, check_interval: int = 5) -> bool:
        """Wait for a port to be accessible in a container."""
        print_info(f"Waiting for {container_name}:{port} to be ready...")

        start_time = time.time()
        while time.time() - start_time < max_wait:
            # Try to connect to the port
            try:
                result = subprocess.run(
                    ["docker", "exec", container_name, "sh", "-c", f"nc -z localhost {port}"],
                    capture_output=True,
                    timeout=5
                )

                if result.returncode == 0:
                    print_success(f"{container_name}:{port} is ready")
                    return True

            except Exception:
                pass

            time.sleep(check_interval)
            print(".", end="", flush=True)

        print()
        print_error(f"{container_name}:{port} did not become ready within {max_wait} seconds")
        return False


class HTTPClient:
    """HTTP client with automatic retries and proper error handling."""

    def __init__(self, base_url: str, timeout: int = 30):
        """Initialize HTTP client with retry strategy."""
        self.base_url = base_url
        self.timeout = timeout

        # Configure retry strategy
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session = requests.Session()
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def get(self, endpoint: str, **kwargs) -> Optional[requests.Response]:
        """Send GET request."""
        try:
            url = urljoin(self.base_url, endpoint)
            response = self.session.get(url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"GET {endpoint} failed: {e}")
            return None

    def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, **kwargs) -> Optional[requests.Response]:
        """Send POST request."""
        try:
            url = urljoin(self.base_url, endpoint)
            response = self.session.post(url, json=json_data, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"POST {endpoint} failed: {e}")
            return None

    def delete(self, endpoint: str, **kwargs) -> Optional[requests.Response]:
        """Send DELETE request."""
        try:
            url = urljoin(self.base_url, endpoint)
            response = self.session.delete(url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"DELETE {endpoint} failed: {e}")
            return None

    def wait_for_api(self, health_endpoint: str = "/health", max_wait: int = 120, check_interval: int = 5) -> bool:
        """Wait for API to be available."""
        print_info(f"Waiting for API at {self.base_url} to be ready...")

        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                response = self.session.get(
                    urljoin(self.base_url, health_endpoint),
                    timeout=5
                )
                if response.status_code == 200:
                    print_success(f"API is ready at {self.base_url}")
                    return True
            except Exception:
                pass

            time.sleep(check_interval)
            print(".", end="", flush=True)

        print()
        print_error(f"API did not become ready within {max_wait} seconds")
        return False


def load_json_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Load JSON from file with error handling."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON from {file_path}: {e}")
        return None


def save_json_file(file_path: Path, data: Dict[str, Any]) -> bool:
    """Save JSON to file with error handling."""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save JSON to {file_path}: {e}")
        return False


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def get_deployment_root() -> Path:
    """Get the deployment directory."""
    return Path(__file__).parent.parent
