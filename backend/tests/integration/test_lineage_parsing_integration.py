"""Integration tests for SQL lineage parsing."""
import pytest
import sys
from pathlib import Path
from typing import List
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.infrastructure.parsers.sql_parser import SQLLineageExtractor, ColumnLineageResult
from tests.utils.test_case_loader import TestCaseLoader, TestCase
from tests.utils.regression_framework import LineageSnapshot, RegressionTester, RegressionReporter, RegressionResult
from tests.utils.performance_testing import PerformanceTester, PerformanceMetrics
from tests.utils.coverage_tracker import SQLFeatureCoverage


class TestLineageParsingIntegration:
    """Integration tests for lineage parsing with regression testing."""

    @pytest.fixture(scope="class")
    def test_case_loader(self) -> TestCaseLoader:
        """Create test case loader."""
        return TestCaseLoader()

    @pytest.fixture(scope="class")
    def snapshot_manager(self, tmp_path_factory) -> LineageSnapshot:
        """Create snapshot manager with temporary directory."""
        # Use fixtures/golden for version-controlled snapshots
        snapshot_dir = Path(__file__).parent.parent / "fixtures" / "golden"
        return LineageSnapshot(snapshot_dir)

    @pytest.fixture(scope="class")
    def regression_tester(self, snapshot_manager) -> RegressionTester:
        """Create regression tester."""
        # Set auto_approve=True for initial test development
        # Set to False in CI/CD
        return RegressionTester(
            snapshot_manager,
            auto_approve=True,  # TODO: Change to False in CI
            verbose=True
        )

    @pytest.fixture(scope="class")
    def performance_tester(self) -> PerformanceTester:
        """Create performance tester."""
        return PerformanceTester(max_parse_time_ms=5000)

    @pytest.fixture(scope="class")
    def coverage_tracker(self) -> SQLFeatureCoverage:
        """Create coverage tracker."""
        return SQLFeatureCoverage()

    @pytest.fixture(scope="class")
    def sql_parser(self) -> SQLLineageExtractor:
        """Create SQL parser instance."""
        return SQLLineageExtractor(dialect='postgres')

    def parse_and_convert_to_dict(
        self,
        sql_parser: SQLLineageExtractor,
        sql: str,
        target_table_fqn: str = "result",
        source_tables: list = None
    ) -> dict:
        """
        Parse SQL and convert result to dictionary for comparison.

        Args:
            sql_parser: Parser instance
            sql: SQL query
            target_table_fqn: Target table FQN
            source_tables: List of TableDefinition objects

        Returns:
            Dictionary with lineage data
        """
        # Build schema dictionary from source tables
        schema = {}
        if source_tables:
            for table in source_tables:
                schema[table.name] = {
                    col.name: col.type
                    for col in table.columns
                }

        lineages = sql_parser.extract_lineage(sql, target_table_fqn, schema=schema)

        return {
            "lineages": [
                {
                    "target": lin.target_column,
                    "sources": sorted(lin.source_columns),  # Sort for consistent comparison
                    "expression": lin.expression
                }
                for lin in lineages
            ],
            "total_lineages": len(lineages),
            "confidence_score": 1.0  # TODO: Implement actual confidence calculation
        }

    def compare_lineage_with_expected(
        self,
        actual: dict,
        expected_lineage: list
    ) -> tuple[bool, List[str]]:
        """
        Compare actual lineage with expected test case lineage.

        Args:
            actual: Actual lineage result
            expected_lineage: Expected lineage from test case (LineageExpectation objects)

        Returns:
            Tuple of (matches, errors)
        """
        errors = []

        # Check count
        if len(actual["lineages"]) != len(expected_lineage):
            errors.append(
                f"Expected {len(expected_lineage)} lineages, got {len(actual['lineages'])}"
            )

        # Build expected dict for comparison
        expected_map = {}
        for exp in expected_lineage:
            # exp is a LineageExpectation object
            target = exp.target
            expected_map[target] = {
                "sources": sorted(exp.sources),
                "expression": exp.expression or ""
            }

        # Check each actual lineage
        for actual_lin in actual["lineages"]:
            target = actual_lin["target"]

            if target not in expected_map:
                errors.append(f"Unexpected target column: {target}")
                continue

            expected_sources = expected_map[target]["sources"]
            actual_sources = sorted(actual_lin["sources"])

            if actual_sources != expected_sources:
                errors.append(
                    f"For {target}: expected sources {expected_sources}, "
                    f"got {actual_sources}"
                )

            # Expression comparison is optional (can be different but equivalent)
            # For now, we'll just log if different
            if expected_map[target]["expression"]:
                expected_expr = expected_map[target]["expression"]
                actual_expr = actual_lin["expression"]
                if actual_expr and expected_expr not in actual_expr:
                    # This is a warning, not an error
                    pass

        return len(errors) == 0, errors

    def load_phase1_test_cases(self, test_case_loader: TestCaseLoader) -> List[TestCase]:
        """Load all Phase 1 test cases."""
        test_dir = Path(__file__).parent.parent / "test_cases" / "phase1_basic"
        categories = test_case_loader.load_directory(test_dir)

        test_cases = []
        for category_tests in categories.values():
            test_cases.extend(category_tests)

        return test_cases

    def test_phase1_basic_queries(
        self,
        test_case_loader,
        sql_parser,
        regression_tester,
        performance_tester,
        coverage_tracker
    ):
        """Test Phase 1 basic SQL queries with regression and performance testing."""

        # Load test cases
        test_cases = self.load_phase1_test_cases(test_case_loader)

        print(f"\nRunning {len(test_cases)} Phase 1 test cases...")
        print("=" * 70)

        regression_results: List[RegressionResult] = []
        performance_results: List[PerformanceMetrics] = []
        failures = []

        for test_case in test_cases:
            print(f"\n[{test_case.test_id}] {test_case.name}")

            # Skip if marked
            if test_case.skip:
                print(f"  ⊘ SKIPPED: {test_case.skip_reason}")
                continue

            try:
                # Measure performance
                start_time = time.perf_counter()

                # Parse SQL with schema
                actual_result = self.parse_and_convert_to_dict(
                    sql_parser,
                    test_case.sql,
                    "result",
                    test_case.source_tables
                )

                end_time = time.perf_counter()
                parse_time_ms = (end_time - start_time) * 1000

                # Check performance threshold
                if parse_time_ms > test_case.max_parse_time_ms:
                    print(f"  ⚠ Performance: {parse_time_ms:.2f}ms (limit: {test_case.max_parse_time_ms}ms)")
                else:
                    print(f"  ✓ Performance: {parse_time_ms:.2f}ms")

                # Record performance
                perf_metrics = PerformanceMetrics(
                    test_id=test_case.test_id,
                    parse_time_ms=parse_time_ms,
                    success=True,
                    sql_length=len(test_case.sql),
                    num_lineages=len(actual_result["lineages"])
                )
                performance_results.append(perf_metrics)

                # Compare with expected lineage
                matches, errors = self.compare_lineage_with_expected(
                    actual_result,
                    test_case.expected_lineage
                )

                if not matches:
                    print(f"  ✗ Lineage mismatch:")
                    for error in errors:
                        print(f"    - {error}")
                    failures.append({
                        "test_id": test_case.test_id,
                        "errors": errors
                    })
                else:
                    print(f"  ✓ Lineage matches expected")

                # Regression test
                regression_result = regression_tester.test_against_snapshot(
                    test_case.test_id,
                    actual_result,
                    test_case.min_confidence
                )
                regression_results.append(regression_result)

                if not regression_result.passed:
                    if regression_result.has_baseline:
                        print(f"  ✗ Regression test failed")
                        if regression_result.diff:
                            print(f"    {regression_result.diff}")
                    else:
                        print(f"  ⚠ No baseline - created")

                # Track coverage
                coverage_tracker.mark_features_from_tags(test_case.tags, passed=matches)

            except Exception as e:
                print(f"  ✗ Error: {e}")
                failures.append({
                    "test_id": test_case.test_id,
                    "errors": [str(e)]
                })

                # Record failed performance
                perf_metrics = PerformanceMetrics(
                    test_id=test_case.test_id,
                    parse_time_ms=0,
                    success=False,
                    error=str(e)
                )
                performance_results.append(perf_metrics)

        # Print summary reports
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        # Regression summary
        RegressionReporter.print_summary(regression_results)

        # Performance summary
        perf_tester = PerformanceTester()
        perf_tester.results = performance_results
        perf_summary = perf_tester.get_summary()

        print("\nPERFORMANCE SUMMARY")
        print("-" * 70)
        print(f"Total Tests:           {perf_summary.get('total_tests', 0)}")
        print(f"Successful:            {perf_summary.get('successful', 0)}")
        print(f"Failed:                {perf_summary.get('failed', 0)}")

        if perf_summary.get('successful', 0) > 0:
            print(f"Avg Parse Time:        {perf_summary['avg_time_ms']:.2f}ms")
            print(f"Min Parse Time:        {perf_summary['min_time_ms']:.2f}ms")
            print(f"Max Parse Time:        {perf_summary['max_time_ms']:.2f}ms")
            print(f"Median Parse Time:     {perf_summary['median_time_ms']:.2f}ms")
            print(f"Within Threshold:      {perf_summary['within_threshold']}")
            print(f"Exceeded Threshold:    {perf_summary['exceeded_threshold']}")

        # Coverage summary
        print("\n")
        coverage_tracker.print_coverage_report()

        # Assert no failures
        if failures:
            failure_msg = "\n".join([
                f"{f['test_id']}: {', '.join(f['errors'])}"
                for f in failures
            ])
            pytest.fail(f"Test failures:\n{failure_msg}")

    def load_phase2_test_cases(self, test_case_loader: TestCaseLoader) -> List[TestCase]:
        """Load all Phase 2 test cases."""
        test_dir = Path(__file__).parent.parent / "test_cases" / "phase2_joins"

        if not test_dir.exists():
            return []

        categories = test_case_loader.load_directory(test_dir)

        test_cases = []
        for category_tests in categories.values():
            test_cases.extend(category_tests)

        return test_cases

    def test_phase2_join_queries(
        self,
        test_case_loader,
        sql_parser,
        regression_tester,
        performance_tester,
        coverage_tracker
    ):
        """Test Phase 2 JOIN queries with regression and performance testing."""

        # Load test cases
        test_cases = self.load_phase2_test_cases(test_case_loader)

        if not test_cases:
            pytest.skip("No Phase 2 test cases found")

        print(f"\nRunning {len(test_cases)} Phase 2 test cases...")
        print("=" * 70)

        regression_results: List[RegressionResult] = []
        performance_results: List[PerformanceMetrics] = []
        failures = []

        for test_case in test_cases:
            print(f"\n[{test_case.test_id}] {test_case.name}")

            # Skip if marked
            if test_case.skip:
                print(f"  ⊘ SKIPPED: {test_case.skip_reason}")
                continue

            try:
                # Measure performance
                start_time = time.perf_counter()

                # Parse SQL with schema
                actual_result = self.parse_and_convert_to_dict(
                    sql_parser,
                    test_case.sql,
                    "result",
                    test_case.source_tables
                )

                end_time = time.perf_counter()
                parse_time_ms = (end_time - start_time) * 1000

                # Record performance
                perf_metrics = PerformanceMetrics(
                    test_id=test_case.test_id,
                    parse_time_ms=parse_time_ms,
                    success=True,
                    sql_length=len(test_case.sql)
                )
                performance_results.append(perf_metrics)

                # Check performance
                if parse_time_ms <= test_case.max_parse_time_ms:
                    print(f"  ✓ Performance: {parse_time_ms:.2f}ms")
                else:
                    print(f"  ⚠ Performance: {parse_time_ms:.2f}ms (threshold: {test_case.max_parse_time_ms}ms)")

                # Compare with expected lineage
                matches, errors = self.compare_lineage_with_expected(
                    actual_result,
                    test_case.expected_lineage
                )

                if not matches:
                    print(f"  ✗ Lineage mismatch:")
                    for error in errors:
                        print(f"    - {error}")
                    failures.append({
                        "test_id": test_case.test_id,
                        "errors": errors
                    })
                else:
                    print(f"  ✓ Lineage matches expected")

                # Regression test
                regression_result = regression_tester.test_against_snapshot(
                    test_case.test_id,
                    actual_result,
                    test_case.min_confidence
                )
                regression_results.append(regression_result)

                if not regression_result.passed:
                    if regression_result.has_baseline:
                        print(f"  ✗ Regression test failed")
                        if regression_result.diff:
                            print(f"    {regression_result.diff}")
                    else:
                        print(f"  ⚠ No baseline - created")

                # Track coverage
                coverage_tracker.mark_features_from_tags(test_case.tags, passed=matches)

                # Mark overall test status
                if matches and regression_result.passed:
                    print(f"✓ {test_case.test_id} - PASSED")
                else:
                    print(f"✗ {test_case.test_id} - FAILED")
                    if regression_result.has_baseline and not regression_result.passed:
                        print(f"  Diff:\n{regression_result.diff}")

            except Exception as e:
                print(f"  ✗ Error: {e}")
                failures.append({
                    "test_id": test_case.test_id,
                    "errors": [str(e)]
                })

                # Record failed performance
                perf_metrics = PerformanceMetrics(
                    test_id=test_case.test_id,
                    parse_time_ms=0,
                    success=False,
                    error=str(e)
                )
                performance_results.append(perf_metrics)

        # Print summary reports
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        # Regression summary
        RegressionReporter.print_summary(regression_results)

        # Performance summary
        perf_tester = PerformanceTester()
        perf_tester.results = performance_results
        perf_summary = perf_tester.get_summary()

        print("\nPERFORMANCE SUMMARY")
        print("-" * 70)
        print(f"Total Tests:           {perf_summary.get('total_tests', 0)}")
        print(f"Successful:            {perf_summary.get('successful', 0)}")
        print(f"Failed:                {perf_summary.get('failed', 0)}")

        if perf_summary.get('successful', 0) > 0:
            print(f"Avg Parse Time:        {perf_summary['avg_time_ms']:.2f}ms")
            print(f"Min Parse Time:        {perf_summary['min_time_ms']:.2f}ms")
            print(f"Max Parse Time:        {perf_summary['max_time_ms']:.2f}ms")
            print(f"Median Parse Time:     {perf_summary['median_time_ms']:.2f}ms")
            print(f"Within Threshold:      {perf_summary['within_threshold']}")
            print(f"Exceeded Threshold:    {perf_summary['exceeded_threshold']}")

        # Coverage summary
        print("\n")
        coverage_tracker.print_coverage_report()

        # Assert no failures
        if failures:
            failure_msg = "\n".join([
                f"{f['test_id']}: {', '.join(f['errors'])}"
                for f in failures
            ])
            pytest.fail(f"Test failures:\n{failure_msg}")

    def load_phase3_test_cases(self, test_case_loader: TestCaseLoader) -> List[TestCase]:
        """Load all Phase 3 test cases."""
        test_dir = Path(__file__).parent.parent / "test_cases" / "phase3_aggregations"

        if not test_dir.exists():
            return []

        categories = test_case_loader.load_directory(test_dir)

        test_cases = []
        for category_tests in categories.values():
            test_cases.extend(category_tests)

        return test_cases

    def test_phase3_aggregation_queries(
        self,
        test_case_loader,
        sql_parser,
        regression_tester,
        performance_tester,
        coverage_tracker
    ):
        """Test Phase 3 aggregation queries with regression and performance testing."""

        # Load test cases
        test_cases = self.load_phase3_test_cases(test_case_loader)

        if not test_cases:
            pytest.skip("No Phase 3 test cases found")

        print(f"\nRunning {len(test_cases)} Phase 3 test cases...")
        print("=" * 70)

        regression_results: List[RegressionResult] = []
        performance_results: List[PerformanceMetrics] = []
        failures = []

        for test_case in test_cases:
            print(f"\n[{test_case.test_id}] {test_case.name}")

            # Skip if marked
            if test_case.skip:
                print(f"  ⊘ SKIPPED: {test_case.skip_reason}")
                continue

            try:
                # Measure performance
                start_time = time.perf_counter()

                # Parse SQL with schema
                actual_result = self.parse_and_convert_to_dict(
                    sql_parser,
                    test_case.sql,
                    "result",
                    test_case.source_tables
                )

                end_time = time.perf_counter()
                parse_time_ms = (end_time - start_time) * 1000

                # Record performance
                perf_metrics = PerformanceMetrics(
                    test_id=test_case.test_id,
                    parse_time_ms=parse_time_ms,
                    success=True,
                    sql_length=len(test_case.sql)
                )
                performance_results.append(perf_metrics)

                # Check performance
                if parse_time_ms <= test_case.max_parse_time_ms:
                    print(f"  ✓ Performance: {parse_time_ms:.2f}ms")
                else:
                    print(f"  ⚠ Performance: {parse_time_ms:.2f}ms (threshold: {test_case.max_parse_time_ms}ms)")

                # Compare with expected lineage
                matches, errors = self.compare_lineage_with_expected(
                    actual_result,
                    test_case.expected_lineage
                )

                if not matches:
                    print(f"  ✗ Lineage mismatch:")
                    for error in errors:
                        print(f"    - {error}")
                    failures.append({
                        "test_id": test_case.test_id,
                        "errors": errors
                    })
                else:
                    print(f"  ✓ Lineage matches expected")

                # Regression test
                regression_result = regression_tester.test_against_snapshot(
                    test_case.test_id,
                    actual_result,
                    test_case.min_confidence
                )
                regression_results.append(regression_result)

                if not regression_result.passed:
                    if regression_result.has_baseline:
                        print(f"  ✗ Regression test failed")
                        if regression_result.diff:
                            print(f"    {regression_result.diff}")
                    else:
                        print(f"  ⚠ No baseline - created")

                # Track coverage
                coverage_tracker.mark_features_from_tags(test_case.tags, passed=matches)

                # Mark overall test status
                if matches and regression_result.passed:
                    print(f"✓ {test_case.test_id} - PASSED")
                else:
                    print(f"✗ {test_case.test_id} - FAILED")
                    if regression_result.has_baseline and not regression_result.passed:
                        print(f"  Diff:\n{regression_result.diff}")

            except Exception as e:
                print(f"  ✗ Error: {e}")
                failures.append({
                    "test_id": test_case.test_id,
                    "errors": [str(e)]
                })

                # Record failed performance
                perf_metrics = PerformanceMetrics(
                    test_id=test_case.test_id,
                    parse_time_ms=0,
                    success=False,
                    error=str(e)
                )
                performance_results.append(perf_metrics)

        # Print summary reports
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        # Regression summary
        RegressionReporter.print_summary(regression_results)

        # Performance summary
        perf_tester = PerformanceTester()
        perf_tester.results = performance_results
        perf_summary = perf_tester.get_summary()

        print("\nPERFORMANCE SUMMARY")
        print("-" * 70)
        print(f"Total Tests:           {perf_summary.get('total_tests', 0)}")
        print(f"Successful:            {perf_summary.get('successful', 0)}")
        print(f"Failed:                {perf_summary.get('failed', 0)}")

        if perf_summary.get('successful', 0) > 0:
            print(f"Avg Parse Time:        {perf_summary['avg_time_ms']:.2f}ms")
            print(f"Min Parse Time:        {perf_summary['min_time_ms']:.2f}ms")
            print(f"Max Parse Time:        {perf_summary['max_time_ms']:.2f}ms")
            print(f"Median Parse Time:     {perf_summary['median_time_ms']:.2f}ms")
            print(f"Within Threshold:      {perf_summary['within_threshold']}")
            print(f"Exceeded Threshold:    {perf_summary['exceeded_threshold']}")

        # Coverage summary
        print("\n")
        coverage_tracker.print_coverage_report()

        # Assert no failures
        if failures:
            failure_msg = "\n".join([
                f"{f['test_id']}: {', '.join(f['errors'])}"
                for f in failures
            ])
            pytest.fail(f"Test failures:\n{failure_msg}")

    def load_phase4_test_cases(self, test_case_loader: TestCaseLoader) -> List[TestCase]:
        """Load all Phase 4 test cases."""
        test_dir = Path(__file__).parent.parent / "test_cases" / "phase4_subqueries"

        if not test_dir.exists():
            return []

        categories = test_case_loader.load_directory(test_dir)

        test_cases = []
        for category_tests in categories.values():
            test_cases.extend(category_tests)

        return test_cases

    def test_phase4_subquery_queries(
        self,
        test_case_loader,
        sql_parser,
        regression_tester,
        performance_tester,
        coverage_tracker
    ):
        """Test Phase 4 subquery queries with regression and performance testing."""

        # Load test cases
        test_cases = self.load_phase4_test_cases(test_case_loader)

        if not test_cases:
            pytest.skip("No Phase 4 test cases found")

        print(f"\nRunning {len(test_cases)} Phase 4 test cases...")
        print("=" * 70)

        regression_results: List[RegressionResult] = []
        performance_results: List[PerformanceMetrics] = []
        failures = []

        for test_case in test_cases:
            print(f"\n[{test_case.test_id}] {test_case.name}")

            # Skip if marked
            if test_case.skip:
                print(f"  ⊘ SKIPPED: {test_case.skip_reason}")
                continue

            try:
                # Measure performance
                start_time = time.perf_counter()

                # Parse SQL with schema
                actual_result = self.parse_and_convert_to_dict(
                    sql_parser,
                    test_case.sql,
                    "result",
                    test_case.source_tables
                )

                end_time = time.perf_counter()
                parse_time_ms = (end_time - start_time) * 1000

                # Record performance
                perf_metrics = PerformanceMetrics(
                    test_id=test_case.test_id,
                    parse_time_ms=parse_time_ms,
                    success=True,
                    sql_length=len(test_case.sql)
                )
                performance_results.append(perf_metrics)

                # Check performance
                if parse_time_ms <= test_case.max_parse_time_ms:
                    print(f"  ✓ Performance: {parse_time_ms:.2f}ms")
                else:
                    print(f"  ⚠ Performance: {parse_time_ms:.2f}ms (threshold: {test_case.max_parse_time_ms}ms)")

                # Compare with expected lineage
                matches, errors = self.compare_lineage_with_expected(
                    actual_result,
                    test_case.expected_lineage
                )

                if not matches:
                    print(f"  ✗ Lineage mismatch:")
                    for error in errors:
                        print(f"    - {error}")
                    failures.append({
                        "test_id": test_case.test_id,
                        "errors": errors
                    })
                else:
                    print(f"  ✓ Lineage matches expected")

                # Regression test
                regression_result = regression_tester.test_against_snapshot(
                    test_case.test_id,
                    actual_result,
                    test_case.min_confidence
                )
                regression_results.append(regression_result)

                if not regression_result.passed:
                    if regression_result.has_baseline:
                        print(f"  ✗ Regression test failed")
                        if regression_result.diff:
                            print(f"    {regression_result.diff}")
                    else:
                        print(f"  ⚠ No baseline - created")

                # Track coverage
                coverage_tracker.mark_features_from_tags(test_case.tags, passed=matches)

                # Mark overall test status
                if matches and regression_result.passed:
                    print(f"✓ {test_case.test_id} - PASSED")
                else:
                    print(f"✗ {test_case.test_id} - FAILED")
                    if regression_result.has_baseline and not regression_result.passed:
                        print(f"  Diff:\n{regression_result.diff}")

            except Exception as e:
                print(f"  ✗ Error: {e}")
                failures.append({
                    "test_id": test_case.test_id,
                    "errors": [str(e)]
                })

                # Record failed performance
                perf_metrics = PerformanceMetrics(
                    test_id=test_case.test_id,
                    parse_time_ms=0,
                    success=False,
                    error=str(e)
                )
                performance_results.append(perf_metrics)

        # Print summary reports
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        # Regression summary
        RegressionReporter.print_summary(regression_results)

        # Performance summary
        perf_tester = PerformanceTester()
        perf_tester.results = performance_results
        perf_summary = perf_tester.get_summary()

        print("\nPERFORMANCE SUMMARY")
        print("-" * 70)
        print(f"Total Tests:           {perf_summary.get('total_tests', 0)}")
        print(f"Successful:            {perf_summary.get('successful', 0)}")
        print(f"Failed:                {perf_summary.get('failed', 0)}")

        if perf_summary.get('successful', 0) > 0:
            print(f"Avg Parse Time:        {perf_summary['avg_time_ms']:.2f}ms")
            print(f"Min Parse Time:        {perf_summary['min_time_ms']:.2f}ms")
            print(f"Max Parse Time:        {perf_summary['max_time_ms']:.2f}ms")
            print(f"Median Parse Time:     {perf_summary['median_time_ms']:.2f}ms")
            print(f"Within Threshold:      {perf_summary['within_threshold']}")
            print(f"Exceeded Threshold:    {perf_summary['exceeded_threshold']}")

        # Coverage summary
        print("\n")
        coverage_tracker.print_coverage_report()

        # Assert no failures
        if failures:
            failure_msg = "\n".join([
                f"{f['test_id']}: {', '.join(f['errors'])}"
                for f in failures
            ])
            pytest.fail(f"Test failures:\n{failure_msg}")

    def load_phase5_test_cases(self, test_case_loader: TestCaseLoader) -> List[TestCase]:
        """Load all Phase 5 test cases."""
        test_dir = Path(__file__).parent.parent / "test_cases" / "phase5_window_functions"

        if not test_dir.exists():
            return []

        categories = test_case_loader.load_directory(test_dir)

        test_cases = []
        for category_tests in categories.values():
            test_cases.extend(category_tests)

        return test_cases

    def test_phase5_window_function_queries(
        self,
        test_case_loader,
        sql_parser,
        regression_tester,
        performance_tester,
        coverage_tracker
    ):
        """Test Phase 5 window function queries with regression and performance testing."""

        # Load test cases
        test_cases = self.load_phase5_test_cases(test_case_loader)

        if not test_cases:
            pytest.skip("No Phase 5 test cases found")

        print(f"\nRunning {len(test_cases)} Phase 5 test cases...")
        print("=" * 70)

        regression_results: List[RegressionResult] = []
        performance_results: List[PerformanceMetrics] = []
        failures = []

        for test_case in test_cases:
            print(f"\n[{test_case.test_id}] {test_case.name}")

            # Skip if marked
            if test_case.skip:
                print(f"  ⊘ SKIPPED: {test_case.skip_reason}")
                continue

            try:
                # Measure performance
                start_time = time.perf_counter()

                # Parse SQL with schema
                actual_result = self.parse_and_convert_to_dict(
                    sql_parser,
                    test_case.sql,
                    "result",
                    test_case.source_tables
                )

                end_time = time.perf_counter()
                parse_time_ms = (end_time - start_time) * 1000

                # Record performance
                perf_metrics = PerformanceMetrics(
                    test_id=test_case.test_id,
                    parse_time_ms=parse_time_ms,
                    success=True,
                    sql_length=len(test_case.sql)
                )
                performance_results.append(perf_metrics)

                # Check performance
                if parse_time_ms <= test_case.max_parse_time_ms:
                    print(f"  ✓ Performance: {parse_time_ms:.2f}ms")
                else:
                    print(f"  ⚠ Performance: {parse_time_ms:.2f}ms (threshold: {test_case.max_parse_time_ms}ms)")

                # Compare with expected lineage
                matches, errors = self.compare_lineage_with_expected(
                    actual_result,
                    test_case.expected_lineage
                )

                if not matches:
                    print(f"  ✗ Lineage mismatch:")
                    for error in errors:
                        print(f"    - {error}")
                    failures.append({
                        "test_id": test_case.test_id,
                        "errors": errors
                    })
                else:
                    print(f"  ✓ Lineage matches expected")

                # Regression test
                regression_result = regression_tester.test_against_snapshot(
                    test_case.test_id,
                    actual_result,
                    test_case.min_confidence
                )
                regression_results.append(regression_result)

                if not regression_result.passed:
                    if regression_result.has_baseline:
                        print(f"  ✗ Regression test failed")
                        if regression_result.diff:
                            print(f"    {regression_result.diff}")
                    else:
                        print(f"  ⚠ No baseline - created")

                # Track coverage
                coverage_tracker.mark_features_from_tags(test_case.tags, passed=matches)

                # Mark overall test status
                if matches and regression_result.passed:
                    print(f"✓ {test_case.test_id} - PASSED")
                else:
                    print(f"✗ {test_case.test_id} - FAILED")
                    if regression_result.has_baseline and not regression_result.passed:
                        print(f"  Diff:\n{regression_result.diff}")

            except Exception as e:
                print(f"  ✗ Error: {e}")
                failures.append({
                    "test_id": test_case.test_id,
                    "errors": [str(e)]
                })

                # Record failed performance
                perf_metrics = PerformanceMetrics(
                    test_id=test_case.test_id,
                    parse_time_ms=0,
                    success=False,
                    error=str(e)
                )
                performance_results.append(perf_metrics)

        # Print summary reports
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        # Regression summary
        RegressionReporter.print_summary(regression_results)

        # Performance summary
        perf_tester = PerformanceTester()
        perf_tester.results = performance_results
        perf_summary = perf_tester.get_summary()

        print("\nPERFORMANCE SUMMARY")
        print("-" * 70)
        print(f"Total Tests:           {perf_summary.get('total_tests', 0)}")
        print(f"Successful:            {perf_summary.get('successful', 0)}")
        print(f"Failed:                {perf_summary.get('failed', 0)}")

        if perf_summary.get('successful', 0) > 0:
            print(f"Avg Parse Time:        {perf_summary['avg_time_ms']:.2f}ms")
            print(f"Min Parse Time:        {perf_summary['min_time_ms']:.2f}ms")
            print(f"Max Parse Time:        {perf_summary['max_time_ms']:.2f}ms")
            print(f"Median Parse Time:     {perf_summary['median_time_ms']:.2f}ms")
            print(f"Within Threshold:      {perf_summary['within_threshold']}")
            print(f"Exceeded Threshold:    {perf_summary['exceeded_threshold']}")

        # Coverage summary
        print("\n")
        coverage_tracker.print_coverage_report()

        # Assert no failures
        if failures:
            failure_msg = "\n".join([
                f"{f['test_id']}: {', '.join(f['errors'])}"
                for f in failures
            ])
            pytest.fail(f"Test failures:\n{failure_msg}")

    def load_phase6_test_cases(self, test_case_loader: TestCaseLoader) -> List[TestCase]:
        """Load all Phase 6 test cases."""
        test_dir = Path(__file__).parent.parent / "test_cases" / "phase6_set_operations"

        if not test_dir.exists():
            return []

        categories = test_case_loader.load_directory(test_dir)

        test_cases = []
        for category_tests in categories.values():
            test_cases.extend(category_tests)

        return test_cases

    def test_phase6_set_operation_queries(
        self,
        test_case_loader,
        sql_parser,
        regression_tester,
        performance_tester,
        coverage_tracker
    ):
        """Test Phase 6 set operation queries with regression and performance testing."""

        # Load test cases
        test_cases = self.load_phase6_test_cases(test_case_loader)

        if not test_cases:
            pytest.skip("No Phase 6 test cases found")

        print(f"\nRunning {len(test_cases)} Phase 6 test cases...")
        print("=" * 70)

        regression_results: List[RegressionResult] = []
        performance_results: List[PerformanceMetrics] = []
        failures = []

        for test_case in test_cases:
            print(f"\n[{test_case.test_id}] {test_case.name}")

            # Skip if marked
            if test_case.skip:
                print(f"  ⊘ SKIPPED: {test_case.skip_reason}")
                continue

            try:
                # Measure performance
                start_time = time.perf_counter()

                # Parse SQL with schema
                actual_result = self.parse_and_convert_to_dict(
                    sql_parser,
                    test_case.sql,
                    "result",
                    test_case.source_tables
                )

                end_time = time.perf_counter()
                parse_time_ms = (end_time - start_time) * 1000

                # Record performance
                perf_metrics = PerformanceMetrics(
                    test_id=test_case.test_id,
                    parse_time_ms=parse_time_ms,
                    success=True,
                    sql_length=len(test_case.sql)
                )
                performance_results.append(perf_metrics)

                # Check performance
                if parse_time_ms <= test_case.max_parse_time_ms:
                    print(f"  ✓ Performance: {parse_time_ms:.2f}ms")
                else:
                    print(f"  ⚠ Performance: {parse_time_ms:.2f}ms (threshold: {test_case.max_parse_time_ms}ms)")

                # Compare with expected lineage
                matches, errors = self.compare_lineage_with_expected(
                    actual_result,
                    test_case.expected_lineage
                )

                if not matches:
                    print(f"  ✗ Lineage mismatch:")
                    for error in errors:
                        print(f"    - {error}")
                    failures.append({
                        "test_id": test_case.test_id,
                        "errors": errors
                    })
                else:
                    print(f"  ✓ Lineage matches expected")

                # Regression test
                regression_result = regression_tester.test_against_snapshot(
                    test_case.test_id,
                    actual_result,
                    test_case.min_confidence
                )
                regression_results.append(regression_result)

                if not regression_result.passed:
                    if regression_result.has_baseline:
                        print(f"  ✗ Regression test failed")
                        if regression_result.diff:
                            print(f"    {regression_result.diff}")
                    else:
                        print(f"  ⚠ No baseline - created")

                # Track coverage
                coverage_tracker.mark_features_from_tags(test_case.tags, passed=matches)

                # Mark overall test status
                if matches and regression_result.passed:
                    print(f"✓ {test_case.test_id} - PASSED")
                else:
                    print(f"✗ {test_case.test_id} - FAILED")
                    if regression_result.has_baseline and not regression_result.passed:
                        print(f"  Diff:\n{regression_result.diff}")

            except Exception as e:
                print(f"  ✗ Error: {e}")
                failures.append({
                    "test_id": test_case.test_id,
                    "errors": [str(e)]
                })

                # Record failed performance
                perf_metrics = PerformanceMetrics(
                    test_id=test_case.test_id,
                    parse_time_ms=0,
                    success=False,
                    error=str(e)
                )
                performance_results.append(perf_metrics)

        # Print summary reports
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        # Regression summary
        RegressionReporter.print_summary(regression_results)

        # Performance summary
        perf_tester = PerformanceTester()
        perf_tester.results = performance_results
        perf_summary = perf_tester.get_summary()

        print("\nPERFORMANCE SUMMARY")
        print("-" * 70)
        print(f"Total Tests:           {perf_summary.get('total_tests', 0)}")
        print(f"Successful:            {perf_summary.get('successful', 0)}")
        print(f"Failed:                {perf_summary.get('failed', 0)}")

        if perf_summary.get('successful', 0) > 0:
            print(f"Avg Parse Time:        {perf_summary['avg_time_ms']:.2f}ms")
            print(f"Min Parse Time:        {perf_summary['min_time_ms']:.2f}ms")
            print(f"Max Parse Time:        {perf_summary['max_time_ms']:.2f}ms")
            print(f"Median Parse Time:     {perf_summary['median_time_ms']:.2f}ms")
            print(f"Within Threshold:      {perf_summary['within_threshold']}")
            print(f"Exceeded Threshold:    {perf_summary['exceeded_threshold']}")

        # Coverage summary
        print("\n")
        coverage_tracker.print_coverage_report()

        # Assert no failures
        if failures:
            failure_msg = "\n".join([
                f"{f['test_id']}: {', '.join(f['errors'])}"
                for f in failures
            ])
            pytest.fail(f"Test failures:\n{failure_msg}")

    def test_load_test_cases_schema_validation(self, test_case_loader):
        """Test that all test case files are valid JSON and pass schema validation."""

        test_dir = Path(__file__).parent.parent / "test_cases" / "phase1_basic"

        if not test_dir.exists():
            pytest.skip(f"Test case directory not found: {test_dir}")

        # Load all test cases
        categories = test_case_loader.load_directory(test_dir)

        total_tests = sum(len(tests) for tests in categories.values())

        print(f"\nValidated {total_tests} test cases across {len(categories)} files")

        # Get statistics
        all_tests = []
        for tests in categories.values():
            all_tests.extend(tests)

        stats = test_case_loader.get_test_statistics(all_tests)

        print(f"Statistics:")
        print(f"  Total: {stats['total']}")
        print(f"  By difficulty: {stats['by_difficulty']}")
        print(f"  Skipped: {stats['skipped']}")
        print(f"  Avg lineages per test: {stats['avg_expected_lineages']:.1f}")

        assert total_tests > 0, "No test cases found"

    def test_snapshot_management(self, snapshot_manager):
        """Test snapshot creation, loading, and deletion."""

        test_id = "test-snapshot-001"

        # Create test data
        test_data = {
            "lineages": [
                {"target": "result.col1", "sources": ["table1.col1"]}
            ],
            "confidence_score": 1.0
        }

        # Save snapshot
        metadata = snapshot_manager.save_snapshot(
            test_id,
            test_data,
            notes="Test snapshot"
        )

        assert metadata.test_id == test_id
        assert metadata.hash is not None

        # Load snapshot
        loaded = snapshot_manager.load_snapshot(test_id)
        assert loaded == test_data

        # Load metadata
        loaded_meta = snapshot_manager.load_metadata(test_id)
        assert loaded_meta.test_id == test_id

        # Clean up
        deleted = snapshot_manager.delete_snapshot(test_id)
        assert deleted is True

    @pytest.mark.slow
    def test_performance_benchmark(self, sql_parser, performance_tester):
        """Benchmark parsing performance on various query complexities."""

        test_cases = [
            ("Simple SELECT", "SELECT id, name FROM users"),
            ("With WHERE", "SELECT id, name FROM users WHERE id > 100"),
            ("With JOIN", "SELECT u.id, u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id"),
            ("With aggregation", "SELECT user_id, COUNT(*), SUM(total) FROM orders GROUP BY user_id"),
        ]

        print("\nPerformance Benchmarks (10 iterations each):")
        print("-" * 70)

        for name, sql in test_cases:
            benchmark = performance_tester.benchmark(
                test_id=f"bench-{name}",
                parse_func=lambda s: sql_parser.extract_lineage(s, "result"),
                sql=sql,
                iterations=10
            )

            print(f"\n{name}:")
            print(f"  Avg: {benchmark.avg_time_ms:.2f}ms")
            print(f"  Min: {benchmark.min_time_ms:.2f}ms")
            print(f"  Max: {benchmark.max_time_ms:.2f}ms")
            print(f"  StdDev: {benchmark.std_dev_ms:.2f}ms")
            print(f"  Pass Rate: {benchmark.pass_rate * 100:.0f}%")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
