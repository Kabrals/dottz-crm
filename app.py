import streamlit as st
import pandas as pd
import calendar as py_calendar
from datetime import date, timedelta
import os
import base64
import numpy as np
from supabase import create_client, Client

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="CRM Dottz", page_icon="logo.png", layout="wide")

# --- CONEXÃO AO SUPABASE (NUVEM) ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_connection()
except Exception as e:
    st.error("Erro ao ligar ao servidor. Verifica as chaves no Streamlit Secrets.")
    st.stop()

# --- FUNÇÕES DE LEITURA E GRAVAÇÃO NA NUVEM ---
def load_table(table_name, default_columns):
    try:
        response = supabase.table("crm_data").select("data").eq("table_name", table_name).execute()
        if response.data and response.data[0]["data"]:
            df = pd.DataFrame(response.data[0]["data"])
            for col in default_columns:
                if col not in df.columns:
                    df[col] = ""
            
            # Força a ordem exata das colunas independentemente do formato JSON
            ordered_cols = [c for c in default_columns if c in df.columns]
            extra_cols = [c for c in df.columns if c not in default_columns]
            df = df[ordered_cols + extra_cols]
            
            return df.astype(object)
    except Exception:
        pass
    return pd.DataFrame(columns=default_columns).astype(object)

def save_table(table_name, df):
    df_clean = df.copy()
    for col in df_clean.columns:
        def clean_val(x):
            try:
                if pd.isna(x): return ""
            except: pass
            if str(x) in ["NaT", "nan", "NaN", "None", "<NA>"]: return ""
            if isinstance(x, (date, pd.Timestamp)): return str(x)
            return x
        df_clean[col] = df_clean[col].apply(clean_val)
        
    data_json = df_clean.to_dict(orient="records")
    try:
        supabase.table("crm_data").upsert({"table_name": table_name, "data": data_json}).execute()
    except Exception as e:
        st.error(f"Erro de gravação na nuvem: {e}")

# --- FUNÇÕES DE STORAGE (ANEXOS) NA NUVEM PROTEGIDAS ---
def save_uploaded_file(uploaded_file, prefix):
    if uploaded_file is not None:
        safe_name = "".join([c for c in uploaded_file.name if c.isalpha() or c.isdigit() or c in (' ', '.', '_', '-')]).rstrip()
        file_path = f"{prefix}_{safe_name}"
        file_bytes = uploaded_file.getvalue()
        try:
            supabase.storage.from_("anexos").upload(file_path, file_bytes, {"upsert": "true"})
            return file_path
        except Exception as e:
            st.error("🚨 Erro: O Supabase rejeitou o anexo. Confirma se criaste o bucket 'anexos' (em minúsculas) e se está 'Public'.")
            return None
    return None

# --- SISTEMA DE LOGIN ---
USERS = {
    "amcabral": "DBS2027",
    "alcastro": "DBS2027",
    "mguerra": "DBS2027"
}

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""

def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except: return ""

if not st.session_state["logged_in"]:
    logo_b64 = get_base64_of_bin_file("logo.png")
    st.markdown(
        """
        <style>
        .stApp { background-color: #FFFFFF !important; }
        header { visibility: hidden !important; }
        [data-testid="stForm"] { border: none !important; padding: 0 !important; background: transparent !important; max-width: 350px !important; margin: 0 auto !important; }
        [data-testid="stForm"] input { background-color: #F8F9FA !important; border: 1px solid #E0E0E0 !important; color: #333333 !important; border-radius: 6px !important; padding: 14px !important; text-align: center !important; font-size: 16px !important; margin-bottom: 10px !important; transition: all 0.2s ease !important; }
        [data-testid="stForm"] input:focus { border-color: #7B2CBF !important; box-shadow: 0 0 0 1px #7B2CBF !important; background-color: #FFFFFF !important; }
        [data-testid="stFormSubmitButton"] button { background-color: #7B2CBF !important; color: #FFFFFF !important; font-weight: bold !important; border-radius: 6px !important; border: none !important; width: 100% !important; padding: 12px !important; margin-top: 15px !important; transition: all 0.3s ease !important; }
        [data-testid="stFormSubmitButton"] button:hover { background-color: #5B2C83 !important; }
        [data-testid="stFormSubmitButton"] button * { color: #FFFFFF !important; }
        </style>
        """, unsafe_allow_html=True
    )
    st.markdown("<br><br><br><br><br><br>", unsafe_allow_html=True)
    _, col_center, _ = st.columns([1, 1, 1])
    with col_center:
        if logo_b64:
            st.markdown(f"<div style='text-align: center; margin-bottom: 35px;'><img src='data:image/png;base64,{logo_b64}' style='max-width: 250px;'></div>", unsafe_allow_html=True)
        else:
            st.markdown("<h2 style='text-align: center; color: #5B2C83; margin-bottom: 35px;'>DOTTZ CRM</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            user_input = st.text_input("Utilizador", placeholder="Username", label_visibility="collapsed")
            pass_input = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
            submit_login = st.form_submit_button("ENTRAR NO CRM", use_container_width=True)
            if submit_login:
                if user_input in USERS and USERS[user_input] == pass_input:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = user_input
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")
    st.stop()

# --- CSS MODO LOGADO ---
st.markdown(
    """
    <style>
    :root {
        color-scheme: light !important; --gdg-bg-cell: #FFFFFF !important; --gdg-bg-cell-medium: #F8F9FA !important; --gdg-bg-header: #F1F3F5 !important;
        --gdg-text-dark: #000000 !important; --gdg-text-medium: #333333 !important; --gdg-text-header: #000000 !important;
        --gdg-border-color: #E0E0E0 !important; --gdg-accent-color: #7B2CBF !important;
    }
    body, p, label, input, textarea, select, button, code { font-family: "Agency FB", "Bahnschrift", "Segoe UI Variable", sans-serif !important; }
    h1, h2, h3, h4, h5, h6 { font-family: "Agency FB", "Bahnschrift", sans-serif !important; font-weight: 700 !important; }
    .stApp { background-color: #FFFFFF !important; color: #000000 !important; }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stText { color: #000000 !important; }
    input, textarea, div[data-baseweb="select"] > div, div[data-baseweb="base-input"] { background-color: #F8F9FA !important; color: #000000 !important; border: 1px solid #CCCCCC !important; -webkit-text-fill-color: #000000 !important; }
    div[data-baseweb="popover"], div[data-baseweb="popover"] *, ul[role="listbox"], ul[role="listbox"] li { background-color: #FFFFFF !important; color: #000000 !important; }
    [data-testid="stDataFrame"], [data-testid="stTable"] { background-color: #FFFFFF !important; }
    [data-testid="stDataFrame"] div, [data-testid="stDataFrame"] span { color: #000000 !important; }
    div.stButton > button, [data-testid="stFormSubmitButton"] > button, [data-testid="stDownloadButton"] > button { background-color: #7B2CBF !important; color: #FFFFFF !important; border: none !important; border-radius: 6px !important; font-weight: bold !important; padding: 8px 16px !important; transition: all 0.2s ease !important; }
    div.stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover, [data-testid="stDownloadButton"] > button:hover { background-color: #5B2C83 !important; }
    div.stButton > button *, [data-testid="stFormSubmitButton"] > button *, [data-testid="stDownloadButton"] > button * { color: #FFFFFF !important; }
    [data-testid="stExpander"] details summary { background-color: #7B2CBF !important; color: #FFFFFF !important; border-radius: 6px !important; padding: 10px 15px !important; font-weight: bold !important; }
    [data-testid="stExpander"] details summary * { color: #FFFFFF !important; fill: #FFFFFF !important; }
    [data-testid="stExpander"] details { border: 1px solid #E0E0E0 !important; border-radius: 6px !important; background-color: #FFFFFF !important; }
    button[data-baseweb="tab"] p { color: #666666 !important; }
    button[data-baseweb="tab"][aria-selected="true"] p { color: #000000 !important; font-weight: bold !important; }
    .stTabs [role="tablist"] { justify-content: center; flex-wrap: wrap; }
    .stTabs [data-testid="stTab"] p { font-size: 1.1em !important; }
    .stTabs [data-testid="stTab"] .react-aria-SelectionIndicator { background-color: #7B2CBF !important; }
    .st-key-btn_logout { position: absolute; top: -40px; left: 10px; z-index: 999999; }
    .st-key-btn_logout button { background-color: transparent !important; border: none !important; color: #888888 !important; font-size: 12px !important; font-weight: 300 !important; opacity: 0.6 !important; box-shadow: none !important; padding: 5px !important; }
    .st-key-btn_logout button * { color: #888888 !important; }
    .st-key-btn_logout button:hover, .st-key-btn_logout button:hover * { color: #000000 !important; opacity: 1 !important; }
    </style>
    """, unsafe_allow_html=True
)

if st.button("log out", key="btn_logout"):
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.rerun()

# --- CONSTANTES E FUNÇÕES AUXILIARES ---
EMPRESAS_CONSTRUCAO = [f"Empresa de Construção {i}" for i in range(1, 6)]
DATAS_ORCAMENTO = [f"Data de Entrega do Orçamento {i}" for i in range(1, 6)]
VALORES_ORCAMENTO = [f"Valor do Orçamento {i}" for i in range(1, 6)]
FOLLOW_UPS_EMPRESA = [f"Follow up Empresa {i}" for i in range(1, 6)]
ANEXOS_EMPRESA = [f"Anexo Empresa {i}" for i in range(1, 6)]
COLUNA_ARQUITECTO = "Arquitecto"
COLUNA_ANEXO_PROJETO = "Anexo Projeto"
FASES_ATUAIS = ["⚪ Em Análise", "🟡 Em Concurso", "🟣 Em Negociação", "🟢 Adjudicado", "🔴 Não Adjudicado"]
ESTADOS_PAGAMENTO = ["⚪ Não facturado", "🟡 Fatura por pagar", "🟢 Recebido"]
OPCOES_SIM_NAO = ["🟢 Sim", "🔴 Não"]

def get_clean_list(df, col):
    if col not in df.columns: return ["Todos"]
    raw = df[col].dropna().astype(str).unique()
    clean = sorted([str(x).strip() for x in raw if str(x).strip() != "" and str(x).strip().lower() != "nan"])
    return ["Todos"] + clean

def parse_currency(val):
    try:
        if pd.isna(val) or val == "": return 0.0
        if isinstance(val, (int, float)): return float(val)
        s = str(val).replace("€", "").strip()
        if "apurar" in s.lower(): return 0.0
        s = s.replace("<", "").replace(">", "").strip()
        if "-" in s: s = s.split("-")[0]
        s = s.replace(" ", "")
        if "." in s and "," in s:
            if s.rfind(".") > s.rfind(","): s = s.replace(",", "")
            else: s = s.replace(".", "").replace(",", ".")
        elif "," in s: s = s.replace(",", ".")
        elif "." in s:
            parts = s.split(".")
            if len(parts) > 1 and len(parts[-1]) == 3: s = s.replace(".", "")
        return float(s)
    except: return 0.0

def sync_financial_math(df):
    changed = False
    if df.empty: return df, changed
    
    colunas_matematicas = ["Valor Estimado", "% DBS", "Valor da % DBS", "% Inter", "Valor da % Inter"]
    for col in colunas_matematicas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0).astype(float)

    if "Inter" in df.columns:
        old_inter = df["Inter"].astype(str).copy()
        df["Inter"] = df["Inter"].fillna("").astype(str).replace(["nan", "None", "<NA>", "NaN"], "")
        if not df["Inter"].astype(str).equals(old_inter): changed = True
        
    for idx in df.index:
        if "Valor Estimado" not in df.columns: continue
        v_est = parse_currency(df.at[idx, "Valor Estimado"])
        p_dbs = pd.to_numeric(df.at[idx, "% DBS"], errors="coerce") if "% DBS" in df.columns else 0.0
        p_int = pd.to_numeric(df.at[idx, "% Inter"], errors="coerce") if "% Inter" in df.columns else 0.0
        if pd.isna(p_dbs): p_dbs = 0.0
        if pd.isna(p_int): p_int = 0.0
        
        calc_dbs = v_est * (p_dbs / 100.0)
        calc_int = v_est * (p_int / 100.0)
        
        if df.at[idx, "Valor Estimado"] != v_est: df.at[idx, "Valor Estimado"] = v_est; changed = True
        if "% DBS" in df.columns and df.at[idx, "% DBS"] != p_dbs: df.at[idx, "% DBS"] = p_dbs; changed = True
        if "% Inter" in df.columns and df.at[idx, "% Inter"] != p_int: df.at[idx, "% Inter"] = p_int; changed = True
            
        if "Valor da % DBS" in df.columns:
            atual_dbs = pd.to_numeric(df.at[idx, "Valor da % DBS"], errors="coerce")
            if pd.isna(atual_dbs): atual_dbs = 0.0
            if round(calc_dbs, 2) != round(atual_dbs, 2): df.at[idx, "Valor da % DBS"] = calc_dbs; changed = True
                
        if "Valor da % Inter" in df.columns:
            atual_int = pd.to_numeric(df.at[idx, "Valor da % Inter"], errors="coerce")
            if pd.isna(atual_int): atual_int = 0.0
            if round(calc_int, 2) != round(atual_int, 2): df.at[idx, "Valor da % Inter"] = calc_int; changed = True
            
    return df, changed

