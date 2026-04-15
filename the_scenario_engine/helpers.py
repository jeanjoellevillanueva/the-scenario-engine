import os
from pathlib import Path


class MissingEnvironmentVariableError(RuntimeError):
    """
    Raised when a required environment variable is missing.
    """


def _load_dotenv(dotenv_path: Path) -> None:
    """
    Load key/value pairs from a .env file into process environment.
    """
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue

        if '=' not in line:
            continue

        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip()

        if not key:
            continue
        os.environ.setdefault(key, value)


_UNSET = object()


def get_env(name: str, *, cast=str, required: bool = True, default=_UNSET) -> object:
    """
    Get an environment variable from `.env` or the process.
    """
    base_dir = Path(__file__).resolve().parent.parent
    _load_dotenv(base_dir / '.env')

    raw_value = os.environ.get(name)

    if raw_value is None or raw_value == '':
        if default is not _UNSET:
            return default
        if required:
            raise MissingEnvironmentVariableError(
                f'Missing required environment variable: {name}'
            )
        return None

    if cast is bool:
        normalized = raw_value.strip().lower()
        if normalized in {'true'}:
            return True
        if normalized in {'false'}:
            return False
        raise ValueError(f'Invalid boolean for {name}: {raw_value!r}')

    return cast(raw_value)
