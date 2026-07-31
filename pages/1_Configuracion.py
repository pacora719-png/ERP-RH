import streamlit as st
import pandas as pd
import base64
from database import get_connection, get_config, set_config, execute, read_sql_query

st.set_page_config(page_title="Configuración", page_icon="⚙️", layout="wide")

if not st.session_state.get("autenticado"):
    st.warning("Por favor inicia sesión desde la página principal.")
    st.stop()

st.title("⚙️ Configuración")

tab_empresa, tab_ubicaciones, tab_nomina = st.tabs(["🏢 Datos de la empresa", "📍 Ubicaciones / Sedes", "💰 Parámetros de nómina"])

# ---------- DATOS DE LA EMPRESA ----------
with tab_empresa:
    nombre_empresa = get_config("nombre_empresa", "Mi Empresa")
    nit_empresa = get_config("nit_empresa", "")
    representante_empresa = get_config("representante_empresa", "")
    logo_actual = get_config("logo_empresa_base64", "")

    with st.form("form_empresa"):
        nuevo_nombre = st.text_input("Nombre de la empresa", value=nombre_empresa)
        nuevo_nit = st.text_input("NIT", value=nit_empresa)
        nuevo_representante = st.text_input("Representante legal", value=representante_empresa)
        logo_subido = st.file_uploader("Logo de la empresa (PNG o JPG)", type=["png", "jpg", "jpeg"])
        guardar_empresa = st.form_submit_button("💾 Guardar datos de la empresa")

    if logo_actual:
        st.caption("Logo actual:")
        st.image(base64.b64decode(logo_actual), width=150)

    if guardar_empresa:
        set_config("nombre_empresa", nuevo_nombre)
        set_config("nit_empresa", nuevo_nit)
        set_config("representante_empresa", nuevo_representante)
        if logo_subido is not None:
            logo_b64 = base64.b64encode(logo_subido.read()).decode("utf-8")
            set_config("logo_empresa_base64", logo_b64)
        st.success("Datos de la empresa guardados.")
        st.rerun()

# ---------- UBICACIONES ----------
with tab_ubicaciones:
    st.caption("Agrega las sedes o sucursales de tu empresa. Estas aparecerán como opción en Empleados.")

    with get_connection() as conn:
        df = read_sql_query("SELECT * FROM ubicaciones ORDER BY nombre", conn)

    if not df.empty:
        st.dataframe(df[["id", "nombre"]], use_container_width=True, hide_index=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        nueva_ubicacion = st.text_input("Nueva ubicación / sede", key="nueva_ubicacion")
    with col2:
        st.write("")
        st.write("")
        if st.button("➕ Agregar ubicación"):
            if nueva_ubicacion.strip():
                try:
                    with get_connection() as conn:
                        execute(conn, "INSERT INTO ubicaciones (nombre) VALUES (?)", (nueva_ubicacion.strip(),))
                    st.success(f"Ubicación '{nueva_ubicacion}' agregada.")
                    st.rerun()
                except Exception:
                    st.error("Esa ubicación ya existe.")
            else:
                st.error("Escribe un nombre para la ubicación.")

    if not df.empty:
        ubicacion_a_borrar = st.selectbox(
            "Eliminar una ubicación",
            df["id"].tolist(),
            format_func=lambda x: df[df["id"] == x]["nombre"].values[0]
        )
        if st.button("🗑️ Eliminar ubicación seleccionada"):
            with get_connection() as conn:
                execute(conn, "DELETE FROM ubicaciones WHERE id=?", (int(ubicacion_a_borrar),))
            st.success("Ubicación eliminada.")
            st.rerun()

# ---------- PARÁMETROS DE NÓMINA ----------
with tab_nomina:
    st.caption("Estos parámetros se usan para calcular el valor de la hora y los recargos de horas extra.")

    horas_mensuales = st.number_input(
        "Horas mensuales para calcular el valor hora (salario base ÷ este número)",
        value=float(get_config("horas_mensuales", "210")), step=1.0
    )

    st.markdown("**Recargos de horas extra (%)**")
    col1, col2 = st.columns(2)
    with col1:
        recargo_diurna = st.number_input("Hora extra diurna", value=float(get_config("recargo_extra_diurna", "25")), step=5.0)
        recargo_dominical_festivo = st.number_input("Hora extra dominical/festivo", value=float(get_config("recargo_extra_dominical_festivo", "115")), step=5.0)
    with col2:
        recargo_nocturna = st.number_input("Hora extra nocturna", value=float(get_config("recargo_extra_nocturna", "75")), step=5.0)
        recargo_dominical_festivo_nocturna = st.number_input("Hora extra dominical/festivo nocturna", value=float(get_config("recargo_extra_dominical_festivo_nocturna", "165")), step=5.0)

    st.markdown("**Recargos simples (no son horas extra, solo recargo por horario)**")
    col3, col4 = st.columns(2)
    with col3:
        recargo_nocturno_simple = st.number_input("Recargo nocturno (%)", value=float(get_config("recargo_nocturno", "35")), step=5.0)
    with col4:
        recargo_dominical_simple = st.number_input("Recargo dominical (%)", value=float(get_config("recargo_dominical", "90")), step=5.0)

    st.markdown("**Seguridad social y auxilio de transporte**")
    col5, col6 = st.columns(2)
    with col5:
        salud_pct = st.number_input("Salud a cargo del empleado (%)", value=float(get_config("salud_pct", "4")), step=0.5)
        auxilio_transporte = st.number_input("Valor auxilio de transporte (mensual)", value=float(get_config("auxilio_transporte_mensual", "249095")), step=1000.0)
    with col6:
        pension_pct = st.number_input("Pensión a cargo del empleado (%)", value=float(get_config("pension_pct", "4")), step=0.5)
        tope_auxilio = st.number_input("Tope salarial para recibir auxilio de transporte", value=float(get_config("tope_salarial_auxilio_transporte", "3501810")), step=10000.0)

    horas_normales_dia = st.number_input(
        "Horas normales máximas por día (jornada legal — ej. 7h/día = 42h/semana)",
        value=float(get_config("horas_normales_por_dia", "7")), step=0.5,
        help="Lo que se trabaje por encima de este límite, después de descontar el tiempo no laboral, se sugiere registrar como hora extra."
    )

    if st.button("💾 Guardar parámetros de nómina"):
        set_config("horas_mensuales", str(horas_mensuales))
        set_config("recargo_extra_diurna", str(recargo_diurna))
        set_config("recargo_extra_nocturna", str(recargo_nocturna))
        set_config("recargo_extra_dominical_festivo", str(recargo_dominical_festivo))
        set_config("recargo_extra_dominical_festivo_nocturna", str(recargo_dominical_festivo_nocturna))
        set_config("recargo_nocturno", str(recargo_nocturno_simple))
        set_config("recargo_dominical", str(recargo_dominical_simple))
        set_config("salud_pct", str(salud_pct))
        set_config("pension_pct", str(pension_pct))
        set_config("auxilio_transporte_mensual", str(auxilio_transporte))
        set_config("tope_salarial_auxilio_transporte", str(tope_auxilio))
        set_config("horas_normales_por_dia", str(horas_normales_dia))
        st.success("Parámetros guardados.")
        st.rerun()
