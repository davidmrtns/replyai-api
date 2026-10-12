from redis import Redis
from redis.exceptions import LockError
from redis.lock import Lock

from app.queue.queue import redis_conn

LOCK_TIMEOUT_SECONDS = 360


def acquire_conversation_lock(conversation_key: str):
    lock: Lock = redis_conn.lock(
        name=f"lock:{conversation_key}",
        timeout=LOCK_TIMEOUT_SECONDS,
        blocking_timeout=0,
        thread_local=False,
    )

    if lock.acquire():
        return lock

    return None


def release_conversation_lock(lock: Lock | None) -> None:
    if lock is None:
        return

    try:
        lock.release()
    except LockError:
        # The lease may have expired or the lock may already be gone.
        pass
