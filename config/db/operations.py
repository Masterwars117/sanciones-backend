"""
Operaciones Oracle 10g: sin FETCH FIRST / OFFSET (requieren 12c+).
"""
import datetime

from django.db.backends.oracle.operations import DatabaseOperations as OracleDatabaseOperations


class DatabaseOperations(OracleDatabaseOperations):
    compiler_module = "config.db.compiler"

    def limit_offset_sql(self, low_mark, high_mark):
        # El límite lo aplica config.db.compiler con ROWNUM (Oracle 10g).
        return ""

    def cache_key_culling_sql(self):
        cache_key = self.quote_name("cache_key")
        return (
            f"SELECT {cache_key} FROM ("
            f"SELECT {cache_key} FROM %s ORDER BY {cache_key}"
            f") WHERE ROWNUM <= %%s + 1 AND ROWNUM > %%s"
        )

    def convert_datefield_value(self, value, expression, connection):
        # oracledb expone Timestamp como función, no como tipo (rompe isinstance del backend).
        if isinstance(value, datetime.datetime):
            return value.date()
        if isinstance(value, datetime.date):
            return value
        return value
