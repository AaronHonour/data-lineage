"""Regression testing framework with version-controlled snapshots."""
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from deepdiff import DeepDiff


@dataclass
class RegressionResult:
    """Result of a regression test."""
    test_id: str
    passed: bool
    has_baseline: bool
    diff: Optional[str] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    confidence_score: float = 0.0


@dataclass
class SnapshotMetadata:
    """Metadata for a snapshot."""
    test_id: str
    created_at: str
    updated_at: str
    hash: str
    parser_version: str = "1.0.0"
    notes: str = ""


class LineageSnapshot:
    """Manages lineage snapshots for regression testing."""

    def __init__(self, snapshot_dir: Path):
        """
        Initialize snapshot manager.

        Args:
            snapshot_dir: Directory for storing snapshots
        """
        self.snapshot_dir = snapshot_dir
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir = snapshot_dir / "_metadata"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def _get_snapshot_path(self, test_id: str) -> Path:
        """Get path for snapshot file."""
        return self.snapshot_dir / f"{test_id}.snapshot.json"

    def _get_metadata_path(self, test_id: str) -> Path:
        """Get path for metadata file."""
        return self.metadata_dir / f"{test_id}.meta.json"

    def _compute_hash(self, data: dict) -> str:
        """Compute hash of snapshot data."""
        # Convert to canonical JSON for consistent hashing
        canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()

    def load_snapshot(self, test_id: str) -> Optional[dict]:
        """
        Load snapshot for test case.

        Args:
            test_id: Test identifier

        Returns:
            Snapshot data or None if not exists
        """
        snapshot_path = self._get_snapshot_path(test_id)
        if not snapshot_path.exists():
            return None

        with open(snapshot_path) as f:
            return json.load(f)

    def load_metadata(self, test_id: str) -> Optional[SnapshotMetadata]:
        """
        Load snapshot metadata.

        Args:
            test_id: Test identifier

        Returns:
            Metadata or None if not exists
        """
        metadata_path = self._get_metadata_path(test_id)
        if not metadata_path.exists():
            return None

        with open(metadata_path) as f:
            data = json.load(f)
            return SnapshotMetadata(**data)

    def save_snapshot(
        self,
        test_id: str,
        data: dict,
        notes: str = "",
        update: bool = False
    ) -> SnapshotMetadata:
        """
        Save snapshot for test case.

        Args:
            test_id: Test identifier
            data: Snapshot data
            notes: Optional notes about this snapshot
            update: If True, update existing snapshot

        Returns:
            Snapshot metadata

        Raises:
            ValueError: If snapshot exists and update=False
        """
        snapshot_path = self._get_snapshot_path(test_id)
        metadata_path = self._get_metadata_path(test_id)

        # Check if snapshot exists
        existing_metadata = self.load_metadata(test_id)
        if existing_metadata and not update:
            raise ValueError(
                f"Snapshot for {test_id} already exists. Use update=True to overwrite."
            )

        # Compute hash
        data_hash = self._compute_hash(data)

        # Create metadata
        now = datetime.utcnow().isoformat()
        metadata = SnapshotMetadata(
            test_id=test_id,
            created_at=existing_metadata.created_at if existing_metadata else now,
            updated_at=now,
            hash=data_hash,
            notes=notes
        )

        # Save snapshot
        with open(snapshot_path, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)

        # Save metadata
        with open(metadata_path, 'w') as f:
            json.dump(asdict(metadata), f, indent=2)

        return metadata

    def delete_snapshot(self, test_id: str) -> bool:
        """
        Delete snapshot and metadata.

        Args:
            test_id: Test identifier

        Returns:
            True if deleted, False if not found
        """
        snapshot_path = self._get_snapshot_path(test_id)
        metadata_path = self._get_metadata_path(test_id)

        deleted = False

        if snapshot_path.exists():
            snapshot_path.unlink()
            deleted = True

        if metadata_path.exists():
            metadata_path.unlink()
            deleted = True

        return deleted

    def list_snapshots(self) -> List[str]:
        """
        List all snapshot test IDs.

        Returns:
            List of test IDs
        """
        snapshots = []
        for path in self.snapshot_dir.glob("*.snapshot.json"):
            snapshots.append(path.stem.replace(".snapshot", ""))
        return sorted(snapshots)


