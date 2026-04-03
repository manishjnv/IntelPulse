"""AbuseIPDB lookup Lambda function for Bedrock agent action group.

Queries AbuseIPDB API v2 for IP reputation data.
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
    """Retrieve AbuseIPDB API key from Secrets Manager."""
    try:
        response = secrets_client.get_secret_value(SecretId=SECRET_ARN)
        secret = json.loads(response["SecretString"])
        return secret.get("ABUSEIPDB_API_KEY", "")
    except Exception as e:
        print(f"Error retrieving secret: {e}")
        return ""


def check_ip(api_key: str, ip: str, max_age_days: int = 90) -> dict:
    """Check IP address in AbuseIPDB.
    
    Args:
        api_key: AbuseIPDB API key
        ip: IP address to check
        max_age_days: Maximum age of reports to include (default 90 days)
    """
    url = "https://api.abuseipdb.com/api/v2/check"
    headers = {
        "Key": api_key,
        "Accept": "application/json",
    }
    params = {
        "ipAddress": ip,
        "maxAgeInDays": max_age_days,
        "verbose": True,
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        ip_data = data.get("data", {})
        
        return {
            "source": "abuseipdb",
            "ioc": ip,
            "ioc_type": "ip",
            "abuse_confidence_score": ip_data.get("abuseConfidenceScore", 0),
            "total_reports": ip_data.get("totalReports", 0),
            "num_distinct_users": ip_data.get("numDistinctUsers", 0),
            "is_whitelisted": ip_data.get("isWhitelisted", False),
            "country_code": ip_data.get("countryCode", ""),
            "usage_type": ip_data.get("usageType", ""),
            "isp": ip_data.get("isp", ""),
            "domain": ip_data.get("domain", ""),
            "last_reported_at": ip_data.get("lastReportedAt", ""),
        }
    except Exception as e:
        return {"error": str(e), "source": "abuseipdb"}


def lambda_handler(event: dict, context: Any) -> dict:
    """Lambda handler for AbuseIPDB check.
    
    Expected event format:
    {
        "ioc": "8.8.8.8",
        "ioc_type": "ip",
        "max_age_days": 90  # optional
    }
    """
    print(f"Received event: {json.dumps(event)}")
    
    # Extract parameters
    ioc = event.get("ioc", "")
    ioc_type = event.get("ioc_type", "").lower()
    max_age_days = event.get("max_age_days", 90)
    
    if not ioc:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing required parameter: ioc"})
        }
    
    if ioc_type != "ip":
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "AbuseIPDB only supports IP addresses"})
        }
    
    # Get API key
    api_key = get_api_key()
    if not api_key:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "AbuseIPDB API key not configured"})
        }
    
    # Check IP
    result = check_ip(api_key, ioc, max_age_days)
    
    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }
