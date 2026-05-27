"""
Compilador SQL con paginación ROWNUM para Oracle 10g.

operations.compiler_module apunta aquí; además del SELECT con ROWNUM,
hay que reexportar los compiladores de escritura que usa Django en save().
"""
from django.db.models.sql.compiler import (
    SQLAggregateCompiler,
    SQLCompiler as BaseSQLCompiler,
    SQLDeleteCompiler,
    SQLInsertCompiler,
    SQLUpdateCompiler,
)


class SQLCompiler(BaseSQLCompiler):
    def as_sql(self, with_limits=True, with_col_aliases=False):
        sql, params = super().as_sql(
            with_limits=False, with_col_aliases=with_col_aliases
        )
        if not with_limits:
            return sql, params
        if self.query.high_mark is None and not self.query.low_mark:
            return sql, params

        fetch, offset = self.connection.ops._get_limit_offset_params(
            self.query.low_mark, self.query.high_mark
        )
        if fetch is None and not offset:
            return sql, params

        if offset and fetch is not None:
            high = offset + fetch
            sql = (
                "SELECT * FROM ("
                "SELECT subq.*, ROWNUM AS rn FROM (%s) subq "
                "WHERE ROWNUM <= %d"
                ") WHERE rn > %d"
            ) % (sql, high, offset)
        elif fetch is not None:
            sql = "SELECT * FROM (%s) WHERE ROWNUM <= %d" % (sql, fetch)
        else:
            sql = (
                "SELECT * FROM ("
                "SELECT subq.*, ROWNUM AS rn FROM (%s) subq"
                ") WHERE rn > %d"
            ) % (sql, offset)
        return sql, params
