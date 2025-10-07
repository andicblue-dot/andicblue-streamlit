# andicblue_streamlit_gs.py
# Streamlit app para AndicBlue (Google Sheets backend)
# Requisitos: colocar credenciales de la cuenta de servicio en Streamlit Secrets
#             y subir este archivo + requirements.txt a un repo de GitHub para deploy en Streamlit Cloud.

import streamlit as st
import pandas as pd
import gspread
import os
from google.oauth2.service_account import Credentials
from datetime import datetime

st.set_page_config(page_title="AndicBlue - Pedidos & Flujo", page_icon="🫐", layout="wide")

st.title("Sistema de Gestión AndicBlue 🍇")

# ---------------------------
# CONFIG
# ---------------------------
SHEET_NAME = "andicblue_pedidos"  # Nombre de la hoja de cálculo en Google Sheets

PRODUCTOS = {
    "Docena de Arándanos 125g": 52500,
    "Arandanos_125g": 5000,
    "Arandanos_250g": 10000,
    "Arandanos_500g": 20000,
    "Kilo_industrial": 30000,
    "Mermelada_azucar": 16000,
    "Mermelada_sin_azucar": 20000,
}

DOMICILIO_COST = 3000  # COP

# ---------------------------
# AUTH & CLIENT
# ---------------------------
if "gcp_service_account" not in st.secrets:
    st.error("⚠️ Falta la sección 'gcp_service_account' en Streamlit Secrets. Sube las credenciales JSON antes de continuar.")
    st.stop()

creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=[
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
])
gc = gspread.authorize(creds)

# ---------------------------
# UTILIDADES
# ---------------------------
def open_or_create_spreadsheet(name):
    try:
        ss = gc.open(name)
    except Exception:
        ss = gc.create(name)
    return ss

def ensure_worksheet(ss, title, headers):
    try:
        ws = ss.worksheet(title)
    except Exception:
        ws = ss.add_worksheet(title=title, rows="1000", cols="20")
    vals = ws.row_values(1)
    if not vals or len(vals) < len(headers) or vals[:len(headers)] != headers:
        ws.delete_rows(1) if ws.row_count >= 1 and any(ws.row_values(1)) else None
        ws.insert_row(headers, index=1)
    return ws

ss = open_or_create_spreadsheet(SHEET_NAME)

# Encabezados
HEAD_CLIENTES = ["ID Cliente", "Nombre", "Telefono", "Direccion"]
HEAD_PEDIDOS = [
    "ID Pedido", "Fecha", "ID Cliente", "Nombre Cliente", "Productos_detalle",
    "Subtotal_productos", "Monto_domicilio", "Total_pedido", "Estado",
    "Medio_pago", "Monto_pagado", "Saldo_pendiente"
]
HEAD_INVENTARIO = ["Producto", "Stock"]
HEAD_FLUJO = [
    "Fecha", "ID Pedido", "Cliente", "Medio_pago",
    "Ingreso_productos_recibido", "Ingreso_domicilio_recibido", "Saldo_pendiente_total"
]
HEAD_GASTOS = ["Fecha", "Concepto", "Monto"]

ws_clientes = ensure_worksheet(ss, "Clientes", HEAD_CLIENTES)
ws_pedidos = ensure_worksheet(ss, "Pedidos", HEAD_PEDIDOS)
ws_inventario = ensure_worksheet(ss, "Inventario", HEAD_INVENTARIO)
ws_flujo = ensure_worksheet(ss, "FlujoCaja", HEAD_FLUJO)
ws_gastos = ensure_worksheet(ss, "Gastos", HEAD_GASTOS)

# Inicializar inventario
inv_df = pd.DataFrame(ws_inventario.get_all_records())
if inv_df.empty:
    for p in PRODUCTOS.keys():
        ws_inventario.append_row([p, 0])
    inv_df = pd.DataFrame(ws_inventario.get_all_records())

# ---------------------------
# FUNCIONES AUXILIARES
# ---------------------------
def df_from_ws(ws):
    return pd.DataFrame(ws.get_all_records())

def append_row_ws(ws, row):
    ws.append_row(row)

def next_id_for_sheet(ws, id_col):
    df = df_from_ws(ws)
    if df.empty or id_col not in df.columns:
        return 1
    existing = df[id_col].dropna().astype(int).tolist()
    return max(existing) + 1 if existing else 1

def add_cliente(nombre, telefono, direccion):
    cid = next_id_for_sheet(ws_clientes, "ID Cliente")
    append_row_ws(ws_clientes, [cid, nombre, telefono, direccion])
    return cid

def get_inventory_map():
    df = df_from_ws(ws_inventario)
    return {r["Producto"]: int(r["Stock"]) for _, r in df.iterrows()}