# --- NOVA FUNÇÃO DE RECUPERAÇÃO SEGURA DO ÍNDICE ---
def get_lead_index(project_id):
    if st.session_state.leads_db.empty: return None
    safe_ids = pd.to_numeric(st.session_state.leads_db["ID"], errors="coerce").fillna(0).astype(int)
    matches = st.session_state.leads_db.index[safe_ids == int(project_id)]
    return matches[0] if len(matches) > 0 else None

def guardar_campo_projeto(project_id, column_name, widget_key, is_currency=False):
    indice = get_lead_index(project_id)
    if indice is not None:
        valor = st.session_state[widget_key]
        if is_currency: valor = parse_currency(valor)
        st.session_state.leads_db.at[indice, column_name] = valor if valor is not None else ""
        st.session_state.leads_db, _ = sync_financial_math(st.session_state.leads_db)
        save_table("leads_db", st.session_state.leads_db)

def listar_nomes_arquitectos():
    if "architects_db" not in st.session_state: return []
    arquitectos = st.session_state.architects_db
    if "Nome" not in arquitectos.columns: return []
    nomes = arquitectos["Nome"].dropna().astype(str).str.strip()
    return sorted(nomes[nomes != ""].unique().tolist())

# --- INICIALIZAÇÃO DE DADOS (VIA SUPABASE) ---
cols_leads = ["ID", "Cliente", "Projeto", COLUNA_ARQUITECTO, "Fase", "Valor Estimado", "Próximo Follow-up", "Notas", COLUNA_ANEXO_PROJETO, *EMPRESAS_CONSTRUCAO, *DATAS_ORCAMENTO, *VALORES_ORCAMENTO, *FOLLOW_UPS_EMPRESA, *ANEXOS_EMPRESA, "% DBS", "Valor da % DBS", "Inter", "% Inter", "Valor da % Inter"]
if "leads_db" not in st.session_state: 
    df_l = load_table("leads_db", cols_leads)
    if "Próximo Follow-up" in df_l.columns: df_l["Próximo Follow-up"] = pd.to_datetime(df_l["Próximo Follow-up"], errors="coerce").dt.date
    for col in FOLLOW_UPS_EMPRESA + DATAS_ORCAMENTO:
        if col in df_l.columns: df_l[col] = pd.to_datetime(df_l[col], errors="coerce").dt.date
    for col in VALORES_ORCAMENTO:
        if col in df_l.columns: df_l[col] = pd.to_numeric(df_l[col], errors="coerce")
    st.session_state.leads_db = df_l

fases_migracao = { "Nova Consulta": "⚪ Em Análise", "Qualificação": "⚪ Em Análise", "Proposta Entregue": "🟡 Em Concurso", "Em Análise": "⚪ Em Análise", "Em Concurso": "🟡 Em Concurso", "Em Negociação": "🟣 Em Negociação", "Negociação": "🟣 Em Negociação", "Fechado - Ganho": "🟢 Adjudicado", "Adjudicado": "🟢 Adjudicado", "Fechado - Perdido": "🔴 Não Adjudicado", "Não Adjudicado": "🔴 Não Adjudicado" }
if "Fase" in st.session_state.leads_db.columns:
    st.session_state.leads_db["Fase"] = st.session_state.leads_db["Fase"].replace(fases_migracao).apply(lambda x: x if x in FASES_ATUAIS else "⚪ Em Análise")
st.session_state.leads_db, leads_changed = sync_financial_math(st.session_state.leads_db)
if leads_changed: save_table("leads_db", st.session_state.leads_db)

cols_tct_base = ["ID", "Cliente", "Projeto", "Fase", "Valor Estimado", "% DBS", "Valor da % DBS", "Inter", "% Inter", "Valor da % Inter"]

if "tct_db" not in st.session_state:
    df_tct, changed_tct = sync_financial_math(load_table("tct_db", cols_tct_base))
    needs_save = changed_tct
    for i, row in df_tct.iterrows():
        if pd.isna(row.get("ID")) or str(row.get("ID")).strip() == "":
            df_tct.at[i, "ID"] = i + 1
            needs_save = True
    if needs_save: save_table("tct_db", df_tct)
    st.session_state.tct_db = df_tct

if "alca_db" not in st.session_state:
    df_alca, changed_alca = sync_financial_math(load_table("alca_db", cols_tct_base))
    needs_save = changed_alca
    for i, row in df_alca.iterrows():
        if pd.isna(row.get("ID")) or str(row.get("ID")).strip() == "":
            df_alca.at[i, "ID"] = i + 1
            needs_save = True
    if needs_save: save_table("alca_db", df_alca)
    st.session_state.alca_db = df_alca

if "famo_db" not in st.session_state:
    df_famo, changed_famo = sync_financial_math(load_table("famo_db", cols_tct_base))
    needs_save = changed_famo
    for i, row in df_famo.iterrows():
        if pd.isna(row.get("ID")) or str(row.get("ID")).strip() == "":
            df_famo.at[i, "ID"] = i + 1
            needs_save = True
    if needs_save: save_table("famo_db", df_famo)
    st.session_state.famo_db = df_famo

cols_arq_texto = ["Nome", "Responsável", "Telefone", "Email", "Distrito"]
cols_arq_bool = ["Contactado", "Reunião", "Interessado", "Parceria"]
cols_arq_todas = cols_arq_texto + cols_arq_bool
if "architects_db" not in st.session_state:
    df_arq = load_table("architects_db", cols_arq_todas)
    for col in cols_arq_texto: df_arq[col] = df_arq[col].fillna("").astype(str).replace(["nan", "None"], "")
    for col in cols_arq_bool: df_arq[col] = df_arq[col].replace({"Sim": "🟢 Sim", "Não": "🔴 Não", "": "🔴 Não"}).fillna("🔴 Não").apply(lambda x: x if x in OPCOES_SIM_NAO else "🔴 Não")
    st.session_state.architects_db = df_arq

nomes_arquitectos = listar_nomes_arquitectos()

cols_const_texto = ["Nome", "Alvará", "Distrito", "Responsável", "Função", "Telefone", "Email"]
cols_const_bool = ["Contactado", "Reunião", "Parceria"]
cols_const_todas = cols_const_texto + cols_const_bool
if "builders_db" not in st.session_state:
    df_build = load_table("builders_db", cols_const_todas)
    for col in cols_const_texto: df_build[col] = df_build[col].fillna("").astype(str).replace(["nan", "None"], "")
    for col in cols_const_bool: df_build[col] = df_build[col].replace({"Sim": "🟢 Sim", "Não": "🔴 Não", "": "🔴 Não"}).fillna("🔴 Não").apply(lambda x: x if x in OPCOES_SIM_NAO else "🔴 Não")
    st.session_state.builders_db = df_build

cols_todo_todas = ["Tarefa", "Próximos passos", "Follow up"]
if "todo_db" not in st.session_state:
    df_todo = load_table("todo_db", cols_todo_todas)
    if "Follow up" in df_todo.columns: df_todo["Follow up"] = pd.to_datetime(df_todo["Follow up"], errors="coerce").dt.date
    st.session_state.todo_db = df_todo

col_base_pagamentos = ["Projeto", "Valor Global", "Data de Início", "Data Final", "Meses de duração", "Valor mensal"]
if "payments_db" not in st.session_state:
    df_pag = load_table("payments_db", col_base_pagamentos)
    df_pag["Valor Global"] = pd.to_numeric(df_pag["Valor Global"], errors="coerce").fillna(0.0)
    df_pag["Meses de duração"] = pd.to_numeric(df_pag["Meses de duração"], errors="coerce").fillna(1).astype(int)
    df_pag["Valor mensal"] = pd.to_numeric(df_pag["Valor mensal"], errors="coerce").fillna(0.0)
    st.session_state.payments_db = df_pag

