"""VirusTotal lookup Lambda function for Bedrock agent action group.

Queries VirusTotal API v3 for IOC reputation data.
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
    """Retrieve VirusTotal API key from Secrets Manager."""
    try:
        response = secrets_client.get_secret_value(SecretId=SECRET_ARN)
        secret = json.loads(response["SecretString"])
        return secret.get("VIRUSTOTAL_API_KEY", "")
    except Exception as e:
        print(f"Error retrieving secret: {e}")
        return ""


def lookup_ip(api_key: str, ip: str) -> dict:
    """Look up IP address in VirusTotal."""
    url = f"https://www.virustotal.com/api/v3/ip_addresses/{ip}"
    headers = {"x-apikey": api_key}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
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
    except Exception as e:
        return {"error": str(e), "source": "virustotal"}


def lookup_domain(api_key: str, domain: str) -> dict:
    """Look up domain in VirusTotal."""
    url = f"https://www.virustotal.com/api/v3/domains/{domain}"
    headers = {"x-apikey": api_key}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
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
    except Exception as e:
        return {"error": str(e), "source": "virustotal"}


def lookup_hash(api_key: str, file_hash: str) -> dict:
    """Look up file hash in VirusTotal."""
    url = f"https://www.virustotal.com/api/v3/files/{file_hash}"
    headers = {"x-apikey": api_key}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
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
    except Exception as e:
        return {"error": str(e), "source": "virustotal"}


def lambda_handler(event: dict, context: Any) -> dict:
    """Lambda handler for VirusTotal lookup.
    
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
            "body": json.dumps({"error": "VirusTotal API key not configured"})
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
