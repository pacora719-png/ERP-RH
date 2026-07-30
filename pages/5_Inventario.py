import streamlit as st
import pandas as pd
from datetime import date
from database import get_connection, get_ubicaciones

st.set_page_config(page_title="Inventario", page_icon="📦", layout="wide")

if not st.session_state.get("autenticado"):
    st.warning("Por favor inicia sesión desde la página principal.")
    st.stop()

st.title("📦 Inventario")

ubicaciones = get_ubicaciones()
if not ubicaciones:
    st.warning("Todavía no has creado ninguna ubicación/sede. Ve a **Configuración** para agregar al menos una.")
    st.stop()
ubicacion_nombres = {u["id"]: u["nombre"] for u in ubicaciones}

tab_lista, tab_nuevo, tab_movimiento = st.tabs(["📋 Productos", "➕ Nuevo producto", "🔄 Registrar movimiento"])

with tab_lista:
    with get_connection() as conn:
        df = pd.read_sql_query("""
            SELECT i.*, u.nombre AS ubicacion_nombre
            FROM inventario i LEFT JOIN ubicaciones u ON i.ubicacion_id = u.id
            ORDER BY i.nombre
        """, conn)

    if df.empty:
        st.info("Todavía no hay productos. Agrega el primero en la pestaña 'Nuevo producto'.")
    else:
        df["alerta"] = df["stock_actual"] <= df["stock_minimo"]
        bajos = df[df["alerta"]]
        if not bajos.empty:
            st.warning(f"⚠️ {len(bajos)} producto(s) por debajo del stock mínimo: " + ", ".join(bajos["nombre"].tolist()))

        st.dataframe(
            df[["id", "nombre", "categoria", "unidad", "stock_actual", "stock_minimo", "costo_unitario", "ubicacion_nombre"]],
            use_container_width=True,
            hide_index=True
        )

        st.divider()
        prod_id = st.selectbox(
            "Editar / eliminar producto",
            df["id"].tolist(),
            format_func=lambda x: df[df["id"] == x]["nombre"].values[0]
        )
        prod = df[df["id"] == prod_id].iloc[0]

        with st.form("editar_producto"):
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre", prod["nombre"])
                categoria = st.text_input("Categoría", prod["categoria"] or "")
                unidad = st.text_input("Unidad (kg, unidad, litro...)", prod["unidad"] or "")
            with col2:
                stock_minimo = st.number_input("Stock mínimo", value=float(prod["stock_minimo"] or 0))
                costo_unitario = st.number_input("Costo unitario", value=float(prod["costo_unitario"] or 0))
                ids_ubicacion = list(ubicacion_nombres.keys())
                idx_actual = ids_ubicacion.index(prod["ubicacion_id"]) if prod["ubicacion_id"] in ids_ubicacion else 0
                ubicacion_id = st.selectbox("Ubicación", ids_ubicacion, index=idx_actual,
                                             format_func=lambda x: ubicacion_nombres[x])

            col_a, col_b = st.columns(2)
            guardar = col_a.form_submit_button("💾 Guardar cambios")
            eliminar = col_b.form_submit_button("🗑️ Eliminar producto")

        if guardar:
            with get_connection() as conn:
                conn.execute("""
                    UPDATE inventario SET nombre=?, categoria=?, unidad=?, stock_minimo=?,
                    costo_unitario=?, ubicacion_id=? WHERE id=?
                """, (nombre, categoria, unidad, stock_minimo, costo_unitario, ubicacion_id, int(prod_id)))
            st.success("Producto actualizado.")
            st.rerun()

        if eliminar:
            with get_connection() as conn:
                conn.execute("DELETE FROM inventario WHERE id=?", (int(prod_id),))
            st.success("Producto eliminado.")
            st.rerun()

with tab_nuevo:
    with st.form("nuevo_producto", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre *")
            categoria = st.text_input("Categoría")
            unidad = st.text_input("Unidad (kg, unidad, litro...)")
        with col2:
            stock_inicial = st.number_input("Stock inicial", min_value=0.0, step=1.0)
            stock_minimo = st.number_input("Stock mínimo", min_value=0.0, step=1.0)
            costo_unitario = st.number_input("Costo unitario", min_value=0.0, step=100.0)
            ubicacion_id = st.selectbox("Ubicación", list(ubicacion_nombres.keys()),
                                         format_func=lambda x: ubicacion_nombres[x])

        crear = st.form_submit_button("➕ Agregar producto")

    if crear:
        if not nombre:
            st.error("El nombre es obligatorio.")
        else:
            with get_connection() as conn:
                conn.execute("""
                    INSERT INTO inventario (nombre, categoria, unidad, stock_actual, stock_minimo, costo_unitario, ubicacion_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (nombre, categoria, unidad, stock_inicial, stock_minimo, costo_unitario, ubicacion_id))
            st.success(f"Producto '{nombre}' agregado.")

with tab_movimiento:
    with get_connection() as conn:
        productos_df = pd.read_sql_query("SELECT * FROM inventario ORDER BY nombre", conn)

    if productos_df.empty:
        st.info("Agrega primero un producto en la pestaña 'Nuevo producto'.")
    else:
        with st.form("registrar_movimiento", clear_on_submit=True):
            producto_id = st.selectbox(
                "Producto",
                productos_df["id"].tolist(),
                format_func=lambda x: productos_df[productos_df["id"] == x]["nombre"].values[0]
            )
            tipo = st.selectbox("Tipo de movimiento", ["Entrada", "Salida"])
            cantidad = st.number_input("Cantidad", min_value=0.01, step=1.0)
            motivo = st.text_input("Motivo (opcional)")
            fecha_mov = st.date_input("Fecha", value=date.today())
            guardar_mov = st.form_submit_button("💾 Registrar movimiento")

        if guardar_mov:
            stock_actual = float(productos_df[productos_df["id"] == producto_id]["stock_actual"].values[0])
            nuevo_stock = stock_actual + cantidad if tipo == "Entrada" else stock_actual - cantidad

            if nuevo_stock < 0:
                st.error("No hay suficiente stock para esta salida.")
            else:
                with get_connection() as conn:
                    conn.execute("""
                        INSERT INTO movimientos_inventario (producto_id, fecha, tipo, cantidad, motivo)
                        VALUES (?, ?, ?, ?, ?)
                    """, (int(producto_id), str(fecha_mov), tipo, cantidad, motivo))
                    conn.execute("UPDATE inventario SET stock_actual=? WHERE id=?", (nuevo_stock, int(producto_id)))
                st.success(f"Movimiento registrado. Nuevo stock: {nuevo_stock}")
