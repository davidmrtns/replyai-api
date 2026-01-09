import asyncio
import multiprocessing
from app.jobs.base import Job


class ProcessJobRunner:
    def run(self, job: Job) -> None:
        process = multiprocessing.Process(target=self._run_job, args=(job,))
        process.start()

    def _run_job(self, job: Job) -> None:
        asyncio.run(job.run())