class RegressionTester:
    """Run regression tests against snapshots."""

    def __init__(
        self,
        snapshot_manager: LineageSnapshot,
        auto_approve: bool = False,
        verbose: bool = True
    ):
        """
        Initialize regression tester.

        Args:
            snapshot_manager: Snapshot manager instance
            auto_approve: Automatically approve new baselines
            verbose: Print detailed output
        """
        self.snapshot_manager = snapshot_manager
        self.auto_approve = auto_approve
        self.verbose = verbose

    def compare_lineage(
        self,
        expected: dict,
        actual: dict,
        ignore_keys: Optional[List[str]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Compare lineage results with detailed diff.

        Args:
            expected: Expected lineage data
            actual: Actual lineage data
            ignore_keys: Keys to ignore in comparison

        Returns:
            Tuple of (matches, diff_report)
        """
        # Default keys to ignore
        if ignore_keys is None:
            ignore_keys = ['execution_time_ms', 'timestamp']

        # Remove ignored keys
        expected_filtered = self._filter_dict(expected, ignore_keys)
        actual_filtered = self._filter_dict(actual, ignore_keys)

        # Compare
        diff = DeepDiff(
            expected_filtered,
            actual_filtered,
            ignore_order=True,
            significant_digits=6  # For float comparison
        )

        if not diff:
            return True, None

        # Format diff for human readability
        diff_report = self._format_diff(diff)
        return False, diff_report

    def _filter_dict(self, data: dict, ignore_keys: List[str]) -> dict:
        """Recursively filter dictionary removing ignored keys."""
        if not isinstance(data, dict):
            return data

        filtered = {}
        for key, value in data.items():
            if key in ignore_keys:
                continue

            if isinstance(value, dict):
                filtered[key] = self._filter_dict(value, ignore_keys)
            elif isinstance(value, list):
                filtered[key] = [
                    self._filter_dict(item, ignore_keys) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                filtered[key] = value

        return filtered

    def _format_diff(self, diff: DeepDiff) -> str:
        """Format DeepDiff output for readability."""
        lines = []

        if 'values_changed' in diff:
            lines.append("❌ Changed values:")
            for path, change in diff['values_changed'].items():
                lines.append(f"  {path}:")
                lines.append(f"    Expected: {change['old_value']}")
                lines.append(f"    Actual:   {change['new_value']}")

        if 'iterable_item_added' in diff:
            lines.append("\n➕ Added items:")
            for path, value in diff['iterable_item_added'].items():
                lines.append(f"  {path}: {value}")

        if 'iterable_item_removed' in diff:
            lines.append("\n➖ Removed items:")
            for path, value in diff['iterable_item_removed'].items():
                lines.append(f"  {path}: {value}")

        if 'type_changes' in diff:
            lines.append("\n⚠️  Type changes:")
            for path, change in diff['type_changes'].items():
                lines.append(f"  {path}: {change['old_type']} → {change['new_type']}")

        return "\n".join(lines)

    def test_against_snapshot(
        self,
        test_id: str,
        actual_result: dict,
        min_confidence: float = 0.8
    ) -> RegressionResult:
        """
        Test actual result against snapshot.

        Args:
            test_id: Test identifier
            actual_result: Actual lineage result
            min_confidence: Minimum acceptable confidence score

        Returns:
            RegressionResult with test outcome
        """
        # Load snapshot
        snapshot = self.snapshot_manager.load_snapshot(test_id)

        # Check confidence score if present
        confidence = actual_result.get('confidence_score', 1.0)
        if confidence < min_confidence:
            return RegressionResult(
                test_id=test_id,
                passed=False,
                has_baseline=snapshot is not None,
                error=f"Confidence score {confidence:.2f} below minimum {min_confidence:.2f}",
                confidence_score=confidence
            )

        # No snapshot - create new baseline
        if snapshot is None:
            if self.auto_approve:
                self.snapshot_manager.save_snapshot(
                    test_id,
                    actual_result,
                    notes="Auto-approved initial baseline"
                )
                if self.verbose:
                    print(f"✓ Created baseline for {test_id}")

                return RegressionResult(
                    test_id=test_id,
                    passed=True,
                    has_baseline=False,
                    confidence_score=confidence
                )
            else:
                if self.verbose:
                    print(f"⚠ No baseline for {test_id} - needs manual approval")

                return RegressionResult(
                    test_id=test_id,
                    passed=False,
                    has_baseline=False,
                    error="No baseline snapshot - needs approval",
                    confidence_score=confidence
                )

        # Compare with snapshot
        matches, diff = self.compare_lineage(snapshot, actual_result)

        if matches:
            if self.verbose:
                print(f"✓ {test_id} - PASSED")

            return RegressionResult(
                test_id=test_id,
                passed=True,
                has_baseline=True,
                confidence_score=confidence
            )
        else:
            if self.verbose:
                print(f"✗ {test_id} - FAILED")
                if diff:
                    print(f"  Diff:\n{diff}")

            return RegressionResult(
                test_id=test_id,
                passed=False,
                has_baseline=True,
                diff=diff,
                confidence_score=confidence
            )

    def approve_baseline(self, test_id: str, data: dict, notes: str = "") -> None:
        """
        Manually approve a baseline snapshot.

        Args:
            test_id: Test identifier
            data: Snapshot data
            notes: Approval notes
        """
        self.snapshot_manager.save_snapshot(
            test_id,
            data,
            notes=notes or f"Manually approved on {datetime.utcnow().isoformat()}"
        )
        print(f"✓ Approved baseline for {test_id}")

    def update_baseline(self, test_id: str, data: dict, notes: str = "") -> None:
        """
        Update existing baseline (for intentional changes).

        Args:
            test_id: Test identifier
            data: New snapshot data
            notes: Update notes
        """
        self.snapshot_manager.save_snapshot(
            test_id,
            data,
            notes=notes or f"Updated on {datetime.utcnow().isoformat()}",
            update=True
        )
        print(f"✓ Updated baseline for {test_id}")


class RegressionReporter:
    """Generate regression test reports."""

    @staticmethod
    def generate_summary(results: List[RegressionResult]) -> dict:
        """
        Generate summary statistics from results.

        Args:
            results: List of regression results

        Returns:
            Summary statistics dictionary
        """
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)
        no_baseline = sum(1 for r in results if not r.has_baseline)

        avg_confidence = sum(r.confidence_score for r in results) / total if total > 0 else 0

        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "no_baseline": no_baseline,
            "pass_rate": (passed / total * 100) if total > 0 else 0,
            "avg_confidence": avg_confidence,
            "needs_approval": [r.test_id for r in results if not r.has_baseline],
            "failures": [r.test_id for r in results if r.has_baseline and not r.passed]
        }

    @staticmethod
    def print_summary(results: List[RegressionResult]) -> None:
        """Print formatted summary."""
        summary = RegressionReporter.generate_summary(results)

        print("\n" + "="*60)
        print("REGRESSION TEST SUMMARY")
        print("="*60)
        print(f"Total Tests:      {summary['total_tests']}")
        print(f"Passed:           {summary['passed']} ({summary['pass_rate']:.1f}%)")
        print(f"Failed:           {summary['failed']}")
        print(f"No Baseline:      {summary['no_baseline']}")
        print(f"Avg Confidence:   {summary['avg_confidence']:.2f}")

        if summary['needs_approval']:
            print(f"\n⚠ Tests needing baseline approval:")
            for test_id in summary['needs_approval']:
                print(f"  - {test_id}")

        if summary['failures']:
            print(f"\n❌ Failed tests:")
            for test_id in summary['failures']:
                print(f"  - {test_id}")

        print("="*60 + "\n")

    @staticmethod
    def save_report(results: List[RegressionResult], output_path: Path) -> None:
        """
        Save detailed report to JSON file.

        Args:
            results: List of regression results
            output_path: Output file path
        """
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "summary": RegressionReporter.generate_summary(results),
            "results": [asdict(r) for r in results]
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Report saved to {output_path}")