cols_inst = ["Projeto", "Mês", "Mensalidade (€)", "IVA (%)", "Valor com IVA (€)", "IVA IF", "Estado"]
if "installments_db" not in st.session_state:
    df_inst = load_table("installments_db", cols_inst)
    df_inst["Mensalidade (€)"] = pd.to_numeric(df_inst["Mensalidade (€)"], errors="coerce").fillna(0.0)
    df_inst["IVA (%)"] = pd.to_numeric(df_inst["IVA (%)"], errors="coerce").fillna(23.0)
    df_inst["Valor com IVA (€)"] = pd.to_numeric(df_inst["Valor com IVA (€)"], errors="coerce").fillna(0.0)
    mask_z = df_inst["Valor com IVA (€)"] == 0.0
    df_inst.loc[mask_z, "Valor com IVA (€)"] = df_inst.loc[mask_z, "Mensalidade (€)"] * (1 + df_inst.loc[mask_z, "IVA (%)"]/100.0)
    st.session_state.installments_db = df_inst

cols_kpi = ["Métricas Globais", "Valor Atual", "KPIS 2027", "Objetivo"]
if "kpi_db" not in st.session_state:
    df_kpi = load_table("kpi_db", cols_kpi)
    if df_kpi.empty:
        df_kpi = pd.DataFrame({
            "Métricas Globais": ["Total de Parcerias com Arquitectos", "Total de Parcerias com Construtores", "Total de Projectos", "Total de Projectos Adjudicados", "Total de Valor Adjudicado (€)", "Total de Valor da % DBS (€)", "% de Valor (Adjudicado / Estimado) (%)"],
            "KPIS 2027": ["Total de Parcerias com Arquitectos", "Total de Parcerias com Construtores", "Total de Projectos", "Total de Projectos Adjudicados", "Total de Valor Adjudicado (€)", "Total de Valor da % DBS (€)", "% de Valor (Adjudicado / Estimado) (%)"],
            "Objetivo": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        })
        save_table("kpi_db", df_kpi)
    st.session_state.kpi_db = df_kpi

# --- CABEÇALHO COM LOGOTIPO ---
if os.path.exists("logo.png"):
    _, logo_col, _ = st.columns([1, 2, 1])
    with logo_col: st.image("logo.png", width=250)
else:
    _, logo_col, _ = st.columns([1, 2, 1])
    with logo_col: st.warning("Para veres o logotipo aqui, faz upload do ficheiro 'logo.png' no teu repositório Github.")
st.markdown("<br>", unsafe_allow_html=True)

tab_captura, tab_pipeline, tab_comunicacao, tab_arquitectos, tab_construtores, tab_tct, tab_alca, tab_famo, tab_calendario, tab_financeiro, tab_pagamentos, tab_todo, tab_objectivos = st.tabs([
    "Capturar e Enriquecer", "Pipeline de Negócios", "Interações & Follow-Ups", "Arquitectos", "Constructores", "TCT", "ALCA", "FAMO", "Calendário", "Financeiro", "Pagamentos", "To do List", "Objectivos"
])

