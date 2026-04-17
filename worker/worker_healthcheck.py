#!/usr/bin/env python3
"""Docker healthcheck for the RQ worker container.

Exits 0 (healthy) if the worker process has written a fresh RQ heartbeat
to Redis within the last `MAX_HEARTBEAT_AGE_SEC` seconds. Exits 1 otherwise.

RQ workers refresh their heartbeat on every poll tick (~1–5s during idle,
more frequently when jobs are running), so a stale heartbeat is a reliable
signal that the worker loop is dead or deadlocked — something that the
container's own `restart: unless-stopped` policy cannot detect, because the
Python process itself may still be technically alive.
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from redis import Redis
from rq import Worker
from app.core.config import get_settings


# A healthy worker refreshes its heartbeat every few seconds. If the most
# recent beat is older than this, assume the worker is hung / crashed.
MAX_HEARTBEAT_AGE_SEC = 90


try:
    settings = get_settings()
    r = Redis.from_url(settings.redis_url)

    # Liveness gate: Redis must be reachable at all.
    r.ping()

    workers = Worker.all(connection=r)
    if not workers:
        print("UNHEALTHY: no RQ workers registered in Redis")
        sys.exit(1)

    now = time.time()
    fresh = []
    for w in workers:
        beat = w.last_heartbeat
        if beat is None:
            continue
        # `last_heartbeat` is a naive UTC datetime in RQ — convert to epoch
        age = now - beat.timestamp()
        if age <= MAX_HEARTBEAT_AGE_SEC:
            fresh.append((w.name, age))

    if not fresh:
        stale = [
            (w.name, now - w.last_heartbeat.timestamp() if w.last_heartbeat else None)
            for w in workers
        ]
        print(f"UNHEALTHY: no fresh worker heartbeat (workers={stale})")
        sys.exit(1)

    print(f"HEALTHY: {len(fresh)}/{len(workers)} workers heartbeating "
          f"(youngest beat {min(a for _, a in fresh):.1f}s old)")
    sys.exit(0)

except Exception as e:
    print(f"UNHEALTHY: {e}")
    sys.exit(1)
