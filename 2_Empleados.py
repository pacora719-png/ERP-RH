import streamlit as st
import pandas as pd
from database import get_connection, get_ubicaciones

st.set_page_config(page_title="Empleados", page_icon="👥", layout="wide")

if not st.session_state.get("autenticado"):
    st.warning("Por favor inicia sesión desde la página principal.")
    st.stop()

st.title("👥 Empleados")

ubicaciones = get_ubicaciones()
if not ubicaciones:
    st.warning("Todavía no has creado ninguna ubicación/sede. Ve a **Configuración** para agregar al menos una antes de crear empleados.")
    st.stop()

ubicacion_nombres = {u["id"]: u["nombre"] for u in ubicaciones}

tab_lista, tab_nuevo = st.tabs(["📋 Lista de empleados", "➕ Nuevo empleado"])

with tab_lista:
    with get_connection() as conn:
        df = pd.read_sql_query("""
            SELECT e.*, u.nombre AS ubicacion_nombre
            FROM empleados e LEFT JOIN ubicaciones u ON e.ubicacion_id = u.id
            ORDER BY e.nombre
        """, conn)

    if df.empty:
        st.info("Todavía no hay empleados registrados. Agrega el primero en la pestaña 'Nuevo empleado'.")
    else:
        filtro_ubicacion = st.selectbox("Filtrar por ubicación", ["Todas"] + list(ubicacion_nombres.values()))
        df_mostrar = df if filtro_ubicacion == "Todas" else df[df["ubicacion_nombre"] == filtro_ubicacion]

        st.dataframe(
            df_mostrar[["id", "nombre", "identificacion", "cargo", "ubicacion_nombre",
                        "fecha_ingreso", "estado", "eps", "fondo_pension", "arl", "caja_compensacion"]],
            use_container_width=True,
            hide_index=True
        )

        st.divider()
        st.subheader("Editar o eliminar empleado")
        emp_id = st.selectbox(
            "Selecciona un empleado",
            df["id"].tolist(),
            format_func=lambda x: df[df["id"] == x]["nombre"].values[0]
        )
        emp = df[df["id"] == emp_id].iloc[0]

        with st.form("editar_empleado"):
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre completo", emp["nombre"])
                identificacion = st.text_input("Identificación", emp["identificacion"] or "")
                cargo = st.text_input("Cargo", emp["cargo"] or "")
                ids_ubicacion = list(ubicacion_nombres.keys())
                idx_actual = ids_ubicacion.index(emp["ubicacion_id"]) if emp["ubicacion_id"] in ids_ubicacion else 0
                ubicacion_id = st.selectbox(
                    "Ubicación / Sede", ids_ubicacion,
                    index=idx_actual, format_func=lambda x: ubicacion_nombres[x]
                )
            with col2:
                fecha_ingreso = st.text_input("Fecha de ingreso (AAAA-MM-DD)", emp["fecha_ingreso"] or "")
                salario_base = st.number_input("Salario base", value=float(emp["salario_base"] or 0))
                valor_hora = st.number_input("Valor hora", value=float(emp["valor_hora"] or 0))
                telefono = st.text_input("Teléfono", emp["telefono"] or "")
                estado = st.selectbox("Estado", ["Activo", "Inactivo"],
                                       index=0 if emp["estado"] == "Activo" else 1)

            st.markdown("**Afiliaciones**")
            col3, col4 = st.columns(2)
            with col3:
                eps = st.text_input("EPS (salud)", emp["eps"] or "")
                arl = st.text_input("ARL", emp["arl"] or "")
            with col4:
                fondo_pension = st.text_input("Fondo de pensión", emp["fondo_pension"] or "")
                caja_compensacion = st.text_input("Caja de compensación familiar", emp["caja_compensacion"] or "")

            col_a, col_b = st.columns(2)
            guardar = col_a.form_submit_button("💾 Guardar cambios")
            eliminar = col_b.form_submit_button("🗑️ Eliminar empleado")

        if guardar:
            with get_connection() as conn:
                conn.execute("""
                    UPDATE empleados SET nombre=?, identificacion=?, cargo=?, ubicacion_id=?, fecha_ingreso=?,
                    salario_base=?, valor_hora=?, telefono=?, estado=?, eps=?, fondo_pension=?, arl=?, caja_compensacion=?
                    WHERE id=?
                """, (nombre, identificacion, cargo, ubicacion_id, fecha_ingreso, salario_base,
                      valor_hora, telefono, estado, eps, fondo_pension, arl, caja_compensacion, int(emp_id)))
            st.success("Empleado actualizado.")
            st.rerun()

        if eliminar:
            with get_connection() as conn:
                conn.execute("DELETE FROM empleados WHERE id=?", (int(emp_id),))
            st.success("Empleado eliminado.")
            st.rerun()

with tab_nuevo:
    with st.form("nuevo_empleado", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre completo *")
            identificacion = st.text_input("Identificación")
            cargo = st.text_input("Cargo")
            ubicacion_id = st.selectbox(
                "Ubicación / Sede", list(ubicacion_nombres.keys()),
                format_func=lambda x: ubicacion_nombres[x]
            )
        with col2:
            fecha_ingreso = st.date_input("Fecha de ingreso")
            salario_base = st.number_input("Salario base", min_value=0.0, step=10000.0)
            valor_hora = st.number_input("Valor hora", min_value=0.0, step=1000.0)
            telefono = st.text_input("Teléfono")

        st.markdown("**Afiliaciones**")
        col3, col4 = st.columns(2)
        with col3:
            eps = st.text_input("EPS (salud)")
            arl = st.text_input("ARL")
        with col4:
            fondo_pension = st.text_input("Fondo de pensión")
            caja_compensacion = st.text_input("Caja de compensación familiar")

        crear = st.form_submit_button("➕ Agregar empleado")

    if crear:
        if not nombre:
            st.error("El nombre es obligatorio.")
        else:
            with get_connection() as conn:
                conn.execute("""
                    INSERT INTO empleados (nombre, identificacion, cargo, ubicacion_id, fecha_ingreso, salario_base,
                    valor_hora, telefono, eps, fondo_pension, arl, caja_compensacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (nombre, identificacion, cargo, ubicacion_id, str(fecha_ingreso), salario_base, valor_hora,
                      telefono, eps, fondo_pension, arl, caja_compensacion))
            st.success(f"Empleado '{nombre}' agregado correctamente.")
