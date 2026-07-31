import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta, date
from database import get_connection, get_multiplicadores, get_parametros_nomina, execute, read_sql_query
from excel_utils import exportar_excel, plantilla_horas, hhmm_a_decimal, decimal_a_hhmm, texto_hhmm_a_decimal, columnas_a_hhmm

st.set_page_config(page_title="Horas y Nómina", page_icon="⏱️", layout="wide")

if not st.session_state.get("autenticado"):
    st.warning("Por favor inicia sesión desde la página principal.")
    st.stop()

st.title("⏱️ Horas y Nómina")

with get_connection() as conn:
    empleados_df = read_sql_query("SELECT * FROM empleados WHERE estado='Activo' ORDER BY nombre", conn)

if empleados_df.empty:
    st.warning("No hay empleados activos. Ve a **Empleados** para agregar al menos uno.")
    st.stop()

identificacion_a_id = {
    str(row["identificacion"]).strip(): row["id"]
    for _, row in empleados_df.iterrows() if row["identificacion"]
}

COLUMNAS_DURACION = [
    "horas_normales", "horas_extra_diurna", "horas_extra_nocturna",
    "horas_extra_dominical_festivo", "horas_extra_dominical_festivo_nocturna",
    "horas_recargo_nocturno", "horas_recargo_dominical", "horas_recargo_dominical_festivo_nocturno", "horas_descuento"
]


def entrada_horas_minutos(etiqueta, key_prefix):
    """Muestra dos campos numéricos (horas y minutos) y devuelve el total en decimal."""
    col_h, col_m = st.columns(2)
    with col_h:
        h = st.number_input(f"{etiqueta} — horas", min_value=0, step=1, key=f"{key_prefix}_h")
    with col_m:
        m = st.number_input(f"{etiqueta} — minutos", min_value=0, max_value=59, step=5, key=f"{key_prefix}_m")
    return hhmm_a_decimal(h, m)


tab_registrar, tab_historial, tab_excel = st.tabs(["➕ Registrar horas", "📋 Historial", "📁 Cargar/Descargar Excel"])

