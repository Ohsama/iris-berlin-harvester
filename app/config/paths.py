from pathlib import Path


class ProjectPaths:
    """Project directory paths management."""

    def __init__(self, base_dir: Path | None = None):
        self.root = base_dir or Path(__file__).resolve().parent.parent.parent
        self.fixtures = self.root / "fixtures"
        self.output = self.root / "output"
        self.docs = self.root / "docs"
        self.validation = self.root / "validation"
        self.tests = self.root / "tests"

        # Ensure output directories exist
        self.output.mkdir(parents=True, exist_ok=True)
