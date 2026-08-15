import contextvars

current_user_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("current_user_id", default=None)


def require_user_id() -> str:
    user_id = current_user_id.get()
    if not user_id:
        raise RuntimeError("This tool requires an authenticated user")
    return user_id
