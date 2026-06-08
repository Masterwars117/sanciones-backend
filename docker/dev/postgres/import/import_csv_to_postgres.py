from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CSV_DIR = Path(__file__).resolve().parent / "csv"


@dataclass(frozen=True)
class TableSpec:
    name: str
    columns: tuple[str, ...]
    required_columns: tuple[str, ...]


TABLES: tuple[TableSpec, ...] = (
    TableSpec(
        name="CAT_GENERO",
        columns=("GEN_CVE", "GEN_DESCRIPCION"),
        required_columns=("GEN_CVE",),
    ),
    TableSpec(
        name="TIPOSANCION",
        columns=("CLAVE", "DESCRIPCION"),
        required_columns=("CLAVE",),
    ),
    TableSpec(
        name="CAT_MONEDAS",
        columns=("MON_CVE", "MON_DESCRIPCION"),
        required_columns=("MON_CVE",),
    ),
    TableSpec(
        name="CAT_TFALTA",
        columns=("FAL_CLAVE", "FAL_DESCRIPCION"),
        required_columns=("FAL_CLAVE",),
    ),
    TableSpec(
        name="CAT_TIPODOCTO",
        columns=("DESCRIPDOCTO",),
        required_columns=("DESCRIPDOCTO",),
    ),
    TableSpec(
        name="DEPENDENCIAS",
        columns=(
            "CLAVE",
            "DESCRIPCION",
            "TIPO",
            "DEP_SIGLAS",
            "DEP_HABILITADO",
            "DEP_IDANTERIOR",
            "DEP_CVEFINANZAS",
            "MOSTRARSESEA",
        ),
        required_columns=("CLAVE",),
    ),
    TableSpec(
        name="INHABILIFEDERAL",
        columns=(
            "DEPENDENCIA",
            "RFC",
            "HOMOCLAVE",
            "APATERNO",
            "AMATERNO",
            "NOMBRES",
            "AUTSANC",
            "CARGO",
            "PERIODO",
            "FECHARES",
            "FECHANOT",
            "DEINHABIL",
            "AINHABIL",
            "FECHAINF",
        ),
        required_columns=("RFC",),
    ),
    TableSpec(
        name="INHABILITADOS",
        columns=(
            "AÑO",
            "SANCIONID",
            "OFICIO",
            "F_OFICIO",
            "EXPEDIENTE",
            "F_RESOLUCION",
            "APATERNO",
            "AMATERNO",
            "NOMBRES",
            "DEPENDENCIA",
            "CARGO",
            "ENTIDAD_LABORA",
            "TIPOSANCION",
            "TIPOSANCION2",
            "PERIODO",
            "DEINHABIL",
            "AINHABIL",
            "MOTIVO",
            "STATUSSANC1",
            "STATUSSANC2",
            "RFC",
            "FEJEC1",
            "FEJEC2",
            "MONTO1",
            "MONTO2",
            "CURP",
            "FECHAREG",
            "GENERO",
            "IDSESEA",
            "CVE_ENTIDAD_LABORA",
            "TIPOFALTA",
            "NIVELCATEG",
            "RESOLUCIONURL",
            "OBSERVACIONES",
            "CVE_MONEDA1",
            "CVE_MONEDA2",
            "TIPO_DOCTO",
            "TITULO_DOCTO",
            "DESCRIPCION_DOCTO",
            "FECHA_DOCTO",
            "PARTICULAR",
            "MONTOAPI1",
            "MONTOAPI2",
            "GRAVEDAD",
        ),
        required_columns=("AÑO", "SANCIONID"),
    ),
)


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def csv_path_for(csv_dir: Path, table: str) -> Path:
    return csv_dir / f"{table}.csv"


def read_csv_header(path: Path, encoding: str, delimiter: str) -> list[str]:
    with path.open("r", encoding=encoding, newline="") as file:
        reader = csv.reader(file, delimiter=delimiter)
        try:
            header = next(reader)
        except StopIteration:
            raise ValueError(f"{path.name} esta vacio.")

    return [column.strip().lstrip("\ufeff") for column in header]


