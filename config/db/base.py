"""
Backend Oracle para Django 4.1 + Oracle 10g (legacy).

Django 4.1.12+ exige Oracle 19 en el backend oficial; este wrapper
baja el mínimo a 10.2 para el esquema INHABIL existente.

Oracle 10g no admite FETCH FIRST / OFFSET; la paginación usa ROWNUM
(véase config.db.compiler y config.db.operations).
"""
from django.db.backends.oracle.base import DatabaseWrapper as OracleDatabaseWrapper
from django.db.backends.oracle.features import DatabaseFeatures as OracleDatabaseFeatures

from .operations import DatabaseOperations


class DatabaseFeatures(OracleDatabaseFeatures):
    minimum_database_version = (10, 2)


class DatabaseWrapper(OracleDatabaseWrapper):
    features_class = DatabaseFeatures
    ops_class = DatabaseOperations