def update_inventory_after_order(products_qty: dict):
    inv = df_from_ws(ws_inventario)
    for prod, qty in products_qty.items():
        idxs = inv.index[inv["Producto"] == prod].tolist()
        if not idxs:
            append_row_ws(ws_inventario, [prod, max(0, -qty)])
            inv = df_from_ws(ws_inventario)
            continue
        idx = idxs[0]
        current = int(inv.at[idx, "Stock"])
        new_stock = max(0, current - int(qty))
        ws_inventario.update_cell(idx + 2, 2, new_stock)

def create_order(cliente_id, productos_cant: dict, domicilio_bool: bool, estado_inicial: str):
    clientes_df = df_from_ws(ws_clientes)
    if clientes_df.empty or cliente_id not in clientes_df["ID Cliente"].values:
        raise ValueError("ID cliente no encontrado")
    client_name = clientes_df.loc[clientes_df["ID Cliente"] == cliente_id, "Nombre"].values[0]

    inv_map = get_inventory_map()
    for p, q in productos_cant.items():
        if q <= 0:
            continue
        if p not in inv_map:
            raise ValueError(f"Producto no existe en inventario: {p}")
        if inv_map[p] < q:
            raise ValueError(f"Stock insuficiente para {p}: disponible {inv_map[p]}, pedido {q}")

    subtotal = 0
    detalle = []
    for p, q in productos_cant.items():
        precio = PRODUCTOS.get(p) if p in PRODUCTOS else 0
        subtotal += precio * q
        if q > 0:
            detalle.append(f"{p} x{q} (@{precio})")
    domicilio_monto = DOMICILIO_COST if domicilio_bool else 0
    total_pedido = subtotal + domicilio_monto

    pid = next_id_for_sheet(ws_pedidos, "ID Pedido")
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    productos_detalle_str = " | ".join(detalle) if detalle else ""

    append_row_ws(ws_pedidos, [
        pid, fecha, cliente_id, client_name, productos_detalle_str,
        subtotal, domicilio_monto, total_pedido, estado_inicial, "", 0, subtotal
    ])
    update_inventory_after_order(productos_cant)
    return pid

def mark_order_delivered(order_id, medio_pago, monto_pagado):
    dfp = df_from_ws(ws_pedidos)
    if dfp.empty or order_id not in dfp["ID Pedido"].values:
        raise ValueError("Pedido no encontrado")
    row_idx = dfp.index[dfp["ID Pedido"] == order_id].tolist()[0] + 2
    row = dfp.loc[dfp["ID Pedido"] == order_id].iloc[0]

    subtotal_products = float(row["Subtotal_productos"])
    domicilio_monto = float(row["Monto_domicilio"])
    total_pedido = float(row["Total_pedido"])

    monto = float(monto_pagado)
    prod_paid = min(monto, subtotal_products)
    rem = max(0.0, monto - prod_paid)
    domicilio_paid = min(rem, domicilio_monto)
    saldo_total = (subtotal_products - prod_paid) + (domicilio_monto - domicilio_paid)

    ws_pedidos.update_cell(row_idx, HEAD_PEDIDOS.index("Estado") + 1, "Entregado")
    ws_pedidos.update_cell(row_idx, HEAD_PEDIDOS.index("Medio_pago") + 1, medio_pago)
    ws_pedidos.update_cell(row_idx, HEAD_PEDIDOS.index("Monto_pagado") + 1, monto)
    ws_pedidos.update_cell(row_idx, HEAD_PEDIDOS.index("Saldo_pendiente") + 1, saldo_total)

    cliente_nombre = row["Nombre Cliente"]
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    append_row_ws(ws_flujo, [
        fecha, order_id, cliente_nombre, medio_pago,
        prod_paid, domicilio_paid, saldo_total
    ])
    return {"prod_paid": prod_paid, "domicilio_paid": domicilio_paid, "saldo_total": saldo_total}

def add_expense(concepto, monto):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    append_row_ws(ws_gastos, [fecha, concepto, monto])

# ---------------------------
# INTERFAZ STREAMLIT
# ---------------------------
st.markdown("Aplicación desplegada en Streamlit Cloud — datos guardados en Google Sheets")

menu = st.sidebar.selectbox("Selecciona módulo", ["Clientes", "Pedidos", "Inventario", "Entregas/Pagos", "Flujo & Gastos", "Reportes"])
st.write("---")

# ---------- CLIENTES ----------
if menu == "Clientes":
    st.header("Clientes")
    dfc = df_from_ws(ws_clientes)
    st.dataframe(dfc, use_container_width=True)

    with st.form("form_add_cliente"):
        st.subheader("Agregar nuevo cliente")
        n = st.text_input("Nombre completo")
        t = st.text_input("Teléfono")
        d = st.text_input("Dirección")
        s = st.form_submit_button("Agregar cliente")
        if s:
            if not n:
                st.error("⚠️ Nombre requerido")
            else:
                cid = add_cliente(n, t, d)
                st.success(f"Cliente agregado con ID {cid}")

