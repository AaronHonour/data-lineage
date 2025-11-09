"""Test case loader and validator for SQL lineage tests."""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any
import jsonschema
from enum import Enum


class Difficulty(str, Enum):
    """Test difficulty levels."""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    EDGE_CASE = "edge_case"


class TransformationType(str, Enum):
    """Types of SQL transformations."""
    PROJECTION = "projection"
    TRANSFORMATION = "transformation"
    AGGREGATION = "aggregation"
    JOIN = "join"
    SUBQUERY = "subquery"
    WINDOW = "window"


@dataclass
class ColumnDefinition:
    """Column schema definition."""
    name: str
    type: str
    nullable: bool = True
    primary_key: bool = False


@dataclass
class TableDefinition:
    """Table schema definition."""
    name: str
    columns: List[ColumnDefinition]

    @classmethod
    def from_dict(cls, data: dict) -> "TableDefinition":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            columns=[ColumnDefinition(**col) for col in data["columns"]]
        )


@dataclass
class LineageExpectation:
    """Expected lineage relationship."""
    target: str
    sources: List[str]
    expression: Optional[str] = None
    transformation_type: TransformationType = TransformationType.PROJECTION
    confidence: float = 1.0

    @classmethod
    def from_dict(cls, data: dict) -> "LineageExpectation":
        """Create from dictionary."""
        return cls(
            target=data["target"],
            sources=data["sources"],
            expression=data.get("expression"),
            transformation_type=TransformationType(data.get("transformation_type", "projection")),
            confidence=data.get("confidence", 1.0)
        )


@dataclass
class TestCase:
    """SQL lineage test case."""
    test_id: str
    name: str
    difficulty: Difficulty
    sql: str
    expected_lineage: List[LineageExpectation]

    # Optional fields
    description: Optional[str] = None
    phase: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    dialect: str = "postgres"
    source_tables: List[TableDefinition] = field(default_factory=list)
    min_confidence: float = 0.8
    max_parse_time_ms: int = 5000
    skip: bool = False
    skip_reason: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "TestCase":
        """Create test case from dictionary."""
        return cls(
            test_id=data["test_id"],
            name=data["name"],
            difficulty=Difficulty(data["difficulty"]),
            sql=data["sql"],
            expected_lineage=[
                LineageExpectation.from_dict(e) for e in data["expected_lineage"]
            ],
            description=data.get("description"),
            phase=data.get("phase"),
            tags=data.get("tags", []),
            dialect=data.get("dialect", "postgres"),
            source_tables=[
                TableDefinition.from_dict(t) for t in data.get("source_tables", [])
            ],
            min_confidence=data.get("min_confidence", 0.8),
            max_parse_time_ms=data.get("max_parse_time_ms", 5000),
            skip=data.get("skip", False),
            skip_reason=data.get("skip_reason")
        )

    def should_run_in_phase(self, current_phase: int) -> bool:
        """Check if test should run in current development phase."""
        if self.skip:
            return False

        if self.phase is None:
            return True

        return self.phase <= current_phase


