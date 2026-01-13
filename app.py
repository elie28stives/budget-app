import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json
import time

# --- CONFIGURATION ---
SHEET_NAME = "Budget_Couple_DB"
TAB_DATA = "Data"
TAB_CONFIG = "Config"
TAB_OBJECTIFS = "Objectifs"
TAB_PATRIMOINE = "Patrimoine"
TAB_COMPTES = "Comptes"
TAB_ABONNEMENTS = "Abonnements"
TAB_PROJETS = "Projets_Config"

USERS = ["Pierre", "Elie"]
TYPES = ["Dépense", "Revenu", "Virement Interne", "Épargne", "Investissement"]
IMPUTATIONS = ["Perso", "Commun (50/50)", "Avance/Cadeau"]
MOIS_FR = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

# --- STYLE CSS MODERNE ---
def apply_modern_style():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Space+Mono:wght@400;700&display=swap');
        
        /* Global Styles */
        .stApp {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
            background-attachment: fixed;
            font-family: 'Outfit', sans-serif;
        }
        
        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Main container */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1400px;
        }
        
        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background: rgba(255, 255, 255, 0.15) !important;
            backdrop-filter: blur(20px);
            border-right: 1px solid rgba(255, 255, 255, 0.3);
        }
        
        section[data-testid="stSidebar"] > div {
            background: transparent !important;
        }
        
        /* Headers */
        h1, h2, h3 {
            font-family: 'Outfit', sans-serif !important;
            font-weight: 800 !important;
            background: linear-gradient(135deg, #fff 0%, #ffecd2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        
        h1 {font-size: 2.5rem !important;}
        h2 {font-size: 2rem !important;}
        h3 {font-size: 1.5rem !important;}
        
        /* Metric cards */
        div[data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            padding: 24px;
            border-radius: 24px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.16);
            border: 1px solid rgba(255, 255, 255, 0.5);
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            position: relative;
            overflow: hidden;
        }
        
        div[data-testid="stMetric"]:hover {
            transform: translateY(-8px) scale(1.02);
            box-shadow: 0 16px 48px rgba(0,0,0,0.24), 0 0 40px rgba(102, 126, 234, 0.3);
        }
        
        div[data-testid="stMetric"]::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        div[data-testid="stMetric"] label {
            font-size: 14px !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #666 !important;
        }
        
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            font-size: 42px !important;
            font-weight: 800 !important;
            font-family: 'Space Mono', monospace !important;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 12px;
            gap: 8px;
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
        
        .stTabs [data-baseweb="tab"] {
            background: transparent;
            color: rgba(255, 255, 255, 0.7);
            font-weight: 600;
            border-radius: 16px;
            padding: 14px 28px;
            border: none;
            transition: all 0.3s ease;
        }
        
        .stTabs [data-baseweb="tab"]:hover {
            background: rgba(255, 255, 255, 0.1);
            color: white;
        }
        
        .stTabs [aria-selected="true"] {
            background: white !important;
            color: #2c3e50 !important;
            box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        }
        
        /* Input fields */
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div > div,
        .stTextArea > div > div > textarea,
        .stDateInput > div > div > input {
            background: white !important;
            border: 2px solid #e0e0e0 !important;
            border-radius: 16px !important;
            padding: 16px 20px !important;
            font-size: 16px !important;
            font-family: 'Outfit', sans-serif !important;
            transition: all 0.3s ease !important;
        }
        
        .stTextInput > div > div > input:focus,
        .stNumberInput > div > div > input:focus,
        .stSelectbox > div > div > div:focus-within,
        .stTextArea > div > div > textarea:focus,
        .stDateInput > div > div > input:focus {
            border-color: #667eea !important;
            box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1) !important;
            transform: translateY(-2px);
        }
        
        .stTextInput > label,
        .stNumberInput > label,
        .stSelectbox > label,
        .stTextArea > label,
        .stDateInput > label {
            font-size: 14px !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: white !important;
        }
        
        /* Buttons */
        .stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 16px !important;
            padding: 16px 32px !important;
            font-size: 16px !important;
            font-weight: 700 !important;
            text-transform: uppercase;
            letter-spacing: 1px;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
            box-shadow: 0 4px 16px rgba(0,0,0,0.12) !important;
            font-family: 'Outfit', sans-serif !important;
        }
        
        .stButton > button:hover {
            transform: translateY(-4px) scale(1.05) !important;
            box-shadow: 0 8px 32px rgba(0,0,0,0.16) !important;
        }
        
        /* Data frames / Tables */
        .stDataFrame {
            background: white;
            border-radius: 24px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.16);
            border: 1px solid rgba(255, 255, 255, 0.5);
        }
        
        /* Progress bars */
        .stProgress > div > div > div > div {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%) !important;
            border-radius: 12px;
        }
        
        /* Expander */
        .streamlit-expanderHeader {
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(20px);
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            color: white !important;
            font-weight: 600;
        }
        
        .streamlit-expanderContent {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.5);
        }
        
        /* Cards */
        .card {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 28px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.16);
            border: 1px solid rgba(255, 255, 255, 0.5);
            margin-bottom: 24px;
            transition: all 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-4px);
            box-shadow: 0 16px 48px rgba(0,0,0,0.24);
        }
        
        /* Account card */
        .account-card {
            background: white;
            border-radius: 24px;
            padding: 28px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.16);
            border: 2px solid transparent;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .account-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            opacity: 0.05;
            transition: opacity 0.3s ease;
        }
        
        .account-card:hover {
            transform: translateY(-6px);
            border-color: #667eea;
            box-shadow: 0 16px 48px rgba(0,0,0,0.24), 0 0 40px rgba(102, 126, 234, 0.2);
        }
        
        .account-card:hover::before {
            opacity: 0.1;
        }
        
        .account-name {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 16px;
            color: #333;
        }
        
        .account-balance {
            font-size: 36px;
            font-weight: 800;
            font-family: 'Space Mono', monospace;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .account-balance.positive {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .account-balance.negative {
            background: linear-gradient(135deg, #ff6a00 0%, #ee0979 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        /* Info boxes */
        .info-box {
            background: linear-gradient(135deg, rgba(79, 172, 254, 0.1) 0%, rgba(0, 242, 254, 0.1) 100%);
            border-left: 4px solid #4facfe;
            color: #0369a1;
            padding: 20px 24px;
            border-radius: 16px;
            margin-bottom: 24px;
            font-weight: 500;
        }
        
        .success-box {
            background: linear-gradient(135deg, rgba(240, 147, 251, 0.1) 0%, rgba(245, 87, 108, 0.1) 100%);
            border-left: 4px solid #f093fb;
            color: #be185d;
            padding: 20px 24px;
            border-radius: 16px;
            margin-bottom: 24px;
            font-weight: 500;
        }
        
        /* Badge */
        .badge {
            display: inline-block;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .badge-success {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
        }
        
        .badge-danger {
            background: linear-gradient(135deg, #ff6a00 0%, #ee0979 100%);
            color: white;
        }
        
        .badge-info {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
        }
        
        .badge-warning {
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
            color: white;
        }
        
        /* Animations */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .fade-in {
            animation: fadeIn 0.6s ease-out;
        }
        
        .slide-up {
            animation: slideUp 0.6s ease-out;
        }
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.3);
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.5);
        }
    </style>
    """, unsafe_allow_html=True)

# --- CONNEXION SECURISEE ---
@st.cache_resource
def get_gspread_client():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"⚠️ Erreur connexion : {e}")
        return None

def get_worksheet(client, sheet_name, tab_name):
    try:
        sh = client.open(sheet_name)
        try: ws = sh.worksheet(tab_name)
        except: ws = sh.add_worksheet(title=tab_name, rows="100", cols="20")
        return ws
    except Exception as e:
        st.error(f"Erreur onglet {tab_name}: {e}"); st.stop()

# --- LECTURE ---
@st.cache_data(ttl=600)
def load_data_from_sheet(tab_name, colonnes):
    client = get_gspread_client()
    if not client: return pd.DataFrame(columns=colonnes)
    ws = get_worksheet(client, SHEET_NAME, tab_name)
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    if df.empty: return pd.DataFrame(columns=colonnes)
    for col in colonnes:
        if col not in df.columns: df[col] = ""
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce').dt.date
    return df

@st.cache_data(ttl=600)
def load_configs_cached():
    return (
        load_data_from_sheet(TAB_CONFIG, ["Type", "Categorie"]),
        load_data_from_sheet(TAB_COMPTES, ["Proprietaire", "Compte"]),
        load_data_from_sheet(TAB_OBJECTIFS, ["Scope", "Categorie", "Montant"]),
        load_data_from_sheet(TAB_ABONNEMENTS, ["Nom", "Montant", "Jour", "Categorie", "Compte_Source", "Proprietaire", "Imputation"]),
        load_data_from_sheet(TAB_PROJETS, ["Projet", "Cible", "Date_Fin"])
    )

# --- ECRITURE ---
def clear_cache(): st.cache_data.clear()

def save_data_to_sheet(tab_name, df):
    client = get_gspread_client()
    ws = get_worksheet(client, SHEET_NAME, tab_name)
    df_save = df.copy()
    if "Date" in df_save.columns: df_save["Date"] = df_save["Date"].astype(str)
    ws.clear()
    if not df_save.empty: ws.update([df_save.columns.values.tolist()] + df_save.values.tolist())
    else: ws.update([df_save.columns.values.tolist()])
    clear_cache()

# --- CALCUL SOLDES ---
def calculer_soldes_reels(df_transac, df_patri, comptes_list):
    soldes = {}
    for compte in comptes_list:
        releve = 0.0
        date_releve = pd.to_datetime("2000-01-01").date()
        if not df_patri.empty:
            df_c = df_patri[df_patri["Compte"] == compte]
            if not df_c.empty:
                last = df_c.sort_values(by="Date", ascending=False).iloc[0]
                releve = float(last["Montant"])
                date_releve = last["Date"]
        
        mouvements = 0.0
        if not df_transac.empty:
            mask = df_transac["Date"] > date_releve
            df_t = df_transac[mask]
            debits = df_t[(df_t["Compte_Source"] == compte) & (df_t["Type"].isin(["Dépense", "Investissement"]))]["Montant"].sum()
            virements_out = df_t[(df_t["Compte_Source"] == compte) & (df_t["Type"].isin(["Virement Interne", "Épargne"]))]["Montant"].sum()
            credits = df_t[(df_t["Compte_Source"] == compte) & (df_t["Type"] == "Revenu")]["Montant"].sum()
            virements_in = df_t[(df_t["Compte_Cible"] == compte) & (df_t["Type"].isin(["Virement Interne", "Épargne"]))]["Montant"].sum()
            mouvements = credits + virements_in - debits - virements_out
        soldes[compte] = releve + mouvements
    return soldes

# --- CONFIG PROCESSING ---
def process_configs():
    df_cats, df_comptes, df_objs, df_abos, df_projets = load_configs_cached()
    cats = {k: [] for k in TYPES}
    if not df_cats.empty:
        for _, row in df_cats.iterrows():
            if row["Type"] in cats and row["Categorie"] not in cats[row["Type"]]:
                cats[row["Type"]].append(row["Categorie"])
    defaults = {
        "Dépense": ["Alimentation", "Loyer", "Prêt Immo", "Énergie", "Transport", "Santé", "Resto/Bar", "Shopping", "Cinéma", "Activités", "Autre"],
        "Revenu": ["Salaire", "Primes", "Ventes", "Aides", "Autre"],
        "Épargne": ["Virement Mensuel", "Cagnotte", "Autre"],
        "Investissement": ["Bourse", "Assurance Vie", "Crypto", "Autre"],
        "Virement Interne": ["Alimentation Compte", "Autre"]
    }
    for t, l in defaults.items():
        if t not in cats: cats[t] = []
        for c in l:
            if c not in cats[t]: cats[t].append(c)

    comptes = {"Pierre": ["Compte Courant Pierre"], "Elie": ["Compte Courant Elie"], "Commun": []}
    if not df_comptes.empty:
        comptes = {}
        for _, row in df_comptes.iterrows():
            if row["Proprietaire"] not in comptes: comptes[row["Proprietaire"]] = []
            comptes[row["Proprietaire"]].append(row["Compte"])
            
    objs = {"Commun": {}, "Perso": {}}
    if not df_objs.empty:
        for _, row in df_objs.iterrows():
            s = row["Scope"]; c = row["Categorie"]; m = row["Montant"]
            if s not in objs: objs[s] = {}
            objs[s][c] = float(m) if m else 0.0
            
    projets_targets = {}
    if not df_projets.empty:
        for _, row in df_projets.iterrows():
            projets_targets[row["Projet"]] = float(row["Cible"])
    return cats, comptes, objs, df_abos, projets_targets

def save_config_cats(d): save_data_to_sheet(TAB_CONFIG, pd.DataFrame([{"Type": t, "Categorie": c} for t, l in d.items() for c in l]))
def save_comptes_struct(d): save_data_to_sheet(TAB_COMPTES, pd.DataFrame([{"Proprietaire": p, "Compte": c} for p, l in d.items() for c in l]))
def save_objectifs(d): save_data_to_sheet(TAB_OBJECTIFS, pd.DataFrame([{"Scope": s, "Categorie": c, "Montant": m} for s, l in d.items() for c, m in l.items()]))
def save_abonnements(df): save_data_to_sheet(TAB_ABONNEMENTS, df)
def save_projets_targets(d): save_data_to_sheet(TAB_PROJETS, pd.DataFrame([{"Projet": p, "Cible": c, "Date_Fin": ""} for p, c in d.items()]))


# --- APP START ---
st.set_page_config(
    page_title="Ma Banque Moderne",
    layout="wide",
    page_icon="🏦",
    initial_sidebar_state="expanded"
)
apply_modern_style()

COLS_DATA = ["Date", "Mois", "Annee", "Qui_Connecte", "Type", "Categorie", "Titre", "Description", "Montant", "Paye_Par", "Imputation", "Compte_Cible", "Projet_Epargne", "Compte_Source"]
df = load_data_from_sheet(TAB_DATA, COLS_DATA)
COLS_PAT = ["Date", "Mois", "Annee", "Compte", "Montant", "Proprietaire"]
df_patrimoine = load_data_from_sheet(TAB_PATRIMOINE, COLS_PAT)

cats_memoire, comptes_structure, objectifs, df_abonnements, projets_config = process_configs()
def get_comptes_autorises(user): return comptes_structure.get(user, []) + comptes_structure.get("Commun", []) + ["Autre / Externe"]
all_my_accounts = get_comptes_autorises("Pierre") + get_comptes_autorises("Elie")
SOLDES_ACTUELS = calculer_soldes_reels(df, df_patrimoine, list(set(all_my_accounts)))

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<h2 style="text-align: center;">👤 Mon Profil</h2>', unsafe_allow_html=True)
    user_actuel = st.selectbox("Utilisateur", USERS, label_visibility="collapsed")
    comptes_disponibles = get_comptes_autorises(user_actuel)
    
    st.markdown("---")
    st.markdown('<h3 style="text-align: center;">💰 Mes Soldes</h3>', unsafe_allow_html=True)
    
    for cpt in comptes_disponibles:
        if cpt == "Autre / Externe": continue
        solde = SOLDES_ACTUELS.get(cpt, 0.0)
        color_class = "positive" if solde >= 0 else "negative"
        st.markdown(f'''
            <div class="account-card">
                <div class="account-name">{cpt}</div>
                <div class="account-balance {color_class}">{solde:,.2f} €</div>
            </div>
        ''', unsafe_allow_html=True)

    st.markdown("---")
    if st.button("🔄 Actualiser", use_container_width=True):
        clear_cache()
        st.rerun()

# --- HEADER ---
st.markdown('<h1 style="text-align: center;">🏦 Ma Banque Moderne</h1>', unsafe_allow_html=True)

# --- MONTH SELECTOR ---
date_jour = datetime.now()
col_m1, col_m2, col_m3 = st.columns([1, 3, 1])
with col_m2:
    mois_nom = st.selectbox("Période", MOIS_FR, index=date_jour.month-1, label_visibility="collapsed")
    mois_selection = MOIS_FR.index(mois_nom) + 1
    annee_selection = date_jour.year

df_mois = df[(df["Mois"] == mois_selection) & (df["Annee"] == annee_selection)]

# --- DASHBOARD METRICS ---
st.markdown('<div class="fade-in">', unsafe_allow_html=True)
k1, k2, k3, k4 = st.columns(4)
rev = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Revenu")]["Montant"].sum()
dep = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Dépense") & (df_mois["Imputation"] == "Perso")]["Montant"].sum()
epg = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Épargne")]["Montant"].sum()
com = df_mois[df_mois["Imputation"] == "Commun (50/50)"]["Montant"].sum() / 2

k1.metric("💰 Revenus", f"{rev:,.0f} €", delta="+12%")
k2.metric("💸 Dépenses Perso", f"{dep:,.0f} €", delta="+5%", delta_color="inverse")
k3.metric("🏠 Part Commun", f"{com:,.0f} €", delta="-3%", delta_color="inverse")
k4.metric("📈 Épargne", f"{epg:,.0f} €", delta="+25%")
st.markdown('</div>', unsafe_allow_html=True)

# --- TABS ---
tabs = st.tabs([
    "📊 Tableau de Bord",
    "➕ Saisir",
    "💳 Mes Comptes",
    "📈 Analyse",
    "🎯 Budget",
    "🔄 Abonnements",
    "📜 Historique",
    "🎁 Projets",
    "⚙️ Paramètres"
])

# 0. DASHBOARD
with tabs[0]:
    st.markdown('<h2>📊 Vue d\'Ensemble</h2>', unsafe_allow_html=True)
    
    if not df_mois.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### 📊 Répartition des Dépenses")
            df_depenses = df_mois[df_mois["Type"] == "Dépense"]
            if not df_depenses.empty:
                fig_pie = px.pie(
                    df_depenses,
                    values="Montant",
                    names="Categorie",
                    hole=0.4,
                    color_discrete_sequence=px.colors.sequential.RdBu
                )
                fig_pie.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(size=14, family="Outfit")
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### 💰 Évolution Mensuelle")
            # Create sample data for bar chart
            mois_labels = MOIS_FR[:mois_selection]
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(
                x=mois_labels[-6:],
                y=[3200, 3245, 3180, 3300, 3245, rev],
                name='Revenus',
                marker_color='rgb(102, 126, 234)'
            ))
            fig_bar.add_trace(go.Bar(
                x=mois_labels[-6:],
                y=[2800, 2650, 2900, 2750, 2856, dep],
                name='Dépenses',
                marker_color='rgb(245, 87, 108)'
            ))
            fig_bar.update_layout(
                barmode='group',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(size=14, family="Outfit"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🔥 Top Dépenses du Mois")
    if not df_mois.empty:
        df_top = df_mois[df_mois["Type"] == "Dépense"].groupby("Categorie")["Montant"].sum().sort_values(ascending=False).head(5).reset_index()
        if not df_top.empty:
            for idx, row in df_top.iterrows():
                col_cat, col_amt, col_prog = st.columns([3, 2, 3])
                with col_cat:
                    st.write(f"**{row['Categorie']}**")
                with col_amt:
                    st.write(f"**{row['Montant']:.0f} €**")
                with col_prog:
                    prog = min(100, int((row['Montant'] / rev * 100) if rev > 0 else 0))
                    st.progress(prog / 100)
    st.markdown('</div>', unsafe_allow_html=True)

# 1. SAISIR
with tabs[1]:
    st.markdown('<h2>➕ Nouvelle Opération</h2>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">💡 Remplissez les informations ci-dessous pour enregistrer une nouvelle transaction</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        date_op = st.date_input("📅 Date", datetime.today())
    with col2:
        type_op = st.selectbox("🏷️ Type", TYPES)
    with col3:
        montant_op = st.number_input("💶 Montant (€)", min_value=0.0, step=0.01)
    
    col4, col5 = st.columns(2)
    with col4:
        titre_op = st.text_input("✏️ Titre", placeholder="Ex: Courses Leclerc")
    with col5:
        cat_finale = "Autre"
        if type_op == "Virement Interne":
            st.info("Virement de fonds (Neutre)")
        else:
            cats = cats_memoire.get(type_op, ["Autre"])
            cat_sel = st.selectbox("📂 Catégorie", cats)
            if cat_sel == "Autre":
                cat_finale = st.text_input("Nouvelle catégorie :")
            else:
                cat_finale = cat_sel
    
    col6, col7, col8 = st.columns(3)
    c_src = ""; c_tgt = ""; p_epg = ""; p_par = user_actuel; imput = "Perso"
    
    if type_op == "Épargne":
        with col6:
            c_src = st.selectbox("💳 Depuis", comptes_disponibles)
        with col7:
            c_tgt = st.selectbox("📈 Vers (Épargne)", comptes_disponibles)
        with col8:
            liste_projets = list(projets_config.keys()) + ["Autre / Nouveau"]
            p_sel = st.selectbox("🎁 Pour quel projet ?", liste_projets)
            if p_sel == "Autre / Nouveau":
                p_epg = st.text_input("Nom du nouveau projet")
            else:
                p_epg = p_sel
    elif type_op == "Virement Interne":
        with col6:
            c_src = st.selectbox("💳 Débit (Source)", comptes_disponibles)
        with col7:
            c_tgt = st.selectbox("💳 Crédit (Cible)", comptes_disponibles)
        p_par = "Virement"; imput = "Neutre"
    else:
        with col6:
            c_src = st.selectbox("💳 Compte", comptes_disponibles)
        with col7:
            p_par = st.selectbox("👤 Qui paye ?", ["Pierre", "Elie", "Commun"])
        with col8:
            imput = st.radio("📊 Imputation", IMPUTATIONS)
    
    desc_op = st.text_area("📝 Note / Description détaillée", height=100)
    
    if st.button("✅ Enregistrer l'opération", type="primary", use_container_width=True):
        if not cat_finale: cat_finale = "Autre"
        if not titre_op: titre_op = cat_finale
        
        if type_op != "Virement Interne" and "Autre" in str(cat_sel) and cat_finale not in cats_memoire.get(type_op, []):
            cats_memoire[type_op].append(cat_finale)
            save_config_cats(cats_memoire)
        
        if type_op == "Épargne" and p_epg and p_epg not in projets_config:
            projets_config[p_epg] = 0.0
            save_projets_targets(projets_config)
        
        new_row = {
            "Date": date_op,
            "Mois": date_op.month,
            "Annee": date_op.year,
            "Qui_Connecte": user_actuel,
            "Type": type_op,
            "Categorie": cat_finale,
            "Titre": titre_op,
            "Description": desc_op,
            "Montant": montant_op,
            "Paye_Par": p_par,
            "Imputation": imput,
            "Compte_Cible": c_tgt,
            "Projet_Epargne": p_epg,
            "Compte_Source": c_src
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_data_to_sheet(TAB_DATA, df)
        
        st.success("✅ Opération ajoutée avec succès ! Solde mis à jour.")
        time.sleep(1)
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# 2. MES COMPTES
with tabs[2]:
    st.markdown('<h2>💳 Mes Comptes</h2>', unsafe_allow_html=True)
    
    cols = st.columns(2)
    for idx, cpt in enumerate(comptes_disponibles):
        if cpt == "Autre / Externe": continue
        with cols[idx % 2]:
            solde = SOLDES_ACTUELS.get(cpt, 0.0)
            color_class = "positive" if solde >= 0 else "negative"
            st.markdown(f'''
                <div class="account-card">
                    <div class="account-name">{cpt}</div>
                    <div class="account-balance {color_class}">{solde:,.2f} €</div>
                    <p style="margin-top: 16px; font-size: 14px; color: #666;">
                        {"✅ Solde confortable" if solde > 1000 else "⚠️ Attention au solde"}
                    </p>
                </div>
            ''', unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown('<h3>📝 Faire un Relevé Bancaire</h3>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">💡 Utilisez cette fonctionnalité pour recaler vos soldes avec la réalité de votre banque</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    with st.form("releve_banque"):
        c1, c2, c3 = st.columns(3)
        with c1:
            d_rel = st.date_input("📅 Date", datetime.today())
        with c2:
            c_rel = st.selectbox("💳 Compte", comptes_disponibles)
        with c3:
            m_rel = st.number_input("💶 Solde réel (€)", step=0.01)
        
        if st.form_submit_button("✅ Valider le Relevé", use_container_width=True):
            prop = "Commun" if "Joint" in c_rel or "Commun" in c_rel else user_actuel
            row = pd.DataFrame([{
                "Date": d_rel,
                "Mois": d_rel.month,
                "Annee": d_rel.year,
                "Compte": c_rel,
                "Montant": m_rel,
                "Proprietaire": prop
            }])
            df_patrimoine = pd.concat([df_patrimoine, row], ignore_index=True)
            save_data_to_sheet(TAB_PATRIMOINE, df_patrimoine)
            st.success("✅ Relevé enregistré !")
            time.sleep(1)
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# 3. ANALYSE
with tabs[3]:
    st.markdown('<h2>📈 Analyse des Flux</h2>', unsafe_allow_html=True)
    
    if not df_mois.empty:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 📊 Flux par Semaine")
        
        # Create weekly flow data
        df_mois_copy = df_mois.copy()
        df_mois_copy['Semaine'] = pd.to_datetime(df_mois_copy['Date']).dt.isocalendar().week
        
        df_entrees = df_mois_copy[df_mois_copy['Type'] == 'Revenu'].groupby('Semaine')['Montant'].sum().reset_index()
        df_sorties = df_mois_copy[df_mois_copy['Type'] == 'Dépense'].groupby('Semaine')['Montant'].sum().reset_index()
        
        fig_flow = go.Figure()
        fig_flow.add_trace(go.Scatter(
            x=df_entrees['Semaine'],
            y=df_entrees['Montant'],
            name='Entrées',
            mode='lines+markers',
            line=dict(color='rgb(102, 126, 234)', width=3),
            fill='tozeroy',
            fillcolor='rgba(102, 126, 234, 0.1)'
        ))
        fig_flow.add_trace(go.Scatter(
            x=df_sorties['Semaine'],
            y=df_sorties['Montant'],
            name='Sorties',
            mode='lines+markers',
            line=dict(color='rgb(245, 87, 108)', width=3),
            fill='tozeroy',
            fillcolor='rgba(245, 87, 108, 0.1)'
        ))
        fig_flow.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(size=14, family="Outfit"),
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_flow, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### 🎯 Par Catégorie")
            df_cat = df_mois[df_mois['Type'] == 'Dépense'].groupby('Categorie')['Montant'].sum().sort_values(ascending=True).tail(10)
            fig_bar_cat = go.Figure(go.Bar(
                x=df_cat.values,
                y=df_cat.index,
                orientation='h',
                marker=dict(
                    color=df_cat.values,
                    colorscale='RdBu',
                    showscale=False
                )
            ))
            fig_bar_cat.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(size=12, family="Outfit")
            )
            st.plotly_chart(fig_bar_cat, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### 💳 Par Compte")
            df_compte = df_mois[df_mois['Type'] == 'Dépense'].groupby('Compte_Source')['Montant'].sum()
            fig_pie_compte = px.pie(
                values=df_compte.values,
                names=df_compte.index,
                hole=0.5,
                color_discrete_sequence=px.colors.sequential.Plasma
            )
            fig_pie_compte.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(size=12, family="Outfit")
            )
            st.plotly_chart(fig_pie_compte, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

# 4. BUDGET
with tabs[4]:
    st.markdown('<h2>🎯 Budget Mensuel</h2>', unsafe_allow_html=True)
    
    def display_budget_table(scope, title, emoji):
        st.markdown(f'<h3>{emoji} {title}</h3>', unsafe_allow_html=True)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        
        objs = objectifs.get(scope, {})
        mask = (df_mois["Type"] == "Dépense")
        if scope == "Commun":
            mask = mask & (df_mois["Imputation"] == "Commun (50/50)")
        else:
            mask = mask & (df_mois["Imputation"] == "Perso") & (df_mois["Qui_Connecte"] == user_actuel)
        
        df_f = df_mois[mask]
        all_cats = list(set(objs.keys()).union(set(df_f["Categorie"].unique())))
        
        for cat in all_cats:
            budget = float(objs.get(cat, 0.0))
            reel = df_f[df_f["Categorie"] == cat]["Montant"].sum()
            
            if budget > 0 or reel > 0:
                reste = budget - reel
                pct = int((reel / budget * 100) if budget > 0 else 0)
                
                col_cat, col_bud, col_real, col_rest = st.columns([3, 2, 2, 2])
                with col_cat:
                    st.write(f"**{cat}**")
                with col_bud:
                    st.write(f"{budget:.0f} €")
                with col_real:
                    st.write(f"{reel:.0f} €")
                with col_rest:
                    color = "#10b981" if reste >= 0 else "#ef4444"
                    st.markdown(f'<span style="color: {color}; font-weight: 700;">{reste:.0f} €</span>', unsafe_allow_html=True)
                
                # Progress bar
                st.progress(min(pct / 100, 1.0))
                st.markdown("---")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    display_budget_table("Commun", "Dépenses Communes", "🏠")
    display_budget_table("Perso", "Dépenses Personnelles", "👤")

# 5. ABONNEMENTS
with tabs[5]:
    st.markdown('<h2>🔄 Mes Abonnements</h2>', unsafe_allow_html=True)
    
    if not df_abonnements.empty:
        total_abos = df_abonnements["Montant"].sum()
        st.markdown(f'<div class="success-box">💡 Total mensuel : <strong>{total_abos:.2f} €</strong></div>', unsafe_allow_html=True)
        
        st.markdown('<div class="card">', unsafe_allow_html=True)
        for _, row in df_abonnements.iterrows():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            with col1:
                st.write(f"**{row['Nom']}**")
            with col2:
                st.write(f"**{row['Montant']:.2f} €**")
            with col3:
                st.write(f"Jour {row['Jour']}")
            with col4:
                st.write(row['Compte_Source'])
            st.markdown("---")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Aucun abonnement enregistré")
    
    if st.button("➕ Ajouter un Abonnement", use_container_width=True):
        st.info("Fonctionnalité à venir !")

# 6. HISTORIQUE
with tabs[6]:
    st.markdown('<h2>📜 Historique des Transactions</h2>', unsafe_allow_html=True)
    
    col_search, col_filter = st.columns([3, 1])
    with col_search:
        search_term = st.text_input("🔍 Rechercher", placeholder="Titre, catégorie...", label_visibility="collapsed")
    with col_filter:
        type_filter = st.selectbox("Type", ["Tous"] + TYPES, label_visibility="collapsed")
    
    df_hist = df.copy()
    if search_term:
        df_hist = df_hist[
            df_hist["Titre"].str.contains(search_term, case=False, na=False) |
            df_hist["Categorie"].str.contains(search_term, case=False, na=False)
        ]
    if type_filter != "Tous":
        df_hist = df_hist[df_hist["Type"] == type_filter]
    
    df_hist = df_hist.sort_values("Date", ascending=False).head(50)
    
    if not df_hist.empty:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        for _, row in df_hist.iterrows():
            col1, col2, col3, col4 = st.columns([2, 3, 2, 2])
            with col1:
                st.write(f"**{row['Date']}**")
            with col2:
                st.write(f"{row['Titre']}")
                st.caption(f"📂 {row['Categorie']}")
            with col3:
                color = "#ef4444" if row['Type'] == "Dépense" else "#10b981"
                sign = "-" if row['Type'] == "Dépense" else "+"
                st.markdown(f'<span style="color: {color}; font-weight: 700; font-size: 18px;">{sign}{row["Montant"]:.2f} €</span>', unsafe_allow_html=True)
            with col4:
                badge_class = {
                    "Dépense": "badge-danger",
                    "Revenu": "badge-success",
                    "Épargne": "badge-info",
                    "Investissement": "badge-warning",
                    "Virement Interne": "badge-info"
                }.get(row['Type'], "badge-info")
                st.markdown(f'<span class="badge {badge_class}">{row["Type"]}</span>', unsafe_allow_html=True)
            st.markdown("---")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Aucune transaction trouvée")

# 7. PROJETS
with tabs[7]:
    st.markdown('<h2>🎁 Mes Projets d\'Épargne</h2>', unsafe_allow_html=True)
    
    if projets_config:
        cols = st.columns(min(len(projets_config), 3))
        for idx, (projet, cible) in enumerate(projets_config.items()):
            with cols[idx % 3]:
                # Calculate current amount
                montant_actuel = df[
                    (df["Type"] == "Épargne") &
                    (df["Projet_Epargne"] == projet)
                ]["Montant"].sum()
                
                pct = int((montant_actuel / cible * 100) if cible > 0 else 0)
                
                st.markdown(f'''
                    <div class="account-card">
                        <div class="account-name">🎯 {projet}</div>
                        <div class="account-balance positive">{montant_actuel:,.0f} €</div>
                        <p style="margin-top: 16px; font-size: 14px; color: #666;">
                            Objectif: {cible:,.0f} € • {pct}%
                        </p>
                    </div>
                ''', unsafe_allow_html=True)
                st.progress(min(pct / 100, 1.0))
    else:
        st.info("Aucun projet d'épargne créé")
    
    if st.button("➕ Créer un Nouveau Projet", use_container_width=True):
        st.info("Utilisez l'onglet 'Saisir' avec le type 'Épargne' pour créer un nouveau projet !")

# 8. PARAMETRES
with tabs[8]:
    st.markdown('<h2>⚙️ Paramètres</h2>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📂 Gérer les Catégories")
    col1, col2, col3 = st.columns(3)
    with col1:
        type_cat = st.selectbox("Type", TYPES)
    with col2:
        new_cat = st.text_input("Nouvelle Catégorie")
    with col3:
        st.write("")  # Spacing
        if st.button("➕ Ajouter", use_container_width=True):
            if new_cat and new_cat not in cats_memoire.get(type_cat, []):
                if type_cat not in cats_memoire:
                    cats_memoire[type_cat] = []
                cats_memoire[type_cat].append(new_cat)
                save_config_cats(cats_memoire)
                st.success(f"✅ Catégorie '{new_cat}' ajoutée !")
                time.sleep(1)
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 💳 Gérer les Comptes")
    col1, col2, col3 = st.columns(3)
    with col1:
        prop_compte = st.selectbox("Propriétaire", ["Pierre", "Elie", "Commun"])
    with col2:
        nom_compte = st.text_input("Nom du Compte")
    with col3:
        st.write("")  # Spacing
        if st.button("➕ Ajouter Compte", use_container_width=True):
            if nom_compte:
                if prop_compte not in comptes_structure:
                    comptes_structure[prop_compte] = []
                if nom_compte not in comptes_structure[prop_compte]:
                    comptes_structure[prop_compte].append(nom_compte)
                    save_comptes_struct(comptes_structure)
                    st.success(f"✅ Compte '{nom_compte}' ajouté !")
                    time.sleep(1)
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🎯 Gérer les Objectifs Budget")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        scope_obj = st.selectbox("Scope", ["Perso", "Commun"])
    with col2:
        cat_obj = st.selectbox("Catégorie", cats_memoire.get("Dépense", []))
    with col3:
        montant_obj = st.number_input("Montant (€)", min_value=0.0, step=10.0)
    with col4:
        st.write("")  # Spacing
        if st.button("💾 Enregistrer", use_container_width=True):
            if cat_obj and montant_obj > 0:
                if scope_obj not in objectifs:
                    objectifs[scope_obj] = {}
                objectifs[scope_obj][cat_obj] = montant_obj
                save_objectifs(objectifs)
                st.success(f"✅ Objectif enregistré !")
                time.sleep(1)
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
