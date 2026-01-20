from app.db.database import get_db_session_with_context
from app.db.models import User
from app.utils.logger import logger
from app.utils.password_utils import hash_password


def create_root_user():
    with get_db_session_with_context() as db:
        try:
            root_user = User(
                name="Root",
                email="root@example.com",
                password=hash_password("root"),
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