# --- 1. CAPTURAR E ENRIQUECER ---
with tab_captura:
    st.markdown("### Nova Consulta")
    with st.form("form_nova_lead", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            novo_cliente = st.text_input("Nome do Cliente / Entidade")
            novo_email = st.text_input("Email de Contacto")
        with col2:
            novo_projeto = st.text_input("Nome/Localização do Projeto")
            novo_valor = st.number_input("Valor Estimado (€)", min_value=0.0, step=1000.0)
        novo_arquitecto = st.selectbox("Arquitecto", [""] + nomes_arquitectos, key="novo_projeto_arquitecto")
        notas_iniciais = st.text_area("Notas Iniciais / Enriquecimento")
        
        if st.form_submit_button("Criar Oportunidade"):
            if novo_cliente and novo_projeto:
                safe_ids = pd.to_numeric(st.session_state.leads_db["ID"], errors="coerce").dropna()
                novo_id = 1 if safe_ids.empty else int(safe_ids.max()) + 1
                nova_linha = {"ID": novo_id, "Cliente": novo_cliente, "Projeto": novo_projeto, COLUNA_ARQUITECTO: novo_arquitecto, "Fase": "⚪ Em Análise", "Valor Estimado": float(novo_valor), "Próximo Follow-up": date.today() + timedelta(days=1), "Notas": notas_iniciais}
                st.session_state.leads_db = pd.concat([st.session_state.leads_db, pd.DataFrame([nova_linha])], ignore_index=True)
                st.session_state.leads_db, _ = sync_financial_math(st.session_state.leads_db)
                save_table("leads_db", st.session_state.leads_db)
                st.toast("Oportunidade guardada no pipeline.")
                st.rerun()

# --- 2. PIPELINE DE NEGÓCIOS ---
with tab_pipeline:
    st.markdown("### Oportunidades em Curso")
    st.markdown("Move os negócios pelas diferentes fases e anexa documentação relevante.")
    cores_fase = { "⚪ Em Análise": ("#FFFFFF", "#000000"), "🟡 Em Concurso": ("#FFD700", "#000000"), "🟣 Em Negociação": ("#7B2CBF", "#FFFFFF"), "🟢 Adjudicado": ("#A5D6A7", "#000000"), "🔴 Não Adjudicado": ("#FF6B6B", "#000000") }
    proporcoes_colunas = [1.8, 1.4, 1.3, 1.8, 1.1, 1.3, 1.4]
    cabecalhos = ["Cliente", "Projeto", "Arquitecto", "Fase do Negócio", "Valor", "Follow up", "Anexo Projeto"]

    if not st.session_state.leads_db.empty:
        st.markdown("<style>.st-key-pipeline_header {background:transparent;color:#5B2C83;padding:0 8px;border-radius:4px;min-height:48px;display:flex;align-items:center;font-size:0.9rem;} .st-key-pipeline_header p {color:#5B2C83 !important;text-align:center !important;font-size:0.9rem !important;font-weight:700 !important;line-height:1.1 !important;}</style>", unsafe_allow_html=True)
        with st.container(key="pipeline_header"):
            for coluna, cabecalho in zip(st.columns(proporcoes_colunas), cabecalhos):
                coluna.markdown(f"**{cabecalho}**")

        for indice, registo in st.session_state.leads_db.iterrows():
            id_registo = int(pd.to_numeric(registo.get("ID", 0), errors="coerce"))
            margem_linha = "-24px" if indice != st.session_state.leads_db.index[-1] else "0px"
            margem_superior_linha = "-24px" if indice == st.session_state.leads_db.index[0] else "0px"
            chave_linha = f"pipeline_row_{id_registo}"
            chave_fase = f"pipeline_fase_{id_registo}"
            fase_atual = registo["Fase"] if registo["Fase"] in FASES_ATUAIS else "⚪ Em Análise"
            cor_fundo, cor_texto = cores_fase[fase_atual]
            
            st.markdown(
                f"""<style>
                [data-testid="stLayoutWrapper"]:has(.st-key-{chave_linha}) {{margin-top:{margem_superior_linha} !important;margin-bottom:{margem_linha} !important;}}
                .st-key-{chave_linha} {{background:transparent;padding:0 8px;display:flex;align-items:center;}}
                .st-key-{chave_linha} input {{background:#F8F9FA !important;color:#000 !important;text-align:center !important;border-color:#CCC !important;font-size:0.9rem !important;}}
                .st-key-{chave_fase} [data-testid="stSelectbox"] .react-aria-ComboBox > div {{background:{cor_fundo} !important;}}
                .st-key-{chave_fase} [data-testid="stSelectbox"] .react-aria-ComboBox input {{color:{cor_texto} !important;text-align:center !important;font-weight:bold;}}
                </style>""", unsafe_allow_html=True
            )
            
            with st.container(key=chave_linha):
                colunas = st.columns(proporcoes_colunas)
                cliente_atual = "" if pd.isna(registo.get("Cliente")) else str(registo.get("Cliente"))
                with colunas[0]: st.text_input("Cliente", value=cliente_atual, key=f"pipeline_cliente_{id_registo}", label_visibility="collapsed", on_change=guardar_campo_projeto, args=(id_registo, "Cliente", f"pipeline_cliente_{id_registo}"))
                projeto_atual = "" if pd.isna(registo.get("Projeto")) else str(registo.get("Projeto"))
                with colunas[1]: st.text_input("Projeto", value=projeto_atual, key=f"pipeline_projeto_{id_registo}", label_visibility="collapsed", on_change=guardar_campo_projeto, args=(id_registo, "Projeto", f"pipeline_projeto_{id_registo}"))
                
                arquitecto_atual = "" if pd.isna(registo.get(COLUNA_ARQUITECTO)) else str(registo.get(COLUNA_ARQUITECTO))
                opcoes_arquitecto = [""] + nomes_arquitectos
                if arquitecto_atual and arquitecto_atual not in opcoes_arquitecto: opcoes_arquitecto.append(arquitecto_atual)
                with colunas[2]: st.selectbox("Arquitecto", opcoes_arquitecto, index=opcoes_arquitecto.index(arquitecto_atual), key=f"pipeline_arquitecto_{id_registo}", label_visibility="collapsed", on_change=guardar_campo_projeto, args=(id_registo, COLUNA_ARQUITECTO, f"pipeline_arquitecto_{id_registo}"))
                with colunas[3]: nova_fase = st.selectbox("Fase do Negócio", FASES_ATUAIS, index=FASES_ATUAIS.index(fase_atual), key=chave_fase, label_visibility="collapsed")
                
                val_fmt = f"{int(parse_currency(registo.get('Valor Estimado', 0.0))):,} €".replace(",", " ")
                with colunas[4]: st.text_input("Valor", value=val_fmt, key=f"pipeline_valor_{id_registo}", label_visibility="collapsed", on_change=guardar_campo_projeto, args=(id_registo, "Valor Estimado", f"pipeline_valor_{id_registo}", True))
                
                follow_up = registo.get("Próximo Follow-up", None)
                follow_up = None if pd.isna(follow_up) or follow_up == "" else pd.to_datetime(follow_up).date()
                with colunas[5]: st.date_input("Próximo Follow-up", value=follow_up, key=f"pipeline_followup_{id_registo}", label_visibility="collapsed", on_change=guardar_campo_projeto, args=(id_registo, "Próximo Follow-up", f"pipeline_followup_{id_registo}"))
                
                with colunas[6]:
                    anexo_proj = registo.get(COLUNA_ANEXO_PROJETO, "")
                    if pd.notna(anexo_proj) and anexo_proj != "":
                        ca1, ca2 = st.columns([1, 1])
                        with ca1:
                            try:
                                res = supabase.storage.from_("anexos").download(anexo_proj)
                                st.download_button("⬇️", res, file_name=anexo_proj, key=f"dl_proj_{id_registo}")
                            except:
                                st.write("Ficheiro missing")
                        with ca2:
                            if st.button("❌", key=f"del_proj_{id_registo}"):
                                try: supabase.storage.from_("anexos").remove([anexo_proj])
                                except: pass
                                st.session_state.leads_db.at[indice, COLUNA_ANEXO_PROJETO] = ""
                                save_table("leads_db", st.session_state.leads_db)
                                st.rerun()
                    else:
                        upl = st.file_uploader("Anexo", key=f"upl_proj_{id_registo}", label_visibility="collapsed")
                        if upl:
                            path = save_uploaded_file(upl, f"proj_{id_registo}")
                            if path is not None:
                                st.session_state.leads_db.at[indice, COLUNA_ANEXO_PROJETO] = path
                                save_table("leads_db", st.session_state.leads_db)
                                st.rerun()

            if nova_fase != registo["Fase"]:
                st.session_state.leads_db.at[indice, "Fase"] = nova_fase
                save_table("leads_db", st.session_state.leads_db)
                st.rerun()

        with st.expander("Editar outros dados da oportunidade"):
            colunas_protegidas = ["ID", "Cliente", "Projeto", COLUNA_ARQUITECTO, "Fase", "Próximo Follow-up", COLUNA_ANEXO_PROJETO, *EMPRESAS_CONSTRUCAO, *DATAS_ORCAMENTO, *VALORES_ORCAMENTO, *FOLLOW_UPS_EMPRESA, *ANEXOS_EMPRESA, "% DBS", "Valor da % DBS", "Inter", "% Inter", "Valor da % Inter"]
            col_cfg_exp = {col: None for col in colunas_protegidas}
            col_cfg_exp["Valor Estimado"] = st.column_config.NumberColumn("Valor Estimado", format="%.0f €", step=1000.0)
            edited_df = st.data_editor(st.session_state.leads_db, column_order=cols_leads, column_config=col_cfg_exp, use_container_width=True, hide_index=True, num_rows="fixed")
            if not edited_df.equals(st.session_state.leads_db):
                st.session_state.leads_db = edited_df
                st.session_state.leads_db, _ = sync_financial_math(st.session_state.leads_db)
                save_table("leads_db", st.session_state.leads_db)
                st.rerun()

        st.markdown("---")
        st.markdown("### Ações de Gestão")
        col1, col2 = st.columns(2)
        with col1:
            csv = st.session_state.leads_db.to_csv(index=False).encode("utf-8")
            st.download_button("Exportar Base de Dados (CSV)", data=csv, file_name="exportacao_leads_dottz.csv", mime="text/csv")
        with col2:
            projetos_apagar = [""] + [f"{int(pd.to_numeric(row['ID'], errors='coerce'))} | Projeto: {row['Projeto']} | Cliente: {row['Cliente']}" for _, row in st.session_state.leads_db.iterrows()]
            lead_apagar = st.selectbox("Eliminar Registo de Projeto", projetos_apagar)
            if st.button("Eliminar Lead") and lead_apagar != "":
                id_to_delete = int(lead_apagar.split(" | ")[0])
                safe_ids = pd.to_numeric(st.session_state.leads_db["ID"], errors="coerce").fillna(0).astype(int)
                st.session_state.leads_db = st.session_state.leads_db[safe_ids != id_to_delete].reset_index(drop=True)
                st.session_state.leads_db, _ = sync_financial_math(st.session_state.leads_db)
                save_table("leads_db", st.session_state.leads_db)
                st.success("Registo do projeto eliminado com sucesso.")
                st.rerun()
    else:
        st.info("Ainda não existem leads.")

# --- 3. INTERAÇÕES E FOLLOW-UPS ---
with tab_comunicacao:
    st.markdown("### Registar Interação e Orçamentos")
    if not st.session_state.leads_db.empty:
        safe_ids_series = pd.to_numeric(st.session_state.leads_db["ID"], errors="coerce").fillna(0).astype(int)
        projeto_ids = safe_ids_series.tolist()
        projeto_preselecionado = st.session_state.get("selected_project_id")
        try:
            indice_projeto = projeto_ids.index(int(projeto_preselecionado)) if projeto_preselecionado is not None and int(projeto_preselecionado) in projeto_ids else 0
        except:
            indice_projeto = 0
            
        nomes_projetos = {int(safe_ids_series.iloc[i]): f"{row['Projeto']} | {row['Cliente']}" for i, row in enumerate(st.session_state.leads_db.to_dict('records'))}
        projeto_id = st.selectbox("Selecionar Projeto", projeto_ids, index=indice_projeto, key="interaction_project_id", format_func=nomes_projetos.get)
        
        idx = get_lead_index(projeto_id)
        
        if idx is not None:
            projeto_selecionado = st.session_state.leads_db.at[idx, "Projeto"]
            historico_atual = st.session_state.leads_db.at[idx, "Notas"]

            construtores = st.session_state.builders_db
            empresas_disponiveis = sorted(construtores["Nome"].dropna().astype(str).str.strip().loc[lambda nomes: nomes != ""].unique().tolist()) if "Nome" in construtores.columns else []

            st.markdown(f"### Projeto: {projeto_selecionado}")
            st.markdown("### Empresas de Construção")
            id_projeto = int(pd.to_numeric(st.session_state.leads_db.at[idx, "ID"], errors="coerce"))
            for numero, (coluna_empresa, coluna_data, coluna_valor, coluna_follow, coluna_anexo) in enumerate(zip(EMPRESAS_CONSTRUCAO, DATAS_ORCAMENTO, VALORES_ORCAMENTO, FOLLOW_UPS_EMPRESA, ANEXOS_EMPRESA), start=1):
                coluna_empresa_ui, coluna_data_ui, coluna_valor_ui, coluna_follow_ui, coluna_anexo_ui = st.columns([1.6, 1, 1.2, 1, 0.7])
                empresa_atual = "" if pd.isna(st.session_state.leads_db.at[idx, coluna_empresa]) else str(st.session_state.leads_db.at[idx, coluna_empresa])
                opcoes_empresa = [""] + empresas_disponiveis
                with coluna_empresa_ui: st.selectbox(f"Empresa de Construção {numero}", opcoes_empresa, index=opcoes_empresa.index(empresa_atual) if empresa_atual in opcoes_empresa else 0, key=f"emp_{id_projeto}_{numero}", on_change=guardar_campo_projeto, args=(id_projeto, coluna_empresa, f"emp_{id_projeto}_{numero}"))
                
                data_atual = st.session_state.leads_db.at[idx, coluna_data]
                data_atual = None if pd.isna(data_atual) or data_atual == "" else pd.to_datetime(data_atual).date()
                with coluna_data_ui: st.date_input(f"Entrega {numero}", value=data_atual, key=f"dta_{id_projeto}_{numero}", on_change=guardar_campo_projeto, args=(id_projeto, coluna_data, f"dta_{id_projeto}_{numero}"))
                
                valor_atual = None if pd.isna(st.session_state.leads_db.at[idx, coluna_valor]) else float(st.session_state.leads_db.at[idx, coluna_valor])
                with coluna_valor_ui: st.number_input(f"Valor {numero}", min_value=0.0, value=valor_atual, step=1000.0, format="%.0f", key=f"val_{id_projeto}_{numero}", on_change=guardar_campo_projeto, args=(id_projeto, coluna_valor, f"val_{id_projeto}_{numero}", True))
                
                follow_atual = st.session_state.leads_db.at[idx, coluna_follow]
                follow_atual = None if pd.isna(follow_atual) or follow_atual == "" else pd.to_datetime(follow_atual).date()
                with coluna_follow_ui: st.date_input(f"Follow up", value=follow_atual, key=f"fol_{id_projeto}_{numero}", on_change=guardar_campo_projeto, args=(id_projeto, coluna_follow, f"fol_{id_projeto}_{numero}"))
                
                with coluna_anexo_ui:
                    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                    anexo_atual = st.session_state.leads_db.at[idx, coluna_anexo]
                    if pd.notna(anexo_atual) and anexo_atual != "":
                        ca1, ca2 = st.columns([1, 1])
                        with ca1:
                            try:
                                res = supabase.storage.from_("anexos").download(anexo_atual)
                                st.download_button("📥", res, file_name=anexo_atual, key=f"dl_emp_{id_projeto}_{numero}")
                            except: pass
                        with ca2:
                            if st.button("❌", key=f"del_emp_{id_projeto}_{numero}"):
                                try: supabase.storage.from_("anexos").remove([anexo_atual])
                                except: pass
                                st.session_state.leads_db.at[idx, coluna_anexo] = ""
                                save_table("leads_db", st.session_state.leads_db)
                                st.rerun()
                    else:
                        upl = st.file_uploader(f"Anexar a Empresa {numero}", key=f"upl_emp_{id_projeto}_{numero}", label_visibility="collapsed")
                        if upl:
                            path = save_uploaded_file(upl, f"emp{numero}_{id_projeto}")
                            if path is not None:
                                st.session_state.leads_db.at[idx, coluna_anexo] = path
                                save_table("leads_db", st.session_state.leads_db)
                                st.rerun()
            
            if pd.isna(historico_atual) or str(historico_atual).strip() == "": historico_atual = "Sem interações anteriores."
            with st.expander("Ver Histórico Atual deste Projeto", expanded=True): st.text(historico_atual)
            
            with st.form("form_interacao", clear_on_submit=True):
                data_interacao = st.date_input("Data da Interação", date.today())
                tipo = st.selectbox("Tipo de Comunicação", ["Email", "Chamada", "Reunião Presencial", "Teams/Zoom", "WhatsApp"])
                resumo = st.text_area("Resumo da Conversa")
                novo_follow_up = st.date_input("Agendar Próximo Follow-up Global", date.today() + timedelta(days=3))
                if st.form_submit_button("Registar Interação"):
                    historico_limpo = historico_atual if historico_atual != 'Sem interações anteriores.' else ''
                    st.session_state.leads_db.at[idx, "Notas"] = f"[{data_interacao.strftime('%d/%m/%Y')} {tipo}]: {resumo}\n{historico_limpo}"
                    st.session_state.leads_db.at[idx, "Próximo Follow-up"] = novo_follow_up
                    save_table("leads_db", st.session_state.leads_db)
                    st.success("Interação registada com sucesso!")
                    st.rerun() 
    else:
        st.info("Ainda não existem leads no sistema.")

# --- 4. ABA ARQUITECTOS ---
with tab_arquitectos:
    st.markdown("### Base de Dados de Arquitectos")
    with st.expander("➕ Adicionar Arquitecto"):
        with st.form("form_add_arquitecto", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1: arq_nome = st.text_input("Nome"); arq_resp = st.text_input("Responsável")
            with c2: arq_tel = st.text_input("Telefone"); arq_email = st.text_input("Email")
            with c3: arq_dist = st.text_input("Distrito")
            st.markdown("**Estado do Contacto**")
            b1, b2, b3, b4 = st.columns(4)
            with b1: arq_contactado = st.selectbox("Contactado", OPCOES_SIM_NAO, index=1)
            with b2: arq_reuniao = st.selectbox("Reunião", OPCOES_SIM_NAO, index=1)
            with b3: arq_interessado = st.selectbox("Interessado", OPCOES_SIM_NAO, index=1)
            with b4: arq_parceria = st.selectbox("Parceria", OPCOES_SIM_NAO, index=1)
            if st.form_submit_button("Confirmar e Adicionar Arquitecto"):
                if not arq_nome.strip(): st.warning("O campo 'Nome' é obrigatório.")
                else:
                    novo_arq = {"Nome": arq_nome.strip(), "Responsável": arq_resp.strip(), "Telefone": arq_tel.strip(), "Email": arq_email.strip(), "Distrito": arq_dist.strip(), "Contactado": arq_contactado, "Reunião": arq_reuniao, "Interessado": arq_interessado, "Parceria": arq_parceria}
                    st.session_state.architects_db = pd.concat([st.session_state.architects_db, pd.DataFrame([novo_arq])], ignore_index=True)
                    save_table("architects_db", st.session_state.architects_db)
                    st.success("Arquitecto adicionado com sucesso!")
                    st.rerun()

    st.markdown("#### Quadro de Arquitectos (Editável)")
    f_arq1, f_arq2 = st.columns(2)
    pesq_arq_nome = f_arq1.text_input("Filtrar por Nome", key="filtro_arq_nome")
    distritos_arq = get_clean_list(st.session_state.architects_db, "Distrito")
    pesq_arq_dist = f_arq2.selectbox("Filtrar por Distrito", distritos_arq, key="filtro_arq_dist")
    df_arq_view = st.session_state.architects_db.copy()
    if pesq_arq_nome.strip(): df_arq_view = df_arq_view[df_arq_view["Nome"].astype(str).str.contains(pesq_arq_nome.strip(), case=False, na=False)]
    if pesq_arq_dist != "Todos": df_arq_view = df_arq_view[df_arq_view["Distrito"] == pesq_arq_dist]

    edited_arq = st.data_editor(
        df_arq_view,
        column_order=cols_arq_todas,
        column_config={
            "Nome": st.column_config.TextColumn("Nome", required=True), "Responsável": st.column_config.TextColumn("Responsável"), "Telefone": st.column_config.TextColumn("Telefone"), "Email": st.column_config.TextColumn("Email"), "Distrito": st.column_config.TextColumn("Distrito"),
            "Contactado": st.column_config.SelectboxColumn("Contactado", options=OPCOES_SIM_NAO, default="🔴 Não"), "Reunião": st.column_config.SelectboxColumn("Reunião", options=OPCOES_SIM_NAO, default="🔴 Não"), "Interessado": st.column_config.SelectboxColumn("Interessado", options=OPCOES_SIM_NAO, default="🔴 Não"), "Parceria": st.column_config.SelectboxColumn("Parceria", options=OPCOES_SIM_NAO, default="🔴 Não"),
        },
        use_container_width=True, hide_index=True, num_rows="dynamic", key="editor_arquitectos"
    )

    if not edited_arq.equals(df_arq_view):
        st.session_state.architects_db.update(edited_arq)
        novas_linhas = edited_arq.loc[~edited_arq.index.isin(st.session_state.architects_db.index)].copy()
        if not novas_linhas.empty:
            for c in cols_arq_bool: novas_linhas[c] = novas_linhas[c].fillna("🔴 Não").replace("", "🔴 Não")
            st.session_state.architects_db = pd.concat([st.session_state.architects_db, novas_linhas])
        apagados = df_arq_view.index.difference(edited_arq.index)
        if not apagados.empty: st.session_state.architects_db = st.session_state.architects_db.drop(apagados)
        st.session_state.architects_db = st.session_state.architects_db.reset_index(drop=True)
        save_table("architects_db", st.session_state.architects_db)
        st.rerun()

    if not st.session_state.architects_db.empty:
        st.markdown("---")
        col_del1, col_del2 = st.columns([3, 1])
        op_del_arq = [""] + [f"{idx} | {row['Nome']}" for idx, row in st.session_state.architects_db.iterrows()]
        arq_del = col_del1.selectbox("Remover Arquitecto específico:", op_del_arq, key="del_a")
        if col_del1.button("🗑️ Eliminar Selecionado") and arq_del:
            st.session_state.architects_db = st.session_state.architects_db.drop(int(arq_del.split(" | ")[0])).reset_index(drop=True)
            save_table("architects_db", st.session_state.architects_db)
            st.rerun()
        with col_del2:
            st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
            if st.button("⚠️ Esvaziar Tabela"):
                st.session_state.architects_db = pd.DataFrame(columns=cols_arq_todas)
                save_table("architects_db", st.session_state.architects_db)
                st.rerun()

# --- 5. ABA CONSTRUCTORES ---
with tab_construtores:
    st.markdown("### Base de Dados de Constructores")
    with st.expander("➕ Adicionar Construtor"):
        with st.form("form_add_construtor", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1: con_nome = st.text_input("Nome"); con_alvara = st.text_input("Alvará"); con_dist = st.text_input("Distrito")
            with c2: con_resp = st.text_input("Responsável"); con_funcao = st.text_input("Função")
            with c3: con_tel = st.text_input("Telefone"); con_email = st.text_input("Email")
            st.markdown("**Estado do Contacto**")
            b1, b2, b3 = st.columns(3)
            with b1: con_contactado = st.selectbox("Contactado", OPCOES_SIM_NAO, index=1)
            with b2: con_reuniao = st.selectbox("Reunião", OPCOES_SIM_NAO, index=1)
            with b3: con_parceria = st.selectbox("Parceria", OPCOES_SIM_NAO, index=1)
            if st.form_submit_button("Confirmar e Adicionar Construtor"):
                if not con_nome.strip(): st.warning("O campo 'Nome' é obrigatório.")
                else:
                    novo_con = {"Nome": con_nome.strip(), "Alvará": con_alvara.strip(), "Distrito": con_dist.strip(), "Responsável": con_resp.strip(), "Função": con_funcao.strip(), "Telefone": con_tel.strip(), "Email": con_email.strip(), "Contactado": con_contactado, "Reunião": con_reuniao, "Parceria": con_parceria}
                    st.session_state.builders_db = pd.concat([st.session_state.builders_db, pd.DataFrame([novo_con])], ignore_index=True)
                    save_table("builders_db", st.session_state.builders_db)
                    st.success("Construtor adicionado com sucesso!")
                    st.rerun()

    st.markdown("#### Quadro de Constructores (Editável)")
    f_con1, f_con2, f_con3 = st.columns(3)
    pesq_con_nome = f_con1.text_input("Filtrar por Nome", key="filtro_con_nome")
    distritos_con = get_clean_list(st.session_state.builders_db, "Distrito")
    pesq_con_dist = f_con2.selectbox("Filtrar por Distrito", distritos_con, key="filtro_con_dist")
    pesq_con_alv = f_con3.text_input("Filtrar por Alvará", key="filtro_con_alv")
    df_con_view = st.session_state.builders_db.copy()
    if pesq_con_nome.strip(): df_con_view = df_con_view[df_con_view["Nome"].astype(str).str.contains(pesq_con_nome.strip(), case=False, na=False)]
    if pesq_con_dist != "Todos": df_con_view = df_con_view[df_con_view["Distrito"] == pesq_con_dist]
    if pesq_con_alv.strip(): df_con_view = df_con_view[df_con_view["Alvará"].astype(str).str.contains(pesq_con_alv.strip(), case=False, na=False)]

    edited_con = st.data_editor(
        df_con_view,
        column_order=cols_const_todas,
        column_config={
            "Nome": st.column_config.TextColumn("Nome", required=True), "Alvará": st.column_config.TextColumn("Alvará"), "Distrito": st.column_config.TextColumn("Distrito"), "Responsável": st.column_config.TextColumn("Responsável"), "Função": st.column_config.TextColumn("Função"), "Telefone": st.column_config.TextColumn("Telefone"), "Email": st.column_config.TextColumn("Email"),
            "Contactado": st.column_config.SelectboxColumn("Contactado", options=OPCOES_SIM_NAO, default="🔴 Não"), "Reunião": st.column_config.SelectboxColumn("Reunião", options=OPCOES_SIM_NAO, default="🔴 Não"), "Parceria": st.column_config.SelectboxColumn("Parceria", options=OPCOES_SIM_NAO, default="🔴 Não"),
        },
        use_container_width=True, hide_index=True, num_rows="dynamic", key="editor_constructores"
    )

    if not edited_con.equals(df_con_view):
        st.session_state.builders_db.update(edited_con)
        novas_linhas = edited_con.loc[~edited_con.index.isin(st.session_state.builders_db.index)].copy()
        if not novas_linhas.empty:
            for c in cols_const_bool: novas_linhas[c] = novas_linhas[c].fillna("🔴 Não").replace("", "🔴 Não")
            st.session_state.builders_db = pd.concat([st.session_state.builders_db, novas_linhas])
        apagados = df_con_view.index.difference(edited_con.index)
        if not apagados.empty: st.session_state.builders_db = st.session_state.builders_db.drop(apagados)
        st.session_state.builders_db = st.session_state.builders_db.reset_index(drop=True)
        save_table("builders_db", st.session_state.builders_db)
        st.rerun()

    if not st.session_state.builders_db.empty:
        st.markdown("---")
        col_del1, col_del2 = st.columns([3, 1])
        op_del_con = [""] + [f"{idx} | {row['Nome']}" for idx, row in st.session_state.builders_db.iterrows()]
        con_del = col_del1.selectbox("Remover Construtor específico:", op_del_con, key="del_c")
        if col_del1.button("🗑️ Eliminar Selecionado") and con_del:
            st.session_state.builders_db = st.session_state.builders_db.drop(int(con_del.split(" | ")[0])).reset_index(drop=True)
            save_table("builders_db", st.session_state.builders_db)
            st.rerun()
        with col_del2:
            st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
            if st.button("⚠️ Esvaziar Tabela", key="clr_c"):
                st.session_state.builders_db = pd.DataFrame(columns=cols_const_todas)
                save_table("builders_db", st.session_state.builders_db)
                st.rerun()

# --- 6. TCT ---
with tab_tct:
    st.markdown("### Gestão TCT")
    edited_tct = st.data_editor(
        st.session_state.tct_db,
        column_order=cols_tct_base,
        column_config={
            "ID": st.column_config.NumberColumn("ID", disabled=True),
            "Fase": st.column_config.SelectboxColumn("Fase", options=FASES_ATUAIS),
            "Valor Estimado": st.column_config.NumberColumn("Valor Estimado", format="%.0f €", step=1000.0),
            "% DBS": st.column_config.NumberColumn("% DBS", format="%.2f %%"),
            "Valor da % DBS": st.column_config.NumberColumn("Valor da % DBS", format="%.0f €", disabled=True),
            "Inter": st.column_config.TextColumn("Inter"),
            "% Inter": st.column_config.NumberColumn("% Inter", format="%.2f %%"),
            "Valor da % Inter": st.column_config.NumberColumn("Valor da % Inter", format="%.0f €", disabled=True)
        },
        use_container_width=True, hide_index=True, num_rows="dynamic", key="tct_editor"
    )
    if not edited_tct.equals(st.session_state.tct_db):
        temp_ids = pd.to_numeric(st.session_state.tct_db["ID"], errors="coerce").dropna()
        max_id = int(temp_ids.max()) if not temp_ids.empty else 0
        for idx in edited_tct.index:
            if pd.isna(edited_tct.at[idx, "ID"]) or str(edited_tct.at[idx, "ID"]).strip() == "":
                max_id += 1
                edited_tct.at[idx, "ID"] = max_id
        st.session_state.tct_db = edited_tct
        st.session_state.tct_db, _ = sync_financial_math(st.session_state.tct_db)
        save_table("tct_db", st.session_state.tct_db)
        st.rerun()

    st.markdown("---")
    st.markdown("### Resumo de Projetos")
    c1, c2, c3, c4 = st.columns(4)
    tot_proj_tct = len(edited_tct)
    adj_tct = edited_tct[edited_tct["Fase"] == "🟢 Adjudicado"]
    tot_adj_tct = len(adj_tct)
    val_tot_tct = edited_tct["Valor Estimado"].apply(parse_currency).sum()
    val_dbs_adj_tct = pd.to_numeric(adj_tct["Valor da % DBS"], errors='coerce').fillna(0.0).sum()
    
    c1.metric("Total de Projetos", tot_proj_tct)
    c2.metric("Projetos Adjudicados", tot_adj_tct)
    c3.metric("Valor Total Estimado", f"{int(val_tot_tct):,} €".replace(",", " "))
    c4.metric("Valor % DBS Adjudicado", f"{int(val_dbs_adj_tct):,} €".replace(",", " "))

# --- 7. ALCA ---
with tab_alca:
    st.markdown("### Gestão ALCA")
    edited_alca = st.data_editor(
        st.session_state.alca_db,
        column_order=cols_tct_base,
        column_config={
            "ID": st.column_config.NumberColumn("ID", disabled=True),
            "Fase": st.column_config.SelectboxColumn("Fase", options=FASES_ATUAIS),
            "Valor Estimado": st.column_config.NumberColumn("Valor Estimado", format="%.0f €", step=1000.0),
            "% DBS": st.column_config.NumberColumn("% DBS", format="%.2f %%"),
            "Valor da % DBS": st.column_config.NumberColumn("Valor da % DBS", format="%.0f €", disabled=True),
            "Inter": st.column_config.TextColumn("Inter"),
            "% Inter": st.column_config.NumberColumn("% Inter", format="%.2f %%"),
            "Valor da % Inter": st.column_config.NumberColumn("Valor da % Inter", format="%.0f €", disabled=True)
        },
        use_container_width=True, hide_index=True, num_rows="dynamic", key="alca_editor"
    )
    if not edited_alca.equals(st.session_state.alca_db):
        temp_ids = pd.to_numeric(st.session_state.alca_db["ID"], errors="coerce").dropna()
        max_id = int(temp_ids.max()) if not temp_ids.empty else 0
        for idx in edited_alca.index:
            if pd.isna(edited_alca.at[idx, "ID"]) or str(edited_alca.at[idx, "ID"]).strip() == "":
                max_id += 1
                edited_alca.at[idx, "ID"] = max_id
        st.session_state.alca_db = edited_alca
        st.session_state.alca_db, _ = sync_financial_math(st.session_state.alca_db)
        save_table("alca_db", st.session_state.alca_db)
        st.rerun()

    st.markdown("---")
    st.markdown("### Resumo de Projetos")
    c1, c2, c3, c4 = st.columns(4)
    tot_proj_alca = len(edited_alca)
    adj_alca = edited_alca[edited_alca["Fase"] == "🟢 Adjudicado"]
    tot_adj_alca = len(adj_alca)
    val_tot_alca = edited_alca["Valor Estimado"].apply(parse_currency).sum()
    val_dbs_adj_alca = pd.to_numeric(adj_alca["Valor da % DBS"], errors='coerce').fillna(0.0).sum()
    
    c1.metric("Total de Projetos", tot_proj_alca)
    c2.metric("Projetos Adjudicados", tot_adj_alca)
    c3.metric("Valor Total Estimado", f"{int(val_tot_alca):,} €".replace(",", " "))
    c4.metric("Valor % DBS Adjudicado", f"{int(val_dbs_adj_alca):,} €".replace(",", " "))

# --- 8. FAMO ---
with tab_famo:
    st.markdown("### Gestão FAMO")
    edited_famo = st.data_editor(
        st.session_state.famo_db,
        column_order=cols_tct_base,
        column_config={
            "ID": st.column_config.NumberColumn("ID", disabled=True),
            "Fase": st.column_config.SelectboxColumn("Fase", options=FASES_ATUAIS),
            "Valor Estimado": st.column_config.NumberColumn("Valor Estimado", format="%.0f €", step=1000.0),
            "% DBS": st.column_config.NumberColumn("% DBS", format="%.2f %%"),
            "Valor da % DBS": st.column_config.NumberColumn("Valor da % DBS", format="%.0f €", disabled=True),
            "Inter": st.column_config.TextColumn("Inter"),
            "% Inter": st.column_config.NumberColumn("% Inter", format="%.2f %%"),
            "Valor da % Inter": st.column_config.NumberColumn("Valor da % Inter", format="%.0f €", disabled=True)
        },
        use_container_width=True, hide_index=True, num_rows="dynamic", key="famo_editor"
    )
    if not edited_famo.equals(st.session_state.famo_db):
        temp_ids = pd.to_numeric(st.session_state.famo_db["ID"], errors="coerce").dropna()
        max_id = int(temp_ids.max()) if not temp_ids.empty else 0
        for idx in edited_famo.index:
            if pd.isna(edited_famo.at[idx, "ID"]) or str(edited_famo.at[idx, "ID"]).strip() == "":
                max_id += 1
                edited_famo.at[idx, "ID"] = max_id
        st.session_state.famo_db = edited_famo
        st.session_state.famo_db, _ = sync_financial_math(st.session_state.famo_db)
        save_table("famo_db", st.session_state.famo_db)
        st.rerun()

    st.markdown("---")
    st.markdown("### Resumo de Projetos")
    c1, c2, c3, c4 = st.columns(4)
    tot_proj_famo = len(edited_famo)
    adj_famo = edited_famo[edited_famo["Fase"] == "🟢 Adjudicado"]
    tot_adj_famo = len(adj_famo)
    val_tot_famo = edited_famo["Valor Estimado"].apply(parse_currency).sum()
    val_dbs_adj_famo = pd.to_numeric(adj_famo["Valor da % DBS"], errors='coerce').fillna(0.0).sum()
    
    c1.metric("Total de Projetos", tot_proj_famo)
    c2.metric("Projetos Adjudicados", tot_adj_famo)
    c3.metric("Valor Total Estimado", f"{int(val_tot_famo):,} €".replace(",", " "))
    c4.metric("Valor % DBS Adjudicado", f"{int(val_dbs_adj_famo):,} €".replace(",", " "))

# --- 9. CALENDÁRIO ---
with tab_calendario:
    nomes_meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    st.session_state.setdefault("followup_calendar_month", date.today().replace(day=1))
    mes_atual = st.session_state["followup_calendar_month"]
    
    coluna_anterior, coluna_titulo, coluna_seguinte = st.columns([1, 3, 1])
    with coluna_anterior:
        if st.button("Anterior", key="cal_prev"):
            mes_index = mes_atual.year * 12 + mes_atual.month - 2
            st.session_state["followup_calendar_month"] = date(mes_index // 12, mes_index % 12 + 1, 1)
            st.session_state["selected_followup_date"] = None
            st.rerun()
    with coluna_seguinte:
        if st.button("Seguinte", key="cal_next"):
            mes_index = mes_atual.year * 12 + mes_atual.month
            st.session_state["followup_calendar_month"] = date(mes_index // 12, mes_index % 12 + 1, 1)
            st.session_state["selected_followup_date"] = None
            st.rerun()

    mes_atual = st.session_state["followup_calendar_month"]
    with coluna_titulo: st.markdown(f"### {nomes_meses[mes_atual.month - 1]} {mes_atual.year}")

    eventos_por_dia = {}
    try: eventos_por_dia.setdefault(date(mes_atual.year, mes_atual.month, 10), []).append({"tipo": "⚠️ Automático", "aba": "Pagamentos", "texto": "Emitir Faturas (Dia 10)", "id": None})
    except ValueError: pass

    for idx, row in st.session_state.leads_db.iterrows():
        val_f = row.get("Próximo Follow-up")
        if pd.notna(val_f) and val_f != "":
            dt_f = pd.to_datetime(val_f, errors="coerce")
            if pd.notna(dt_f) and dt_f.year == mes_atual.year and dt_f.month == mes_atual.month:
                eventos_por_dia.setdefault(dt_f.date(), []).append({"tipo": "Pipeline", "aba": "Pipeline de Negócios", "texto": f"Pipeline: {row.get('Projeto', '')} ({row.get('Cliente', '')})", "id": row.get("ID")})
        for i in range(1, 6):
            val_f2 = row.get(f"Follow up Empresa {i}")
            if pd.notna(val_f2) and val_f2 != "":
                dt_f2 = pd.to_datetime(val_f2, errors="coerce")
                if pd.notna(dt_f2) and dt_f2.year == mes_atual.year and dt_f2.month == mes_atual.month:
                    eventos_por_dia.setdefault(dt_f2.date(), []).append({"tipo": "Construtor", "aba": "Interações & Follow-Ups", "texto": f"Orçamento {str(row.get(f'Empresa de Construção {i}', f'Empresa {i}'))} - {str(row.get('Projeto', ''))}", "id": row.get("ID")})

    if not st.session_state.todo_db.empty:
        for idx, row in st.session_state.todo_db.iterrows():
            val_f = row.get("Follow up")
            if pd.notna(val_f) and val_f != "":
                dt_f = pd.to_datetime(val_f, errors="coerce")
                if pd.notna(dt_f) and dt_f.year == mes_atual.year and dt_f.month == mes_atual.month:
                    eventos_por_dia.setdefault(dt_f.date(), []).append({"tipo": "To Do", "aba": "To do List", "texto": f"Tarefa: {row.get('Tarefa', '')}", "id": None})

    dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    for coluna, dia_semana in zip(st.columns(7), dias_semana): coluna.markdown(f"**{dia_semana}**")

    for semana in py_calendar.monthcalendar(mes_atual.year, mes_atual.month):
        for coluna, dia in zip(st.columns(7), semana):
            with coluna:
                with st.container(border=True):
                    if dia == 0: st.write(" ")
                    elif date(mes_atual.year, mes_atual.month, dia) in eventos_por_dia:
                        if st.button(str(dia), key=f"cal_{mes_atual.year}_{mes_atual.month}_{dia}", type="primary", use_container_width=True):
                            st.session_state["selected_followup_date"] = date(mes_atual.year, mes_atual.month, dia)
                    else: st.markdown(f"**{dia}**")

    data_sel = st.session_state.get("selected_followup_date")
    if data_sel and data_sel.year == mes_atual.year and data_sel.month == mes_atual.month:
        st.markdown(f"### Detalhes de {data_sel.strftime('%d/%m/%Y')}")
        for i, ev in enumerate(eventos_por_dia.get(data_sel, [])):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{ev['tipo']}** | {ev['texto']}")
            if ev["id"] is not None:
                if c2.button(f"Ir para {ev['aba']}", key=f"btn_go_{i}_{ev['id']}"):
                    st.session_state["selected_project_id"] = int(ev["id"])
                    st.success(f"Projeto colocado na memória. Clica no menu da aba **{ev['aba']}** lá em cima!")

# --- 10. FINANCEIRO ---
with tab_financeiro:
    st.markdown("### Painel Financeiro e Estatístico")
    if st.session_state.leads_db.empty: st.info("Ainda não existem projectos registados no pipeline.")
    else:
        st.markdown("**Edição e Resumo Financeiro de Projectos**")
        df_fin = st.session_state.leads_db[["Cliente", "Projeto", "Fase", "Valor Estimado", "% DBS", "Valor da % DBS", "Inter", "% Inter", "Valor da % Inter"]].copy()
        df_fin["Inter"] = df_fin["Inter"].astype(str).replace("nan", "").replace("None", "")
        for col in ["% DBS", "Valor da % DBS", "% Inter", "Valor da % Inter"]: df_fin[col] = pd.to_numeric(df_fin[col], errors='coerce').fillna(0.0)
        
        edited_fin = st.data_editor(
            df_fin,
            column_order=["Cliente", "Projeto", "Fase", "Valor Estimado", "% DBS", "Valor da % DBS", "Inter", "% Inter", "Valor da % Inter"],
            column_config={
                "Fase": st.column_config.SelectboxColumn("Fase", options=FASES_ATUAIS),
                "Valor Estimado": st.column_config.NumberColumn("Valor Estimado", format="%.0f €", step=1000.0),
                "% DBS": st.column_config.NumberColumn("% DBS", format="%.2f %%"), "Valor da % DBS": st.column_config.NumberColumn("Valor da % DBS", format="%.0f €", disabled=True),
                "Inter": st.column_config.TextColumn("Inter"), "% Inter": st.column_config.NumberColumn("% Inter", format="%.2f %%"), "Valor da % Inter": st.column_config.NumberColumn("Valor da % Inter", format="%.0f €", disabled=True),
            }, use_container_width=True, hide_index=True, key="fin_editor"
        )
        if not edited_fin.equals(df_fin):
            for col in df_fin.columns: st.session_state.leads_db[col] = edited_fin[col]
            st.session_state.leads_db, _ = sync_financial_math(st.session_state.leads_db)
            save_table("leads_db", st.session_state.leads_db)
            st.rerun()

        st.markdown("---")
        st.markdown("### Totais Globais e Médias")
        val_estimados = edited_fin["Valor Estimado"].apply(parse_currency)
        total_estimado = val_estimados.sum()
        c_est = (val_estimados > 0).sum()
        
        df_adjudicados = edited_fin[edited_fin["Fase"] == "🟢 Adjudicado"]
        val_adjudicados = df_adjudicados["Valor Estimado"].apply(parse_currency)
        total_adjudicado = val_adjudicados.sum()
        c_adj = (val_adjudicados > 0).sum()
        
        val_dbs = edited_fin["Valor da % DBS"]
        total_perc_dbs = val_dbs.sum()
        c_dbs = (val_dbs > 0).sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Valor Estimado", f"{int(total_estimado):,} €".replace(",", " "), delta=f"Média: {int(total_estimado / c_est if c_est > 0 else 0):,} €".replace(",", " "), delta_color="off")
        c2.metric("Total Valor Adjudicado", f"{int(total_adjudicado):,} €".replace(",", " "), delta=f"Média: {int(total_adjudicado / c_adj if c_adj > 0 else 0):,} €".replace(",", " "), delta_color="off")
        c3.metric("Total Valor da % DBS", f"{int(total_perc_dbs):,} €".replace(",", " "), delta=f"Média: {int(total_perc_dbs / c_dbs if c_dbs > 0 else 0):,} €".replace(",", " "), delta_color="off")

# --- 11. PAGAMENTOS ---
with tab_pagamentos:
    st.markdown("### Mapa Cronológico de Pagamentos")
    projetos_cadastrados = st.session_state.leads_db["Projeto"].dropna().loc[lambda x: x!=""].unique().tolist()
    proj_pag = st.selectbox("Selecione o Projeto para gerir o Plano de Pagamentos", [""] + projetos_cadastrados)

    if proj_pag:
        mask_inst = st.session_state.installments_db["Projeto"] == proj_pag
        has_plan = mask_inst.any()
        with st.expander("⚙️ Configurar / Gerar Plano de Pagamentos", expanded=not has_plan):
            with st.form("form_gen_pagamentos", clear_on_submit=False):
                proj_row = st.session_state.leads_db[st.session_state.leads_db["Projeto"] == proj_pag].iloc[0]
                val_dbs_def = pd.to_numeric(proj_row.get("Valor da % DBS", 0.0), errors="coerce")
                val_est_def = parse_currency(proj_row.get("Valor Estimado", 0.0))
                default_val = float(val_dbs_def) if pd.notna(val_dbs_def) and val_dbs_def > 0 else float(val_est_def)
                
                c1, c2, c3, c4 = st.columns(4)
                with c1: val_global = st.number_input("Valor Global (€)", min_value=0.0, value=default_val, step=1000.0)
                with c2: meses_dur = st.number_input("Meses de duração", min_value=1, value=1, step=1)
                with c3: data_inicio = st.date_input("Data de Início", date.today().replace(day=1))
                m = int(meses_dur)
                val_mensal = val_global / m if m > 0 else 0.0
                try:
                    y_f = data_inicio.year + ((data_inicio.month - 1 + m) // 12)
                    m_f = ((data_inicio.month - 1 + m) % 12) + 1
                    d_f = data_inicio.day
                    while True:
                        try: data_final = date(y_f, m_f, d_f); break
                        except ValueError: d_f -= 1
                except: data_final = data_inicio + timedelta(days=30*m)
                with c4: st.markdown(f"<div style='margin-top:28px'><b>Mensalidade Estimada:</b> {val_mensal:,.2f} €<br><b>Data Final:</b> {data_final.strftime('%d/%m/%Y')}</div>", unsafe_allow_html=True)
                
                if st.form_submit_button("Gerar Plano (Folha Excel)"):
                    if has_plan: st.session_state.installments_db = st.session_state.installments_db[~mask_inst]
                    d = data_inicio.replace(day=1)
                    novos_meses = []
                    for _ in range(m):
                        novos_meses.append({"Projeto": proj_pag, "Mês": d.strftime("%Y-%m"), "Mensalidade (€)": float(val_mensal), "IVA (%)": 23.0, "Valor com IVA (€)": float(val_mensal * 1.23), "IVA IF": "", "Estado": "⚪ Não facturado"})
                        year = d.year + (d.month // 12)
                        month = (d.month % 12) + 1
                        d = d.replace(year=year, month=month, day=1)
                    st.session_state.installments_db = pd.concat([st.session_state.installments_db, pd.DataFrame(novos_meses)], ignore_index=True)
                    st.session_state.installments_db["IVA IF"] = st.session_state.installments_db["IVA IF"].astype(str).replace("nan", "").replace("None", "")
                    save_table("installments_db", st.session_state.installments_db)
                    
                    if proj_pag in st.session_state.payments_db["Projeto"].values: idx_pag = st.session_state.payments_db.index[st.session_state.payments_db["Projeto"] == proj_pag][0]
                    else: st.session_state.payments_db = pd.concat([st.session_state.payments_db, pd.DataFrame([{"Projeto": proj_pag}])], ignore_index=True); idx_pag = st.session_state.payments_db.index[-1]
                    st.session_state.payments_db.at[idx_pag, "Valor Global"] = float(val_global)
                    st.session_state.payments_db.at[idx_pag, "Meses de duração"] = int(m)
                    st.session_state.payments_db.at[idx_pag, "Valor mensal"] = float(val_mensal)
                    st.session_state.payments_db.at[idx_pag, "Data de Início"] = str(data_inicio)
                    st.session_state.payments_db.at[idx_pag, "Data Final"] = str(data_final)
                    save_table("payments_db", st.session_state.payments_db)
                    st.success("Folha Excel de Pagamentos gerada!")
                    st.rerun()

        mask_inst_updated = st.session_state.installments_db["Projeto"] == proj_pag
        if mask_inst_updated.any():
            st.markdown(f"#### Folha de Faturação: {proj_pag}")
            df_proj_inst = st.session_state.installments_db[mask_inst_updated].copy()
            df_proj_inst["IVA IF"] = df_proj_inst["IVA IF"].astype(str).replace("nan", "").replace("None", "")
            edited_inst = st.data_editor(
                df_proj_inst,
                column_order=cols_inst,
                column_config={ "Projeto": st.column_config.TextColumn("Projeto", disabled=True), "Mês": st.column_config.TextColumn("Mês", disabled=True), "Mensalidade (€)": st.column_config.NumberColumn("Mensalidade s/ IVA", format="%.2f €"), "IVA (%)": st.column_config.NumberColumn("IVA (%)", format="%.1f %%"), "Valor com IVA (€)": st.column_config.NumberColumn("Valor c/ IVA", format="%.2f €", disabled=True), "IVA IF": st.column_config.TextColumn("Refª Fatura (IVA IF)"), "Estado": st.column_config.SelectboxColumn("Status de Envio da Fatura", options=ESTADOS_PAGAMENTO) },
                hide_index=True, use_container_width=True, key=f"edit_inst_{proj_pag}"
            )
            if not edited_inst.equals(df_proj_inst):
                for idx in edited_inst.index:
                    v_base = edited_inst.at[idx, "Mensalidade (€)"]
                    v_iva = edited_inst.at[idx, "IVA (%)"]
                    edited_inst.at[idx, "Valor com IVA (€)"] = v_base * (1 + v_iva / 100.0)
                    st.session_state.installments_db.loc[idx] = edited_inst.loc[idx]
                st.session_state.installments_db["IVA IF"] = st.session_state.installments_db["IVA IF"].astype(str).replace("nan", "").replace("None", "")
                save_table("installments_db", st.session_state.installments_db)
                st.rerun()

    st.markdown("---")
    st.markdown("### Quadro Geral de Obras Adjudicadas")
    resumo_data = []
    tot_adj, tot_rec, tot_porpagar, tot_arec = 0.0, 0.0, 0.0, 0.0
    leads_adj = st.session_state.leads_db[st.session_state.leads_db["Fase"] == "🟢 Adjudicado"]
    for idx, row in leads_adj.iterrows():
        p = row["Projeto"]
        val_final_adj = float(pd.to_numeric(row.get("Valor da % DBS", 0.0), errors='coerce')) if pd.notna(pd.to_numeric(row.get("Valor da % DBS", 0.0), errors='coerce')) and float(pd.to_numeric(row.get("Valor da % DBS", 0.0), errors='coerce')) > 0 else float(parse_currency(row["Valor Estimado"]))
        installs = st.session_state.installments_db[st.session_state.installments_db["Projeto"] == p]
        val_rec = pd.to_numeric(installs[installs["Estado"] == "🟢 Recebido"]["Mensalidade (€)"], errors="coerce").sum()
        val_por_pagar = pd.to_numeric(installs[installs["Estado"] == "🟡 Fatura por pagar"]["Mensalidade (€)"], errors="coerce").sum()
        val_a_rec = val_final_adj - val_rec
        resumo_data.append({"Projeto": p, "Valor Adjudicado / DBS": val_final_adj, "Valor Recebido": val_rec, "Faturas por Pagar (🟡)": val_por_pagar, "Valor a Receber": val_a_rec})
        tot_adj += val_final_adj; tot_rec += val_rec; tot_porpagar += val_por_pagar; tot_arec += val_a_rec
        
    if resumo_data:
        st.dataframe(pd.DataFrame(resumo_data).style.format({"Valor Adjudicado / DBS": "{:,.0f} €", "Valor Recebido": "{:,.0f} €", "Faturas por Pagar (🟡)": "{:,.0f} €", "Valor a Receber": "{:,.0f} €"}), hide_index=True, use_container_width=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Adjudicado", f"{int(tot_adj):,} €".replace(",", " "))
        c2.metric("Total Recebido", f"{int(tot_rec):,} €".replace(",", " "))
        c3.metric("Faturas por Pagar", f"{int(tot_porpagar):,} €".replace(",", " "))
        c4.metric("Total a Receber", f"{int(tot_arec):,} €".replace(",", " "))
    else: st.info("Ainda não existem obras classificadas como '🟢 Adjudicado' na Pipeline.")

# --- 12. TO DO LIST ---
with tab_todo:
    st.markdown("### To Do List")
    with st.form("add_todo"):
        c1, c2, c3 = st.columns([2, 3, 1])
        with c1: t_proj = st.text_input("Tarefa")
        with c2: t_passo = st.text_input("Próximos passos")
        with c3: t_date = st.date_input("Follow up", date.today())
        if st.form_submit_button("Adicionar Tarefa"):
            if t_proj.strip() == "" or t_passo.strip() == "": st.warning("Preenche a Tarefa e os Próximos passos.")
            else:
                st.session_state.todo_db = pd.concat([st.session_state.todo_db, pd.DataFrame([{"Tarefa": t_proj, "Próximos passos": t_passo, "Follow up": t_date}])], ignore_index=True)
                save_table("todo_db", st.session_state.todo_db)
                st.success("Tarefa gravada!"); st.rerun()

    if not st.session_state.todo_db.empty:
        edited_todo = st.data_editor(
            st.session_state.todo_db,
            column_order=cols_todo_todas,
            column_config={ "Tarefa": st.column_config.TextColumn("Tarefa", width="medium"), "Próximos passos": st.column_config.TextColumn("Próximos passos", width="large"), "Follow up": st.column_config.DateColumn("Follow up") },
            use_container_width=True, hide_index=True, num_rows="dynamic", key="todo_editor_grid"
        )
        if not edited_todo.equals(st.session_state.todo_db):
            st.session_state.todo_db = edited_todo
            save_table("todo_db", st.session_state.todo_db)
        st.markdown("---")
        col_del_t1, _ = st.columns([3, 1])
        t_del = col_del_t1.selectbox("Selecione a tarefa a apagar de vez:", [""] + [f"{i} | {row.get('Tarefa', '')} - {row['Próximos passos']}" for i, row in st.session_state.todo_db.iterrows()])
        if col_del_t1.button("🗑️ Eliminar Tarefa Selecionada") and t_del != "":
            st.session_state.todo_db = st.session_state.todo_db.drop(int(t_del.split(" | ")[0])).reset_index(drop=True)
            save_table("todo_db", st.session_state.todo_db)
            st.rerun()
    else: st.info("Não há tarefas na tua lista.")

# --- 13. OBJECTIVOS ---
with tab_objectivos:
    st.markdown("### Quadro Global de Objetivos e KPIs (2027)")
    def parse_kpi_input(val):
        try:
            if pd.isna(val): return 0.0
            if isinstance(val, (int, float)): return float(val)
            s = str(val).replace("€", "").replace("%", "").strip().replace(" ", "")
            if "." in s and "," in s:
                if s.rfind(".") > s.rfind(","): s = s.replace(",", "")
                else: s = s.replace(".", "").replace(",", ".")
            elif "," in s: s = s.replace(",", ".")
            elif s.count(".") > 1: s = s.replace(".", "")
            return float(s)
        except: return 0.0

    tot_parc_arq = float((st.session_state.architects_db["Parceria"] == "🟢 Sim").sum()) if "Parceria" in st.session_state.architects_db.columns else 0.0
    tot_parc_const = float((st.session_state.builders_db["Parceria"] == "🟢 Sim").sum()) if "Parceria" in st.session_state.builders_db.columns else 0.0
    tot_proj = float(len(st.session_state.leads_db))
    if not st.session_state.leads_db.empty:
        tot_adj = float((st.session_state.leads_db["Fase"] == "🟢 Adjudicado").sum())
        tot_v_est = st.session_state.leads_db["Valor Estimado"].apply(parse_currency).sum()
        tot_v_adj = st.session_state.leads_db[st.session_state.leads_db["Fase"] == "🟢 Adjudicado"]["Valor Estimado"].apply(parse_currency).sum()
        tot_v_dbs = pd.to_numeric(st.session_state.leads_db["Valor da % DBS"], errors='coerce').fillna(0.0).sum()
        perc_v = float((tot_v_adj / tot_v_est * 100) if tot_v_est > 0 else 0.0)
    else: tot_adj, tot_v_est, tot_v_adj, tot_v_dbs, perc_v = 0.0, 0.0, 0.0, 0.0, 0.0

    def formatar_kpi(val, idx):
        if pd.isna(val): val = 0.0
        if idx in [4, 5]: return f"{int(val):,} €".replace(",", " ")
        elif idx == 6: return f"{val:.1f} %".replace(".", ",")
        else: return str(int(val))

    df_kpi_display = pd.DataFrame({
        "Métricas Globais": ["Total de Parcerias com Arquitectos", "Total de Parcerias com Construtores", "Total de Projectos", "Total de Projectos Adjudicados", "Total de Valor Adjudicado (€)", "Total de Valor da % DBS (€)", "% de Valor (Adjudicado / Estimado) (%)"],
        "Valor Atual": [formatar_kpi(v, i) for i, v in enumerate([tot_parc_arq, tot_parc_const, tot_proj, tot_adj, tot_v_adj, tot_v_dbs, perc_v])],
        "KPIS 2027": ["Total de Parcerias com Arquitectos", "Total de Parcerias com Construtores", "Total de Projectos", "Total de Projectos Adjudicados", "Total de Valor Adjudicado (€)", "Total de Valor da % DBS (€)", "% de Valor (Adjudicado / Estimado) (%)"],
        "Objetivo (Editável)": [formatar_kpi(v, i) for i, v in enumerate(st.session_state.kpi_db["Objetivo"])]
    })

    edited_kpi = st.data_editor(
        df_kpi_display,
        column_order=cols_kpi,
        column_config={ "Métricas Globais": st.column_config.TextColumn("Métricas Globais", disabled=True), "Valor Atual": st.column_config.TextColumn("Valor Atual", disabled=True), "KPIS 2027": st.column_config.TextColumn("KPIS 2027", disabled=True), "Objetivo (Editável)": st.column_config.TextColumn("Objetivo (Editável)") },
        use_container_width=True, hide_index=True, key="kpi_editor"
    )

    if not edited_kpi["Objetivo (Editável)"].equals(df_kpi_display["Objetivo (Editável)"]):
        st.session_state.kpi_db["Objetivo"] = edited_kpi["Objetivo (Editável)"].apply(parse_kpi_input)
        save_table("kpi_db", st.session_state.kpi_db)
        st.rerun()
