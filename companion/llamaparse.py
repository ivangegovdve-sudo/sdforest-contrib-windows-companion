"""LlamaParse EU API client for the SDForest Contribution Tool.

Mirrors the logic in the gateway's llamaparse_gate.py so contributors can run
LlamaParse locally with their own API key and submit the pre-parsed markdown.
"""
import time
import httpx

LLAMAPARSE_BASE_URL = "https://api.cloud.eu.llamaindex.ai"
_POLL_INTERVAL_S = 4
_MAX_POLLS = 30


class ParseError(Exception):
    """The document was rejected by LlamaParse (contributor's problem)."""


class ParseUnavailable(Exception):
    """LlamaParse is unreachable or erroring (service-side problem)."""


def parse_pdf(pdf_bytes: bytes, api_key: str) -> dict:
    """Parse a PDF via LlamaParse and return parsed content.

    Args:
        pdf_bytes: raw PDF bytes
        api_key:   LlamaParse API key (contributor's own)

    Returns:
        dict with keys:
            parsed_markdown (str)  — full markdown text
            page_count (int)       — number of pages detected

    Raises:
        ParseError       — document rejected (too short, bad format, …)
        ParseUnavailable — network error or service outage
    """
    if not api_key:
        raise ParseUnavailable("LlamaParse API key is not configured")

    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        with httpx.Client(base_url=LLAMAPARSE_BASE_URL, headers=headers, timeout=120) as client:
            # 1. Upload
            upload_r = client.post(
                "/api/parsing/upload",
                files={"file": ("document.pdf", pdf_bytes, "application/pdf")},
                data={"result_type": "markdown"},
            )
            upload_r.raise_for_status()
            job_id = upload_r.json()["id"]

            # 2. Poll for completion
            for _ in range(_MAX_POLLS):
                time.sleep(_POLL_INTERVAL_S)
                status_r = client.get(f"/api/parsing/job/{job_id}")
                status_r.raise_for_status()
                job_status = status_r.json().get("status")
                if job_status == "SUCCESS":
                    break
                if job_status in ("ERROR", "CANCELLED"):
                    raise ParseError(f"LlamaParse job failed with status: {job_status}")
            else:
                raise ParseUnavailable(
                    f"LlamaParse job did not finish within {_MAX_POLLS * _POLL_INTERVAL_S}s"
                )

            # 3. Fetch result
            result_r = client.get(f"/api/parsing/job/{job_id}/result/markdown")
            result_r.raise_for_status()
            data = result_r.json()
            md = data.get("markdown", "")
            pages = data.get("pages", [])

    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        # 402 = out of credits; 401/403 = bad key; 429 = throttled; 5xx = outage
        raise ParseUnavailable(f"LlamaParse HTTP {code}: {e.response.text[:200]}") from e
    except httpx.RequestError as e:
        raise ParseUnavailable(f"LlamaParse unreachable: {type(e).__name__}: {e}") from e

    if len(md) < 200:
        raise ParseError("Parsed output too short to be a scientific paper")

    return {
        "parsed_markdown": md,
        "page_count": len(pages) or 1,
    }
