import httpx, uuid, json, redis
from jose import jwt
from datetime import datetime, timedelta, timezone

SECRET_KEY = "ca11ded3d44a5499adec236209a4d0ff62cd0a935c7d019b239d47d983917962"
r = redis.Redis(host="redis", port=6379, password="IntelPulse_R3dis_2026", db=0)
session_id = str(uuid.uuid4())
token_data = {
    "sub": "admin-user-id",
    "email": "manishjnvk@gmail.com",
    "role": "admin",
    "name": "Admin",
    "sid": session_id,
    "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    "iat": datetime.now(timezone.utc),
    "jti": str(uuid.uuid4()),
}
token = jwt.encode(token_data, SECRET_KEY, algorithm="HS256")
r.setex(f"session:{session_id}", 3600, "admin-user-id")
client = httpx.Client(base_url="http://localhost:8000/api/v1", timeout=30)
# Test with cookies header approach
resp = client.post("/cases", json={"title": "debug test"}, cookies={"iw_session": token})
print(f"Status: {resp.status_code}")
print(f"Headers: {dict(resp.headers)}")
print(f"Body: {resp.text[:500]}")
# Test GET
resp2 = client.get("/cases/assignees", cookies={"iw_session": token})
print(f"\nAssignees status: {resp2.status_code}")
