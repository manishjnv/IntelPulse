"""AlienVault OTX lookup Lambda function for Bedrock agent action group.

Queries AlienVault OTX API for threat intelligence data.
"""

import json
import os
from typing import Any

import boto3
import requests

# Initialize clients
secrets_client = boto3.client("secretsmanager")
SECRET_ARN = os.environ.get("SECRET_ARN")


def get_api_key() -> str:
    """Retrieve OTX API key from Secrets Manager."""
    try:
        response = secrets_client.get_secret_value(SecretId=SECRET_ARN)
        secret = json.loads(response["SecretString"])
        return secret.get("OTX_API_KEY", "")
    except Exception as e:
        print(f"Error retrieving secret: {e}")
        return ""


def lookup_ip(api_key: str, ip: str) -> dict:
    """Look up IP address in OTX."""
    url = f"https://otx.alienvault.com/api/v1/indicators/IPv4/{ip}/general"
    headers = {"X-OTX-API-KEY": api_key}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            "source": "otx",
            "ioc": ip,
            "ioc_type": "ip",
            "pulse_count": data.get("pulse_info", {}).get("count", 0),
            "reputation": data.get("reputation", 0),
            "country": data.get("country_name", ""),
            "asn": data.get("asn", ""),
            "city": data.get("city", ""),
            "continent": data.get("continent_code", ""),
        }
    except Exception as e:
        return {"error": str(e), "source": "otx"}


def lookup_domain(api_key: str, domain: str) -> dict:
    """Look up domain in OTX."""
    url = f"https://otx.alienvault.com/api/v1/indicators/domain/{domain}/general"
    headers = {"X-OTX-API-KEY": api_key}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            "source": "otx",
            "ioc": domain,
            "ioc_type": "domain",
            "pulse_count": data.get("pulse_info", {}).get("count", 0),
            "alexa_rank": data.get("alexa", ""),
            "whois": data.get("whois", ""),
        }
    except Exception as e:
        return {"error": str(e), "source": "otx"}


def lookup_hash(api_key: str, file_hash: str) -> dict:
    """Look up file hash in OTX."""
    url = f"https://otx.alienvault.com/api/v1/indicators/file/{file_hash}/general"
    headers = {"X-OTX-API-KEY": api_key}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            "source": "otx",
            "ioc": file_hash,
            "ioc_type": "hash",
            "pulse_count": data.get("pulse_info", {}).get("count", 0),
            "file_type": data.get("type", ""),
            "file_class": data.get("file_class", ""),
        }
    except Exception as e:
        return {"error": str(e), "source": "otx"}


def lambda_handler(event: dict, context: Any) -> dict:
    """Lambda handler for OTX lookup.
    
    Expected event format:
    {
        "ioc": "8.8.8.8",
        "ioc_type": "ip"  # or "domain", "hash"
    }
    """
    print(f"Received event: {json.dumps(event)}")
    
    # Extract parameters
    ioc = event.get("ioc", "")
    ioc_type = event.get("ioc_type", "").lower()
    
    if not ioc or not ioc_type:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing required parameters: ioc, ioc_type"})
        }
    
    # Get API key
    api_key = get_api_key()
    if not api_key:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "OTX API key not configured"})
        }
    
    # Route to appropriate lookup function
    if ioc_type == "ip":
        result = lookup_ip(api_key, ioc)
    elif ioc_type == "domain":
        result = lookup_domain(api_key, ioc)
    elif ioc_type in ["hash", "md5", "sha1", "sha256"]:
        result = lookup_hash(api_key, ioc)
    else:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Unsupported IOC type: {ioc_type}"})
        }
    
    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }
