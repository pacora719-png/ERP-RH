"""
Módulo de base de datos compartida para el ERP.
Usa SQLite como motor de almacenamiento local.
Diseñado para ser genérico: las ubicaciones/sedes son configurables
por el usuario, no están fijas en el código, y el nombre de la
empresa se define en la configuración.
"""
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).parent / "erp.db"


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Crea todas las tablas si no existen todavía."""
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS ubicaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS empleados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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

        # Migración: agrega las columnas de afiliaciones si la tabla ya existía sin ellas
        cur.execute("PRAGMA table_info(empleados)")
        columnas_existentes = {fila["name"] for fila in cur.fetchall()}
        columnas_nuevas = {
            "eps": "TEXT",
            "fondo_pension": "TEXT",
            "arl": "TEXT",
            "caja_compensacion": "TEXT",
        }
        for columna, tipo in columnas_nuevas.items():
            if columna not in columnas_existentes:
                cur.execute(f"ALTER TABLE empleados ADD COLUMN {columna} {tipo}")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS horas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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

        cur.execute("""
        CREATE TABLE IF NOT EXISTS asistencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_id INTEGER NOT NULL,
            fecha_inicio TEXT NOT NULL,
            fecha_fin TEXT NOT NULL,
            tipo TEXT CHECK(tipo IN ('Vacaciones', 'Permiso', 'Incapacidad', 'Ausencia injustificada')),
            comentario TEXT,
            FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE CASCADE
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS inventario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            categoria TEXT,
            unidad TEXT,
            stock_actual REAL DEFAULT 0,
            stock_minimo REAL DEFAULT 0,
            costo_unitario REAL DEFAULT 0,
            ubicacion_id INTEGER,
            FOREIGN KEY (ubicacion_id) REFERENCES ubicaciones(id) ON DELETE SET NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS movimientos_inventario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            tipo TEXT CHECK(tipo IN ('Entrada', 'Salida')),
            cantidad REAL NOT NULL,
            motivo TEXT,
            FOREIGN KEY (producto_id) REFERENCES inventario(id) ON DELETE CASCADE
        )
        """)

        conn.commit()


def get_config(clave, default=""):
    with get_connection() as conn:
        row = conn.execute("SELECT valor FROM configuracion WHERE clave=?", (clave,)).fetchone()
        return row["valor"] if row else default


def set_config(clave, valor):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO configuracion (clave, valor) VALUES (?, ?)
            ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor
        """, (clave, valor))


def get_ubicaciones():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM ubicaciones ORDER BY nombre").fetchall()
        return [dict(r) for r in rows]
