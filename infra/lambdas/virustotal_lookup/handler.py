"""VirusTotal lookup Lambda function.

Supports two invocation shapes:
  1. Legacy direct invoke: {"ioc": "...", "ioc_type": "..."}
  2. Bedrock Agent action-group invoke (messageVersion / actionGroup present)

Falls back to deterministic stub data when no API key is configured, so the
Lambda can be shipped and demoed before a real VirusTotal key is available.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import boto3

# Initialize clients
secrets_client = boto3.client("secretsmanager")
SECRET_ARN = os.environ.get("SECRET_ARN")

# IOC types that normalise to "hash"
_HASH_ALIASES = {"hash", "md5", "sha1", "sha256", "hash_md5", "hash_sha1", "hash_sha256"}

# Stub data returned when no API key is available
_STUBS: dict[str, dict] = {
    "ip": {
        "source": "virustotal",
        "ioc_type": "ip",
        "stub": True,
        "malicious_count": 3,
        "suspicious_count": 1,
        "harmless_count": 62,
        "undetected_count": 20,
        "reputation": -5,
        "country": "US",
        "as_owner": "Stub AS 0",
    },
    "domain": {
        "source": "virustotal",
        "ioc_type": "domain",
        "stub": True,
        "malicious_count": 2,
        "suspicious_count": 0,
        "harmless_count": 70,
        "undetected_count": 15,
        "reputation": 0,
        "categories": {},
    },
    "hash": {
        "source": "virustotal",
        "ioc_type": "hash",
        "stub": True,
        "malicious_count": 42,
        "suspicious_count": 5,
        "harmless_count": 0,
        "undetected_count": 18,
        "file_type": "Win32 EXE",
        "file_size": 0,
        "names": [],
    },
}


def get_api_key() -> str:
    """Retrieve VirusTotal API key from Secrets Manager."""
    if not SECRET_ARN:
        return ""
    try:
        response = secrets_client.get_secret_value(SecretId=SECRET_ARN)
        secret = json.loads(response["SecretString"])
        return secret.get("VIRUSTOTAL_API_KEY", "")
    except Exception as e:
        print(f"Error retrieving secret: {e}")
        return ""


def _http_get_json(url: str, headers: dict, timeout: int = 10) -> dict:
    """Perform a GET returning parsed JSON (or an error dict on any failure).

    Uses stdlib ``urllib`` so the Lambda package stays dependency-free.
    """
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", errors="replace") if e.fp else ""
        except Exception:
            pass
        return {"__error__": f"HTTP {e.code}: {detail[:200] or e.reason}"}
    except urllib.error.URLError as e:
        return {"__error__": f"URLError: {e.reason}"}
    except Exception as e:
        return {"__error__": f"{type(e).__name__}: {e}"}


def lookup_ip(api_key: str, ip: str) -> dict:
    """Look up IP address in VirusTotal."""
    url = f"https://www.virustotal.com/api/v3/ip_addresses/{ip}"
    data = _http_get_json(url, {"x-apikey": api_key})
    if "__error__" in data:
        return {"error": data["__error__"], "source": "virustotal"}

    attributes = data.get("data", {}).get("attributes", {})
    stats = attributes.get("last_analysis_stats", {})
    return {
        "source": "virustotal",
        "ioc": ip,
        "ioc_type": "ip",
        "malicious_count": stats.get("malicious", 0),
        "suspicious_count": stats.get("suspicious", 0),
        "harmless_count": stats.get("harmless", 0),
        "undetected_count": stats.get("undetected", 0),
        "reputation": attributes.get("reputation", 0),
        "country": attributes.get("country", ""),
        "as_owner": attributes.get("as_owner", ""),
    }


def lookup_domain(api_key: str, domain: str) -> dict:
    """Look up domain in VirusTotal."""
    url = f"https://www.virustotal.com/api/v3/domains/{domain}"
    data = _http_get_json(url, {"x-apikey": api_key})
    if "__error__" in data:
        return {"error": data["__error__"], "source": "virustotal"}

    attributes = data.get("data", {}).get("attributes", {})
    stats = attributes.get("last_analysis_stats", {})
    return {
        "source": "virustotal",
        "ioc": domain,
        "ioc_type": "domain",
        "malicious_count": stats.get("malicious", 0),
        "suspicious_count": stats.get("suspicious", 0),
        "harmless_count": stats.get("harmless", 0),
        "undetected_count": stats.get("undetected", 0),
        "reputation": attributes.get("reputation", 0),
        "categories": attributes.get("categories", {}),
    }


def lookup_hash(api_key: str, file_hash: str) -> dict:
    """Look up file hash in VirusTotal."""
    url = f"https://www.virustotal.com/api/v3/files/{file_hash}"
    data = _http_get_json(url, {"x-apikey": api_key})
    if "__error__" in data:
        return {"error": data["__error__"], "source": "virustotal"}

    attributes = data.get("data", {}).get("attributes", {})
    stats = attributes.get("last_analysis_stats", {})
    return {
        "source": "virustotal",
        "ioc": file_hash,
        "ioc_type": "hash",
        "malicious_count": stats.get("malicious", 0),
        "suspicious_count": stats.get("suspicious", 0),
        "harmless_count": stats.get("harmless", 0),
        "undetected_count": stats.get("undetected", 0),
        "file_type": attributes.get("type_description", ""),
        "file_size": attributes.get("size", 0),
        "names": attributes.get("names", []),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_params(event: dict) -> tuple[str, str, bool]:
    """Return (ioc, ioc_type, is_bedrock) from either event shape.

    Bedrock shape is detected when ``messageVersion`` or ``actionGroup``
    is present in the event.
    """
    is_bedrock = bool(event.get("messageVersion") or event.get("actionGroup"))

    if is_bedrock:
        params_list = event.get("parameters", [])
        params = {p["name"]: p["value"] for p in params_list if "name" in p and "value" in p}
        ioc = params.get("ioc", "")
        ioc_type = params.get("ioc_type", "").lower()
    else:
        ioc = event.get("ioc", "")
        ioc_type = event.get("ioc_type", "").lower()

    # Normalise hash aliases
    if ioc_type in _HASH_ALIASES:
        ioc_type = "hash"

    return ioc, ioc_type, is_bedrock


def _do_lookup(ioc: str, ioc_type: str) -> dict:
    """Resolve API key, fall back to stub, then dispatch to the right lookup.

    Returns a result dict (never raises).
    """
    # Validate type before touching secrets
    if ioc_type not in ("ip", "domain", "hash"):
        return {"error": f"Unsupported IOC type: {ioc_type}", "source": "virustotal"}

    api_key = get_api_key()

    if not api_key:
        print(f"virustotal_stub_fallback reason=no_api_key ioc={ioc}")
        stub = dict(_STUBS[ioc_type])   # shallow copy
        stub["ioc"] = ioc
        return stub

    if ioc_type == "ip":
        return lookup_ip(api_key, ioc)
    elif ioc_type == "domain":
        return lookup_domain(api_key, ioc)
    else:
        return lookup_hash(api_key, ioc)


def _wrap_response(result: dict, event: dict, is_bedrock: bool, status: int = 200) -> dict:
    """Produce the correct response envelope for the calling shape.

    For Bedrock shape the HTTP status concept does not apply — the envelope is
    always well-formed so the agent can reason about the payload; errors are
    surfaced via the JSON body instead.
    """
    if is_bedrock:
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup", ""),
                "function": event.get("function", ""),
                "functionResponse": {
                    "responseBody": {
                        "TEXT": {"body": json.dumps(result)}
                    }
                },
            },
        }

    return {
        "statusCode": status,
        "body": json.dumps(result),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def lambda_handler(event: dict, context: Any) -> dict:
    """Lambda handler for VirusTotal lookup.

    Supports legacy direct-invoke and Bedrock Agent action-group shapes.
    """
    print(f"Received event: {json.dumps(event)}")

    ioc, ioc_type, is_bedrock = _extract_params(event)

    # Validate required parameters
    if not ioc or not ioc_type:
        err = {"error": "Missing required parameters: ioc, ioc_type"}
        return _wrap_response(err, event, is_bedrock, status=400)

    # Validate type before calling lookup (unsupported type → error, not 500)
    if ioc_type not in ("ip", "domain", "hash"):
        err = {"error": f"Unsupported IOC type: {ioc_type}"}
        return _wrap_response(err, event, is_bedrock, status=400)

    result = _do_lookup(ioc, ioc_type)

    # If the lookup itself returned an error key, reflect the right status code
    status = 500 if "error" in result and not result.get("stub") else 200
    return _wrap_response(result, event, is_bedrock, status=status)
