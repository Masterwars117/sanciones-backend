import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import os

import oracledb

_lib_dir = os.environ.get("ORACLE_CLIENT_LIB_DIR")
if _lib_dir:
    oracledb.init_oracle_client(lib_dir=_lib_dir)
else:
    oracledb.init_oracle_client()

# Django 4.1 importa cx_Oracle; python-oracledb lo sustituye en thick mode.
class Binary(bytes):
    """Tipo para isinstance(); cx_Oracle lo exponía como clase, oracledb como función."""


oracledb.Binary = Binary
sys.modules["cx_Oracle"] = oracledb