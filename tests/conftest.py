import os
import sys
from dotenv import load_dotenv


def _ensure_src_on_path() -> None:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    src_path = os.path.join(repo_root, "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


_ensure_src_on_path()

# Load .env so tests can access keys like TAVILY_API_KEY locally
load_dotenv()

