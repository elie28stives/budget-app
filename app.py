import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import json
import time
from io import BytesIO

# --- CONFIGURATION --- 
SHEET_NAME = "Budget_Couple_DB"
TAB_DATA = "Data"
TAB_CONFIG = "Config"
TAB_OBJECTIFS = "Objectifs"
TAB_PATRIMOINE = "Patrimoine"
TAB_COMPTES = "Comptes"
TAB_ABONNEMENTS = "Abonnements"
TAB_PROJETS = "Projets_Config"
TAB_MOTS_CLES = "Mots_Cles"  # MODULE 4: Mots-clés automatiques

USERS = ["Pierre", "Elie"]
TYPES = ["Dépense", "Revenu", "Virement Interne", "Épargne", "Investissement"]
IMPUTATIONS = ["Perso", "Commun (50/50)", "Commun (Autre %)", "Avance/Cadeau"]
FREQUENCES = ["Mensuel", "Annuel", "Trimestriel", "Hebdomadaire"]
TYPES_COMPTE = ["Courant", "Épargne"]
MOIS_FR = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

# --- STYLE CSS (REVOLUT-INSPIRED DESIGN) ---
def apply_custom_style():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        :root {
            --primary: #FF6B35;
            --primary-dark: #E55A2B;
            --success: #10B981;
            --warning: #F59E0B;
            --danger: #EF4444;
            --bg-main: #F5F7FA;
            --bg-card: #FFFFFF;
            --text-primary: #0A1929;
            --text-secondary: #6B7280;
            --border: #E5E7EB;
            --shadow: 0 1px 3px rgba(0,0,0,0.04);
            --shadow-lg: 0 4px 12px rgba(0,0,0,0.08);
        }

        .stApp {
            background: var(--bg-main);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            color: var(--text-primary);
        }
        
        .main .block-container {
            padding: 2rem 3rem !important;
            max-width: 1400px;
        }
        
        #MainMenu, footer, header {visibility: hidden;}

        /* TABS - Style Revolut */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0;
            background: var(--bg-card);
            border-radius: 12px;
            padding: 4px;
            box-shadow: var(--shadow);
            border: none;
        }
        .stTabs [data-baseweb="tab"] {
            height: 44px;
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-weight: 600;
            font-size: 14px;
            border-radius: 8px;
            padding: 0 20px;
            transition: all 0.2s;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background: rgba(255, 107, 53, 0.08);
            color: var(--primary);
        }
        .stTabs [aria-selected="true"] {
            background: var(--primary) !important;
            color: white !important;
            border: none !important;
        }

        /* MÉTRIQUES - Cards modernes */
        div[data-testid="stMetric"] {
            background: var(--bg-card);
            padding: 20px;
            border-radius: 16px;
            border: none !important;
            box-shadow: var(--shadow-lg) !important;
        }
        
        div[data-testid="stMetric"] label {
            font-size: 13px !important;
            font-weight: 600 !important;
            color: var(--text-secondary) !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            font-size: 32px !important;
            font-weight: 700 !important;
            color: var(--text-primary) !important;
        }

        /* SIDEBAR - Style app mobile */
        section[data-testid="stSidebar"] {
            background: var(--bg-card);
            border-right: 1px solid var(--border);
            padding-top: 1rem;
        }
        
        section[data-testid="stSidebar"] > div {
            padding: 0 1.5rem;
        }

        /* INPUTS - Minimalistes */
        .stTextInput input, .stNumberInput input {
            background: #FFFFFF !important;
            border: 1.5px solid var(--border) !important;
            border-radius: 12px !important;
            font-size: 15px !important;
            font-weight: 600 !important;
            color: #0A1929 !important;
            padding: 12px 16px !important;
            transition: all 0.2s;
        }
        
        .stTextInput input:focus, .stNumberInput input:focus {
            border-color: var(--primary) !important;
            box-shadow: 0 0 0 3px rgba(255, 107, 53, 0.1) !important;
        }
        
        /* SELECTBOX - CORRECTION MAXIMALE DU CONTRASTE */
        .stSelectbox {
            color: #000000 !important;
        }
        
        .stSelectbox > div > div {
            background: #FFFFFF !important;
        }
        
        .stSelectbox [data-baseweb="select"] {
            background: #FFFFFF !important;
        }
        
        .stSelectbox [data-baseweb="select"] > div {
            background: #FFFFFF !important;
            color: #000000 !important;
        }
        
        /* Le texte visible dans le champ */
        .stSelectbox [data-baseweb="select"] > div > div {
            color: #000000 !important;
            font-weight: 700 !important;
        }
        
        /* Tous les spans et divs internes */
        .stSelectbox [data-baseweb="select"] span,
        .stSelectbox [data-baseweb="select"] div,
        .stSelectbox [data-baseweb="select"] p {
            color: #000000 !important;
            font-weight: 600 !important;
        }
        
        /* L'icône et le texte sélectionné */
        .stSelectbox [data-baseweb="select"] [data-baseweb="select-value"] {
            color: #000000 !important;
            font-weight: 700 !important;
        }
        
        /* Menu déroulant */
        .stSelectbox [role="listbox"] {
            background: #FFFFFF !important;
        }
        
        .stSelectbox [role="option"] {
            color: #000000 !important;
            font-weight: 600 !important;
            background: #FFFFFF !important;
            padding: 10px 16px !important;
        }
        
        .stSelectbox [role="option"]:hover {
            background: #FFF4ED !important;
            color: #000000 !important;
        }
        
        .stSelectbox [aria-selected="true"] {
            background: #FFE5D9 !important;
            color: #000000 !important;
            font-weight: 700 !important;
        }
        
        /* Forcer ABSOLUMENT le texte visible */
        [data-baseweb="select"] [id*="react-select"] {
            color: #000000 !important;
        }
        
        /* RADIO BUTTONS - Meilleure visibilité */
        .stRadio label {
            color: #0A1929 !important;
            font-weight: 600 !important;
        }
        
        .stRadio div[role="radiogroup"] label {
            color: #0A1929 !important;
            font-weight: 600 !important;
        }
        
        .stRadio div[role="radiogroup"] label span {
            color: #0A1929 !important;
        }
        
        /* DATE INPUT */
        .stDateInput input {
            color: #000000 !important;
            font-weight: 600 !important;
            background: #FFFFFF !important;
        }
        
        /* TEXT AREA */
        .stTextArea textarea {
            background: #FFFFFF !important;
            border: 1.5px solid var(--border) !important;
            border-radius: 12px !important;
            color: #0A1929 !important;
            font-weight: 600 !important;
        }
        
        /* SLIDER */
        .stSlider label {
            color: #0A1929 !important;
            font-weight: 600 !important;
        }
        
        /* LABELS - Tous les labels d'inputs */
        .stTextInput label, .stNumberInput label, .stSelectbox label, .stDateInput label {
            color: #0A1929 !important;
            font-weight: 600 !important;
            font-size: 14px !important;
        }

        /* BOUTONS - Style Revolut */
        div.stButton > button {
            background: var(--primary) !important;
            color: white !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            font-size: 15px !important;
            border: none !important;
            padding: 12px 24px !important;
            box-shadow: 0 2px 8px rgba(255, 107, 53, 0.3) !important;
            transition: all 0.2s !important;
        }
        
        div.stButton > button:hover {
            background: var(--primary-dark) !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(255, 107, 53, 0.4) !important;
        }
        
        div.stButton > button:active {
            transform: translateY(0);
        }

        /* DOWNLOAD BUTTON */
        div.stDownloadButton > button {
            background: var(--success) !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            border: none !important;
            padding: 10px 20px !important;
            box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3) !important;
        }

        /* DATAFRAME - Cards épurées */
        div.stDataFrame {
            background: var(--bg-card);
            border-radius: 16px !important;
            border: none !important;
            box-shadow: var(--shadow-lg) !important;
            overflow: hidden;
        }

        /* HEADERS */
        h1, h2, h3 { 
            color: var(--text-primary) !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 700 !important;
        }
        
        h2 {
            font-size: 28px !important;
            margin-bottom: 1.5rem !important;
        }
        
        h3 {
            font-size: 20px !important;
            font-weight: 600 !important;
            margin-top: 2rem !important;
        }

        /* PROGRESS BAR */
        .stProgress > div > div {
            background: var(--primary);
            border-radius: 8px;
        }

        /* EXPANDER */
        div[data-testid="stExpander"] {
            background: var(--bg-card);
            border: none !important;
            border-radius: 12px;
            box-shadow: var(--shadow);
        }

        /* FORMS */
        div.stForm {
            background: var(--bg-card);
            padding: 24px;
            border-radius: 16px !important;
            border: none !important;
            box-shadow: var(--shadow-lg) !important;
        }
    </style>
    """, unsafe_allow_html=True)

def page_header(title, subtitle=None):
    if subtitle:
        st.markdown(f"""
        <div style="margin-bottom: 2rem;">
            <h2 style='font-size:32px; font-weight:800; color:#0A1929; margin-bottom:8px;'>{title}</h2>
            <p style='font-size:16px; color:#6B7280; font-weight:500;'>{subtitle}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"<h2 style='font-size:32px; font-weight:800; color:#0A1929; margin-bottom:2rem;'>{title}</h2>", unsafe_allow_html=True)

