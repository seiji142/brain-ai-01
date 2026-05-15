from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    app_env: str = "dev"
    embedding_provider: str = "hash"
    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    chroma_persist_dir: str = ".ai_memory/chroma"
    log_dir: str = "logs"
    memory_root: str = "memory"
    ai_dir: str = ".ai"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()

ROOT = Path.cwd()
AI_DIR = ROOT / settings.ai_dir
MEMORY_ROOT = ROOT / settings.memory_root
CHROMA_DIR = ROOT / settings.chroma_persist_dir
LOG_DIR = ROOT / settings.log_dir

EPISODIC_DIR = MEMORY_ROOT / "episodic"
SEMANTIC_DIR = MEMORY_ROOT / "semantic"
WORKING_DIR = MEMORY_ROOT / "working"
SUMMARIES_DIR = MEMORY_ROOT / "summaries"
REFLECTIONS_DIR = MEMORY_ROOT / "reflections"
INDEXES_DIR = MEMORY_ROOT / "indexes"
MEDIA_ROOT = ROOT / "media"
IMAGES_DIR = MEDIA_ROOT / "images"
PDFS_DIR = MEDIA_ROOT / "pdfs"
TEXT_DIR = MEDIA_ROOT / "text"
PAGES_DIR = MEDIA_ROOT / "pages"

TRACES_DIR = LOG_DIR / "traces"
TOOLCALLS_DIR = LOG_DIR / "tool_calls"
EVALS_DIR = LOG_DIR / "evaluations"
FAILS_DIR = LOG_DIR / "failures"

for p in [AI_DIR, MEMORY_ROOT, CHROMA_DIR, LOG_DIR,
          EPISODIC_DIR, SEMANTIC_DIR, WORKING_DIR, SUMMARIES_DIR, REFLECTIONS_DIR, INDEXES_DIR,
          MEDIA_ROOT, IMAGES_DIR, PDFS_DIR, TEXT_DIR, PAGES_DIR,
          TRACES_DIR, TOOLCALLS_DIR, EVALS_DIR, FAILS_DIR]:
    p.mkdir(parents=True, exist_ok=True)
