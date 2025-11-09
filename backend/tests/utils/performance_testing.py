"""Performance testing utilities for SQL lineage parsing."""
import time
import statistics
from dataclasses import dataclass, asdict
from typing import List, Optional, Callable, Any
from pathlib import Path
import json


@dataclass
class PerformanceMetrics:
    """Performance metrics for a test run."""
    test_id: str
    parse_time_ms: float
    success: bool
    error: Optional[str] = None
    sql_length: int = 0
    num_tables: int = 0
    num_columns: int = 0
    num_lineages: int = 0


@dataclass
class PerformanceBenchmark:
    """Performance benchmark results."""
    test_id: str
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    std_dev_ms: float
    iterations: int
    pass_rate: float
    max_allowed_ms: int


class PerformanceTester:
    """Test SQL parsing performance."""

    def __init__(self, max_parse_time_ms: int = 5000):
        """
        Initialize performance tester.

        Args:
            max_parse_time_ms: Maximum allowed parse time
        """
        self.max_parse_time_ms = max_parse_time_ms
        self.results: List[PerformanceMetrics] = []

    def measure_parse_time(
        self,
        test_id: str,
        parse_func: Callable,
        sql: str,
        **kwargs
    ) -> PerformanceMetrics:
        """
        Measure parsing time for a SQL query.

        Args:
            test_id: Test identifier
            parse_func: Function to call for parsing
            sql: SQL query
            **kwargs: Additional arguments for parse_func

        Returns:
            Performance metrics
        """
        start_time = time.perf_counter()

        try:
            result = parse_func(sql, **kwargs)
            end_time = time.perf_counter()

            parse_time_ms = (end_time - start_time) * 1000

            # Extract metrics from result if available
            num_lineages = len(result) if isinstance(result, list) else 0

            metrics = PerformanceMetrics(
                test_id=test_id,
                parse_time_ms=parse_time_ms,
                success=True,
                sql_length=len(sql),
                num_lineages=num_lineages
            )

        except Exception as e:
            end_time = time.perf_counter()
            parse_time_ms = (end_time - start_time) * 1000

            metrics = PerformanceMetrics(
                test_id=test_id,
                parse_time_ms=parse_time_ms,
                success=False,
                error=str(e),
                sql_length=len(sql)
            )

        self.results.append(metrics)
        return metrics

    def benchmark(
        self,
        test_id: str,
        parse_func: Callable,
        sql: str,
        iterations: int = 10,
        **kwargs
    ) -> PerformanceBenchmark:
        """
        Run benchmark with multiple iterations.

        Args:
            test_id: Test identifier
            parse_func: Function to call for parsing
            sql: SQL query
            iterations: Number of iterations
            **kwargs: Additional arguments for parse_func

        Returns:
            Performance benchmark results
        """
        times: List[float] = []
        successes = 0

        for i in range(iterations):
            metrics = self.measure_parse_time(
                f"{test_id}-iter{i}",
                parse_func,
                sql,
                **kwargs
            )

            times.append(metrics.parse_time_ms)
            if metrics.success:
                successes += 1

        return PerformanceBenchmark(
            test_id=test_id,
            avg_time_ms=statistics.mean(times),
            min_time_ms=min(times),
            max_time_ms=max(times),
            std_dev_ms=statistics.stdev(times) if len(times) > 1 else 0,
            iterations=iterations,
            pass_rate=successes / iterations,
            max_allowed_ms=self.max_parse_time_ms
        )

    def test_performance_threshold(
        self,
        test_id: str,
        parse_func: Callable,
        sql: str,
        max_time_ms: Optional[int] = None,
        **kwargs
    ) -> tuple[bool, PerformanceMetrics]:
        """
        Test if parsing meets performance threshold.

        Args:
            test_id: Test identifier
            parse_func: Function to call for parsing
            sql: SQL query
            max_time_ms: Maximum allowed time (overrides default)
            **kwargs: Additional arguments for parse_func

        Returns:
            Tuple of (passed, metrics)
        """
        threshold = max_time_ms or self.max_parse_time_ms
        metrics = self.measure_parse_time(test_id, parse_func, sql, **kwargs)

        passed = metrics.success and metrics.parse_time_ms <= threshold

        return passed, metrics

    def get_summary(self) -> dict:
        """Get summary statistics of all performance tests."""
        if not self.results:
            return {}

        successful = [r for r in self.results if r.success]

        if not successful:
            return {
                "total_tests": len(self.results),
                "successful": 0,
                "failed": len(self.results)
            }

        times = [r.parse_time_ms for r in successful]

        return {
            "total_tests": len(self.results),
            "successful": len(successful),
            "failed": len(self.results) - len(successful),
            "avg_time_ms": statistics.mean(times),
            "min_time_ms": min(times),
            "max_time_ms": max(times),
            "median_time_ms": statistics.median(times),
            "std_dev_ms": statistics.stdev(times) if len(times) > 1 else 0,
            "threshold_ms": self.max_parse_time_ms,
            "within_threshold": sum(1 for t in times if t <= self.max_parse_time_ms),
            "exceeded_threshold": sum(1 for t in times if t > self.max_parse_time_ms)
        }