# --- CONNEXION ---
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
        st.error(f"Erreur technique : {e}")
        return None

def get_worksheet(client, sheet_name, tab_name):
    try:
        sh = client.open(sheet_name)
        try: ws = sh.worksheet(tab_name)
        except: ws = sh.add_worksheet(title=tab_name, rows="100", cols="20")
        return ws
    except Exception as e:
        st.error(f"Erreur d'accès onglet : {e}"); st.stop()

# --- DATA ---
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
        load_data_from_sheet(TAB_COMPTES, ["Proprietaire", "Compte", "Type", "Partage"]),
        load_data_from_sheet(TAB_OBJECTIFS, ["Scope", "Categorie", "Montant"]),
        load_data_from_sheet(TAB_ABONNEMENTS, ["Nom", "Montant", "Jour", "Categorie", "Compte_Source", "Proprietaire", "Imputation", "Frequence"]),
        load_data_from_sheet(TAB_PROJETS, ["Projet", "Cible", "Date_Fin"]),
        load_data_from_sheet(TAB_MOTS_CLES, ["Mot_Cle", "Categorie", "Type", "Compte"])
    )

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

# --- LOGIC ---
def to_excel_download(df):
    """Génère un fichier Excel téléchargeable - VERSION CORRIGÉE"""
    output = BytesIO()
    # Conversion des dates en string pour éviter les problèmes
    df_export = df.copy()
    if "Date" in df_export.columns:
        df_export["Date"] = df_export["Date"].astype(str)
    
    # Utiliser openpyxl comme moteur (plus fiable)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Transactions')
    
    output.seek(0)
    return output

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

