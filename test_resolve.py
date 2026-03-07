import asyncio, httpx, json

async def main():
    # Test the debug-test endpoint with a masked key (simulating post-save behavior)
    async with httpx.AsyncClient(timeout=30) as client:
        # Test primary with masked key
        print("=== PRIMARY (masked key) ===")
        resp = await client.post(
            "http://localhost:8000/api/v1/ai-settings/debug-test",
            json={
                "url": "https://api.groq.com/openai/v1/chat/completions",
                "key": "gsk_****r3eP",
                "model": "llama-3.3-70b-versatile",
                "provider_type": "primary",
            },
        )
        print(json.dumps(resp.json(), indent=2))

        # Test fallback with masked key
        print("\n=== FALLBACK 0 (masked key) ===")
        resp = await client.post(
            "http://localhost:8000/api/v1/ai-settings/debug-test",
            json={
                "url": "https://api.cerebras.ai/v1/",
                "key": "csk-****6whv",
                "model": "llama3.1-8b",
                "provider_type": "0",
            },
        )
        print(json.dumps(resp.json(), indent=2))

        # Test primary WITHOUT provider_type (what old JS would send)
        print("\n=== PRIMARY (no provider_type) ===")
        resp = await client.post(
            "http://localhost:8000/api/v1/ai-settings/debug-test",
            json={
                "url": "https://api.groq.com/openai/v1/chat/completions",
                "key": "gsk_****r3eP",
                "model": "llama-3.3-70b-versatile",
            },
        )
        print(json.dumps(resp.json(), indent=2))

asyncio.run(main())
