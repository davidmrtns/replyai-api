import logging


logger = logging.getLogger("replyai-api")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def log_job_error(job_name: str, company_slug: str, e: Exception):
    logger.error(
        f"Error processing job {job_name} for company {company_slug}: {e}",
        exc_info=True,
    )
