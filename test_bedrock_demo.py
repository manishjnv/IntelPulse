#!/usr/bin/env python3
"""Test script for Bedrock demo endpoint.

Run this to verify the demo endpoint is working correctly.
"""

import asyncio
import json
import sys

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Run: pip install httpx")
    sys.exit(1)


async def test_health():
    """Test the health endpoint."""
    print("🔍 Testing health endpoint...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8000/api/v1/demo/health")
            response.raise_for_status()
            
            data = response.json()
            print(f"✅ Health check passed")
            print(f"   Status: {data.get('status')}")
            print(f"   Bedrock: {data.get('bedrock', {}).get('healthy')}")
            print()
            return True
            
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            print()
            return False


async def test_analyze(ioc: str, ioc_type: str):
    """Test the analyze endpoint."""
    print(f"🔍 Testing analysis for {ioc_type}: {ioc}")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                "http://localhost:8000/api/v1/demo/analyze",
                json={
                    "ioc": ioc,
                    "ioc_type": ioc_type,
                }
            )
            response.raise_for_status()
            
            data = response.json()
            
            print(f"✅ Analysis completed")
            print(f"   IOC: {data.get('ioc')}")
            print(f"   Type: {data.get('ioc_type')}")
            print(f"   Risk Score: {data.get('risk_score')}")
            print(f"   Severity: {data.get('severity')}")
            print(f"   Confidence: {data.get('confidence')}%")
            print(f"   MITRE Techniques: {', '.join(data.get('mitre_techniques', []))}")
            print(f"   Recommended Actions: {len(data.get('recommended_actions', []))} actions")
            print()
            print("📝 Analysis Summary:")
            print(data.get('analysis', '')[:300] + "...")
            print()
            return True
            
        except httpx.HTTPStatusError as e:
            print(f"❌ Analysis failed with status {e.response.status_code}")
            print(f"   Error: {e.response.text}")
            print()
            return False
            
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            print()
            return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("IntelPulse Bedrock Demo - Test Suite")
    print("=" * 60)
    print()
    
    # Test health
    health_ok = await test_health()
    if not health_ok:
        print("⚠️  Health check failed. Is the API running?")
        print("   Start with: docker-compose -f docker-compose.demo.yml up -d")
        return
    
    # Test different IOC types
    test_cases = [
        ("192.168.1.100", "ip"),
        ("malicious-domain.com", "domain"),
        ("44d88612fea8a8f36de82e1278abb02f", "hash"),
    ]
    
    results = []
    for ioc, ioc_type in test_cases:
        success = await test_analyze(ioc, ioc_type)
        results.append(success)
        await asyncio.sleep(1)  # Rate limiting
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"✅ Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Demo is ready.")
    else:
        print("⚠️  Some tests failed. Check the logs above.")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