def validate_header(spec: TableSpec, header: list[str]) -> list[str]:
    known_columns = set(spec.columns)
    unknown_columns = [column for column in header if column not in known_columns]
    if unknown_columns:
        joined = ", ".join(unknown_columns)
        raise ValueError(f"{spec.name}.csv trae columnas no esperadas: {joined}")

    missing_required = [
        column for column in spec.required_columns if column not in header
    ]
    if missing_required:
        joined = ", ".join(missing_required)
        raise ValueError(f"{spec.name}.csv no trae columnas obligatorias: {joined}")

    return header


def connect():
    load_dotenv(PROJECT_ROOT / ".env")
    return psycopg2.connect(
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
    )


def count_rows(cursor, table_name: str) -> int:
    cursor.execute(f"SELECT COUNT(*) FROM {quote_identifier(table_name)}")
    return cursor.fetchone()[0]


def truncate_table(cursor, table_name: str) -> None:
    cursor.execute(f"TRUNCATE TABLE {quote_identifier(table_name)}")


def copy_csv(cursor, spec: TableSpec, path: Path, columns: list[str], args) -> None:
    table_sql = quote_identifier(spec.name)
    columns_sql = ", ".join(quote_identifier(column) for column in columns)
    delimiter_sql = args.delimiter.replace("'", "''")
    null_sql = args.null.replace("'", "''")

    copy_sql = f"""
        COPY {table_sql} ({columns_sql})
        FROM STDIN
        WITH (
            FORMAT CSV,
            HEADER TRUE,
            DELIMITER '{delimiter_sql}',
            NULL '{null_sql}',
            QUOTE '"',
            ESCAPE '"'
        )
    """

    with path.open("r", encoding=args.encoding, newline="") as file:
        cursor.copy_expert(copy_sql, file)


def import_table(cursor, spec: TableSpec, args) -> None:
    path = csv_path_for(args.csv_dir, spec.name)
    if not path.exists():
        if args.strict:
            raise FileNotFoundError(f"No existe {path}")
        print(f"- {spec.name}: sin archivo, se omite")
        return

    columns = validate_header(
        spec,
        read_csv_header(path, encoding=args.encoding, delimiter=args.delimiter),
    )

    before = count_rows(cursor, spec.name)
    if args.truncate:
        truncate_table(cursor, spec.name)
        before = 0

    copy_csv(cursor, spec, path, columns, args)
    after = count_rows(cursor, spec.name)
    print(f"- {spec.name}: {before} -> {after} filas")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Importa CSV exportados desde Oracle a PostgreSQL."
    )
    parser.add_argument(
        "--csv-dir",
        type=Path,
        default=DEFAULT_CSV_DIR,
        help=f"Carpeta con los CSV. Default: {DEFAULT_CSV_DIR}",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Vacia cada tabla antes de importar su CSV.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Falla si falta algun CSV esperado.",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        choices=[spec.name for spec in TABLES],
        help="Importa solo las tablas indicadas.",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8-sig",
        help="Encoding de los CSV. Usa latin-1 si Oracle exporto ANSI.",
    )
    parser.add_argument(
        "--delimiter",
        default=",",
        help="Delimitador de los CSV. Default: coma.",
    )
    parser.add_argument(
        "--null",
        default="",
        help="Valor que PostgreSQL interpretara como NULL. Default: cadena vacia.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.csv_dir = args.csv_dir.resolve()

    selected_tables = TABLES
    if args.only:
        selected = set(args.only)
        selected_tables = tuple(spec for spec in TABLES if spec.name in selected)

    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET datestyle TO 'ISO, DMY'")
            for spec in selected_tables:
                import_table(cursor, spec, args)

    print("Importacion terminada.")


if __name__ == "__main__":
    main()
