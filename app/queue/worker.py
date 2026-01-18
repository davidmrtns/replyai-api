import time

from app.queue.queue import check_debounce, get_active_chats
from app.queue.tasks import process_reply
from app.utils.logger import logger


def debounce_worker():
    logger.info("Debounce worker initialized")

    while True:
        try:
            active_chats = get_active_chats()

            if not active_chats:
                time.sleep(2)
                continue

            for entry in active_chats:
                user_id, company_slug, token = entry.split(":", 2)

                # If the debounce has expired, the user has stopped messaging for a while
                if not check_debounce(user_id, company_slug):
                    logger.info(f"Processing conversation for user {user_id}")

                    try:
                        logger.info("Processing reply task started")

                        process_reply(
                            slug=company_slug,
                            token=token,
                            user_id=user_id,
                        )
                    except Exception as e:
                        logger.error(f"Error processing conversation {user_id}: {e}")
                        # Do not remove from set to try again later
                        continue

            time.sleep(2)

        except Exception as e:
            logger.error(f"Error in debounce worker loop: {e}")
            time.sleep(2)


if __name__ == "__main__":
    debounce_worker()