# ---------- REGISTRAR ----------
with tab_registrar:
    p = get_parametros_nomina()
    horas_normales_max = p["horas_normales_por_dia"]

    empleado_id = st.selectbox(
        "Empleado",
        empleados_df["id"].tolist(),
        format_func=lambda x: empleados_df[empleados_df["id"] == x]["nombre"].values[0]
    )

    st.subheader("Jornada del día")
    fecha = st.date_input("Fecha", key="reg_fecha")
    col1, col2 = st.columns(2)
    with col1:
        hora_entrada = st.time_input("Hora de entrada", value=time(8, 0), key="reg_entrada")
    with col2:
        hora_salida = st.time_input("Hora de salida", value=time(17, 0), key="reg_salida")

    st.caption(f"Jornada normal: máximo {decimal_a_hhmm(horas_normales_max)} por día, después de descontar el tiempo no laboral.")

    st.subheader("Tiempo a descontar (no laboral)")
    tipo_descuento = st.selectbox("Tipo", ["Ninguno", "Alimentación", "Break", "No laboral (otro)"], key="reg_tipo_descuento")
    horas_descuento = entrada_horas_minutos("Tiempo a descontar", "descuento")

    # ---- Cálculo en vivo: apenas cambian entrada/salida/descuento, se recalcula el excedente ----
    entrada_dt = datetime.combine(fecha, hora_entrada)
    salida_dt = datetime.combine(fecha, hora_salida)
    tiempo_bruto = max(0, (salida_dt - entrada_dt).total_seconds() / 3600)
    tiempo_neto = max(0, tiempo_bruto - horas_descuento)
    horas_normales_calc = min(tiempo_neto, horas_normales_max)
    excedente = max(0, tiempo_neto - horas_normales_max)

    st.info(
        f"⏱️ Tiempo trabajado neto: **{decimal_a_hhmm(tiempo_neto)}** → "
        f"Horas normales: **{decimal_a_hhmm(horas_normales_calc)}**"
        + (f" | Excedente autocompletado como hora extra diurna: **{decimal_a_hhmm(excedente)}**" if excedente > 0 else "")
    )

    # Autocompletar 'Extra diurna' con el excedente (el usuario puede moverlo a otra categoría abajo)
    exc_h = int(excedente)
    exc_m = round((excedente - exc_h) * 60)
    st.session_state["ed_h"] = exc_h
    st.session_state["ed_m"] = exc_m

    with st.form("registrar_horas", clear_on_submit=True):
        st.subheader("Horas extra")
        st.caption("'Extra diurna' se autocompleta con el excedente sobre la jornada normal. Muévelo a otra categoría si el tiempo extra fue nocturno, dominical o festivo.")
        st.markdown("**Extra diurna**")
        horas_extra_diurna = entrada_horas_minutos("Extra diurna", "ed")
        st.markdown("**Extra nocturna**")
        horas_extra_nocturna = entrada_horas_minutos("Extra nocturna", "en")
        st.markdown("**Extra dominical/festivo**")
        horas_extra_dominical_festivo = entrada_horas_minutos("Extra dominical/festivo", "ef")
        st.markdown("**Extra dominical/festivo nocturna**")
        horas_extra_dominical_festivo_nocturna = entrada_horas_minutos("Extra dominical/festivo nocturna", "efn")

        st.subheader("Recargos (no son horas extra)")
        st.markdown("**Recargo nocturno**")
        horas_recargo_nocturno = entrada_horas_minutos("Recargo nocturno", "rn")
        st.markdown("**Recargo dominical/festivo**")
        horas_recargo_dominical = entrada_horas_minutos("Recargo dominical/festivo", "rd")
        st.markdown("**Recargo dominical/festivo nocturno**")
        horas_recargo_dominical_festivo_nocturno = entrada_horas_minutos("Recargo dominical/festivo nocturno", "rdn")

        col7, col8 = st.columns(2)
        with col7:
            bonificacion = st.number_input("Bonificación", min_value=0.0, step=1000.0)
        with col8:
            deduccion = st.number_input("Deducción", min_value=0.0, step=1000.0)

        observacion = st.text_input("Observación (opcional)")
        guardar = st.form_submit_button("💾 Guardar registro")

    if guardar:
        horas_normales = horas_normales_calc
        tipo_descuento_guardar = None if tipo_descuento == "Ninguno" else tipo_descuento

        with get_connection() as conn:
            execute(conn, """
                INSERT INTO horas (empleado_id, fecha, hora_entrada, hora_salida, horas_normales,
                horas_extra_diurna, horas_extra_nocturna, horas_extra_dominical_festivo,
                horas_extra_dominical_festivo_nocturna, horas_recargo_nocturno, horas_recargo_dominical,
                horas_recargo_dominical_festivo_nocturno, horas_descuento, tipo_descuento, bonificacion, deduccion, observacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (int(empleado_id), str(fecha), str(hora_entrada), str(hora_salida), round(horas_normales, 4),
                  horas_extra_diurna, horas_extra_nocturna, horas_extra_dominical_festivo,
                  horas_extra_dominical_festivo_nocturna, horas_recargo_nocturno, horas_recargo_dominical,
                  horas_recargo_dominical_festivo_nocturno, horas_descuento, tipo_descuento_guardar, bonificacion, deduccion, observacion))

        mensaje = f"Registro guardado: {decimal_a_hhmm(horas_normales)} de horas normales."
        if excedente > 0:
            mensaje += f" ⚠️ Trabajó {decimal_a_hhmm(excedente)} por encima de la jornada normal ({decimal_a_hhmm(horas_normales_max)}) — recuerda registrar ese tiempo como hora extra si corresponde."
        st.success(mensaje)

# ---------- HISTORIAL ----------
with tab_historial:
    st.caption("Elige un rango de fechas, o usa el atajo de 'semana actual' / 'semana pasada'.")
    atajo = st.radio("Atajo rápido", ["Rango personalizado", "Semana actual", "Semana pasada"], horizontal=True)

    hoy = date.today()
    inicio_semana_actual = hoy - timedelta(days=hoy.weekday())  # lunes de esta semana

    if atajo == "Semana actual":
        fecha_inicio = inicio_semana_actual
        fecha_fin = inicio_semana_actual + timedelta(days=6)
    elif atajo == "Semana pasada":
        fecha_inicio = inicio_semana_actual - timedelta(days=7)
        fecha_fin = inicio_semana_actual - timedelta(days=1)
    else:
        col1, col2 = st.columns(2)
        with col1:
            fecha_inicio = st.date_input("Desde", key="hist_desde")
        with col2:
            fecha_fin = st.date_input("Hasta", key="hist_hasta")

    if atajo != "Rango personalizado":
        st.info(f"Mostrando del **{fecha_inicio}** al **{fecha_fin}**")

    with get_connection() as conn:
        df = read_sql_query("""
            SELECT h.*, e.nombre AS empleado_nombre, e.valor_hora, u.nombre AS ubicacion_nombre
            FROM horas h
            JOIN empleados e ON h.empleado_id = e.id
            LEFT JOIN ubicaciones u ON e.ubicacion_id = u.id
            WHERE h.fecha BETWEEN ? AND ?
            ORDER BY h.fecha
        """, conn, params=(str(fecha_inicio), str(fecha_fin)))

    if df.empty:
        st.info("No hay registros de horas en ese rango de fechas.")
    else:
        sedes_disponibles = sorted(df["ubicacion_nombre"].dropna().unique().tolist())
        if sedes_disponibles:
            filtro_sede = st.selectbox("Filtrar por sede", ["Todas"] + sedes_disponibles)
            if filtro_sede != "Todas":
                df = df[df["ubicacion_nombre"] == filtro_sede]

        m = get_multiplicadores()
        df["pago_normales"] = df["horas_normales"] * df["valor_hora"]
        df["pago_extra_diurna"] = df["horas_extra_diurna"] * df["valor_hora"] * m["extra_diurna"]
        df["pago_extra_nocturna"] = df["horas_extra_nocturna"] * df["valor_hora"] * m["extra_nocturna"]
        df["pago_extra_dom_festivo"] = df["horas_extra_dominical_festivo"] * df["valor_hora"] * m["extra_dominical_festivo"]
        df["pago_extra_dom_festivo_noc"] = df["horas_extra_dominical_festivo_nocturna"] * df["valor_hora"] * m["extra_dominical_festivo_nocturna"]
        df["pago_recargo_nocturno"] = df["horas_recargo_nocturno"] * df["valor_hora"] * m["recargo_nocturno"]
        df["pago_recargo_dominical"] = df["horas_recargo_dominical"] * df["valor_hora"] * m["recargo_dominical_festivo"]
        df["pago_recargo_dominical_nocturno"] = df["horas_recargo_dominical_festivo_nocturno"] * df["valor_hora"] * m["recargo_dominical_festivo_nocturno"]
        df["pago_descuento"] = df["horas_descuento"] * df["valor_hora"]

        df["total_a_pagar"] = (
            df["pago_normales"] + df["pago_extra_diurna"] + df["pago_extra_nocturna"]
            + df["pago_extra_dom_festivo"] + df["pago_extra_dom_festivo_noc"]
            + df["pago_recargo_nocturno"] + df["pago_recargo_dominical"] + df["pago_recargo_dominical_nocturno"]
            + df["bonificacion"] - df["deduccion"] - df["pago_descuento"]
        )

        detalle_mostrar = df[[
            "fecha", "empleado_nombre", "ubicacion_nombre", "horas_normales", "horas_extra_diurna", "horas_extra_nocturna",
            "horas_extra_dominical_festivo", "horas_extra_dominical_festivo_nocturna",
            "horas_recargo_nocturno", "horas_recargo_dominical", "horas_recargo_dominical_festivo_nocturno", "horas_descuento", "tipo_descuento",
            "bonificacion", "deduccion", "total_a_pagar"
        ]]
        detalle_mostrar_hhmm = columnas_a_hhmm(detalle_mostrar, COLUMNAS_DURACION)

        st.dataframe(detalle_mostrar_hhmm, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Resumen de nómina por empleado")
        resumen = df.groupby(["empleado_nombre", "ubicacion_nombre"]).agg(
            horas_normales=("horas_normales", "sum"),
            horas_extra_diurna=("horas_extra_diurna", "sum"),
            horas_extra_nocturna=("horas_extra_nocturna", "sum"),
            horas_extra_dominical_festivo=("horas_extra_dominical_festivo", "sum"),
            horas_extra_dominical_festivo_nocturna=("horas_extra_dominical_festivo_nocturna", "sum"),
            horas_recargo_nocturno=("horas_recargo_nocturno", "sum"),
            horas_recargo_dominical=("horas_recargo_dominical", "sum"),
            horas_recargo_dominical_festivo_nocturno=("horas_recargo_dominical_festivo_nocturno", "sum"),
            horas_descuento=("horas_descuento", "sum"),
            bonificaciones=("bonificacion", "sum"),
            deducciones=("deduccion", "sum"),
            total_a_pagar=("total_a_pagar", "sum")
        ).reset_index()
        resumen_hhmm = columnas_a_hhmm(resumen, COLUMNAS_DURACION)

        st.dataframe(resumen_hhmm, use_container_width=True, hide_index=True)
        st.metric("Total nómina del período", f"${resumen['total_a_pagar'].sum():,.0f}")

        st.divider()
        nombre_archivo = f"horas_{fecha_inicio}_a_{fecha_fin}.xlsx"

        col_a, col_b = st.columns(2)
        with col_a:
            st.download_button(
                "⬇️ Descargar detalle diario en Excel",
                data=exportar_excel(detalle_mostrar_hhmm, "Detalle horas"),
                file_name=nombre_archivo,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        with col_b:
            st.download_button(
                "⬇️ Descargar resumen de nómina en Excel",
                data=exportar_excel(resumen_hhmm, "Resumen nómina"),
                file_name=f"resumen_{nombre_archivo}",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# ---------- CARGAR / DESCARGAR EXCEL ----------
with tab_excel:
    st.subheader("Descargar reporte por período (todos los empleados y sedes)")
    col1, col2 = st.columns(2)
    with col1:
        desde_reporte = st.date_input("Desde", key="excel_desde")
    with col2:
        hasta_reporte = st.date_input("Hasta", key="excel_hasta")

    if st.button("📊 Generar reporte del período"):
        with get_connection() as conn:
            df_reporte = read_sql_query("""
                SELECT h.fecha, e.nombre AS empleado, e.identificacion, u.nombre AS sede,
                       h.hora_entrada, h.hora_salida, h.horas_normales,
                       h.horas_extra_diurna, h.horas_extra_nocturna,
                       h.horas_extra_dominical_festivo, h.horas_extra_dominical_festivo_nocturna,
                       h.horas_recargo_nocturno, h.horas_recargo_dominical, h.horas_recargo_dominical_festivo_nocturno,
                       h.horas_descuento, h.tipo_descuento, h.bonificacion, h.deduccion, h.observacion
                FROM horas h
                JOIN empleados e ON h.empleado_id = e.id
                LEFT JOIN ubicaciones u ON e.ubicacion_id = u.id
                WHERE h.fecha BETWEEN ? AND ?
                ORDER BY u.nombre, e.nombre, h.fecha
            """, conn, params=(str(desde_reporte), str(hasta_reporte)))

        if df_reporte.empty:
            st.info("No hay registros de horas en ese rango de fechas.")
        else:
            df_reporte_hhmm = columnas_a_hhmm(df_reporte, COLUMNAS_DURACION)
            st.dataframe(df_reporte_hhmm, use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ Descargar reporte completo en Excel",
                data=exportar_excel(df_reporte_hhmm, "Horas"),
                file_name=f"reporte_horas_{desde_reporte}_a_{hasta_reporte}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    st.divider()
    st.subheader("Descargar plantilla para cargar horas")
    st.caption("Descarga la plantilla, llénala (una fila por día trabajado por empleado) y súbela abajo. El empleado se identifica por su número de identificación.")
    st.download_button(
        "⬇️ Descargar plantilla de Excel",
        data=plantilla_horas(),
        file_name="plantilla_horas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.divider()
    st.subheader("Cargar horas desde Excel")
    archivo_horas = st.file_uploader("Selecciona el archivo .xlsx", type=["xlsx"], key="upload_horas")

    if archivo_horas is not None:
        try:
            df_carga = pd.read_excel(archivo_horas)
        except Exception as e:
            st.error(f"No se pudo leer el archivo: {e}")
            df_carga = None

        if df_carga is not None:
            columnas_esperadas = {
                "identificacion_empleado", "fecha", "hora_entrada", "hora_salida",
                "horas_extra_diurna", "horas_extra_nocturna", "horas_extra_dominical_festivo",
                "horas_extra_dominical_festivo_nocturna", "horas_recargo_nocturno", "horas_recargo_dominical",
                "horas_recargo_dominical_festivo_nocturno", "horas_descuento", "tipo_descuento", "bonificacion", "deduccion", "observacion"
            }
            faltantes = columnas_esperadas - set(df_carga.columns)
            if faltantes:
                st.error(f"Al archivo le faltan estas columnas: {', '.join(faltantes)}. Usa la plantilla como base.")
            else:
                st.write("Vista previa:")
                st.dataframe(df_carga, use_container_width=True, hide_index=True)

                if st.button("✅ Confirmar carga de estas horas"):
                    insertados, errores = 0, []
                    with get_connection() as conn:
                        for i, fila in df_carga.iterrows():
                            identificacion = str(fila.get("identificacion_empleado", "")).strip()
                            if not identificacion or identificacion.lower() == "nan":
                                continue

                            emp_id = identificacion_a_id.get(identificacion)
                            if emp_id is None:
                                errores.append(f"Fila {i + 2}: no existe un empleado activo con identificación '{identificacion}'.")
                                continue

                            try:
                                hora_ent = str(fila.get("hora_entrada", "")).strip()
                                hora_sal = str(fila.get("hora_salida", "")).strip()
                                fecha_fila = str(fila.get("fecha", "")).strip()
                                horas_desc = texto_hhmm_a_decimal(fila.get("horas_descuento", 0))

                                horas_normales_fila = 0.0
                                if hora_ent and hora_sal and hora_ent.lower() != "nan" and hora_sal.lower() != "nan":
                                    h_ent = datetime.strptime(hora_ent[:5], "%H:%M")
                                    h_sal = datetime.strptime(hora_sal[:5], "%H:%M")
                                    tiempo_neto = max(0, (h_sal - h_ent).total_seconds() / 3600) - horas_desc
                                    horas_normales_fila = max(0, min(tiempo_neto, horas_normales_max))

                                tipo_desc = str(fila.get("tipo_descuento", "")).strip()
                                tipo_desc = None if (not tipo_desc or tipo_desc.lower() == "nan") else tipo_desc

                                execute(conn, """
                                    INSERT INTO horas (empleado_id, fecha, hora_entrada, hora_salida, horas_normales,
                                    horas_extra_diurna, horas_extra_nocturna, horas_extra_dominical_festivo,
                                    horas_extra_dominical_festivo_nocturna, horas_recargo_nocturno, horas_recargo_dominical,
                                    horas_recargo_dominical_festivo_nocturno, horas_descuento, tipo_descuento, bonificacion, deduccion, observacion)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    emp_id, fecha_fila, hora_ent, hora_sal, round(horas_normales_fila, 4),
                                    texto_hhmm_a_decimal(fila.get("horas_extra_diurna", 0)),
                                    texto_hhmm_a_decimal(fila.get("horas_extra_nocturna", 0)),
                                    texto_hhmm_a_decimal(fila.get("horas_extra_dominical_festivo", 0)),
                                    texto_hhmm_a_decimal(fila.get("horas_extra_dominical_festivo_nocturna", 0)),
                                    texto_hhmm_a_decimal(fila.get("horas_recargo_nocturno", 0)),
                                    texto_hhmm_a_decimal(fila.get("horas_recargo_dominical", 0)),
                                    texto_hhmm_a_decimal(fila.get("horas_recargo_dominical_festivo_nocturno", 0)),
                                    horas_desc, tipo_desc,
                                    float(fila.get("bonificacion", 0) or 0),
                                    float(fila.get("deduccion", 0) or 0),
                                    str(fila.get("observacion", "")).strip(),
                                ))
                                insertados += 1
                            except Exception as e:
                                errores.append(f"Fila {i + 2} ({identificacion}): {e}")

                    if insertados:
                        st.success(f"Se cargaron {insertados} registro(s) de horas correctamente.")
                    if errores:
                        st.warning("Algunas filas no se pudieron cargar:\n\n" + "\n".join(errores))