def process_configs():
    df_cats, df_comptes, df_objs, df_abos, df_projets, df_mots_cles = load_configs_cached()
    cats = {k: [] for k in TYPES}
    if not df_cats.empty:
        for _, row in df_cats.iterrows():
            if row["Type"] in cats and row["Categorie"] not in cats[row["Type"]]:
                cats[row["Type"]].append(row["Categorie"])
    if df_cats.empty:
        defaults = {
            "Dépense": ["Alimentation", "Loyer", "Prêt Immo", "Énergie", "Transport", "Santé", "Resto/Bar", "Shopping", "Cinéma", "Activités", "Autre"],
            "Revenu": ["Salaire", "Primes", "Ventes", "Aides", "Autre"],
            "Épargne": ["Virement Mensuel", "Cagnotte", "Autre"],
            "Investissement": ["Bourse", "Assurance Vie", "Crypto", "Autre"],
            "Virement Interne": ["Alimentation Compte", "Autre"]
        }
        cats = defaults
        save_data_to_sheet(TAB_CONFIG, pd.DataFrame([{"Type": t, "Categorie": c} for t, l in defaults.items() for c in l]))

    # --- Comptes : structure plus professionnelle ---
    comptes = {"Pierre": ["Compte Courant Pierre"], "Elie": ["Compte Courant Elie"], "Commun": []}
    comptes_types = {}
    comptes_partage = {}  # map compte -> mode de partage (Propriétaire ou Commun)
    if not df_comptes.empty:
        comptes = {}
        for _, row in df_comptes.iterrows():
            owner = row.get("Proprietaire", "").strip() or "Inconnu"
            compte_name = row.get("Compte", "").strip() or "Compte sans nom"
            if owner not in comptes: comptes[owner] = []
            comptes[owner].append(compte_name)
            c_type = row.get("Type", "Courant")
            if not c_type: c_type = "Courant"
            comptes_types[compte_name] = c_type
            partage = row.get("Partage", "")  # peut être "Privé" ou "Commun"
            comptes_partage[compte_name] = partage or "Privé"
            
    objs_list = []
    if not df_objs.empty: objs_list = df_objs.to_dict('records')
            
    projets_data = {}
    if not df_projets.empty:
        for _, row in df_projets.iterrows():
            projets_data[row["Projet"]] = {"Cible": float(row["Cible"]), "Date_Fin": row["Date_Fin"]}
    
    mots_cles_dict = {}
    if not df_mots_cles.empty:
        for _, row in df_mots_cles.iterrows():
            mots_cles_dict[row["Mot_Cle"].lower()] = {
                "Categorie": row["Categorie"],
                "Type": row["Type"],
                "Compte": row["Compte"]
            }
            
    return cats, comptes, objs_list, df_abos, projets_data, comptes_types, mots_cles_dict, comptes_partage

def save_config_cats(d): save_data_to_sheet(TAB_CONFIG, pd.DataFrame([{"Type": t, "Categorie": c} for t, l in d.items() for c in l]))
def save_comptes_struct(d, types_map, partage_map=None): 
    rows = []
    for p, l in d.items():
        for c in l:
            rows.append({"Proprietaire": p, "Compte": c, "Type": types_map.get(c, "Courant"), "Partage": (partage_map.get(c, "Privé") if partage_map else "Privé")})
    save_data_to_sheet(TAB_COMPTES, pd.DataFrame(rows))
def save_objectifs_from_df(df_obj): save_data_to_sheet(TAB_OBJECTIFS, df_obj)
def save_abonnements(df): save_data_to_sheet(TAB_ABONNEMENTS, df)
def save_projets_targets(d): 
    rows = []
    for p, data in d.items():
        rows.append({"Projet": p, "Cible": data["Cible"], "Date_Fin": data["Date_Fin"]})
    save_data_to_sheet(TAB_PROJETS, pd.DataFrame(rows))

def save_mots_cles(d):
    rows = []
    for mc, data in d.items():
        rows.append({"Mot_Cle": mc, "Categorie": data["Categorie"], "Type": data["Type"], "Compte": data["Compte"]})
    save_data_to_sheet(TAB_MOTS_CLES, pd.DataFrame(rows))


# --- APP START ---
st.set_page_config(page_title="Ma Banque V52", layout="wide", page_icon="🏦", initial_sidebar_state="expanded")
apply_custom_style()

COLS_DATA = ["Date", "Mois", "Annee", "Qui_Connecte", "Type", "Categorie", "Titre", "Description", "Montant", "Paye_Par", "Imputation", "Compte_Cible", "Projet_Epargne", "Compte_Source"]
df = load_data_from_sheet(TAB_DATA, COLS_DATA)
COLS_PAT = ["Date", "Mois", "Annee", "Compte", "Montant", "Proprietaire"]
df_patrimoine = load_data_from_sheet(TAB_PATRIMOINE, COLS_PAT)

cats_memoire, comptes_structure, objectifs_list, df_abonnements, projets_config, comptes_types_map, mots_cles_map, comptes_partage_map = process_configs()

def get_comptes_autorises(user):
    """Retourne uniquement les comptes que l'utilisateur peut voir/gérer.
    Inclut les comptes privés du user + les comptes marqués 'Commun' (partage) + option 'Autre / Externe'."""
    user_list = comptes_structure.get(user, [])
    commun_list = comptes_structure.get("Commun", [])
    # On retourne une copie pour éviter modifications accidentelles
    return list(user_list) + list(commun_list) + ["Autre / Externe"]

# Construire la liste complète des comptes pour calculs (soldes, etc.)
all_accounts = set()
for owner, lst in comptes_structure.items():
    for c in lst:
        all_accounts.add(c)
all_accounts.add("Autre / Externe")
SOLDES_ACTUELS = calculer_soldes_reels(df, df_patrimoine, list(all_accounts))

