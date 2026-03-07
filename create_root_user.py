import os
from app.db.database import get_db_session_with_context
from app.db.models import User
from app.utils.logger import logger
from app.utils.password_utils import hash_password


def create_root_user():
    with get_db_session_with_context() as db:
        try:
            ROOT_PASSWORD = os.getenv("ROOT_PASSWORD", "root")
            ROOT_EMAIL = os.getenv("ROOT_EMAIL", "root@example.com")

            # Verifies if a root user already exists to avoid duplicates
            existing_root = db.query(User).filter(User.email == ROOT_EMAIL).first()
            if existing_root:
                logger.info("Root user already exists. Skipping creation.")
                return

            if ROOT_PASSWORD == "root" or ROOT_EMAIL == "root@example.com":
                logger.warning(
                    "Using default root password 'root' and email. This should NOT be used in production."
                )

            root_user = User(
                name="Root",
                email=ROOT_EMAIL,
                password=hash_password(ROOT_PASSWORD),
                is_admin=True,
            )
            db.add(root_user)
            db.commit()

            logger.info("Root user created successfully.")
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating root user: {e}")


if __name__ == "__main__":
    create_root_user()
