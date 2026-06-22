# Importacion de datos Oracle a PostgreSQL

Esta carpeta es para cargar CSV exportados desde Oracle hacia PostgreSQL.
No pongas estos archivos dentro de `postgres/init`: esa carpeta solo crea el
esquema cuando el volumen de PostgreSQL nace por primera vez.

## 1. Exportar CSV desde Oracle en Docker

Si Oracle corre en el contenedor local `oracle_xe`, exporta los CSV con:

```powershell
powershell -ExecutionPolicy Bypass -File .\docker\dev\postgres\import\export_oracle_csv_from_docker.ps1
```

El script intenta leer `APP_USER` y `APP_USER_PASSWORD` del contenedor. Si
necesitas pasar credenciales manualmente:

```powershell
powershell -ExecutionPolicy Bypass -File .\docker\dev\postgres\import\export_oracle_csv_from_docker.ps1 `
  -Container oracle_xe `
  -User SABG `
  -Password tu_password `
  -Service XEPDB1
```

Los CSV se guardan en:

```text
docker/dev/postgres/import/csv/
```

## 2. Exportar CSV desde una herramienta visual

Exporta cada tabla con encabezados y encoding UTF-8:

- `CAT_GENERO.csv`
- `TIPOSANCION.csv`
- `CAT_MONEDAS.csv`
- `CAT_TFALTA.csv`
- `CAT_TIPODOCTO.csv`
- `DEPENDENCIAS.csv`
- `INHABILIFEDERAL.csv`
- `INHABILITADOS.csv`

Recomendaciones al exportar:

- Incluir encabezados.
- Usar coma como delimitador.
- Usar UTF-8.
- Exportar fechas como `YYYY-MM-DD` o `DD/MM/YYYY`.
- Exportar numeros sin separador de miles.
- Mantener los nombres de columnas como en Oracle, por ejemplo `AÑO`,
  `SANCIONID`, `RFC`, `FECHAREG`.

Si usas SQL Developer o DBeaver, coloca los archivos en:

```text
docker/dev/postgres/import/csv/
```

## 3. Levantar Docker

Desde la raiz del proyecto:

```bash
docker compose --env-file .env -f docker/dev/docker-compose.yml down &&
docker compose --env-file .env -f docker/dev/docker-compose.yml up --build -d &&
docker compose --env-file .env -f docker/dev/docker-compose.yml logs -f
```

Si corres este backend junto a `gestiondocumental`, usa los puertos alternativos de
`docker/dev/.env` (Django `9000`, PostgreSQL `5433`) para evitar conflictos:

```bash
docker compose --env-file .env --env-file docker/dev/.env -f docker/dev/docker-compose.yml down &&
docker compose --env-file .env --env-file docker/dev/.env -f docker/dev/docker-compose.yml up --build -d &&
docker compose --env-file .env --env-file docker/dev/.env -f docker/dev/docker-compose.yml logs -f
```

## 4. Importar datos

Para una carga inicial, normalmente quieres vaciar cada tabla antes de importar:

```bash
docker compose --env-file .env -f docker/dev/docker-compose.yml exec django \
  python docker/dev/postgres/import/import_csv_to_postgres.py --truncate
```

Para cargar sin borrar datos existentes:

```bash
docker compose --env-file .env -f docker/dev/docker-compose.yml exec django \
  python docker/dev/postgres/import/import_csv_to_postgres.py
```

Para importar solo una tabla:

```bash
docker compose --env-file .env -f docker/dev/docker-compose.yml exec django \
  python docker/dev/postgres/import/import_csv_to_postgres.py --only INHABILITADOS --truncate
```

Si Oracle exporto los CSV en ANSI/Latin-1:

```bash
docker compose --env-file .env -f docker/dev/docker-compose.yml exec django \
  python docker/dev/postgres/import/import_csv_to_postgres.py --encoding latin-1 --truncate
```

Si el CSV usa punto y coma:

```bash
docker compose --env-file .env -f docker/dev/docker-compose.yml exec django \
  python docker/dev/postgres/import/import_csv_to_postgres.py --delimiter ";" --truncate
```

## 5. Validar conteos

El script imprime el conteo antes y despues por tabla:

```text
- INHABILITADOS: 0 -> 1234 filas
```

Tambien puedes validar directo en PostgreSQL:

```bash
docker compose --env-file .env -f docker/dev/docker-compose.yml exec postgres_db \
  psql -U sanciones -d sanciones -c 'SELECT COUNT(*) FROM "INHABILITADOS";'
```

## Notas

- Si falta un CSV, el script lo omite.
- Usa `--strict` si quieres que falle cuando falte cualquier CSV.
- Si cambiaste el esquema y necesitas recrear la base local desde cero, puedes
  usar `docker compose --env-file .env -f docker/dev/docker-compose.yml down -v`.
  Eso borra el volumen local de PostgreSQL.