# --- SIDEBAR (COMPTES PUIS PÉRIODE) ---
with st.sidebar:
    st.markdown("<h3 style='margin-bottom:20px;'>Menu</h3>", unsafe_allow_html=True)
    user_actuel = st.selectbox("Utilisateur", USERS)
    
    st.markdown("---")
    # Afficher uniquement les comptes autorisés pour l'utilisateur sélectionné
    comptes_disponibles = get_comptes_autorises(user_actuel)
    total_courant = 0; total_epargne = 0
    list_courant = []; list_epargne = []
    
    for cpt in comptes_disponibles:
        if cpt == "Autre / Externe": continue
        val = SOLDES_ACTUELS.get(cpt, 0.0)
        ctype = comptes_types_map.get(cpt, "Courant")
        if ctype == "Épargne": total_epargne += val; list_epargne.append((cpt, val))
        else: total_courant += val; list_courant.append((cpt, val))

    def draw_account_card(name, val, is_saving=False):
        if is_saving:
            gradient = "linear-gradient(135deg, #0066FF 0%, #00D4FF 100%)"
            icon = "💎"
        else:
            gradient = "linear-gradient(135deg, #10B981 0%, #059669 100%)" if val >= 0 else "linear-gradient(135deg, #EF4444 0%, #DC2626 100%)"
            icon = "💳"
        
        st.markdown(f"""
        <div style="background: {gradient}; border-radius: 16px; padding: 20px; margin-bottom: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); position: relative; overflow: hidden;">
            <div style="position: absolute; top: 10px; right: 15px; font-size: 32px; opacity: 0.3;">{icon}</div>
            <div style="font-size: 12px; color: rgba(255,255,255,0.9); font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">{name}</div>
            <div style="font-size: 28px; font-weight: 800; color: white;">{val:,.2f} €</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"**COMPTES (Disponible pour {user_actuel})**")
    for name, val in list_courant: draw_account_card(name, val, False)
    st.write("")
    st.markdown(f"**ÉPARGNE (Disponible pour {user_actuel})**")
    for name, val in list_epargne: draw_account_card(name, val, True)

    st.markdown("---")
    st.markdown("**Période**")
    date_jour = datetime.now()
    mois_nom = st.selectbox("Mois", MOIS_FR, index=date_jour.month-1)
    mois_selection = MOIS_FR.index(mois_nom) + 1
    annee_selection = st.number_input("Année", value=date_jour.year)
    
    df_mois = df[(df["Mois"] == mois_selection) & (df["Annee"] == annee_selection)]

    st.markdown("---")
    if st.button("Actualiser", use_container_width=True): clear_cache(); st.rerun()

# --- MAIN ---
tabs = st.tabs(["Transactions", "Synthèse", "Analyse & Budget", "Prévisionnel", "Équilibre", "Patrimoine", "Configuration"])

# 1. SYNTHESE
with tabs[0]:
    page_header("Synthèse du mois")
    
    rev = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Revenu")]["Montant"].sum()
    dep = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Dépense") & (df_mois["Imputation"] == "Perso")]["Montant"].sum()
    epg = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Épargne")]["Montant"].sum()
    com = df_mois[df_mois["Imputation"] == "Commun (50/50)"]["Montant"].sum() / 2
    
    # ===== MODULE 1: RESTE À VIVRE =====
    charges_fixes = 0.0
    if not df_abonnements.empty:
        abos_user = df_abonnements[(df_abonnements["Proprietaire"] == user_actuel) | (df_abonnements["Imputation"].str.contains("Commun", na=False))]
        for _, row in abos_user.iterrows():
            if "Commun" in str(row["Imputation"]):
                charges_fixes += float(row["Montant"]) / 2
            else:
                charges_fixes += float(row["Montant"])
    
    reste_a_vivre = rev - charges_fixes - dep - com
    
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Revenus", f"{rev:,.0f} €")
    k2.metric("Charges Fixes", f"{charges_fixes:,.0f} €", delta=None, delta_color="inverse")
    k3.metric("Dépenses Variables", f"{(dep + com):,.0f} €", delta=None, delta_color="inverse")
    k4.metric("Épargne", f"{epg:,.0f} €", delta=None, delta_color="normal")
    
    rav_color = "#10B981" if reste_a_vivre > 0 else "#EF4444"
    rav_gradient = "linear-gradient(135deg, #10B981 0%, #059669 100%)" if reste_a_vivre > 0 else "linear-gradient(135deg, #EF4444 0%, #DC2626 100%)"
    k5.markdown(f"""
    <div style="background: {rav_gradient}; border-radius: 16px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); position: relative; overflow: hidden;">
        <div style="position: absolute; top: 10px; right: 15px; font-size: 48px; opacity: 0.2;">{'💰' if reste_a_vivre > 0 else '⚠️'}</div>
        <div style="font-size: 12px; color: rgba(255,255,255,0.9); font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Reste à Vivre</div>
        <div style="font-size: 32px; font-weight: 800; color: white; margin-bottom: 4px;">{reste_a_vivre:,.0f} €</div>
        <div style="font-size: 13px; color: rgba(255,255,255,0.8); font-weight: 500;">Pour finir le mois</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Répartition")
        if not df_mois.empty:
            fig_pie = px.pie(df_mois[df_mois["Type"]=="Dépense"], values="Montant", names="Categorie", hole=0.6, color_discrete_sequence=['#DA7756', '#202124', '#5F6368', '#9CA3AF', '#D1D5DB'])
            fig_pie.update_layout(showlegend=True)
            st.plotly_chart(fig_pie, use_container_width=True)
        else: st.info("Pas de données")
    
    with c2:
        st.subheader("Alertes Budget")
        objs_perso = [o for o in objectifs_list if o["Scope"] == "Perso" or (o["Scope"] in USERS and o["Scope"] == user_actuel)]
        mask = (df_mois["Type"] == "Dépense") & (df_mois["Imputation"] == "Perso") & (df_mois["Qui_Connecte"] == user_actuel)
        df_f = df_mois[mask]
        
        alerts = []
        for obj in objs_perso:
            cat = obj["Categorie"]
            budget = float(obj["Montant"])
            if budget > 0:
                r = df_f[df_f["Categorie"] == cat]["Montant"].sum()
                if r/budget > 0.75: alerts.append((cat, r, budget, r/budget))
        
        if alerts:
            for c, r, b, p in alerts:
                col = "orange" if p < 1 else "red"
                st.write(f"**{c}** : {r:.0f}€ / {b:.0f}€")
                st.progress(min(p, 1.0))
        else:
            st.success("Tout est sous contrôle !")

# 2. TRANSACTIONS
with tabs[1]:
    subtabs = st.tabs(["Nouvelle Saisie", "Journal", "Abonnements"])
    
    # --- SAISIE ---
    with subtabs[0]:
        c1, c2, c3 = st.columns(3)
        date_op = c1.date_input("Date", datetime.today(), key="d_op")
        type_op = c2.selectbox("Type", TYPES, key="t_op")
        montant_op = c3.number_input("Montant (€)", min_value=0.0, step=0.01, key="m_op")
        
        c4, c5 = st.columns(2)
        titre_op = c4.text_input("Titre", placeholder="Libellé...", key="tit_op")
        
        # MODULE 4: Auto-complétion conditionnelle par mots-clés
        cat_finale = "Autre"
        compte_auto = None
        suggestion_active = False
        
        if titre_op and mots_cles_map:
            for mc, data in mots_cles_map.items():
                if mc in titre_op.lower() and data["Type"] == type_op:  # Vérification du type
                    cat_finale = data["Categorie"]
                    compte_auto = data["Compte"]
                    suggestion_active = True
                    break
        
        if suggestion_active:
            c5.success(f"✨ Suggestion : {cat_finale}")
        
        if type_op == "Virement Interne": 
            c5.info("Virement de fonds"); cat_finale = "Virement"
        else:
            cats = cats_memoire.get(type_op, [])
            default_idx = cats.index(cat_finale) if cat_finale in cats else 0
            cat_sel = c5.selectbox("Catégorie", cats + ["Autre (nouvelle)"], index=default_idx, key="c_sel")
            if cat_sel == "Autre (nouvelle)": 
                cat_finale = c5.text_input("Nom catégorie", key="c_new")
            else: 
                cat_finale = cat_sel
        
        st.write("")
        c_src = ""; c_tgt = ""; p_epg = ""; p_par = user_actuel; imput = "Perso"
        
        if type_op == "Épargne":
            st.markdown("**Épargne**")
            ce1, ce2, ce3 = st.columns(3)
            c_src = ce1.selectbox("Source", get_comptes_autorises(user_actuel), key="src_e")
            c_tgt = ce2.selectbox("Cible", [c for c in get_comptes_autorises(user_actuel) if comptes_types_map.get(c) == "Épargne"] or get_comptes_autorises(user_actuel), key="tgt_e")
            p_sel = ce3.selectbox("Projet", list(projets_config.keys()) + ["Nouveau", "Aucun"], key="prj_e")
            p_epg = st.text_input("Nouveau Projet", key="new_prj") if p_sel == "Nouveau" else ("" if p_sel == "Aucun" else p_sel)
            
        elif type_op == "Virement Interne":
            st.markdown("**Virement**")
            cv1, cv2 = st.columns(2)
            c_src = cv1.selectbox("Débit", get_comptes_autorises(user_actuel), key="src_v")
            c_tgt = cv2.selectbox("Crédit", get_comptes_autorises(user_actuel), key="tgt_v")
            p_par = "Virement"; imput = "Neutre"
            
        else:
            st.markdown("**Détails**")
            cc1, cc2, cc3 = st.columns(3)
            default_compte_idx = 0
            if compte_auto and compte_auto in get_comptes_autorises(user_actuel):
                default_compte_idx = get_comptes_autorises(user_actuel).index(compte_auto)
            compte_src_sel = cc1.selectbox("Compte (source)", get_comptes_autorises(user_actuel), index=default_compte_idx, key="comp_src")
            compte_cible_sel = cc2.selectbox("Compte (cible, si applicable)", ["Aucun"] + get_comptes_autorises(user_actuel), index=0, key="comp_tgt")
            paye_par_sel = cc3.selectbox("Payé par", USERS + ["Autre"], index=USERS.index(user_actuel) if user_actuel in USERS else 0, key="paye_par")
            description_op = st.text_area("Description (optionnel)", key="desc_op")
            imput_options = ["Perso", "Commun (50/50)", "Commun (Autre %)", "Avance/Cadeau"]
            imput = st.selectbox("Imputation", imput_options, index=0, key="imputation_op")

        # Boutons d'action
        st.write("")
        col_save, col_export = st.columns([1,1])
        with col_save:
            if st.button("Enregistrer la transaction", use_container_width=True):
                # Validation minimale
                if montant_op is None or montant_op <= 0:
                    st.error("Le montant doit être supérieur à 0.")
                elif not titre_op:
                    st.error("Donne un titre à la transaction.")
                else:
                    # Préparer la ligne
                    new_row = {
                        "Date": date_op,
                        "Mois": date_op.month,
                        "Annee": date_op.year,
                        "Qui_Connecte": user_actuel,
                        "Type": type_op,
                        "Categorie": cat_finale,
                        "Titre": titre_op,
                        "Description": description_op or "",
                        "Montant": float(montant_op),
                        "Paye_Par": paye_par_sel,
                        "Imputation": imput,
                        "Compte_Cible": compte_cible_sel if compte_cible_sel != "Aucun" else "",
                        "Projet_Epargne": p_epg or "",
                        "Compte_Source": compte_src_sel or ""
                    }

                    # Append localement et sauvegarder
                    try:
                        df_local = df.copy() if df is not None else pd.DataFrame(columns=COLS_DATA)
                        df_local = pd.concat([df_local, pd.DataFrame([new_row])], ignore_index=True)
                        save_data_to_sheet(TAB_DATA, df_local)
                        st.success("Transaction enregistrée ✅")
                        # Mettre à jour cache local et variables
                        clear_cache()
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de l'enregistrement : {e}")

        with col_export:
            if st.button("Télécharger les transactions (Excel)", use_container_width=True):
                try:
                    buf = to_excel_download(df if not df.empty else pd.DataFrame(columns=COLS_DATA))
                    st.download_button("Télécharger .xlsx", data=buf, file_name=f"transactions_{date.today()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                except Exception as e:
                    st.error(f"Impossible de générer le fichier : {e}")

    # --- JOURNAL ---
    with subtabs[1]:
        page_header("Journal des transactions")
        st.markdown("Filtre et édition des transactions")
        df_journal = df.copy()
        if df_journal.empty:
            st.info("Aucune transaction pour le moment.")
        else:
            # Filtres
            f_col1, f_col2, f_col3 = st.columns(3)
            f_user = f_col1.selectbox("Utilisateur", options=["Tous"] + USERS, index=0)
            f_type = f_col2.selectbox("Type", options=["Tous"] + TYPES, index=0)
            f_search = f_col3.text_input("Recherche (titre / description)")

            mask = pd.Series([True] * len(df_journal))
            if f_user != "Tous":
                mask &= df_journal["Qui_Connecte"] == f_user
            if f_type != "Tous":
                mask &= df_journal["Type"] == f_type
            if f_search:
                mask &= df_journal["Titre"].str.contains(f_search, case=False, na=False) | df_journal["Description"].str.contains(f_search, case=False, na=False)

            df_filtered = df_journal[mask].sort_values(by="Date", ascending=False)
            st.dataframe(df_filtered.reset_index(drop=True), use_container_width=True)

            # Édition / suppression simple (par index)
            st.markdown("**Modifier ou supprimer une transaction**")
            idx_options = df_filtered.index.tolist()
            if idx_options:
                sel_idx = st.selectbox("Sélectionner la ligne (index)", options=idx_options)
                row = df_filtered.loc[sel_idx]
                with st.form("edit_trans", clear_on_submit=False):
                    e_date = st.date_input("Date", value=row["Date"])
                    e_type = st.selectbox("Type", options=TYPES, index=TYPES.index(row["Type"]) if row["Type"] in TYPES else 0)
                    e_titre = st.text_input("Titre", value=row["Titre"])
                    e_montant = st.number_input("Montant", value=float(row["Montant"]), step=0.01)
                    e_categorie = st.text_input("Catégorie", value=row.get("Categorie", ""))
                    e_desc = st.text_area("Description", value=row.get("Description", ""))
                    btn_save_t = st.form_submit_button("Enregistrer")
                    btn_del_t = st.form_submit_button("Supprimer")

                    if btn_save_t:
                        try:
                            df_edit = df.copy()
                            df_edit.loc[sel_idx, ["Date", "Mois", "Annee", "Type", "Titre", "Montant", "Categorie", "Description"]] = [
                                e_date, e_date.month, e_date.year, e_type, e_titre, float(e_montant), e_categorie, e_desc
                            ]
                            save_data_to_sheet(TAB_DATA, df_edit)
                            st.success("Transaction mise à jour")
                            clear_cache(); st.experimental_rerun()
                        except Exception as e:
                            st.error(f"Erreur mise à jour: {e}")
                    if btn_del_t:
                        try:
                            df_del = df.copy()
                            df_del = df_del.drop(index=sel_idx)
                            save_data_to_sheet(TAB_DATA, df_del)
                            st.success("Transaction supprimée")
                            clear_cache(); st.experimental_rerun()
                        except Exception as e:
                            st.error(f"Erreur suppression: {e}")
            else:
                st.info("Aucune ligne sélectionnable.")

    # --- ABONNEMENTS ---
    with subtabs[2]:
        page_header("Abonnements")
        st.markdown("Gérer les abonnements récurrents")
        df_abos_current = df_abonnements.copy() if not df_abonnements.empty else pd.DataFrame(columns=["Nom", "Montant", "Jour", "Categorie", "Compte_Source", "Proprietaire", "Imputation", "Frequence"])
        st.dataframe(df_abos_current, use_container_width=True)
        with st.expander("Ajouter un abonnement"):
            with st.form("form_add_abo", clear_on_submit=True):
                a_nom = st.text_input("Nom")
                a_mont = st.number_input("Montant", min_value=0.0, step=0.01)
                a_jour = st.number_input("Jour du mois", min_value=1, max_value=31, value=1)
                a_cat = st.text_input("Catégorie")
                a_compte = st.selectbox("Compte source", options=get_comptes_autorises(user_actuel))
                a_prop = st.selectbox("Propriétaire", options=USERS)
                a_imput = st.selectbox("Imputation", options=IMPUTATIONS)
                a_freq = st.selectbox("Fréquence", options=FREQUENCES)
                sub = st.form_submit_button("Ajouter")
                if sub:
                    new_ab = {"Nom": a_nom, "Montant": a_mont, "Jour": a_jour, "Categorie": a_cat, "Compte_Source": a_compte, "Proprietaire": a_prop, "Imputation": a_imput, "Frequence": a_freq}
                    df_abos_new = pd.concat([df_abos_current, pd.DataFrame([new_ab])], ignore_index=True)
                    try:
                        save_abonnements(df_abos_new)
                        st.success("Abonnement ajouté")
                        clear_cache(); st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Erreur ajout abonnement: {e}")

# 3. SYNTHÈSE (onglet principal "Synthèse" index 2)
with tabs[2]:
    page_header("Synthèse & Budget")
    st.markdown("Vue consolidée et objectifs")
    # (Contenu synthèse détaillée déjà géré dans l'onglet principal index 0; ici on peut ajouter graphiques supplémentaires)
    st.info("Section synthèse détaillée - à personnaliser selon besoins")

# 4. ANALYSE & BUDGET
with tabs[3]:
    page_header("Analyse & Budget")
    st.markdown("Analyse des dépenses, budgets par catégorie, projections")
    # Exemple rapide : évolution dépenses par catégorie
    if not df.empty:
        df_an = df[df["Type"] == "Dépense"].groupby(["Annee", "Mois", "Categorie"])["Montant"].sum().reset_index()
        st.dataframe(df_an.head(50), use_container_width=True)
    else:
        st.info("Pas de données pour l'analyse")

# 5. PRÉVISIONNEL / ÉQUILIBRE
with tabs[4]:
    page_header("Prévisionnel / Équilibre")
    st.markdown("Prévisions simples basées sur abonnements et moyennes")
    if not df_abonnements.empty:
        st.dataframe(df_abonnements, use_container_width=True)
    else:
        st.info("Aucun abonnement configuré")

# 6. PATRIMOINE
with tabs[5]:
    page_header("Patrimoine")
    st.markdown("Saisie et suivi des relevés de patrimoine")
    df_pat = df_patrimoine.copy()
    if df_pat.empty:
        st.info("Aucun relevé de patrimoine")
    else:
        st.dataframe(df_pat, use_container_width=True)
    with st.expander("Ajouter un relevé"):
        with st.form("form_add_patrimoine", clear_on_submit=True):
            p_date = st.date_input("Date", datetime.today())
            p_compte = st.text_input("Compte")
            p_mont = st.number_input("Montant", step=0.01)
            p_prop = st.selectbox("Propriétaire", options=USERS)
            subp = st.form_submit_button("Ajouter relevé")
            if subp:
                newp = {"Date": p_date, "Mois": p_date.month, "Annee": p_date.year, "Compte": p_compte, "Montant": float(p_mont), "Proprietaire": p_prop}
                df_pat_new = pd.concat([df_pat, pd.DataFrame([newp])], ignore_index=True)
                try:
                    save_data_to_sheet(TAB_PATRIMOINE, df_pat_new)
                    st.success("Relevé ajouté")
                    clear_cache(); st.experimental_rerun()
                except Exception as e:
                    st.error(f"Erreur ajout relevé: {e}")

# 7. CONFIGURATION (Comptes) - section améliorée et complète
with tabs[6]:
    page_header("Configuration", "Gérer les paramètres et la structure des comptes")
    st.subheader("Gestion des comptes")
    st.markdown("Ici tu peux visualiser et gérer les comptes. Seuls les comptes dont tu es **Propriétaire** ou les comptes **partagés** sont modifiables par toi.")

    # Charger la table des comptes actuelle
    df_comptes_current = load_data_from_sheet(TAB_COMPTES, ["Proprietaire", "Compte", "Type", "Partage"])
    # Normaliser colonnes si nécessaire
    if "Partage" not in df_comptes_current.columns:
        df_comptes_current["Partage"] = "Privé"

    # Affichage professionnel : colonnes claires
    df_display = df_comptes_current.rename(columns={
        "Proprietaire": "Propriétaire",
        "Compte": "Nom du compte",
        "Type": "Type de compte",
        "Partage": "Mode de partage"
    })[["Propriétaire", "Nom du compte", "Type de compte", "Mode de partage"]]

    st.markdown("**Liste des comptes**")
    st.dataframe(df_display, use_container_width=True)

    st.markdown("---")
    st.subheader("Ajouter un nouveau compte")
    with st.form("form_add_account", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        # Propriétaire : par défaut l'utilisateur connecté (sélectionné à gauche)
        proprietaire_new = col1.selectbox("Propriétaire", options=USERS + ["Commun"], index=USERS.index(user_actuel) if user_actuel in USERS else 0)
        nom_compte_new = col2.text_input("Nom du compte", placeholder="Ex: Compte Courant Elie")
        type_compte_new = col3.selectbox("Type de compte", options=TYPES_COMPTE, index=0)
        partage_new = st.radio("Mode de partage", options=["Privé (géré par le propriétaire)", "Commun (visible et géré par tous)"], index=0)
        submitted = st.form_submit_button("Créer le compte")

        if submitted:
            if not nom_compte_new:
                st.error("Donne un nom au compte.")
            else:
                # Préparer structure
                df_new = df_comptes_current.copy()
                partage_val = "Commun" if "Commun" in partage_new else "Privé"
                new_row = {"Proprietaire": proprietaire_new, "Compte": nom_compte_new, "Type": type_compte_new, "Partage": partage_val}
                df_new = pd.concat([df_new, pd.DataFrame([new_row])], ignore_index=True)
                try:
                    save_data_to_sheet(TAB_COMPTES, df_new)
                    st.success("Compte créé ✅")
                    clear_cache()
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Erreur lors de la création : {e}")

    st.markdown("---")
    st.subheader("Modifier / Supprimer un compte (restreint)")
    st.markdown("Sélectionne un compte pour le modifier. Tu peux modifier uniquement les comptes dont tu es propriétaire, ou les comptes marqués 'Commun'.")

    comptes_select = df_comptes_current["Compte"].tolist()
    if comptes_select:
        sel_compte = st.selectbox("Compte à modifier", options=comptes_select)
        row = df_comptes_current[df_comptes_current["Compte"] == sel_compte].iloc[0]
        owner_of_sel = row.get("Proprietaire", "")
        partage_of_sel = row.get("Partage", "Privé")

        # Vérifier droits : propriétaire ou partage commun
        can_edit = (owner_of_sel == user_actuel) or (str(partage_of_sel).lower() == "commun")
        if not can_edit:
            st.warning("Tu n'as pas les droits pour modifier ce compte (tu n'es pas le propriétaire et le compte n'est pas partagé).")
        else:
            with st.form("form_edit_account", clear_on_submit=False):
                new_owner = st.selectbox("Propriétaire", options=USERS + ["Commun"], index=(USERS.index(owner_of_sel) if owner_of_sel in USERS else (len(USERS) if owner_of_sel=="Commun" else 0)))
                new_name = st.text_input("Nom du compte", value=sel_compte)
                new_type = st.selectbox("Type de compte", options=TYPES_COMPTE, index=(TYPES_COMPTE.index(row.get("Type")) if row.get("Type") in TYPES_COMPTE else 0))
                new_partage = st.radio("Mode de partage", options=["Privé (géré par le propriétaire)", "Commun (visible et géré par tous)"], index=(1 if str(partage_of_sel).lower()=="commun" else 0))
                btn_save = st.form_submit_button("Enregistrer les modifications")
                btn_delete = st.form_submit_button("Supprimer le compte")

                if btn_save:
                    # Appliquer modifications
                    df_mod = df_comptes_current.copy()
                    partage_val = "Commun" if "Commun" in new_partage else "Privé"
                    df_mod.loc[df_mod["Compte"] == sel_compte, ["Proprietaire", "Compte", "Type", "Partage"]] = [new_owner, new_name, new_type, partage_val]
                    try:
                        save_data_to_sheet(TAB_COMPTES, df_mod)
                        st.success("Modifications enregistrées ✅")
                        clear_cache()
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de la sauvegarde : {e}")

                if btn_delete:
                    # Suppression confirmée
                    df_del = df_comptes_current.copy()
                    df_del = df_del[df_del["Compte"] != sel_compte]
                    try:
                        save_data_to_sheet(TAB_COMPTES, df_del)
                        st.success("Compte supprimé ✅")
                        clear_cache()
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de la suppression : {e}")
    else:
        st.info("Aucun compte configuré pour le moment.")

# --- AUTRES CONFIGURATIONS (Config générale, catégories, objectifs, mots-clés) ---
with tabs[6]:
    # Note: la section comptes est déjà affichée plus haut; ici on propose d'autres configurations
    st.markdown("---")
    st.subheader("Catégories et objectifs")
    df_cats_current = load_data_from_sheet(TAB_CONFIG, ["Type", "Categorie"])
    if df_cats_current.empty:
        st.info("Aucune catégorie configurée.")
    else:
        st.dataframe(df_cats_current, use_container_width=True)

    with st.expander("Ajouter une catégorie"):
        with st.form("form_add_cat", clear_on_submit=True):
            cat_type = st.selectbox("Type", options=TYPES)
            cat_name = st.text_input("Nom de la catégorie")
            subc = st.form_submit_button("Ajouter")
            if subc:
                if not cat_name:
                    st.error("Nom requis")
                else:
                    df_cat_new = pd.concat([df_cats_current, pd.DataFrame([{"Type": cat_type, "Categorie": cat_name}])], ignore_index=True)
                    try:
                        save_config_cats({t: df_cat_new[df_cat_new["Type"] == t]["Categorie"].tolist() for t in df_cat_new["Type"].unique()})
                        st.success("Catégorie ajoutée")
                        clear_cache(); st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Erreur ajout catégorie: {e}")

    st.markdown("---")
    st.subheader("Objectifs")
    df_objs_current = load_data_from_sheet(TAB_OBJECTIFS, ["Scope", "Categorie", "Montant"])
    st.dataframe(df_objs_current, use_container_width=True)
    with st.expander("Ajouter un objectif"):
        with st.form("form_add_obj", clear_on_submit=True):
            o_scope = st.selectbox("Scope", options=["Perso"] + USERS)
            o_cat = st.text_input("Catégorie")
            o_mont = st.number_input("Montant", min_value=0.0, step=0.01)
            subo = st.form_submit_button("Ajouter")
            if subo:
                newo = {"Scope": o_scope, "Categorie": o_cat, "Montant": float(o_mont)}
                df_objs_new = pd.concat([df_objs_current, pd.DataFrame([newo])], ignore_index=True)
                try:
                    save_objectifs_from_df(df_objs_new)
                    st.success("Objectif ajouté")
                    clear_cache(); st.experimental_rerun()
                except Exception as e:
                    st.error(f"Erreur ajout objectif: {e}")

    st.markdown("---")
    st.subheader("Mots-clés automatiques")
    df_mots_current = load_data_from_sheet(TAB_MOTS_CLES, ["Mot_Cle", "Categorie", "Type", "Compte"])
    st.dataframe(df_mots_current, use_container_width=True)
    with st.expander("Ajouter un mot-clé"):
        with st.form("form_add_mot", clear_on_submit=True):
            m_mot = st.text_input("Mot clé (sans espaces)")
            m_cat = st.text_input("Catégorie associée")
            m_type = st.selectbox("Type", options=TYPES)
            m_compte = st.selectbox("Compte associé", options=list(all_accounts))
            subm = st.form_submit_button("Ajouter")
            if subm:
                newm = {"Mot_Cle": m_mot, "Categorie": m_cat, "Type": m_type, "Compte": m_compte}
                df_mots_new = pd.concat([df_mots_current, pd.DataFrame([newm])], ignore_index=True)
                try:
                    save_mots_cles({r["Mot_Cle"]: {"Categorie": r["Categorie"], "Type": r["Type"], "Compte": r["Compte"]} for _, r in df_mots_new.iterrows()})
                    st.success("Mot-clé ajouté")
                    clear_cache(); st.experimental_rerun()
                except Exception as e:
                    st.error(f"Erreur ajout mot-clé: {e}")

# Fin du fichier
