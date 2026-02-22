import os
from dotenv import load_dotenv, find_dotenv

# Explicitly search for the .env file in parent directories
load_dotenv(find_dotenv(usecwd=True))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL:
    raise EnvironmentError("SUPABASE_URL is missing from environment variables.")

if not SUPABASE_SERVICE_ROLE_KEY:
    raise EnvironmentError("SUPABASE_SERVICE_ROLE_KEY is missing from environment variables.")
