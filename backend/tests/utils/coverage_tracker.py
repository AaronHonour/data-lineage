"""SQL feature coverage tracking for comprehensive testing."""
from collections import defaultdict
from typing import Set, Dict, List
from pathlib import Path
import json
from dataclasses import dataclass, asdict


@dataclass
class FeatureCoverage:
    """Coverage statistics for a SQL feature."""
    feature: str
    category: str
    covered: bool
    test_count: int
    passing_tests: int
    failing_tests: int


class SQLFeatureCoverage:
    """Track which SQL features are covered by tests."""

    # Comprehensive SQL feature taxonomy
    SQL_FEATURES = {
        'basic': {
            'select_star': 'SELECT *',
            'select_columns': 'SELECT specific columns',
            'column_alias': 'Column aliasing (AS)',
            'where_clause': 'WHERE filtering',
            'order_by': 'ORDER BY',
            'limit': 'LIMIT/TOP',
            'distinct': 'DISTINCT',
        },
        'transformations': {
            'concat': 'String concatenation (||, CONCAT)',
            'arithmetic': 'Arithmetic operations (+, -, *, /)',
            'case_statement': 'CASE WHEN expressions',
            'coalesce': 'COALESCE/IFNULL',
            'cast': 'Type casting (CAST, ::)',
            'substring': 'String functions (SUBSTRING, LEFT, RIGHT)',
            'date_functions': 'Date/time functions',
            'math_functions': 'Mathematical functions',
            'string_functions': 'String manipulation functions',
        },
        'joins': {
            'inner_join': 'INNER JOIN',
            'left_join': 'LEFT JOIN',
            'right_join': 'RIGHT JOIN',
            'full_join': 'FULL OUTER JOIN',
            'cross_join': 'CROSS JOIN',
            'self_join': 'Self-join',
            'multiple_joins': 'Multiple joins (3+ tables)',
            'complex_join_conditions': 'Complex ON conditions',
        },
        'aggregations': {
            'sum': 'SUM()',
            'count': 'COUNT()',
            'avg': 'AVG()',
            'min': 'MIN()',
            'max': 'MAX()',
            'group_by': 'GROUP BY',
            'having': 'HAVING',
            'group_by_multiple': 'GROUP BY multiple columns',
            'count_distinct': 'COUNT(DISTINCT)',
        },
        'subqueries': {
            'scalar_subquery': 'Scalar subquery in SELECT',
            'in_subquery': 'IN (subquery)',
            'exists_subquery': 'EXISTS (subquery)',
            'not_exists': 'NOT EXISTS',
            'correlated_subquery': 'Correlated subquery',
            'subquery_in_from': 'Subquery in FROM (derived table)',
            'subquery_in_where': 'Subquery in WHERE',
        },
        'advanced': {
            'cte': 'Common Table Expressions (WITH)',
            'recursive_cte': 'Recursive CTE',
            'multiple_ctes': 'Multiple CTEs',
            'window_function': 'Window functions',
            'row_number': 'ROW_NUMBER()',
            'rank': 'RANK()/DENSE_RANK()',
            'lag_lead': 'LAG()/LEAD()',
            'partition_by': 'PARTITION BY in windows',
            'union': 'UNION',
            'union_all': 'UNION ALL',
            'intersect': 'INTERSECT',
            'except': 'EXCEPT',
        },
        'dml': {
            'insert_select': 'INSERT INTO ... SELECT',
            'update_from': 'UPDATE with FROM',
            'delete_with_join': 'DELETE with JOIN',
            'merge': 'MERGE/UPSERT',
        },
        'ddl': {
            'create_view': 'CREATE VIEW',
            'create_materialized_view': 'CREATE MATERIALIZED VIEW',
            'create_table_as': 'CREATE TABLE AS SELECT',
        },
        'edge_cases': {
            'lateral_join': 'LATERAL join',
            'values_clause': 'VALUES clause',
            'pivot': 'PIVOT operations',
            'unpivot': 'UNPIVOT operations',
            'jsonb_operations': 'JSONB operators (PostgreSQL)',
            'array_operations': 'Array operations',
            'generate_series': 'Set-returning functions',
            'recursive_hierarchical': 'Recursive hierarchical queries',
        }
    }

    def __init__(self):
        """Initialize coverage tracker."""
        self.covered_features: Set[str] = set()
        self.feature_test_count: Dict[str, int] = defaultdict(int)
        self.feature_pass_count: Dict[str, int] = defaultdict(int)
        self.feature_fail_count: Dict[str, int] = defaultdict(int)

    def mark_feature_tested(self, feature: str, passed: bool = True) -> None:
        """
        Mark a feature as tested.

        Args:
            feature: Feature identifier
            passed: Whether test passed
        """
        self.covered_features.add(feature)
        self.feature_test_count[feature] += 1

        if passed:
            self.feature_pass_count[feature] += 1
        else:
            self.feature_fail_count[feature] += 1

    def mark_features_from_tags(self, tags: List[str], passed: bool = True) -> None:
        """
        Mark features from test tags.

        Args:
            tags: List of feature tags
            passed: Whether test passed
        """
        for tag in tags:
            self.mark_feature_tested(tag, passed)

    def get_coverage_by_category(self, category: str) -> dict:
        """
        Get coverage for a specific category.

        Args:
            category: Category name

        Returns:
            Coverage statistics for category
        """
        if category not in self.SQL_FEATURES:
            return {}

        features = self.SQL_FEATURES[category]
        total = len(features)
        covered = sum(1 for f in features.keys() if f in self.covered_features)

        return {
            'category': category,
            'total_features': total,
            'covered_features': covered,
            'coverage_percent': (covered / total * 100) if total > 0 else 0,
            'features': {
                fname: {
                    'covered': fname in self.covered_features,
                    'test_count': self.feature_test_count.get(fname, 0),
                    'passing': self.feature_pass_count.get(fname, 0),
                    'failing': self.feature_fail_count.get(fname, 0),
                    'description': fdesc
                }
                for fname, fdesc in features.items()
            }
        }

    def get_full_coverage_report(self) -> dict:
        """
        Get comprehensive coverage report.

        Returns:
            Full coverage statistics
        """
        total_features = sum(len(features) for features in self.SQL_FEATURES.values())
        total_covered = len(self.covered_features)

        categories = {}
        for category in self.SQL_FEATURES.keys():
            categories[category] = self.get_coverage_by_category(category)

        return {
            'overall': {
                'total_features': total_features,
                'covered_features': total_covered,
                'coverage_percent': (total_covered / total_features * 100) if total_features > 0 else 0,
                'total_tests': sum(self.feature_test_count.values()),
                'passing_tests': sum(self.feature_pass_count.values()),
                'failing_tests': sum(self.feature_fail_count.values()),
            },
            'by_category': categories,
            'missing_features': self.get_missing_features(),
            'most_tested': self.get_most_tested_features(10),
        }

    def get_missing_features(self) -> Dict[str, List[str]]:
        """
        Get features not yet covered by tests.

        Returns:
            Dictionary of category -> missing features
        """
        missing = {}

        for category, features in self.SQL_FEATURES.items():
            missing_in_category = [
                fname for fname in features.keys()
                if fname not in self.covered_features
            ]

            if missing_in_category:
                missing[category] = missing_in_category

        return missing

    def get_most_tested_features(self, top_n: int = 10) -> List[dict]:
        """
        Get most tested features.

        Args:
            top_n: Number of top features to return

        Returns:
            List of feature statistics
        """
        features = []

        for feature, count in self.feature_test_count.items():
            # Find category
            category = None
            for cat, feats in self.SQL_FEATURES.items():
                if feature in feats:
                    category = cat
                    break

            features.append({
                'feature': feature,
                'category': category,
                'test_count': count,
                'passing': self.feature_pass_count.get(feature, 0),
                'failing': self.feature_fail_count.get(feature, 0),
            })

        # Sort by test count
        features.sort(key=lambda x: x['test_count'], reverse=True)

        return features[:top_n]

    def get_feature_list(self) -> List[FeatureCoverage]:
        """
        Get list of all features with coverage status.

        Returns:
            List of FeatureCoverage objects
        """
        features = []

        for category, feats in self.SQL_FEATURES.items():
            for feature_name in feats.keys():
                features.append(FeatureCoverage(
                    feature=feature_name,
                    category=category,
                    covered=feature_name in self.covered_features,
                    test_count=self.feature_test_count.get(feature_name, 0),
                    passing_tests=self.feature_pass_count.get(feature_name, 0),
                    failing_tests=self.feature_fail_count.get(feature_name, 0),
                ))

        return features

    def print_coverage_report(self) -> None:
        """Print formatted coverage report."""
        report = self.get_full_coverage_report()

        print("\n" + "="*70)
        print("SQL FEATURE COVERAGE REPORT")
        print("="*70)

        overall = report['overall']
        print(f"\nOverall Coverage: {overall['coverage_percent']:.1f}%")
        print(f"  Features Covered: {overall['covered_features']}/{overall['total_features']}")
        print(f"  Total Tests:      {overall['total_tests']}")
        print(f"  Passing:          {overall['passing_tests']}")
        print(f"  Failing:          {overall['failing_tests']}")

        print("\n" + "-"*70)
        print("Coverage by Category:")
        print("-"*70)

        for category, stats in report['by_category'].items():
            coverage = stats['coverage_percent']
            status = "✓" if coverage == 100 else "⚠" if coverage > 50 else "✗"
            print(f"{status} {category:20s} {coverage:5.1f}% "
                  f"({stats['covered_features']}/{stats['total_features']})")

        if report['missing_features']:
            print("\n" + "-"*70)
            print("Missing Coverage (High Priority):")
            print("-"*70)

            for category, features in report['missing_features'].items():
                if category in ['basic', 'transformations', 'joins', 'aggregations']:
                    print(f"\n{category}:")
                    for feature in features[:5]:  # Show top 5
                        desc = self.SQL_FEATURES[category][feature]
                        print(f"  - {feature}: {desc}")

        print("\n" + "="*70 + "\n")

    def save_coverage_report(self, output_path: Path) -> None:
        """
        Save coverage report to JSON file.

        Args:
            output_path: Output file path
        """
        report = self.get_full_coverage_report()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Coverage report saved to {output_path}")

    def export_missing_tests_template(self, output_path: Path, category: str) -> None:
        """
        Export template test cases for missing features.

        Args:
            output_path: Output file path
            category: Category to export
        """
        if category not in self.SQL_FEATURES:
            raise ValueError(f"Unknown category: {category}")

        missing = [
            fname for fname in self.SQL_FEATURES[category].keys()
            if fname not in self.covered_features
        ]

        templates = []
        for i, feature in enumerate(missing, 1):
            description = self.SQL_FEATURES[category][feature]
            templates.append({
                "test_id": f"{category}-{feature}-001",
                "name": f"Test {description}",
                "description": f"TODO: Implement test for {description}",
                "difficulty": "basic" if category == 'basic' else "intermediate",
                "phase": 1 if category == 'basic' else 2,
                "tags": [feature, category],
                "dialect": "postgres",
                "sql": "TODO: Add SQL here",
                "source_tables": [],
                "expected_lineage": [],
                "min_confidence": 0.8,
                "max_parse_time_ms": 5000
            })

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(templates, f, indent=2)

        print(f"Template test cases saved to {output_path}")
        print(f"Generated {len(templates)} templates for {category}")
