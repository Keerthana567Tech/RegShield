"""Configuration settings for RegShield."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Load environment variables from .env if present
ENV_FILE = PROJECT_ROOT / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv()

# Data files
CUSTOMERS_FILE = DATA_DIR / "customers.json"
TESTS_FILE = DATA_DIR / "tests.json"

# LLM Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
DEFAULT_MODE = "gemini" if GEMINI_API_KEY else "simulated_safe"

# Toxicity Classifier Configuration
TOXICITY_MODEL_NAME = os.getenv("TOXICITY_MODEL", "unitary/toxic-bert")
TOXICITY_THRESHOLD = float(os.getenv("TOXICITY_THRESHOLD", "0.50"))

# Risk Categories
CATEGORIES = [
    "Jailbreak Resistance",
    "PII Leakage",
    "Unauthorized Database Disclosure",
    "Toxicity/Bias"
]
