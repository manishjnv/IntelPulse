import asyncio, httpx

async def main():
    from app.core.database import async_session_factory
    from sqlalchemy import select
    from app.models.models import AISetting
    async with async_session_factory() as db:
        result = await db.execute(select(AISetting).where(AISetting.key == "default"))
        row = result.scalar_one_or_none()
        if not row:
            print("ERROR: No row")
            return
        key = row.primary_api_key or ""
        url = row.primary_api_url or ""
        model = row.primary_model or ""
        print(f"key_len={len(key)} key_start={key[:8]} url={url} model={model}")
        test_url = url.rstrip("/")
        if not test_url.endswith("/chat/completions"):
            test_url += "/chat/completions"
        print(f"test_url={test_url}")
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                test_url,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": "Test"}], "max_tokens": 5, "temperature": 0},
            )
            print(f"status={resp.status_code}")
            print(f"body={resp.text[:300]}")

        # Also test fallback
        fb_list = row.fallback_providers or []
        for i, fb in enumerate(fb_list):
            fb_key = fb.get("key", "")
            fb_url = fb.get("url", "")
            fb_model = fb.get("model", "")
            print(f"\nFallback {i}: key_len={len(fb_key)} key_start={fb_key[:8]} url={fb_url} model={fb_model}")
            fb_test_url = fb_url.rstrip("/")
            if not fb_test_url.endswith("/chat/completions"):
                fb_test_url += "/chat/completions"
            fb_use_model = fb_model.split(",")[0].strip() if "," in fb_model else fb_model
            print(f"fb_test_url={fb_test_url} using_model={fb_use_model}")
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    fb_test_url,
                    headers={"Authorization": f"Bearer {fb_key}", "Content-Type": "application/json"},
                    json={"model": fb_use_model, "messages": [{"role": "user", "content": "Test"}], "max_tokens": 5, "temperature": 0},
                )
                print(f"status={resp.status_code}")
                print(f"body={resp.text[:300]}")

asyncio.run(main())