class LargeFileTester:
    """Test parsing of large SQL files."""

    @staticmethod
    def generate_large_sql(
        num_tables: int = 50,
        num_columns_per_table: int = 20,
        num_joins: int = 10
    ) -> str:
        """
        Generate a large SQL query for testing.

        Args:
            num_tables: Number of tables to reference
            num_columns_per_table: Columns per table
            num_joins: Number of joins

        Returns:
            Generated SQL query
        """
        lines = ["SELECT"]

        # Generate SELECT columns
        select_cols = []
        for t in range(num_tables):
            for c in range(num_columns_per_table):
                select_cols.append(f"  t{t}.col{c}")

        lines.append(",\n".join(select_cols))

        # Generate FROM clause
        lines.append(f"FROM table0 t0")

        # Generate JOINs
        for i in range(1, min(num_joins + 1, num_tables)):
            lines.append(
                f"JOIN table{i} t{i} ON t0.id = t{i}.table0_id"
            )

        return "\n".join(lines)

    @staticmethod
    def create_large_sql_file(
        output_path: Path,
        num_queries: int = 100,
        tables_per_query: int = 10
    ) -> Path:
        """
        Create a large SQL file with multiple queries.

        Args:
            output_path: Output file path
            num_queries: Number of queries to generate
            tables_per_query: Tables per query

        Returns:
            Path to created file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            for i in range(num_queries):
                f.write(f"-- Query {i+1}\n")
                sql = LargeFileTester.generate_large_sql(
                    num_tables=tables_per_query,
                    num_columns_per_table=5,
                    num_joins=min(5, tables_per_query - 1)
                )
                f.write(sql)
                f.write(";\n\n")

        file_size = output_path.stat().st_size
        print(f"Generated {output_path} ({file_size:,} bytes)")

        return output_path

    @staticmethod
    def test_large_file(
        filepath: Path,
        parse_func: Callable,
        max_time_ms: int = 30000
    ) -> dict:
        """
        Test parsing of a large SQL file.

        Args:
            filepath: Path to SQL file
            parse_func: Function to parse SQL
            max_time_ms: Maximum allowed time

        Returns:
            Performance results
        """
        with open(filepath) as f:
            sql = f.read()

        file_size = filepath.stat().st_size
        num_lines = sql.count('\n')

        start_time = time.perf_counter()

        try:
            result = parse_func(sql)
            end_time = time.perf_counter()

            parse_time_ms = (end_time - start_time) * 1000

            return {
                "success": True,
                "file_size_bytes": file_size,
                "num_lines": num_lines,
                "parse_time_ms": parse_time_ms,
                "within_threshold": parse_time_ms <= max_time_ms,
                "queries_per_second": num_lines / (parse_time_ms / 1000),
                "bytes_per_second": file_size / (parse_time_ms / 1000)
            }

        except Exception as e:
            end_time = time.perf_counter()
            parse_time_ms = (end_time - start_time) * 1000

            return {
                "success": False,
                "file_size_bytes": file_size,
                "num_lines": num_lines,
                "parse_time_ms": parse_time_ms,
                "error": str(e)
            }


class PerformanceReporter:
    """Generate performance test reports."""

    @staticmethod
    def print_metrics(metrics: PerformanceMetrics) -> None:
        """Print performance metrics."""
        status = "✓" if metrics.success else "✗"
        print(f"{status} {metrics.test_id}")
        print(f"  Time: {metrics.parse_time_ms:.2f}ms")
        print(f"  SQL Length: {metrics.sql_length} chars")

        if not metrics.success:
            print(f"  Error: {metrics.error}")

    @staticmethod
    def print_benchmark(benchmark: PerformanceBenchmark) -> None:
        """Print benchmark results."""
        print(f"\nBenchmark: {benchmark.test_id}")
        print(f"  Iterations:   {benchmark.iterations}")
        print(f"  Avg Time:     {benchmark.avg_time_ms:.2f}ms")
        print(f"  Min Time:     {benchmark.min_time_ms:.2f}ms")
        print(f"  Max Time:     {benchmark.max_time_ms:.2f}ms")
        print(f"  Std Dev:      {benchmark.std_dev_ms:.2f}ms")
        print(f"  Pass Rate:    {benchmark.pass_rate*100:.1f}%")
        print(f"  Threshold:    {benchmark.max_allowed_ms}ms")

        if benchmark.max_time_ms > benchmark.max_allowed_ms:
            print(f"  ⚠ Exceeded threshold!")

    @staticmethod
    def save_performance_report(
        metrics: List[PerformanceMetrics],
        output_path: Path
    ) -> None:
        """
        Save performance report to JSON.

        Args:
            metrics: List of performance metrics
            output_path: Output file path
        """
        report = {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "metrics": [asdict(m) for m in metrics]
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Performance report saved to {output_path}")


class PerformanceProfiler:
    """Profile SQL parsing to identify bottlenecks."""

    @staticmethod
    def profile_parse(
        parse_func: Callable,
        sql: str,
        output_path: Optional[Path] = None
    ) -> dict:
        """
        Profile parsing with cProfile.

        Args:
            parse_func: Function to profile
            sql: SQL query
            output_path: Optional path to save profile stats

        Returns:
            Profile statistics
        """
        import cProfile
        import pstats
        import io

        profiler = cProfile.Profile()
        profiler.enable()

        try:
            result = parse_func(sql)
            success = True
            error = None
        except Exception as e:
            success = False
            error = str(e)
            result = None

        profiler.disable()

        # Get statistics
        stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        stats.strip_dirs()
        stats.sort_stats('cumulative')
        stats.print_stats(20)  # Top 20 functions

        stats_text = stream.getvalue()

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(stats_text)

        return {
            "success": success,
            "error": error,
            "profile_stats": stats_text
        }
