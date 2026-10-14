import asyncio
from datetime import datetime, timezone

import pytest

from app.providers.discovery import (
    DiscoveryPage,
    ProviderRateLimited,
    ProviderUnavailable,
    UnconfiguredDiscoveryProvider,
    provider_statuses,
    run_discovery_request,
)


@pytest.mark.parametrize(
    "operation",
    ["search_profiles", "search_listings"],
)
def test_unconfigured_discovery_providers_fail_closed(operation):
    provider = UnconfiguredDiscoveryProvider("test provider")
    search = getattr(provider, operation)
    with pytest.raises(ProviderUnavailable, match="no authorized provider is configured"):
        asyncio.run(search("candidate"))


def test_provider_statuses_do_not_claim_live_integrations():
    statuses = provider_statuses()
    assert len(statuses) == 2
    assert all(status["connected"] is False for status in statuses)
    assert all("Unavailable" in status["status"] for status in statuses)


@pytest.mark.parametrize(
    "query,page_token",
    [
        ("   ", None),
        ("x" * 257, None),
        ("candidate\u0000brand", None),
        ("candidate", "bad\u0000token"),
    ],
)
def test_discovery_contract_rejects_invalid_query_and_pagination_input(query, page_token):
    async def unused_search(_query, *, page_token=None):
        pytest.fail("invalid discovery input must not reach the provider")

    with pytest.raises(ValueError):
        asyncio.run(
            run_discovery_request(
                unused_search,
                query,
                source="test provider",
                page_token=page_token,
            )
        )


def test_discovery_contract_normalizes_query_records_provenance_and_deduplicates():
    captured = {}
    retrieved_at = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)

    async def search(query, *, page_token=None):
        captured.update(query=query, page_token=page_token)
        return DiscoveryPage(
            source="authorized test adapter",
            retrieved_at=retrieved_at,
            next_page_token="next-page",
            items=[
                {"platform": "X", "handle": "@Example"},
                {"platform": "x", "handle": "@example"},
                {"package_id": "com.example.app"},
                {"package_id": "COM.EXAMPLE.APP"},
                {"display_name": "Unkeyed result"},
                {"display_name": "Unkeyed result"},
            ],
        )

    page = asyncio.run(
        run_discovery_request(
            search,
            "  Example Brand  ",
            source="authorized test adapter",
            page_token=" page-1 ",
        )
    )

    assert captured == {"query": "Example Brand", "page_token": "page-1"}
    assert page.source == "authorized test adapter"
    assert page.retrieved_at == retrieved_at
    assert page.next_page_token == "next-page"
    assert len(page.items) == 4
    assert page.items[0]["handle"] == "@Example"
    assert page.items[2]["display_name"] == "Unkeyed result"


def test_discovery_contract_maps_timeout_to_explicit_unavailable_error():
    async def slow_search(_query, *, page_token=None):
        await asyncio.sleep(0.02)
        return DiscoveryPage("provider", datetime.now(timezone.utc), [])

    with pytest.raises(ProviderUnavailable, match="timed out") as error:
        asyncio.run(
            run_discovery_request(
                slow_search,
                "candidate",
                source="provider",
                timeout_seconds=0.001,
            )
        )
    assert error.value.reason == "timeout"


def test_discovery_contract_preserves_rate_limit_and_retry_guidance():
    async def limited_search(_query, *, page_token=None):
        raise ProviderRateLimited("provider", retry_after_seconds=30)

    with pytest.raises(ProviderRateLimited) as error:
        asyncio.run(
            run_discovery_request(
                limited_search,
                "candidate",
                source="provider",
            )
        )
    assert error.value.reason == "rate_limited"
    assert error.value.retry_after_seconds == 30


@pytest.mark.parametrize(
    "page",
    [
        None,
        DiscoveryPage("other provider", datetime.now(timezone.utc), []),
        DiscoveryPage("provider", datetime.now(timezone.utc), ["not an object"]),
        DiscoveryPage("provider", datetime.now(timezone.utc).replace(tzinfo=None), []),
    ],
)
def test_discovery_contract_rejects_invalid_provider_response(page):
    async def search(_query, *, page_token=None):
        return page

    with pytest.raises(ProviderUnavailable) as error:
        asyncio.run(run_discovery_request(search, "candidate", source="provider"))
    assert error.value.reason == "invalid_response"
