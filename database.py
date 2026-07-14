from sqlmodel import SQLModel, create_engine
import os

import re
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("DATABASE_URL")  # or other relevant config var
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)



BASE_DIR = os.path.dirname(os.path.realpath(__file__))

conn_str = (
    uri
    or f"sqlite:///{os.path.join(BASE_DIR, 'database.db')}"
)
print(conn_str)

engine = create_engine(conn_str, echo=True)
