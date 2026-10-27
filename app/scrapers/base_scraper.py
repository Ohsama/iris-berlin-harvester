from abc import ABC, abstractmethod
from typing import Any


class BaseScraper(ABC):
    """Abstract base scraper interface."""

    @abstractmethod
    def scrape(self) -> Any:
        """Execute the scrape procedure."""
        pass
