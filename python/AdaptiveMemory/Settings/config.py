import os


def _read_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


api_key = _read_env("AMA_LLM_API_KEY")
base_url = _read_env("AMA_LLM_BASE_URL")
embedding_url = _read_env("AMA_EMBEDDING_URL")