class TestCaseLoader:
    """Load and validate SQL lineage test cases."""

    def __init__(self, schema_path: Optional[Path] = None):
        """
        Initialize test case loader.

        Args:
            schema_path: Path to JSON schema file (optional)
        """
        if schema_path is None:
            # Default to schema in fixtures
            schema_path = Path(__file__).parent.parent / "fixtures" / "schemas" / "test_case_schema.json"

        self.schema = self._load_schema(schema_path)
        self.validator = jsonschema.Draft7Validator(self.schema)

    def _load_schema(self, schema_path: Path) -> dict:
        """Load JSON schema."""
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        with open(schema_path) as f:
            return json.load(f)

    def validate_test_case(self, test_data: dict) -> List[str]:
        """
        Validate test case against schema.

        Args:
            test_data: Test case dictionary

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        for error in self.validator.iter_errors(test_data):
            errors.append(f"{'.'.join(str(p) for p in error.path)}: {error.message}")

        return errors

    def load_test_case(self, filepath: Path) -> TestCase:
        """
        Load single test case from JSON file.

        Args:
            filepath: Path to test case JSON file

        Returns:
            TestCase instance

        Raises:
            ValueError: If test case is invalid
        """
        with open(filepath) as f:
            data = json.load(f)

        # Validate against schema
        errors = self.validate_test_case(data)
        if errors:
            raise ValueError(
                f"Invalid test case in {filepath}:\n" + "\n".join(errors)
            )

        return TestCase.from_dict(data)

    def load_test_cases_from_file(self, filepath: Path) -> List[TestCase]:
        """
        Load multiple test cases from a JSON array file.

        Args:
            filepath: Path to JSON file containing array of test cases

        Returns:
            List of TestCase instances
        """
        with open(filepath) as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError(f"Expected JSON array in {filepath}")

        test_cases = []
        for i, test_data in enumerate(data):
            errors = self.validate_test_case(test_data)
            if errors:
                raise ValueError(
                    f"Invalid test case #{i} in {filepath}:\n" + "\n".join(errors)
                )
            test_cases.append(TestCase.from_dict(test_data))

        return test_cases

    def load_directory(self, directory: Path, pattern: str = "*.json") -> Dict[str, List[TestCase]]:
        """
        Load all test case files from directory.

        Args:
            directory: Directory containing test case files
            pattern: Glob pattern for test files

        Returns:
            Dictionary mapping category name to list of test cases
        """
        if not directory.exists():
            raise FileNotFoundError(f"Test case directory not found: {directory}")

        categories = {}

        for filepath in sorted(directory.glob(pattern)):
            # Skip schema files
            if filepath.name.endswith("_schema.json"):
                continue

            category = filepath.stem

            try:
                test_cases = self.load_test_cases_from_file(filepath)
                categories[category] = test_cases
            except Exception as e:
                raise ValueError(f"Failed to load {filepath}: {e}") from e

        return categories

    def load_all_phases(self, base_path: Path) -> Dict[int, Dict[str, List[TestCase]]]:
        """
        Load test cases organized by phase.

        Args:
            base_path: Base directory containing phase subdirectories

        Returns:
            Dictionary mapping phase number to categories
        """
        phases = {}

        for phase_num in range(1, 7):
            phase_dir = base_path / f"phase{phase_num}_*"
            matching_dirs = list(base_path.glob(f"phase{phase_num}_*"))

            if matching_dirs:
                phase_dir = matching_dirs[0]
                phases[phase_num] = self.load_directory(phase_dir)

        return phases

    def get_test_statistics(self, test_cases: List[TestCase]) -> dict:
        """
        Generate statistics about test cases.

        Args:
            test_cases: List of test cases

        Returns:
            Dictionary with statistics
        """
        stats = {
            "total": len(test_cases),
            "by_difficulty": {},
            "by_phase": {},
            "by_dialect": {},
            "skipped": 0,
            "avg_expected_lineages": 0,
            "total_lineages": 0,
        }

        for tc in test_cases:
            # Count by difficulty
            stats["by_difficulty"][tc.difficulty.value] = \
                stats["by_difficulty"].get(tc.difficulty.value, 0) + 1

            # Count by phase
            if tc.phase:
                stats["by_phase"][tc.phase] = stats["by_phase"].get(tc.phase, 0) + 1

            # Count by dialect
            stats["by_dialect"][tc.dialect] = stats["by_dialect"].get(tc.dialect, 0) + 1

            # Count skipped
            if tc.skip:
                stats["skipped"] += 1

            # Count lineages
            stats["total_lineages"] += len(tc.expected_lineage)

        if stats["total"] > 0:
            stats["avg_expected_lineages"] = stats["total_lineages"] / stats["total"]

        return stats


class TestCaseGenerator:
    """Generate test case templates."""

    @staticmethod
    def create_template(
        test_id: str,
        name: str,
        sql: str,
        difficulty: str = "basic",
        phase: int = 1
    ) -> dict:
        """
        Create a test case template.

        Args:
            test_id: Unique test ID
            name: Test name
            sql: SQL query
            difficulty: Difficulty level
            phase: Development phase

        Returns:
            Test case dictionary ready for manual completion
        """
        return {
            "test_id": test_id,
            "name": name,
            "description": "TODO: Add description",
            "difficulty": difficulty,
            "phase": phase,
            "tags": [],
            "dialect": "postgres",
            "sql": sql.strip(),
            "source_tables": [
                {
                    "name": "TODO_table_name",
                    "columns": [
                        {"name": "TODO_column", "type": "TODO_type"}
                    ]
                }
            ],
            "expected_lineage": [
                {
                    "target": "result.TODO_column",
                    "sources": ["TODO_table.TODO_column"],
                    "expression": "",
                    "transformation_type": "projection"
                }
            ],
            "min_confidence": 0.8,
            "max_parse_time_ms": 5000
        }

    @staticmethod
    def save_template(template: dict, filepath: Path) -> None:
        """Save test case template to file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump([template], f, indent=2)
        print(f"Template saved to {filepath}")
