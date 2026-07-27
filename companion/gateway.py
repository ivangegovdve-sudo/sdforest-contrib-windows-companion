"""Gateway API client for the SDForest Contribution Tool."""
import httpx


class GatewayError(Exception):
    """Non-2xx response from the gateway."""


def submit_parsed_paper(gateway_url: str, target_os: str, parsed: dict) -> str:
    """Submit pre-parsed paper markdown to the gateway.

    Args:
        gateway_url: base URL of the gateway (e.g. https://chloe.blumenkraft.cloud/contrib)
        target_os:   "hypertrophy" or "womens"
        parsed:      dict with keys parsed_markdown, page_count (and optionally llamaparse_job_id)

    Returns:
        receipt_id string

    Raises:
        GatewayError on non-2xx response
    """
    url = f"{gateway_url.rstrip('/')}/submit/parsed-paper"
    payload = {
        "target_os": target_os,
        "parsed_markdown": parsed.get("parsed_markdown", ""),
        "page_count": parsed.get("page_count", 1),
    }
    if parsed.get("llamaparse_job_id"):
        payload["llamaparse_job_id"] = parsed["llamaparse_job_id"]

    try:
        r = httpx.post(url, json=payload, timeout=30)
    except httpx.RequestError as e:
        raise GatewayError(f"Could not reach gateway: {e}") from e

    if not r.is_success:
        detail = r.text[:500]
        raise GatewayError(f"Gateway returned HTTP {r.status_code}: {detail}")

    return r.json()["receipt_id"]


def check_status(gateway_url: str, receipt_id: str) -> dict:
    """Fetch the current status of a submitted proposal.

    Args:
        gateway_url: base URL of the gateway
        receipt_id:  token returned by submit_parsed_paper

    Returns:
        status dict from the gateway

    Raises:
        GatewayError on non-2xx response
    """
    url = f"{gateway_url.rstrip('/')}/status/{receipt_id}"

    try:
        r = httpx.get(url, timeout=15)
    except httpx.RequestError as e:
        raise GatewayError(f"Could not reach gateway: {e}") from e

    if not r.is_success:
        raise GatewayError(f"Gateway returned HTTP {r.status_code}: {r.text[:500]}")

    return r.json()
