from typing import Type, TypeVar, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.exceptions.exceptions import ResourceNotFoundException


T = TypeVar("T")


async def get_resource_from_db(
    model: Type[T],
    resource_id: int,
    db: Session,
    company_id: Optional[int] = None,
) -> T:
    """
    Retrieves a resource from the database by its ID and optional company ID.

    Args:
        model (Type[T]): The SQLAlchemy model class representing the resource.
        resource_id (int): The ID of the resource to retrieve.
        db (Session): The SQLAlchemy database session.
        company_id (Optional[int]): The ID of the company to which the resource belongs. Defaults to None.

    Returns:
        T: The retrieved resource instance.

    Raises:
        ResourceNotFoundException: If the resource is not found in the database.
    """
    query = db.query(model).filter_by(id=resource_id)
    if company_id:
        query = query.filter_by(company_id=company_id)

    resource = query.first()

    if not resource:
        raise ResourceNotFoundException(
            resource_name=model.__name__,
            resource_id=resource_id,
            detail=f"{model.__name__} not found for the specified company and ID.",
            user_friendly_detail=f"{model.__name__} not found, or you do not have access to it.",
            http_status_code=404,
        )
    return resource


def apply_model_update(model, data: dict | BaseModel) -> None:
    """
    Updates a SQLAlchemy model instance with data from a dictionary or Pydantic model.

    Args:
        model: The SQLAlchemy model instance to be updated.
        data (dict | BaseModel): A dictionary or Pydantic model containing the update data.

    Returns:
        None: The function updates the model in place.

    After using the function, call `session.commit()` to persist changes to the database.
    """
    if isinstance(data, BaseModel):
        data = data.model_dump(exclude_unset=True)

    for field, value in data.items():
        setattr(model, field, value)
