# 🍇 AndicBlue — Sistema de Pedidos, Inventario y Flujo de Caja

**AndicBlue** es una aplicación creada con **Streamlit** y conectada a **Google Sheets**, diseñada para gestionar los pedidos, clientes, inventario y flujo de caja del cultivo de arándanos AndicBlue, producido en tierras volcánicas de los Andes colombianos.

---

## 🚀 Funcionalidades principales

### 🧾 Gestión de Clientes
- Registro automático de clientes nuevos (nombre, teléfono, dirección).
- Cada cliente tiene un ID único.

### 📦 Gestión de Pedidos
- Registro de pedidos con las presentaciones de arándanos y mermeladas:
  - Docena de Arándanos 125g – 52,500 COP  
  - Arándanos 125g – 5,000 COP  
  - Arándanos 250g – 10,000 COP  
  - Arándanos 500g – 20,000 COP  
  - Kilo Arándanos industrial – 30,000 COP  
  - Mermelada con azúcar – 16,000 COP  
  - Mermelada sin azúcar – 20,000 COP  
- Cálculo automático del total del pedido.  
- Opción de domicilio (3,000 COP o gratis).  
- Registro del medio de pago (efectivo, transferencia, crédito o parcial).  
- Registro de saldo pendiente si aplica.  

### 🧮 Control de Inventario
- Stock inicial configurable por presentación.  
- Descuento automático al registrar pedidos.  
- Alerta cuando el stock llega a 0 o es insuficiente.

### 💵 Flujo de Caja
- Cálculo automático de ingresos:
  - Por productos (efectivo, transferencia, crédito).  
  - Por **domicilios**, mostrados **por separado** (no incluidos en el total de ingresos).  
- Registro manual de gastos (fecha, concepto, monto).  
- Cálculo del **saldo real en caja = Ingresos por productos – Gastos**.  
- Visualización gráfica de la evolución del flujo de caja.

---

## ⚙️ Tecnologías utilizadas
- **Python 3**
- **Streamlit**
- **Google Sheets API** (vía `gspread` y `google-auth`)
- **pandas**

---

## ☁️ Despliegue en Streamlit Cloud

1. Sube este repositorio a tu cuenta de **GitHub**.  
2. Entra a [Streamlit Cloud](https://share.streamlit.io) y conéctalo con tu cuenta de GitHub.  
3. Selecciona este repositorio y el archivo principal `andicblue_streamlit_gs.py`.  
4. En el apartado **Secrets**, agrega tu archivo de credenciales de Google Sheets (`andicblue-credentials.json`) en formato seguro:  

   ```toml
   [google]
   type = "service_account"
   project_id = "andicblue-pedidos"
   private_key_id = "XXXXXXXXXXXX"
   private_key = "-----BEGIN PRIVATE KEY-----\nXXXX\n-----END PRIVATE KEY-----\n"
   client_email = "andicblue-bot@andicblue-pedidos.iam.gserviceaccount.com"
   client_id = "XXXXXXXXXXXXX"
