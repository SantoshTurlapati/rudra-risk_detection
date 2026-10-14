import asyncio
import math
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Protocol


class ProviderUnavailable(RuntimeError):
    """Raised when no authorized, configured provider can serve a request."""

    def __init__(self, message: str, *, reason: str = "unavailable"):
        super().__init__(message)
        self.reason = reason


class ProviderRateLimited(ProviderUnavailable):
    """A provider explicitly refused the request due to its rate limit."""

    def __init__(self, source: str, retry_after_seconds: float | None = None):
        if retry_after_seconds is not None and (
            not math.isfinite(retry_after_seconds) or retry_after_seconds < 0
        ):
            raise ValueError("retry_after_seconds must be a finite, non-negative value.")
        super().__init__(
            f"{source} is rate limited.",
            reason="rate_limited",
        )
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True)
class DiscoveryPage:
    source: str
    retrieved_at: datetime
    items: list[dict[str, Any]]
    next_page_token: str | None = None


class SocialDiscoveryProvider(Protocol):
    async def search_profiles(
        self,
        query: str,
        *,
        page_token: str | None = None,
    ) -> DiscoveryPage: ...


class AppStoreProvider(Protocol):
    async def search_listings(
        self,
        query: str,
        *,
        page_token: str | None = None,
    ) -> DiscoveryPage: ...


class UnconfiguredDiscoveryProvider:
    """Fail-closed provider placeholder; it never returns synthetic results."""

    def __init__(self, source: str):
        self.source = source

    async def search_profiles(
        self,
        query: str,
        *,
        page_token: str | None = None,
    ) -> DiscoveryPage:
        raise ProviderUnavailable(f"{self.source} is unavailable: no authorized provider is configured.")

    async def search_listings(
        self,
        query: str,
        *,
        page_token: str | None = None,
    ) -> DiscoveryPage:
        raise ProviderUnavailable(f"{self.source} is unavailable: no authorized provider is configured.")


def _validate_query(query: str, page_token: str | None) -> tuple[str, str | None]:
    if not isinstance(query, str):
        raise ValueError("Discovery query must be text.")
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("Discovery query must not be blank.")
    if len(normalized_query) > 256:
        raise ValueError("Discovery query must be at most 256 characters.")
    if any(unicodedata.category(char).startswith("C") for char in normalized_query):
        raise ValueError("Discovery query must not contain control characters.")

    if page_token is not None:
        if not isinstance(page_token, str):
            raise ValueError("Discovery page token must be text.")
        page_token = page_token.strip()
        if not page_token:
            page_token = None
        elif len(page_token) > 1024 or any(
            unicodedata.category(char).startswith("C") for char in page_token
        ):
            raise ValueError("Discovery page token is invalid.")
    return normalized_query, page_token


def _stable_item_key(item: dict[str, Any]) -> tuple[str, str] | None:
    for field in ("profile_id", "listing_id", "app_id", "package_id", "handle", "id"):
        value = item.get(field)
        if not isinstance(value, (str, int)) or isinstance(value, bool):
            continue
        normalized = str(value).strip().casefold()
        if normalized:
            namespace = str(item.get("platform", "")).strip().casefold() if field == "handle" else ""
            return field, f"{namespace}:{normalized}"
    return None


def _validated_page(page: DiscoveryPage, source: str) -> DiscoveryPage:
    if not isinstance(page, DiscoveryPage) or page.source != source:
        raise ProviderUnavailable(
            f"{source} returned invalid source provenance.",
            reason="invalid_response",
        )
    if (
        not isinstance(page.retrieved_at, datetime)
        or page.retrieved_at.tzinfo is None
        or page.retrieved_at.utcoffset() is None
        or not isinstance(page.items, list)
    ):
        raise ProviderUnavailable(
            f"{source} returned invalid response metadata.",
            reason="invalid_response",
        )
    if page.next_page_token is not None and (
        not isinstance(page.next_page_token, str)
        or len(page.next_page_token) > 1024
        or any(unicodedata.category(char).startswith("C") for char in page.next_page_token)
    ):
        raise ProviderUnavailable(
            f"{source} returned an invalid pagination token.",
            reason="invalid_response",
        )

    unique_items = []
    seen = set()
    for item in page.items:
        if not isinstance(item, dict):
            raise ProviderUnavailable(
                f"{source} returned a malformed result.",
                reason="invalid_response",
            )
        stable_key = _stable_item_key(item)
        if stable_key is not None and stable_key in seen:
            continue
        if stable_key is not None:
            seen.add(stable_key)
        unique_items.append(item)

    return DiscoveryPage(
        source=page.source,
        retrieved_at=page.retrieved_at.astimezone(timezone.utc),
        items=unique_items,
        next_page_token=page.next_page_token,
    )


async def run_discovery_request(
    search: Callable[..., Awaitable[DiscoveryPage]],
    query: str,
    *,
    source: str,
    page_token: str | None = None,
    timeout_seconds: float = 10,
) -> DiscoveryPage:
    """Validate and bound a configured provider call; no provider is selected here."""
    normalized_query, normalized_token = _validate_query(query, page_token)
    if (
        not isinstance(timeout_seconds, (int, float))
        or isinstance(timeout_seconds, bool)
        or not math.isfinite(timeout_seconds)
        or not 0 < timeout_seconds <= 60
    ):
        raise ValueError("Provider timeout must be greater than zero and at most 60 seconds.")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("Provider source must be specified.")

    try:
        page = await asyncio.wait_for(
            search(normalized_query, page_token=normalized_token),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        raise ProviderUnavailable(
            f"{source} request timed out.",
            reason="timeout",
        ) from exc

    return _validated_page(page, source.strip())


def provider_statuses() -> list[dict[str, Any]]:
    return [
        {
            "provider": "Social profile discovery",
            "connected": False,
            "status": "Unavailable: no authorized provider configured",
        },
        {
            "provider": "App-store listing discovery",
            "connected": False,
            "status": "Unavailable: no authorized provider configured",
        },
    ]
