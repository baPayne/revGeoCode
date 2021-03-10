import os

import redis
from rq import Worker, Queue, Connection

listen = ['high', 'default', 'low']

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')

conn = redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work()

# from redis import Redis
# from rq import Queue

# connection = Redis()
# queue = Queue(connection=connection)
# registry = queue.failed_job_registry

# # This is how to get jobs from FailedJobRegistry
# for job_id in registry.get_job_ids():
#     registry.requeue(job_id)  # Puts job back in its original queue

# assert len(registry) == 0  # Registry will be empty when job is requeued        