import logging
import time
from typing import Any
import requests

logger = logging.getLogger(__name__)


class HttpClient:
    """
    Robust HTTP Client with configurable retries, timeouts, and user agent.
    Handles network glitches, rate-limiting, and status code documentation.
    """

    DEFAULT_USER_AGENT = (
        "IRIS-Berlin-Bebauungsplaene-Harvester/1.0 "
        "(Candidate evaluation; contact: candidate@iris-intel.com)"
    )

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        user_agent: str | None = None,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent or self.DEFAULT_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            }
        )

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        """
        Execute an HTTP GET request with retry backoff.
        """
        retries = 0
        last_exception = None

        while retries < self.max_retries:
            try:
                logger.debug("Requesting GET %s (attempt %d/%d)", url, retries + 1, self.max_retries)
                response = self.session.get(
                    url,
                    timeout=kwargs.get("timeout", self.timeout),
                    allow_redirects=True,
                )

                if response.status_code == 410:
                    logger.warning("Endpoint returned HTTP 410 (Gone): %s", url)
                    return response

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))
                    logger.warning("Rate limited (429). Waiting %d seconds before retrying.", retry_after)
                    time.sleep(retry_after)
                    retries += 1
                    continue

                if response.status_code >= 500:
                    logger.warning("Server error %d on %s. Retrying...", response.status_code, url)
                    time.sleep(self.backoff_factor * (2 ** retries))
                    retries += 1
                    continue

                response.raise_for_status()
                return response

            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exception = exc
                retries += 1
                wait_time = self.backoff_factor * (2 ** (retries - 1))
                logger.warning("Network error '%s' on %s. Retrying in %.1f seconds...", exc, url, wait_time)
                time.sleep(wait_time)

        if last_exception:
            raise last_exception
        raise RuntimeError(f"Failed to fetch {url} after {self.max_retries} attempts.")
