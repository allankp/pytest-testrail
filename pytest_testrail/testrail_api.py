# -*- coding: UTF-8 -*-
"""
TestRail API Client.

This module provides a modern Python client for TestRail API v2.
Compatible with the latest TestRail API (2024+).

References:
    - https://support.testrail.com/hc/en-us/articles/7077039051284-Accessing-the-TestRail-API
    - https://support.testrail.com/hc/en-us/sections/7077185274644-API-reference
"""
from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from typing import Any
from urllib.parse import urljoin

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class TestRailError(Exception):
    """Base exception for TestRail API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class TestRailAuthenticationError(TestRailError):
    """Raised when authentication fails."""

    pass


class TestRailAPIError(TestRailError):
    """Raised when the API returns an error response."""

    pass


class TestRailRateLimitError(TestRailError):
    """Raised when rate limit is exceeded (after retries are exhausted)."""

    pass


class APIClient:
    """
    TestRail API Client for API v2.

    This client supports both username/password and username/API key authentication.
    API keys are the recommended authentication method for automation.

    Example:
        >>> client = APIClient(
        ...     base_url="https://example.testrail.com",
        ...     user="user@example.com",
        ...     password="your-api-key"  # Can be password or API key
        ... )
        >>> case = client.send_get("get_case/1")

    Attributes:
        user: The TestRail username (typically email address).
        password: The TestRail password or API key.
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retries for rate-limited requests.

    References:
        https://support.testrail.com/hc/en-us/articles/7077039051284-Accessing-the-TestRail-API
    """

    DEFAULT_TIMEOUT = 30.0
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_HEADERS = {"Content-Type": "application/json"}

    def __init__(
        self,
        base_url: str,
        user: str,
        password: str,
        *,
        headers: dict[str, str] | None = None,
        cert_check: bool = True,
        timeout: float | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        """
        Initialize the API client.

        Args:
            base_url: The base URL of your TestRail installation
                (e.g., https://example.testrail.com/).
            user: Username for the account (typically email address).
            password: Password or API key for the account.
                API keys are recommended and can be generated under My Settings.
            headers: Optional custom headers to include with requests.
            cert_check: Whether to verify SSL certificates. Defaults to True.
            timeout: Request timeout in seconds. Defaults to 30.0.
            max_retries: Maximum retries for rate-limited requests. Defaults to 3.
        """
        self.user = user
        self.password = password
        self._base_url = base_url.rstrip("/")
        self._api_url = urljoin(self._base_url + "/", "index.php?/api/v2/")
        self.headers = headers or self.DEFAULT_HEADERS.copy()
        self.cert_check = cert_check
        self.timeout = timeout if timeout is not None else self.DEFAULT_TIMEOUT
        self.max_retries = max_retries

        # Create a session for connection pooling
        self._session = requests.Session()
        self._session.auth = HTTPBasicAuth(self.user, self.password)
        self._session.headers.update(self.headers)
        self._session.verify = self.cert_check

    def _build_url(self, uri: str) -> str:
        """Build the full URL for an API endpoint."""
        return f"{self._api_url}{uri}"

    def _handle_response(self, response: requests.Response) -> dict[str, Any] | list[Any]:
        """
        Handle the API response, checking for errors.

        Args:
            response: The requests Response object.

        Returns:
            The parsed JSON response.

        Raises:
            TestRailAuthenticationError: If authentication fails.
            TestRailAPIError: If the API returns an error.
        """
        if response.status_code == 401:
            raise TestRailAuthenticationError(
                "Authentication failed. Please check your credentials.", status_code=401
            )

        if response.status_code == 403:
            raise TestRailAPIError(
                "Access denied. You may not have permission to access this resource.",
                status_code=403,
            )

        try:
            data = response.json()
        except ValueError:
            if response.status_code >= 400:
                raise TestRailAPIError(
                    f"Request failed with status {response.status_code}: {response.text}",
                    status_code=response.status_code,
                ) from None
            return {}

        if isinstance(data, dict) and "error" in data:
            raise TestRailAPIError(data["error"], status_code=response.status_code)

        return data  # type: ignore[no-any-return]

    def _request_with_retry(
        self,
        method: str,
        uri: str,
        data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any]:
        """
        Make an HTTP request with automatic retry on rate limiting.

        Args:
            method: HTTP method (GET or POST).
            uri: API endpoint URI.
            data: JSON data for POST requests.
            **kwargs: Additional keyword arguments.

        Returns:
            The parsed JSON response.

        Raises:
            TestRailRateLimitError: If rate limit is exceeded after all retries.
        """
        url = self._build_url(uri)
        cert_check = kwargs.pop("cert_check", self.cert_check)
        timeout = kwargs.pop("timeout", self.timeout)

        for attempt in range(self.max_retries + 1):
            try:
                if method.upper() == "GET":
                    response = self._session.get(
                        url, verify=cert_check, timeout=timeout, **kwargs
                    )
                else:
                    response = self._session.post(
                        url, json=data, verify=cert_check, timeout=timeout, **kwargs
                    )

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    if attempt < self.max_retries:
                        logger.warning(
                            "Rate limited (429). Waiting %d seconds before retry %d/%d",
                            retry_after,
                            attempt + 1,
                            self.max_retries,
                        )
                        time.sleep(retry_after)
                        continue
                    raise TestRailRateLimitError(
                        f"Rate limit exceeded after {self.max_retries} retries",
                        status_code=429,
                    )

                return self._handle_response(response)

            except requests.exceptions.RequestException as err:
                if attempt < self.max_retries:
                    logger.warning(
                        "Request error (%s). Retry %d/%d",
                        err.__class__.__name__,
                        attempt + 1,
                        self.max_retries,
                    )
                    continue
                if isinstance(err, requests.exceptions.Timeout):
                    message = f"Request timed out after {timeout} seconds"
                else:
                    message = f"Request failed due to a network error: {err}"
                raise TestRailAPIError(message, status_code=None) from err

        # This should never be reached, but just in case
        raise TestRailAPIError("Request failed after all retries")

    def send_get(self, uri: str, **kwargs: Any) -> dict[str, Any] | list[Any]:
        """
        Send a GET request to the API.

        Args:
            uri: The API method to call (e.g., 'get_case/1').
            **kwargs: Additional arguments (cert_check, timeout, etc.).

        Returns:
            The parsed JSON response.

        Example:
            >>> client.send_get('get_case/1')
            {'id': 1, 'title': 'Test Case', ...}
        """
        return self._request_with_retry("GET", uri, **kwargs)

    def send_post(
        self, uri: str, data: dict[str, Any], **kwargs: Any
    ) -> dict[str, Any] | list[Any]:
        """
        Send a POST request to the API.

        Args:
            uri: The API method to call (e.g., 'add_result/1').
            data: The data to submit as JSON.
            **kwargs: Additional arguments (cert_check, timeout, etc.).

        Returns:
            The parsed JSON response.

        Example:
            >>> client.send_post('add_result/1', {'status_id': 1, 'comment': 'Passed'})
            {'id': 1, 'test_id': 1, 'status_id': 1, ...}
        """
        return self._request_with_retry("POST", uri, data=data, **kwargs)

    def get_paginated(
        self,
        uri: str,
        response_key: str | None = None,
        limit: int = 250,
        **kwargs: Any,
    ) -> Iterator[dict[str, Any]]:
        """
        Fetch all pages of a paginated API endpoint.

        Many TestRail API endpoints return paginated results with a default
        limit of 250 items. This method automatically handles pagination
        and yields all results.

        Args:
            uri: The API method to call (e.g., 'get_tests/1').
            response_key: The key in the response containing the items
                (e.g., 'tests', 'results'). If None, will try common keys.
            limit: Number of items per page. Defaults to 250 (API maximum).
            **kwargs: Additional arguments passed to send_get.

        Yields:
            Individual items from all pages.

        Example:
            >>> for test in client.get_paginated('get_tests/1', 'tests'):
            ...     print(test['id'])
        """
        offset = 0
        separator = "&" if "?" in uri else "?"

        while True:
            paginated_uri = f"{uri}{separator}limit={limit}&offset={offset}"
            response = self.send_get(paginated_uri, **kwargs)

            # Handle both paginated and non-paginated responses
            if isinstance(response, list):
                # Non-paginated response (legacy or simple endpoints)
                yield from response
                break

            # Determine the response key for paginated results
            items = None
            if response_key and response_key in response:
                items = response[response_key]
            else:
                # Try common keys used by TestRail API
                for key in ["tests", "results", "cases", "runs", "plans", "projects"]:
                    if key in response:
                        items = response[key]
                        break

            if items is None:
                # If no known key found, yield the response itself
                yield response
                break

            yield from items

            # Check if there are more pages
            size = response.get("size", len(items))
            if size < limit:
                break

            # Check for next link
            links = response.get("_links", {})
            if links.get("next") is None:
                break

            offset += limit

    @staticmethod
    def get_error(json_response: dict[str, Any] | list[Any] | None) -> str | None:
        """
        Extract error message from an API response.

        This is a legacy helper method for backward compatibility.
        New code should use the exception-based error handling.

        Args:
            json_response: The API response.

        Returns:
            The error message if present, None otherwise.
        """
        if isinstance(json_response, dict) and "error" in json_response:
            error = json_response["error"]
            return str(error) if error is not None else None
        return None

    def close(self) -> None:
        """Close the underlying session."""
        self._session.close()

    def __enter__(self) -> APIClient:
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()
