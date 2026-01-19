import signal
import time

from app.queue.queue import check_debounce, get_active_chats
from app.queue.tasks import process_reply
from app.utils.logger import logger


WORKER_POLL_INTERVAL_SECONDS = 2
shutdown_flag = False


def handle_shutdown(signum, frame):
    global shutdown_flag
    logger.info(f"Received signal {signum}, shutting down worker...")
    shutdown_flag = True


signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)


def debounce_worker():
    """
    Background worker that processes queued chat conversations using a debouncing mechanism.

    This worker ensures that multiple messages sent in a short time window will receive a single AI response.
    """
    logger.info("Debounce worker initialized")

    while not shutdown_flag:
        try:
            active_chats = get_active_chats()

            if not active_chats:
                time.sleep(WORKER_POLL_INTERVAL_SECONDS)
                continue

            for entry in active_chats:
                user_id, company_slug, token, payload_type = entry.split(":", 3)

                # If the debounce has expired, the user has stopped messaging for a while
                if not check_debounce(user_id, company_slug):
                    logger.info(f"Processing conversation for user {user_id}")

                    try:
                        logger.info("Processing reply task started")

                        process_reply(
                            slug=company_slug,
                            token=token,
                            user_id=user_id,
                            payload_type=payload_type,
                        )
                    except Exception as e:
                        logger.error(f"Error processing conversation {user_id}: {e}")
                        # Do not remove from set to try again later
                        continue

            time.sleep(WORKER_POLL_INTERVAL_SECONDS)

        except Exception as e:
            logger.error(f"Error in debounce worker loop: {e}")
            time.sleep(WORKER_POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    debounce_worker()
