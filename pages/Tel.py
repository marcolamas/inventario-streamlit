import pandas as pd
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
import base64
import unicodedata
import plotly.graph_objects as go
import plotly.express as px
import re 

st.set_page_config(page_title="Equipos Telefónicos", layout="wide")

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
    div[data-testid="stButton"] > button:hover { background-color: #0056b3; }
    h1 { margin-top: 0 !important; margin-bottom: 10px; font-size: 20px !important; }
    .img-top-right { position: absolute; top: 15px; right: 5px; width: 100px; }
    .img-top-r { position: absolute; top: 0px; right: 120px; width: 150px; }
</style>
<img src="https://i0.wp.com/web.metricamovil.com/wp-content/uploads/cropped-Logotipo-Me%CC%81trica-Mo%CC%81vil.webp?fit=200%2C125&ssl=1" class="img-top-right">
<img src="https://download.logo.wine/logo/Telcel/Telcel-Logo.wine.png" class="img-top-r">
""", unsafe_allow_html=True)

esp1, menu1, menu2, esp2 = st.columns([.01, 2, 2, 4])
with menu1:
    if st.button("💻Equipos de computo", use_container_width=True):
        st.switch_page("app")
with menu2:
    if st.button("📱Equipos teléfonicos", use_container_width=True):
        st.rerun()

def crear_medidor(valor, titulo, color_barra):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = valor,
        domain = {'x': [0, 1], 'y': [0, 1]},
        number = {'suffix': "%", 'font': {'size': 36}, 'valueformat': '.1f'},
        title = {'text': titulo, 'font': {'size': 16}},
        gauge = {
            'axis': {'range': [None, 100], 'visible': False},
            'bar': {'color': color_barra, 'thickness': 0.8},
            'bgcolor': "#2E2E2E",
            'borderwidth': 2,
            'bordercolor': "gray"
        }
    ))
    fig.update_layout(
        height=150,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)", 
        font={'color': "white"}
    )
    return fig

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1hUDaaqzQ_LKT71YTTwwyRYvvg1itNm46Dhezlz-5Jdk/edit"
SHEET_TABLE = "Hoja 1" 
SHEET_GAUGES = "Web"

@st.cache_data(ttl=300)
def load_all_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive.readonly"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        ws = client.open_by_url(SPREADSHEET_URL).worksheet(SHEET_TABLE)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_url(SPREADSHEET_URL)

        ws_table = spreadsheet.worksheet(SHEET_TABLE)
        values = ws_table.get_all_values()
        if not values or len(values) <= 3:
            df_table = pd.DataFrame()
        else:
            header_row_index = 3
            raw_headers = values[header_row_index]
            headers = [h if str(h).strip() != "" else f"col{i}" for i, h in enumerate(raw_headers)]
            data = values[header_row_index + 1:]
            df_table = pd.DataFrame(data, columns=headers).fillna("").astype(str)

        ws_gauges = spreadsheet.worksheet(SHEET_GAUGES)
        df_gauges = pd.DataFrame(ws_gauges.get_all_records())
        if 'Equipos' in df_gauges.columns:
            df_gauges['Equipos'] = pd.to_numeric(df_gauges['Equipos'], errors='coerce').fillna(0)

        return df_table, df_gauges
    
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return pd.DataFrame(), pd.DataFrame()

def normalize_text(s):
    if s is None: return ""
    s = str(s).strip().lower()
    return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))

def parse_numeric_value(x):
    """Convierte cadenas como '$1,200.50' o '1.200,50' a float; devuelve NaN si no puede."""
    if pd.isna(x):
        return float("nan")
    s = str(x).strip()
    if s == "" or s.upper() == "N/A":
        return float("nan")
    if '.' in s and ',' in s:
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '') 
            s = s.replace(',', '.') 
        else:
            s = s.replace(',', '') 
    else:
        if ',' in s and '.' not in s:
            s = s.replace(',', '.')
    s = re.sub(r'[^\d\.\-]', '', s)
    try:
        return float(s)
    except Exception:
        return float("nan")

df_table, df_gauges_data = load_all_data()

st.markdown("# ")
col1, col2, col3 = st.columns([2.5, 2.5, 2])
with col2:
    if not df_table.empty and 'Estado' in df_table.columns:
        try:
            df_estados = df_table[df_table['Estado'].astype(str).str.strip().str.upper().ne("TOTAL")]
            df_estados = df_estados[df_estados['Estado'].astype(str).str.strip() != ""]

            df_chart_data = (
                df_estados.groupby(['Estado'])
                .size()
                .reset_index(name='Equipos por Estado')
                .sort_values(by='Estado')
            )

            fig_area = px.area(
                df_chart_data,
                x='Estado',
                y='Equipos por Estado',
                title='Equipos por Estado',
                labels={'Equipos por Estado': 'Número de Equipos', 'Estado': 'Estado'}
            )

            fig_area.update_traces(mode="lines", fill='tozeroy')
            fig_area.update_layout(
                height=480,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor='#444'),
                showlegend=False
            )

            st.plotly_chart(fig_area, use_container_width=True, config={'displayModeBar': False})

        except Exception as e:
            st.error(f"No se pudo generar el gráfico: {e}")
    else:
        st.info("No se puede generar el gráfico. Se requiere la columna 'Estado' en los datos.")



with col3:
    if not df_gauges_data.empty and 'Etiqueta' in df_gauges_data.columns and 'Equipos' in df_gauges_data.columns:
        total_series = df_gauges_data[df_gauges_data['Etiqueta'].str.strip().str.upper() == 'TOTAL']['Equipos']
        total = total_series.iloc[0] if not total_series.empty else 0

        if total > 0:
            metricas = {
                "ACTIVOS": "#13C3E8",
                "DISPONIBLES": "#28DE9E",
                "BAJA": "#E68E8E"
            }

            for metrica, color in metricas.items():
                valor_series = df_gauges_data[df_gauges_data['Etiqueta'].str.strip().str.upper() == metrica]['Equipos']
                valor = valor_series.iloc[0] if not valor_series.empty else 0
                
                porcentaje = (valor / total) * 100
                
                fig = crear_medidor(porcentaje, metrica.capitalize(), color)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("El valor 'Total' en la hoja 'Web' es 0 o no se encontró.")
    else:
        st.warning("Asegúrate que la hoja 'Web' tenga las columnas 'Etiqueta' y 'Equipos'.")

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

plan_col = None
normalized_to_real = {normalize_text(c): c for c in df_table.columns}
target_norm = normalize_text("Plan Y Servicios contratados")
if target_norm in normalized_to_real:
    plan_col = normalized_to_real[target_norm]
else:
    for nreal, realcol in normalized_to_real.items():
        if "plan" in nreal and "servici" in nreal:
            plan_col = realcol
            break
    if plan_col is None:
        for nreal, realcol in normalized_to_real.items():
            if "plan" in nreal or "servici" in nreal or "servicios" in nreal:
                plan_col = realcol
                break

otal_plan_servicios = None
media_plan_servicios = None 

if plan_col is not None:
    numeric_series = df_table[plan_col].apply(parse_numeric_value).dropna()
    
    if not numeric_series.empty:
        total_plan_servicios = numeric_series.sum()
        media_plan_servicios = numeric_series.mean()

with col1:
    if total_plan_servicios is not None:
        st.markdown(
            f"""
            <div style="background-color: #0E1117; border-radius: 10px; padding: 15px; text-align: left;">
                <p style="color: white; font-size: 15px; margin-bottom: 0px;">
                    Costo total de Planes y Servicios contratados (ACTIVOS)
                </p>
                <p style="color: #00FF88; font-size: 30px; font-weight: bold; margin: 0;">
                    ${total_plan_servicios:,.2f}
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.info("No se encontró la columna de costos.")

    if media_plan_servicios is not None:
        st.markdown(
            f"""
            <div style="background-color: #0E1117; border-radius: 10px; padding: 15px; text-align: left;">
                <p style="color: white; font-size: 15px; margin-bottom: 0px;">
                    Media de gasto por Línea
                </p>
                <p style="color: #FFD700; font-size: 30px; font-weight: bold; margin: 0;">
                    ${media_plan_servicios:,.2f}
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.info("No se encontró la columna de media de costos.")

    activos = 0
    if not df_gauges_data.empty and 'Etiqueta' in df_gauges_data.columns and 'Equipos' in df_gauges_data.columns:
        activos_series = df_gauges_data[
            df_gauges_data['Etiqueta'].astype(str).str.strip().str.upper() == 'ACTIVOS'
        ]['Equipos']
        if not activos_series.empty and pd.notna(activos_series.iloc[0]):
            try:
                activos = int(activos_series.iloc[0])
            except Exception:
                activos = int(pd.to_numeric(activos_series.iloc[0], errors='coerce')) if pd.notna(activos_series.iloc[0]) else 0

    st.markdown(
        f"""
        <div style="background-color: #0E1117; border-radius: 10px; padding: 10px; text-align: left;">
            <p style="color: white; font-size: 14px; margin: 0;">
                Total de equipos activos:
                <span style="color:#13C3E8; font-weight:bold; font-size:18px;"> {activos}</span>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

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
    df_filtrado, gridOptions=gridOptions, update_mode=GridUpdateMode.MODEL_CHANGED,
    fit_columns_on_grid_load=False, allow_unsafe_jscode=False, theme="streamlit", height=700,
    data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
    custom_css=custom_css
)


