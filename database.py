"""
Módulo de base de datos compartida para el ERP.

Funciona con dos motores:
- SQLite (por defecto): archivo local erp.db, sin configuración adicional.
- PostgreSQL (recomendado en producción): se activa automáticamente si existe
  el secreto `database_url` en Streamlit (Settings > Secrets) o la variable de
  entorno DATABASE_URL. Ejemplo de cadena de conexión (Neon, Supabase, etc.):
  postgresql://usuario:clave@host/dbname?sslmode=require
"""
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager
import pandas as pd

try:
    import streamlit as st
except ImportError:
    st = None

DB_PATH = Path(__file__).parent / "erp.db"


def _get_database_url():
    if st is not None:
        try:
            url = st.secrets.get("database_url")
            if url:
                return url
        except Exception:
            pass
    return os.environ.get("DATABASE_URL")


DATABASE_URL = _get_database_url()
IS_POSTGRES = bool(DATABASE_URL)


@contextmanager
def get_connection():
    """Context manager que da una conexión lista para usar, a SQLite o PostgreSQL
    según esté configurado. Las filas se devuelven como diccionarios en ambos casos
    (acceso por fila["columna"])."""
    if IS_POSTGRES:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def _sql(sql: str) -> str:
    """Traduce los placeholders '?' (estilo SQLite) a '%s' (estilo PostgreSQL) cuando aplica."""
    return sql.replace("?", "%s") if IS_POSTGRES else sql


def execute(conn, sql: str, params=None):
    """Ejecuta una sentencia SQL en la conexión dada (SQLite o PostgreSQL) y
    devuelve un cursor con fetchone()/fetchall() disponibles, igual en ambos motores."""
    sql_t = _sql(sql)
    if IS_POSTGRES:
        cur = conn.cursor()
        cur.execute(sql_t, params or ())
        return cur
    return conn.execute(sql_t, params or ())


def read_sql_query(sql: str, conn, params=None) -> pd.DataFrame:
    """Reemplazo directo de pd.read_sql_query que traduce los placeholders según el motor."""
    sql_t = _sql(sql)
    if params is not None:
        return pd.read_sql_query(sql_t, conn, params=params)
    return pd.read_sql_query(sql_t, conn)


