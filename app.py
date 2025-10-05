import json
import pandas as pd
import streamlit as st
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
import base64

st.set_page_config(page_title="Inventario", layout="wide")

st.markdown("""
<style> 
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {padding-top: 0rem !important;}
    body {background-color: #0E1117; color: white;}
    
    h1 {
        margin-top: 0 !important; 
        margin-bottom: 10px; 
        font-size: 20px !important;
    }
    .img-top-right {
        position: absolute; 
        top: 15px; 
        right: 5px; 
        width: 100px;
    }
    div[data-testid="stHorizontalBlock"] button {
        font-size: 14px !important;        
        padding: 0.05rem 0.5rem !important;      
    }
    .metric-box {
        display: flex;
        justify-content: center;
        align-items: center;
        background-color: #111827;
        padding: 5px; 
        border-radius: 10px;
        font-size: 18px; 
        font-weight: bold;
        color: white;
        border: 1px solid #2D3748;
        margin-top: 30px;
    }
    .map-container {
      width: 100%;
    }
    .map-column {
      width: 48%;
      float: left;
      margin: 1%;
    }
    .map-column img {
      width: 100%;
      margin-bottom: 15px;
      border-radius: 8px;
    }
</style>

<img src="https://i0.wp.com/web.metricamovil.com/wp-content/uploads/cropped-Logotipo-Me%CC%81trica-Mo%CC%81vil.webp?fit=200%2C125&ssl=1" class="img-top-right">
""", unsafe_allow_html=True)

st.markdown("<h1>Inventario de Equipos de Computo Asignados</h1>", unsafe_allow_html=True)

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1WSxtSCoKAZxXjuUKSN_YxuIBa9uEQtWYGRsK_UcWYMA/edit?gid=0#gid=0"
SHEET_GRAPH = "Web"
SHEET_TABLE = "Equipos"

@st.cache_data(ttl=1000)
def load_data():
    try:
        sa_info = st.secrets.get("gcp_service_account")
        if sa_info is None:
            raise Exception("No se encontró 'gcp_service_account' en st.secrets")

        # si guardaste el JSON como string en st.secrets, conviértelo a dict
        if isinstance(sa_info, str):
            sa_info = json.loads(sa_info)

        client = gspread.service_account_from_dict(sa_info)
        spreadsheet = client.open_by_url(SPREADSHEET_URL)

        df_graph = pd.DataFrame(spreadsheet.worksheet(SHEET_GRAPH).get_all_records())
        df_table = pd.DataFrame(spreadsheet.worksheet(SHEET_TABLE).get_all_records())
        df_table = df_table.fillna("").astype(str)

        return df_graph, df_table
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return pd.DataFrame(), pd.DataFrame()

def img_to_base64(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        return None

df_graph, df_table = load_data()

col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("<div style='margin-top:15px;'>Equipos activos en:</div>", unsafe_allow_html=True)
    image_paths = ["assets/1.png", "assets/2.png", "assets/3.png", "assets/4.png", "assets/5.png", "assets/6.png"]

    st.markdown("")
    st.markdown("")
    col_a_html = '<div class="map-column">'
    for path in image_paths[:3]: 
        b64_image = img_to_base64(path)
        if b64_image:
            col_a_html += f'<img src="data:image/png;base64,{b64_image}">'
    col_a_html += '</div>'

    col_b_html = '<div class="map-column">'
    for path in image_paths[3:]: 
        b64_image = img_to_base64(path)
        if b64_image:
            col_b_html += f'<img src="data:image/png;base64,{b64_image}">'
    col_b_html += '</div>'

    final_html = f'<div class="map-container">{col_a_html}{col_b_html}</div>'
    st.markdown(final_html, unsafe_allow_html=True)

if not df_graph.empty:
    try:
        df_graph.columns = df_graph.columns.str.strip()
        if "Etiqueta" in df_graph.columns and "Equipos" in df_graph.columns:
            conteo = df_graph.groupby("Etiqueta")["Equipos"].sum().reset_index()
            fig = px.pie(
                conteo,
                names="Etiqueta",
                values="Equipos",
                hole=0.50,
                color_discrete_sequence=["#3BB5D4", "#003F7D", "#00A6FF", "#DFFC9D", "#385368", "#97D4DA", "#E68E8E", "#D85959"]
            )
            fig.update_traces(
                textinfo="percent+label",
                textfont_size=16,
                marker=dict(line=dict(color="#0E1117", width=2))
            )
            fig.update_layout(
                autosize=False,
                margin=dict(t=30, b=40, l=100, r=0),
                paper_bgcolor="#0E1117",
                plot_bgcolor="#0E1117",
                font=dict(color="white"),
                legend=dict(
                    orientation="v", yanchor="middle", y=0.5,
                    xanchor="left", x=1, font=dict(color="white", size=14)
                )
            )
            fig.update_yaxes(scaleanchor="x", scaleratio=1)

            with col2:
                st.plotly_chart(fig, use_container_width=True)
                total = int(conteo["Equipos"].sum())
                st.markdown(f"<div class='metric-box'>Total de equipos: {total}</div>", unsafe_allow_html=True)
    except Exception as e:
        with col2:
            st.error(f"No se pudo generar el gráfico: {e}")

st.markdown("### ")
estatus_list = ["ACTIVA", "DISPONIBLE", "OBSOLETA", "VENTA/DONAR", "VENDIDA", "DAÑADA", "BAJA", "ROBO"]

if 'filtro_activo' not in st.session_state:
    st.session_state.filtro_activo = None

col_btns = st.columns(len(estatus_list))
for i, estatus in enumerate(estatus_list):
    if col_btns[i].button(estatus, key=f"btn_{estatus}", use_container_width=True):
        st.session_state.filtro_activo = None if st.session_state.filtro_activo == estatus else estatus

search_query = st.text_input("🔍 Buscar", placeholder="Escribe aquí para buscar...")

df_filtrado = df_table.copy()
if st.session_state.filtro_activo:
    df_filtrado = df_filtrado[df_filtrado["ESTATUS"].str.upper() == st.session_state.filtro_activo]

if 'IMAGEN' in df_filtrado.columns:
    df_filtrado = df_filtrado.drop(columns=['IMAGEN'])

if search_query:
    search_series = df_filtrado.apply(lambda row: ' '.join(row.values.astype(str)), axis=1)
    mask = search_series.str.contains(search_query, case=False, na=False)
    df_filtrado = df_filtrado[mask]

gb = GridOptionsBuilder.from_dataframe(df_filtrado)
gb.configure_default_column(editable=False, resizable=False, minWidth=80)
gb.configure_selection(selection_mode="single", use_checkbox=False)
gb.configure_grid_options(domLayout="normal", suppressHorizontalScroll=False, rowHeight=30)
gridOptions = gb.build()

custom_css = {
    ".ag-root-wrapper": {"background-color": "transparent !important", "border": "1px solid #333e5d !important"},
    ".ag-header, .ag-row, .ag-cell": {
        "background-color": "transparent !important",
        "color": "white !important",
        "border": "1px solid #333e5d !important",
        "font-size": "11px !important"
    },
    ".ag-header-cell-text": {"color": "white !important", "font-weight": "bold !important"}
}

AgGrid(
    df_filtrado,
    gridOptions=gridOptions,
    update_mode=GridUpdateMode.NO_UPDATE,
    editable=False,
    fit_columns_on_grid_load=False,
    allow_unsafe_jscode=False,
    theme="streamlit",
    height=700,
    data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
    key=f"tabla_equipos_{st.session_state.filtro_activo}",
    custom_css=custom_css
)