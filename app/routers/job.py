from fastapi import APIRouter
from fastapi.params import Depends

from app.jobs.registry import JOBS
from app.jobs.runners.process_runner import ProcessJobRunner
from .routers_helpers import validate_secret_key

from app.schemas.job_schema import JobExecutedResponse, create_job_executed_response


router = APIRouter(dependencies=[Depends(validate_secret_key)])


@router.post("/{job_name}", response_model=JobExecutedResponse)
def execute_job(job_name: str):
    job_class = JOBS[job_name]
    job = job_class()

    runner = ProcessJobRunner()
    runner.run(job)

    return create_job_executed_response(job_name=job_name)
