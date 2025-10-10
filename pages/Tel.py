import pandas as pd
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
import base64
import unicodedata

st.set_page_config(page_title="Equipos Telefónicos", layout="wide")
# ------------------ estilos ------------------
st.markdown("""
<style> 
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {padding-top: 0rem !important;}
    body {background-color: #0E1117; color: white;}
    
    div[data-testid="stButton"] > button {
    height: 45px;
    font-size: 20px;
    background-color: #0E1117
    border-radius: 10px;
    color: white;
    border: none;
}
div[data-testid="stButton"] > button:hover {
    background-color: #0056b3;
}
    .map-button-link {
        display: block;
        text-decoration: none;
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
        border-radius: 9px;
        margin-bottom: 15px;
    }
    .map-button-link:hover {
        transform: scale(1.03);
        box-shadow: 0px 0px 15px rgba(0, 166, 255, 0.7);
    }
    .map-button-link img {
        width: 100%;
        border-radius: 8px;
        display: block;
    }
    h1 { margin-top: 0 !important; margin-bottom: 10px; font-size: 20px !important; }
    .img-top-right { position: absolute; top: 15px; right: 5px; width: 100px; }
    .metric-box { display: flex; justify-content: center; align-items: center; background-color: #111827; padding: 5px; border-radius: 10px; font-size: 18px; font-weight: bold; color: white; border: 1px solid #2D3748; margin-top: 30px; }
    .estado-link { color: #00A6FF; text-decoration: none; font-weight: bold; cursor:pointer; }
            
    .img-top-r { position: absolute; top: 0px; right: 100px; width: 150px; }
    .metric-box { display: flex; justify-content: rigth; align-items: center; background-color: #111827; padding: 5px; border-radius: 10px; font-size: 18px; font-weight: bold; color: white; border: 1px solid #2D3748; margin-top: 30px; }
    .estado-link { color: #00A6FF; text-decoration: none; font-weight: bold; cursor:pointer; }
</style>

<img src="https://i0.wp.com/web.metricamovil.com/wp-content/uploads/cropped-Logotipo-Me%CC%81trica-Mo%CC%81vil.webp?fit=200%2C125&ssl=1" class="img-top-right">
<img src="https://download.logo.wine/logo/Telcel/Telcel-Logo.wine.png" class="img-top-r">
""", unsafe_allow_html=True)

# ------------------ navegación ------------------
esp1, menu1, menu2, esp2 = st.columns([.01, 2, 2, 4])
with menu1:
    if st.button("💻Equipos de computo", use_container_width=True):
        st.switch_page("app.py")
with menu2:
    if st.button("📱Equipos teléfonicos", use_container_width=True):
        st.session_state.page = "reportes"

# ------------------ Google Sheets ------------------
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1hUDaaqzQ_LKT71YTTwwyRYvvg1itNm46Dhezlz-5Jdk/edit"
SHEET_TABLE = "Hoja 1"  # ajusta si tu pestaña tiene otro nombre

@st.cache_data(ttl=300)
def load_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive.readonly"]
        # Usa st.secrets para mayor seguridad
        creds_dict = st.secrets["google_credentials"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        ws = client.open_by_url(SPREADSHEET_URL).worksheet(SHEET_TABLE)

        values = ws.get_all_values()
        if not values or len(values) <= 3:
            return pd.DataFrame()

        # Advertencia: Esta lógica es frágil. Si el formato de la hoja cambia, fallará.
        # Se recomienda tener un formato de tabla estándar con encabezados en la primera fila.
        header_row_index = 3
        raw_headers = values[header_row_index]
        headers = [h if str(h).strip() != "" else f"col{i}" for i, h in enumerate(raw_headers)]
        data = values[header_row_index + 1:]

        df = pd.DataFrame(data, columns=headers)
        df = df.fillna("").astype(str)
        return df
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return pd.DataFrame()

def normalize_text(s):
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s

# ------------------ cargar datos ------------------
df_table = load_data()
col_normal_map = {normalize_text(col): col for col in df_table.columns}
estatus_key = None
for key in ["estatus", "estado", "status"]:
    if key in col_normal_map:
        estatus_key = col_normal_map[key]
        break

if estatus_key:
    mask_activa = df_table[estatus_key].astype(str).str.upper().str.strip() == "ACTIVA"
    df_table = df_table[mask_activa]
else:
    st.warning("No se encontró una columna con nombre 'ESTATUS' (o similar). No se aplicó filtro 'ACTIVA'.")

# ------------------ eliminar columnas indeseadas ------------------
for col in ["IMAGEN", "*", ""]:
    if col in df_table.columns:
        df_table = df_table.drop(columns=[col])

# ------------------ seleccionar solo columnas deseadas ------------------
columnas_deseadas = [
    "Región", "Número de Teléfono", "Plan Y Servicios contratados", "Ciudad", "Estado",
    "Empleado", "Puesto", "Departamento", "Marca", "Modelo", "IMEI", "N° SERIE"
]

normalized_to_real = {normalize_text(c): c for c in df_table.columns}
matched_columns = []
for desired in columnas_deseadas:
    nd = normalize_text(desired)
    if nd in normalized_to_real:
        matched_columns.append(normalized_to_real[nd])
    else:
        for nreal, realcol in normalized_to_real.items():
            if nd in nreal or nreal in nd:
                matched_columns.append(realcol)
                break

matched_columns = list(dict.fromkeys(matched_columns))
if len(matched_columns) == 0:
    st.info("No se encontraron coincidencias exactas para las columnas deseadas. Se mostrarán todas las columnas.")
    matched_columns = df_table.columns.tolist()

df_filtrado = df_table[matched_columns].copy()

st.markdown("# ")
search_query = st.text_input("🔍 Buscar", placeholder="Escribe aquí para buscar...")

if search_query:
    search_series = df_filtrado.apply(lambda row: " ".join(row.values.astype(str)), axis=1)
    mask = search_series.str.contains(search_query, case=False, na=False)
    df_filtrado = df_filtrado[mask]

# ------------------ AgGrid ------------------
gb = GridOptionsBuilder.from_dataframe(df_filtrado)
gb.configure_default_column(editable=False, resizable=False, minWidth=80)
gb.configure_selection(selection_mode="single", use_checkbox=False)
gb.configure_grid_options(domLayout="normal", suppressHorizontalScroll=False, rowHeight=30)
gridOptions = gb.build()

custom_css = {
    ".ag-root-wrapper": {"background-color": "transparent !important", "border": "1px solid #333e5d !important"},
    ".ag-header, .ag-row, .ag-cell": {"background-color": "transparent !important", "color": "white !important", "border": "1px solid #333e5d !important", "font-size": "11px !important"},
    ".ag-header-cell-text": {"color": "white !important", "font-weight": "bold !important"}
}

AgGrid(
    df_filtrado, gridOptions=gridOptions, update_mode=GridUpdateMode.NO_UPDATE, editable=False,
    fit_columns_on_grid_load=False, allow_unsafe_jscode=False, theme="streamlit", height=700,
    data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
    custom_css=custom_css
)