# ---------- PEDIDOS ----------
elif menu == "Pedidos":
    st.header("Registrar pedido")
    dfc = df_from_ws(ws_clientes)
    if dfc.empty:
        st.warning("No hay clientes registrados.")
    else:
        with st.form("form_new_order"):
            cliente_sel = st.selectbox("Cliente", dfc["ID Cliente"].astype(str) + " - " + dfc["Nombre"])
            cliente_id = int(cliente_sel.split(" - ")[0])
            productos_cant = {}
            for p, price in PRODUCTOS.items():
                q = st.number_input(f"{p} (COP {price})", min_value=0, step=1, value=0)
                productos_cant[p] = int(q)
            domicilio = st.checkbox(f"Incluir domicilio ({DOMICILIO_COST} COP)", value=False)
            estado_inicial = st.radio("Estado del pedido", ["Pendiente", "Entregado"], horizontal=True)
            submit_order = st.form_submit_button("Registrar pedido")
            if submit_order:
                try:
                    pid = create_order(cliente_id, productos_cant, domicilio, estado_inicial)
                    st.success(f"Pedido registrado con ID {pid} — Estado: {estado_inicial}")
                except Exception as e:
                    st.error(f"No se pudo crear pedido: {e}")

# ---------- INVENTARIO ----------
elif menu == "Inventario":
    st.header("Inventario")
    df_inv = df_from_ws(ws_inventario)
    st.dataframe(df_inv, use_container_width=True)

    with st.form("form_update_inventory"):
        prod = st.selectbox("Producto", df_inv["Producto"].tolist())
        nueva = st.number_input("Ingresar nueva cantidad (sumará al stock actual)", min_value=0, step=1, value=0)
        submit_inv = st.form_submit_button("Actualizar stock")
        if submit_inv:
            idx = df_inv.index[df_inv["Producto"] == prod].tolist()[0] + 2
            current = int(ws_inventario.cell(idx, 2).value or 0)
            ws_inventario.update_cell(idx, 2, current + nueva)
            st.success(f"Stock actualizado: {prod} = {current + nueva}")

# ---------- ENTREGAS/PAGOS ----------
elif menu == "Entregas/Pagos":
    st.header("Registrar entrega y pago")
    dfp = df_from_ws(ws_pedidos)
    st.dataframe(dfp, use_container_width=True)
    with st.form("form_deliver"):
        idp = st.number_input("ID Pedido", min_value=1, step=1)
        medio = st.selectbox("Medio de pago", ["Efectivo", "Transferencia", "Crédito", "Pago parcial"])
        monto = st.number_input("Monto pagado (COP)", min_value=0, step=1000, value=0)
        submit_deliver = st.form_submit_button("Registrar entrega")
        if submit_deliver:
            try:
                res = mark_order_delivered(int(idp), medio, float(monto))
                st.success(f"Pedido {idp} entregado. Productos: {res['prod_paid']}, Domicilio: {res['domicilio_paid']}, Saldo: {res['saldo_total']}")
            except Exception as e:
                st.error(f"Error: {e}")

# ---------- FLUJO & GASTOS ----------
elif menu == "Flujo & Gastos":
    st.header("Flujo de caja e ingresos")
    df_flujo = df_from_ws(ws_flujo)
    df_gastos = df_from_ws(ws_gastos)

    total_prod = df_flujo["Ingreso_productos_recibido"].sum() if not df_flujo.empty else 0
    total_domicilios = df_flujo["Ingreso_domicilio_recibido"].sum() if not df_flujo.empty else 0
    total_gastos = df_gastos["Monto"].sum() if not df_gastos.empty else 0
    saldo_real = total_prod - total_gastos

    st.subheader("Resumen general")
    st.metric("Ingresos por productos", f"{int(total_prod):,} COP".replace(",", "."))
    st.metric("Ingresos por domicilios", f"{int(total_domicilios):,} COP".replace(",", "."))
    st.metric("Gastos", f"-{int(total_gastos):,} COP".replace(",", "."))
    st.metric("Saldo disponible", f"{int(saldo_real):,} COP".replace(",", "."))

    st.write("---")
    st.subheader("Agregar nuevo gasto")
    with st.form("form_gasto"):
        concepto = st.text_input("Concepto")
        monto_g = st.number_input("Monto (COP)", min_value=0, step=1000)
        add_gasto = st.form_submit_button("Agregar gasto")
        if add_gasto:
            add_expense(concepto, float(monto_g))
            st.success("Gasto agregado ✅")
            st.experimental_rerun()

    st.write("---")
    st.subheader("Últimos registros de flujo")
    st.dataframe(df_flujo.tail(50), use_container_width=True)

    st.subheader("Últimos gastos")
    st.dataframe(df_gastos.tail(50), use_container_width=True)

# ---------- REPORTES ----------
elif menu == "Reportes":
    st.header("Reportes de pedidos")
    st.dataframe(df_from_ws(ws_pedidos), use_container_width=True)

st.write("---")
st.caption("Nota: Los montos por domicilio se manejan de forma separada al ingreso principal.")
