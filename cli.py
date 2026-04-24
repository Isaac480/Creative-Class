# TODO: export database to csv? can get from db browser already...

import ast
import os
import sqlite3
import subprocess
from pathlib import Path

import fire
import pandas as pd
import psycopg2
import uvicorn
from sqlmodel import Session, SQLModel

import config
from models import Data, Participant

settings = config.Settings()
TABLE_NAMES = ["participant", "data"]
DATA_DIR = Path("data/temp/")
APP_NAME = "lookatfaces"


def create_tables():
    from database import engine

    SQLModel.metadata.create_all(engine)


def drop_tables():
    from database import engine

    SQLModel.metadata.drop_all(engine)


def reset_db():
    drop_tables()
    create_tables()

    print("db successfully reset.")


# TODO: fix this whole running part
def run():
    uvicorn.run("main:app", reload=True)


def install_packages():
    # build project for deployment
    os.system("npm i --prefix frontend")


def build():
    # build project for deployment
    os.system("npm run --prefix frontend build")


def debug():
    # reset_db()
    # build project for debug
    os.system("npm run --prefix frontend dev")
    run()


def export(remote=True):
    if remote:
        conn = psycopg2.connect(settings.database_url)
    else:
        conn = sqlite3.connect("database.db")
    for table_name in TABLE_NAMES:
        df = pd.read_sql(f"SELECT * from {table_name}", conn)
        df.to_csv(DATA_DIR / f"{table_name}.csv", index=False)


def extract_jspsych_data(data_file=DATA_DIR / "data.csv", data_col="json_data"):
    """Extract the data stored as dictionaries
    (as AST strings).
    Args:
        data (pd.DataFrame): The experiment data for many participants. Includes survey responses.
        data_col (str, optional): _descriptin_. Defaults to "data".
    Returns:
        pd.DataFrame: The jsPsych data.
    """

    data = pd.read_csv(data_file)

    df = pd.concat(
        [pd.DataFrame(ast.literal_eval(x)) for x in data[data_col]],
        ignore_index=True,
    )
    df.to_csv(DATA_DIR / f"jspsych_data.csv", index=False)


if __name__ == "__main__":
    fire.Fire()
