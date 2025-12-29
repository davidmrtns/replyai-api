from app.schemas.base import StrictBaseModel


class JobExecutedResponse(StrictBaseModel):
    status: str


def create_job_executed_response(job_name: str) -> JobExecutedResponse:
    return JobExecutedResponse(status=f"Job [{job_name}] executed successfully")
