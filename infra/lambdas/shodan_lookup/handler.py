"""Shodan lookup Lambda function for Bedrock agent action group.

Queries Shodan API for host information and vulnerabilities.
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
    """Retrieve Shodan API key from Secrets Manager."""
    try:
        response = secrets_client.get_secret_value(SecretId=SECRET_ARN)
        secret = json.loads(response["SecretString"])
        return secret.get("SHODAN_API_KEY", "")
    except Exception as e:
        print(f"Error retrieving secret: {e}")
        return ""


def lookup_ip(api_key: str, ip: str) -> dict:
    """Look up IP address in Shodan.
    
    Args:
        api_key: Shodan API key
        ip: IP address to look up
    """
    url = f"https://api.shodan.io/shodan/host/{ip}"
    params = {"key": api_key}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Extract key information
        ports = data.get("ports", [])
        vulns = data.get("vulns", [])
        tags = data.get("tags", [])
        
        return {
            "source": "shodan",
            "ioc": ip,
            "ioc_type": "ip",
            "open_ports": ports,
            "port_count": len(ports),
            "vulnerabilities": vulns,
            "vuln_count": len(vulns),
            "tags": tags,
            "hostnames": data.get("hostnames", []),
            "domains": data.get("domains", []),
            "country": data.get("country_name", ""),
            "city": data.get("city", ""),
            "isp": data.get("isp", ""),
            "org": data.get("org", ""),
            "asn": data.get("asn", ""),
            "last_update": data.get("last_update", ""),
        }
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return {
                "source": "shodan",
                "ioc": ip,
                "ioc_type": "ip",
                "error": "No information available",
                "open_ports": [],
                "vulnerabilities": [],
            }
        return {"error": str(e), "source": "shodan"}
    except Exception as e:
        return {"error": str(e), "source": "shodan"}


def lambda_handler(event: dict, context: Any) -> dict:
    """Lambda handler for Shodan lookup.
    
    Expected event format:
    {
        "ioc": "8.8.8.8",
        "ioc_type": "ip"
    }
    """
    print(f"Received event: {json.dumps(event)}")
    
    # Extract parameters
    ioc = event.get("ioc", "")
    ioc_type = event.get("ioc_type", "").lower()
    
    if not ioc:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing required parameter: ioc"})
        }
    
    if ioc_type != "ip":
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Shodan only supports IP addresses"})
        }
    
    # Get API key
    api_key = get_api_key()
    if not api_key:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Shodan API key not configured"})
        }
    
    # Look up IP
    result = lookup_ip(api_key, ioc)
    
    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }
