from pydantic import BaseModel


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
