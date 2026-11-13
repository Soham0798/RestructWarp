import os
import tempfile

# Tests use a throwaway database file and dummy secrets, never the real .env values.
# Environment variables win over .env, so blanking the keys here keeps tests from calling real services.
_tmp = tempfile.mkdtemp(prefix="sketch2ui-test-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp}/test.db"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["GROQ_API_KEY"] = "test"
os.environ["LLM_API_KEY"] = ""  # never call a real LLM from tests; they pass fake clients where needed
for _key in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "NVIDIA_API_KEY", "VERCEL_TOKEN",
             "LLM_VISION_MODEL", "DEV_ACCOUNT_EMAIL", "DEV_ACCOUNT_PASSWORD"):
    os.environ[_key] = ""
