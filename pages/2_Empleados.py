import streamlit as st
import pandas as pd
from database import get_connection, get_ubicaciones, get_horas_mensuales, execute, read_sql_query
from excel_utils import exportar_excel, plantilla_empleados

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
ubicacion_por_nombre = {v: k for k, v in ubicacion_nombres.items()}
horas_mensuales = get_horas_mensuales()

tab_lista, tab_nuevo, tab_excel = st.tabs(["📋 Lista de empleados", "➕ Nuevo empleado", "📁 Cargar/Descargar Excel"])

with tab_lista:
    with get_connection() as conn:
        df = read_sql_query("""
            SELECT e.*, u.nombre AS ubicacion_nombre
            FROM empleados e LEFT JOIN ubicaciones u ON e.ubicacion_id = u.id
            ORDER BY e.nombre
        """, conn)

    if df.empty:
        st.info("Todavía no hay empleados registrados. Agrega el primero en la pestaña 'Nuevo empleado'.")
    else:
        filtro_estado = st.selectbox("Filtrar por estado", ["Activos", "Todos", "Inactivos"])
        if filtro_estado == "Activos":
            df_mostrar = df[df["estado"] == "Activo"]
        elif filtro_estado == "Inactivos":
            df_mostrar = df[df["estado"] == "Inactivo"]
        else:
            df_mostrar = df

        filtro_ubicacion = st.selectbox("Filtrar por ubicación", ["Todas"] + list(ubicacion_nombres.values()))
        if filtro_ubicacion != "Todas":
            df_mostrar = df_mostrar[df_mostrar["ubicacion_nombre"] == filtro_ubicacion]

        st.dataframe(
            df_mostrar[["id", "nombre", "identificacion", "cargo", "ubicacion_nombre",
                        "fecha_ingreso", "salario_base", "estado", "eps", "fondo_pension", "arl", "caja_compensacion"]],
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "⬇️ Descargar esta lista en Excel",
            data=exportar_excel(df_mostrar.drop(columns=["ubicacion_id"]), "Empleados"),
            file_name="empleados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
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
                st.caption(f"Valor hora calculado: ${(salario_base / horas_mensuales):,.0f} (salario ÷ {horas_mensuales:.0f} horas)")
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
            valor_hora = salario_base / horas_mensuales if horas_mensuales else 0
            with get_connection() as conn:
                execute(conn, """
                    UPDATE empleados SET nombre=?, identificacion=?, cargo=?, ubicacion_id=?, fecha_ingreso=?,
                    salario_base=?, valor_hora=?, telefono=?, estado=?, eps=?, fondo_pension=?, arl=?, caja_compensacion=?
                    WHERE id=?
                """, (nombre, identificacion, cargo, ubicacion_id, fecha_ingreso, salario_base, valor_hora,
                      telefono, estado, eps, fondo_pension, arl, caja_compensacion, int(emp_id)))
            st.success("Empleado actualizado.")
            st.rerun()

        if eliminar:
            with get_connection() as conn:
                execute(conn, "DELETE FROM empleados WHERE id=?", (int(emp_id),))
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
            if salario_base:
                st.caption(f"Valor hora calculado: ${(salario_base / horas_mensuales):,.0f}")
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
            valor_hora = salario_base / horas_mensuales if horas_mensuales else 0
            with get_connection() as conn:
                execute(conn, """
                    INSERT INTO empleados (nombre, identificacion, cargo, ubicacion_id, fecha_ingreso, salario_base,
                    valor_hora, telefono, eps, fondo_pension, arl, caja_compensacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (nombre, identificacion, cargo, ubicacion_id, str(fecha_ingreso), salario_base, valor_hora,
                      telefono, eps, fondo_pension, arl, caja_compensacion))
            st.success(f"Empleado '{nombre}' agregado correctamente.")

with tab_excel:
    st.subheader("Descargar plantilla")
    st.caption("Descarga la plantilla, llénala con tus empleados (una fila por persona) y súbela abajo. El valor hora se calcula automáticamente a partir del salario base, no hace falta incluirlo.")
    st.download_button(
        "⬇️ Descargar plantilla de Excel",
        data=plantilla_empleados(),
        file_name="plantilla_empleados.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    st.caption(f"Ubicaciones válidas para la columna 'ubicacion': {', '.join(ubicacion_nombres.values())}")

    st.divider()
    st.subheader("Cargar empleados desde Excel")
    archivo = st.file_uploader("Selecciona el archivo .xlsx", type=["xlsx"])

    if archivo is not None:
        try:
            df_carga = pd.read_excel(archivo)
        except Exception as e:
            st.error(f"No se pudo leer el archivo: {e}")
            df_carga = None

        if df_carga is not None:
            columnas_esperadas = {
                "nombre", "identificacion", "cargo", "ubicacion", "fecha_ingreso",
                "salario_base", "telefono", "eps", "fondo_pension",
                "arl", "caja_compensacion"
            }
            faltantes = columnas_esperadas - set(df_carga.columns)
            if faltantes:
                st.error(f"Al archivo le faltan estas columnas: {', '.join(faltantes)}. Usa la plantilla como base.")
            else:
                st.write("Vista previa:")
                st.dataframe(df_carga, use_container_width=True, hide_index=True)

                if st.button("✅ Confirmar carga de estos empleados"):
                    insertados, errores = 0, []
                    with get_connection() as conn:
                        for i, fila in df_carga.iterrows():
                            nombre_fila = str(fila.get("nombre", "")).strip()
                            if not nombre_fila or nombre_fila.lower() == "nan":
                                continue

                            ubicacion_nombre = str(fila.get("ubicacion", "")).strip()
                            ubicacion_id = ubicacion_por_nombre.get(ubicacion_nombre)
                            if ubicacion_id is None:
                                errores.append(f"Fila {i + 2}: ubicación '{ubicacion_nombre}' no existe. Créala en Configuración.")
                                continue

                            salario_base_fila = float(fila.get("salario_base", 0) or 0)
                            valor_hora_fila = salario_base_fila / horas_mensuales if horas_mensuales else 0

                            try:
                                execute(conn, """
                                    INSERT INTO empleados (nombre, identificacion, cargo, ubicacion_id, fecha_ingreso,
                                    salario_base, valor_hora, telefono, eps, fondo_pension, arl, caja_compensacion)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    nombre_fila,
                                    str(fila.get("identificacion", "")).strip(),
                                    str(fila.get("cargo", "")).strip(),
                                    ubicacion_id,
                                    str(fila.get("fecha_ingreso", "")).strip(),
                                    salario_base_fila,
                                    valor_hora_fila,
                                    str(fila.get("telefono", "")).strip(),
                                    str(fila.get("eps", "")).strip(),
                                    str(fila.get("fondo_pension", "")).strip(),
                                    str(fila.get("arl", "")).strip(),
                                    str(fila.get("caja_compensacion", "")).strip(),
                                ))
                                insertados += 1
                            except Exception as e:
                                errores.append(f"Fila {i + 2} ({nombre_fila}): {e}")

                    if insertados:
                        st.success(f"Se cargaron {insertados} empleado(s) correctamente.")
                    if errores:
                        st.warning("Algunas filas no se pudieron cargar:\n\n" + "\n".join(errores))
                    if insertados:
                        st.rerun()