def _tabla_existe_columna(cur, tabla, columna):
    if IS_POSTGRES:
        cur.execute("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name=%s AND column_name=%s
        """, (tabla, columna))
        return cur.fetchone() is not None
    else:
        cur.execute(f"PRAGMA table_info({tabla})")
        return columna in {fila["name"] for fila in cur.fetchall()}


def _agregar_columnas_si_faltan(cur, tabla, columnas: dict):
    for columna, tipo_sqlite in columnas.items():
        if not _tabla_existe_columna(cur, tabla, columna):
            tipo = tipo_sqlite
            if IS_POSTGRES:
                tipo = tipo_sqlite.replace("BLOB", "BYTEA")
            cur.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}")


def init_db():
    """Crea todas las tablas si no existen todavía, y migra tablas antiguas.
    El esquema se adapta automáticamente a SQLite o PostgreSQL."""
    pk = "SERIAL PRIMARY KEY" if IS_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"
    blob = "BYTEA" if IS_POSTGRES else "BLOB"

    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT
        )
        """)

        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS ubicaciones (
            id {pk},
            nombre TEXT NOT NULL UNIQUE
        )
        """)

        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS empleados (
            id {pk},
            nombre TEXT NOT NULL,
            identificacion TEXT UNIQUE,
            cargo TEXT,
            ubicacion_id INTEGER,
            fecha_ingreso TEXT,
            salario_base REAL DEFAULT 0,
            valor_hora REAL DEFAULT 0,
            telefono TEXT,
            estado TEXT DEFAULT 'Activo' CHECK(estado IN ('Activo', 'Inactivo')),
            eps TEXT,
            fondo_pension TEXT,
            arl TEXT,
            caja_compensacion TEXT,
            FOREIGN KEY (ubicacion_id) REFERENCES ubicaciones(id) ON DELETE SET NULL
        )
        """)
        _agregar_columnas_si_faltan(cur, "empleados", {
            "eps": "TEXT", "fondo_pension": "TEXT", "arl": "TEXT", "caja_compensacion": "TEXT",
        })

        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS horas (
            id {pk},
            empleado_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            hora_entrada TEXT,
            hora_salida TEXT,
            horas_normales REAL DEFAULT 0,
            horas_extra REAL DEFAULT 0,
            bonificacion REAL DEFAULT 0,
            deduccion REAL DEFAULT 0,
            observacion TEXT,
            FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE CASCADE
        )
        """)
        _agregar_columnas_si_faltan(cur, "horas", {
            "horas_extra_diurna": "REAL DEFAULT 0",
            "horas_extra_nocturna": "REAL DEFAULT 0",
            "horas_extra_dominical_festivo": "REAL DEFAULT 0",
            "horas_extra_dominical_festivo_nocturna": "REAL DEFAULT 0",
            "horas_recargo_nocturno": "REAL DEFAULT 0",
            "horas_recargo_dominical": "REAL DEFAULT 0",
            "horas_descuento": "REAL DEFAULT 0",
            "tipo_descuento": "TEXT",
        })

        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS asistencia (
            id {pk},
            empleado_id INTEGER NOT NULL,
            fecha_inicio TEXT NOT NULL,
            fecha_fin TEXT NOT NULL,
            tipo TEXT CHECK(tipo IN ('Vacaciones', 'Permiso', 'Incapacidad', 'Ausencia injustificada')),
            comentario TEXT,
            FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE CASCADE
        )
        """)

        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS cancelaciones_contrato (
            id {pk},
            empleado_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            motivo TEXT,
            valor_liquidacion REAL DEFAULT 0,
            valor_indemnizacion REAL DEFAULT 0,
            evidencia_nombre TEXT,
            evidencia_datos {blob},
            FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE CASCADE
        )
        """)

        conn.commit()


def get_config(clave, default=""):
    with get_connection() as conn:
        row = execute(conn, "SELECT valor FROM configuracion WHERE clave=?", (clave,)).fetchone()
        return row["valor"] if row else default


def set_config(clave, valor):
    with get_connection() as conn:
        execute(conn, """
            INSERT INTO configuracion (clave, valor) VALUES (?, ?)
            ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor
        """, (clave, valor))


def get_ubicaciones():
    with get_connection() as conn:
        rows = execute(conn, "SELECT * FROM ubicaciones ORDER BY nombre").fetchall()
        return [dict(r) for r in rows]


# ---------- Multiplicadores de horas extra (configurables) ----------
def get_multiplicadores():
    """Devuelve los multiplicadores de pago para cada tipo de hora extra/recargo,
    calculados a partir de los recargos (%) guardados en configuración.
    Los valores por defecto igualan el liquidador de referencia:
    extra diurna 1.25, extra nocturna 1.75, extra dominical/festivo 2.15,
    extra dominical/festivo nocturna 2.65, recargo nocturno 0.35, recargo dominical 0.90."""
    def mult(clave, default_pct):
        pct = float(get_config(clave, str(default_pct)))
        return 1 + (pct / 100)

    def factor(clave, default_pct):
        pct = float(get_config(clave, str(default_pct)))
        return pct / 100

    return {
        "extra_diurna": mult("recargo_extra_diurna", 25),
        "extra_nocturna": mult("recargo_extra_nocturna", 75),
        "extra_dominical_festivo": mult("recargo_extra_dominical_festivo", 115),
        "extra_dominical_festivo_nocturna": mult("recargo_extra_dominical_festivo_nocturna", 165),
        "recargo_nocturno": factor("recargo_nocturno", 35),
        "recargo_dominical": factor("recargo_dominical", 90),
    }


def get_horas_mensuales():
    return float(get_config("horas_mensuales", "210"))


def get_parametros_nomina():
    """Parámetros legales de nómina colombiana, editables en Configuración."""
    return {
        "salud_pct": float(get_config("salud_pct", "4")) / 100,
        "pension_pct": float(get_config("pension_pct", "4")) / 100,
        "auxilio_transporte_mensual": float(get_config("auxilio_transporte_mensual", "249095")),
        "tope_salarial_auxilio_transporte": float(get_config("tope_salarial_auxilio_transporte", "3501810")),
    }
