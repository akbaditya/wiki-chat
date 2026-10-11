import os

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    app_env: str = "dev"
    frontend_origin: str = "http://localhost:5173"
    cookie_secure: bool = False
    trust_proxy: bool = False

    jwt_secret: str
    hmac_secret: str
    jwt_expire_minutes: int = 60 * 24 * 7

    admin_email: str
    admin_password_hash: str

    max_users: int = 10
    max_convos_per_user: int = 10

    login_max_failures: int = 5
    login_max_failures_ip: int = 15
    lockout_hours: str = "3,12,24"

    data_dir: Path = BASE_DIR / "data"
    
    groq_api_key: str = ""
    google_api_key: str = ""
    openrouter_api_key: str = ""

    groq_main_model: str = "llama-3.3-70b-versatile"
    groq_fast_model: str = "llama-3.1-8b-instant"
    gemini_main_model: str = "gemini-3-flash-preview"
    gemini_fast_model: str = ""
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"

    llm_first_token_timeout: float = 15.0
    llm_chunk_timeout: float = 20.0
    retrieve_timeout: float = 45.0

    guest_message_limit: int = 10
    guest_session_ttl_seconds: int = 3600
    history_window: int = 6
    
    summary_trigger_messages: int = 20   
    summary_batch: int = 10              
    context_min_similarity: float = 0.5
    context_top_n: int = 3
    max_memories_per_user: int = 30
    max_memories_in_prompt: int = 15
    memory_task_timeout: float = 20.0
    
    chat_bucket_capacity: float = 5            
    chat_bucket_refill_per_sec: float = 0.1667 
    chat_ip_bucket_capacity: float = 8
    user_daily_token_budget: int = 40_000
    global_daily_token_budget: int = 200_000
    request_timeout: float = 90.0
    
    analyzer_timeout: float = 15.0
    transform_timeout: float = 15.0
    grade_weak_score: float = 0.15    
    max_retrieval_retries: int = 1
    max_search_queries: int = 4
    analysis_history_messages: int = 4
    
    wiki_user_agent: str = "WikiRAGChatbot/1.0 (portfolio project; contact: you@example.com)"
    wiki_cache_ttl_days: int = 7
    embed_model: str = "BAAI/bge-small-en-v1.5"
    rerank_model: str = "ms-marco-MiniLM-L-12-v2"
    rerank_min_score: float = 0.02     
    image_min_similarity: float = 0.40  
    image_relative_window: float = 0.10 
    image_lead_bonus: float = 0.05      
    image_max: int = 5
    
    cache_max_mb: int = 200
    max_indexed_pages: int = 300        
    index_unused_days: int = 30         
    log_retention_days: int = 90        
    maintenance_interval_hours: int = 6
    
    frontend_dist: Path = BASE_DIR.parent / "frontend" / "dist"
    models_path: Path | None = None   
    
    @property
    def db_path(self) -> Path:
        return self.data_dir / "app.db"
    
    @property
    def models_dir(self) -> Path:
        return self.models_path or (self.data_dir / "models")

    @property
    def wiki_cache_dir(self) -> Path:
        return self.data_dir / "wiki_cache"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"
    
    @property
    def checkpoint_path(self) -> Path:
        return self.data_dir / "checkpoints.db"

    @property
    def turn_store_dir(self) -> Path:
        return self.data_dir / "chroma_memory"

    @property
    def lockout_hours_list(self) -> list[int]:
        return [int(h) for h in self.lockout_hours.split(",") if h.strip()]

    @property
    def is_prod(self) -> bool:
        return self.app_env == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()