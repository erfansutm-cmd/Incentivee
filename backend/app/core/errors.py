"""Shared database error mapping.

Turns SQLAlchemy / driver exceptions into (HTTP status, detail) pairs so
every endpoint reports proper errors for the same failure:

- table does not exist            -> 404
- no access (user/table denied)   -> 403
- database unreachable            -> 503
- constraint violation            -> 409
- anything else                   -> 500
"""

from sqlalchemy.exc import SQLAlchemyError

# MySQL error codes (see https://dev.mysql.com/doc/mysql-errors/8.0/en/)
_MYSQL_TABLE_DOES_NOT_EXIST = 1146
_MYSQL_TABLE_ACCESS_DENIED = 1142
_MYSQL_DB_ACCESS_DENIED = 1044
_MYSQL_USER_ACCESS_DENIED = 1045


def db_failure_detail(exc: SQLAlchemyError, table: str, database: str) -> tuple[int, str]:
    """Map a SQLAlchemy error to (status_code, detail message)."""
    origin = getattr(exc, "orig", None) or exc
    args = getattr(origin, "args", ()) or ()
    code = args[0] if args and isinstance(args[0], int) else None
    message = str(origin)
    lowered = message.lower()

    # Missing table -> 404
    if code == _MYSQL_TABLE_DOES_NOT_EXIST or "no such table" in lowered or (
        table.lower() in lowered and "doesn't exist" in lowered
    ):
        return 404, f'Table "{table}" does not exist in database "{database}".'

    # No access -> 403
    if code in (_MYSQL_TABLE_ACCESS_DENIED, _MYSQL_DB_ACCESS_DENIED, _MYSQL_USER_ACCESS_DENIED) or (
        "access denied" in lowered
    ):
        return 403, f'No access to table "{table}" in database "{database}": {message}'

    # Unreachable / operational -> 503
    return 503, f"Database unreachable or operation failed: {message}"
