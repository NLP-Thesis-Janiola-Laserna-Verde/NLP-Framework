from pathlib import Path

import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

CSV_DIR = Path(__file__).resolve().parents[1] / "csv"

load_dotenv()
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

df = pd.read_csv(CSV_DIR / "topics.csv")
supabase.table("topics").upsert(df.to_dict("records")).execute()

print(supabase.table("topics").select("*").limit(3).execute().data)