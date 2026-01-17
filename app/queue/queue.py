from redis import Redis
from rq import Queue


redis_conn = Redis(host="localhost", port=6379, db=0)
message_queue = Queue("messages", connection=redis_conn)
