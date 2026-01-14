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

def get_company_logo_url(company_name):
    """
    Récupère l'URL du logo d'une entreprise
    Compatible avec st.image() de Streamlit
    """
    if not company_name:
        return None
    
    company_clean = company_name.lower().strip()
    
    # Mapping des entreprises vers leurs domaines
    domain_mapping = {
        # Streaming
        "netflix": "netflix.com",
        "spotify": "spotify.com",
        "amazon": "amazon.com",
        "amazon prime": "primevideo.com",
        "disney": "disneyplus.com",
        "disney+": "disneyplus.com",
        "apple tv": "tv.apple.com",
        "apple music": "music.apple.com",
        "youtube": "youtube.com",
        "deezer": "deezer.com",
        "canal+": "canalplus.com",
        "canal plus": "canalplus.com",
        "hbo": "hbo.com",
        
        # Banques françaises
        "bnp": "bnpparibas.com",
        "bnp paribas": "bnpparibas.com",
        "société générale": "societegenerale.com",
        "societe generale": "societegenerale.com",
        "crédit agricole": "credit-agricole.fr",
        "credit agricole": "credit-agricole.fr",
        "lcl": "lcl.fr",
        "boursorama": "boursorama.com",
        "fortuneo": "fortuneo.fr",
        "hello bank": "hellobank.fr",
        "caisse d'épargne": "caisse-epargne.fr",
        "banque postale": "labanquepostale.fr",
        "cic": "cic.fr",
        "crédit mutuel": "creditmutuel.fr",
        
        # Néobanques
        "revolut": "revolut.com",
        "n26": "n26.com",
        "qonto": "qonto.com",
        
        # Telecom
        "orange": "orange.fr",
        "free": "free.fr",
        "sfr": "sfr.fr",
        "bouygues": "bouyguestelecom.fr",
        
        # Énergie
        "edf": "edf.fr",
        "engie": "engie.fr",
        "total": "totalenergies.fr",
        
        # Transport
        "uber": "uber.com",
        "deliveroo": "deliveroo.com",
        "bolt": "bolt.eu",
        "sncf": "sncf.com",
        
        # Voyage
        "airbnb": "airbnb.com",
        "booking": "booking.com",
        
        # Tech
        "google": "google.com",
        "microsoft": "microsoft.com",
        "adobe": "adobe.com",
        "github": "github.com",
        "dropbox": "dropbox.com",
        "notion": "notion.so",
        "slack": "slack.com",
        "zoom": "zoom.us",
        "canva": "canva.com",
        "openai": "openai.com",
        "chatgpt": "openai.com",
    }
    
    # Chercher le domaine
    domain = None
    for key, dom in domain_mapping.items():
        if key in company_clean:
            domain = dom
            break
    
    # Si pas trouvé, essayer le premier mot + .com
    if not domain:
        first_word = company_clean.split()[0] if company_clean else ""
        if first_word and len(first_word) > 2:
            domain = f"{first_word}.com"
    
    # Retourner l'URL Clearbit (fonctionne sans clé API)
    if domain:
        return f"https://logo.clearbit.com/{domain}"
    
    return None

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
        load_data_from_sheet(TAB_COMPTES, ["Proprietaire", "Compte", "Type"]),
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

    comptes = {"Pierre": ["Compte Courant Pierre"], "Elie": ["Compte Courant Elie"], "Commun": []}
    comptes_types = {}
    if not df_comptes.empty:
        comptes = {}
        for _, row in df_comptes.iterrows():
            if row["Proprietaire"] not in comptes: comptes[row["Proprietaire"]] = []
            comptes[row["Proprietaire"]].append(row["Compte"])
            c_type = row.get("Type", "Courant")
            if not c_type: c_type = "Courant"
            comptes_types[row["Compte"]] = c_type
            
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
            
    return cats, comptes, objs_list, df_abos, projets_data, comptes_types, mots_cles_dict

def save_config_cats(d): save_data_to_sheet(TAB_CONFIG, pd.DataFrame([{"Type": t, "Categorie": c} for t, l in d.items() for c in l]))
def save_comptes_struct(d, types_map): 
    rows = []
    for p, l in d.items():
        for c in l:
            rows.append({"Proprietaire": p, "Compte": c, "Type": types_map.get(c, "Courant")})
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

cats_memoire, comptes_structure, objectifs_list, df_abonnements, projets_config, comptes_types_map, mots_cles_map = process_configs()
def get_comptes_autorises(user): return comptes_structure.get(user, []) + comptes_structure.get("Commun", []) + ["Autre / Externe"]
all_my_accounts = get_comptes_autorises("Pierre") + get_comptes_autorises("Elie")
SOLDES_ACTUELS = calculer_soldes_reels(df, df_patrimoine, list(set(all_my_accounts)))

# --- SIDEBAR (COMPTES PUIS PÉRIODE) ---
with st.sidebar:
    st.markdown("<h3 style='margin-bottom:20px;'>Menu</h3>", unsafe_allow_html=True)
    user_actuel = st.selectbox("Utilisateur", USERS)
    
    st.markdown("---")
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

    st.markdown(f"**COMPTES ({total_courant:,.0f}€)**")
    for name, val in list_courant: draw_account_card(name, val, False)
    st.write("")
    st.markdown(f"**ÉPARGNE ({total_epargne:,.0f}€)**")
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
            c_src = ce1.selectbox("Source", comptes_disponibles, key="src_e")
            c_tgt = ce2.selectbox("Cible", [c for c in comptes_disponibles if comptes_types_map.get(c) == "Épargne"] or comptes_disponibles, key="tgt_e")
            p_sel = ce3.selectbox("Projet", list(projets_config.keys()) + ["Nouveau", "Aucun"], key="prj_e")
            p_epg = st.text_input("Nouveau Projet", key="new_prj") if p_sel == "Nouveau" else ("" if p_sel == "Aucun" else p_sel)
            
        elif type_op == "Virement Interne":
            st.markdown("**Virement**")
            cv1, cv2 = st.columns(2)
            c_src = cv1.selectbox("Débit", comptes_disponibles, key="src_v")
            c_tgt = cv2.selectbox("Crédit", comptes_disponibles, key="tgt_v")
            p_par = "Virement"; imput = "Neutre"
            
        else:
            st.markdown("**Détails**")
            cc1, cc2, cc3 = st.columns(3)
            default_compte_idx = 0
            if compte_auto and compte_auto in comptes_disponibles:
                default_compte_idx = comptes_disponibles.index(compte_auto)
            c_src = cc1.selectbox("Compte", comptes_disponibles, index=default_compte_idx, key="src_d")
            p_par = cc2.selectbox("Payé par", ["Pierre", "Elie", "Commun"], key="par_d")
            imput = cc3.radio("Imputation", IMPUTATIONS, key="imp_d")
            if imput == "Commun (Autre %)":
                pc = st.slider("% Pierre", 0, 100, 50, key="sld_d"); imput = f"Commun ({pc}/{100-pc})"
        
        st.write("")
        desc = st.text_area("Note", height=60, key="dsc_d")
        if st.button("Enregistrer Transaction", type="primary", use_container_width=True, key="btn_save"):
            if not cat_finale: st.error("Catégorie requise")
            elif not c_src and type_op != "Revenu": st.error("Compte source requis")
            else:
                if not titre_op: titre_op = cat_finale
                if type_op != "Virement Interne" and cat_finale not in cats_memoire.get(type_op, []):
                    if type_op not in cats_memoire: cats_memoire[type_op] = []
                    cats_memoire[type_op].append(cat_finale); save_config_cats(cats_memoire)
                if type_op == "Épargne" and p_epg and p_epg not in projets_config:
                    projets_config[p_epg] = {"Cible": 0.0, "Date_Fin": ""}
                    save_projets_targets(projets_config)
                
                new_row = {"Date": date_op, "Mois": date_op.month, "Annee": date_op.year, "Qui_Connecte": user_actuel, "Type": type_op, "Categorie": cat_finale, "Titre": titre_op, "Description": desc, "Montant": montant_op, "Paye_Par": p_par, "Imputation": imput, "Compte_Cible": c_tgt, "Projet_Epargne": p_epg, "Compte_Source": c_src}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True); save_data_to_sheet(TAB_DATA, df)
                st.success("Enregistré !"); time.sleep(1); st.rerun()

    # --- JOURNAL ---
    with subtabs[1]:
        col_search, col_export = st.columns([3, 1])
        search = col_search.text_input("Rechercher transaction...", placeholder="Ex: Auchan", key="search_j")
        
        if not df.empty:
            df_e = df.copy().sort_values(by="Date", ascending=False)
            if search: df_e = df_e[df_e.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]
            
            # ===== MODULE 3: EXPORT EXCEL CORRIGÉ =====
            excel_data = to_excel_download(df_e)
            
            col_export.download_button(
                label="Export",
                data=excel_data,
                file_name=f"transactions_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_excel",
                use_container_width=True
            )
            
            df_e.insert(0, "Suppr", False)
            ed = st.data_editor(df_e, use_container_width=True, hide_index=True, column_config={"Suppr": st.column_config.CheckboxColumn("Suppr", width="small")}, key="ed_j")
            if st.button("Supprimer sélection", type="primary", key="del_j"):
                save_data_to_sheet(TAB_DATA, ed[ed["Suppr"]==False].drop(columns=["Suppr"])); st.rerun()

    # --- ABONNEMENTS ---
  with subtabs[2]:
        st.markdown("### 💳 Mes Abonnements")
        
        # Bouton Nouveau en haut
        with st.expander("➕ Nouvel Abonnement", expanded=False):
            with st.form("new_abo_form"):
                col1, col2, col3, col4 = st.columns(4)
                nom_abo = col1.text_input("Nom", placeholder="Ex: Netflix, Spotify...", key="na")
                montant_abo = col2.number_input("Montant (€)", min_value=0.0, key="ma")
                jour_abo = col3.number_input("Jour", 1, 31, 1, key="ja")
                freq_abo = col4.selectbox("Fréquence", FREQUENCES, key="fa")
                
                col5, col6, col7 = st.columns(3)
                cat_abo = col5.selectbox("Catégorie", cats_memoire.get("Dépense", []), key="ca")
                compte_abo = col6.selectbox("Compte", comptes_disponibles, key="cpa")
                imp_abo = col7.selectbox("Imputation", IMPUTATIONS, key="ia")
                
                if imp_abo == "Commun (Autre %)":
                    pc_abo = st.slider("% Pierre", 0, 100, 50, key="pa")
                    imp_abo = f"Commun ({pc_abo}/{100-pc_abo})"
                
                if st.form_submit_button("✅ Ajouter", type="primary", use_container_width=True):
                    new_abo = pd.DataFrame([{
                        "Nom": nom_abo,
                        "Montant": montant_abo,
                        "Jour": jour_abo,
                        "Categorie": cat_abo,
                        "Compte_Source": compte_abo,
                        "Proprietaire": user_actuel,
                        "Imputation": imp_abo,
                        "Frequence": freq_abo
                    }])
                    df_abonnements = pd.concat([df_abonnements, new_abo], ignore_index=True)
                    save_abonnements(df_abonnements)
                    st.success(f"✅ {nom_abo} ajouté !")
                    time.sleep(1)
                    st.rerun()
        
        st.markdown("---")
        
        # Filtrer les abonnements de l'utilisateur
        if not df_abonnements.empty:
            my_abos = df_abonnements[
                (df_abonnements["Proprietaire"] == user_actuel) | 
                (df_abonnements["Imputation"].str.contains("Commun", na=False))
            ].copy()
            
            if not my_abos.empty:
                # Préparer les données
                abo_list = []
                to_generate = []
                
                for idx, row in my_abos.iterrows():
                    is_paid = False
                    if not df_mois.empty:
                        matching = df_mois[
                            (df_mois["Titre"] == row["Nom"]) & 
                            (df_mois["Montant"] == float(row["Montant"]))
                        ]
                        is_paid = not matching.empty
                    
                    abo_list.append({
                        "idx": idx,
                        "nom": row["Nom"],
                        "montant": float(row["Montant"]),
                        "jour": int(row["Jour"]),
                        "categorie": row["Categorie"],
                        "compte": row["Compte_Source"],
                        "imputation": row["Imputation"],
                        "frequence": row["Frequence"],
                        "statut": is_paid,
                        "row_data": row
                    })
                    
                    if not is_paid:
                        to_generate.append(row)
                
                # Bouton génération en masse
                if to_generate:
                    if st.button(f"🔄 Générer {len(to_generate)} abonnement(s) manquant(s)", type="primary", use_container_width=True):
                        new_transactions = []
                        for row in to_generate:
                            try:
                                date_abo = datetime(annee_selection, mois_selection, int(row["Jour"])).date()
                            except:
                                date_abo = datetime(annee_selection, mois_selection, 28).date()
                            
                            paye_par = "Commun" if "Commun" in str(row["Imputation"]) else row["Proprietaire"]
                            
                            new_transactions.append({
                                "Date": date_abo,
                                "Mois": mois_selection,
                                "Annee": annee_selection,
                                "Qui_Connecte": row["Proprietaire"],
                                "Type": "Dépense",
                                "Categorie": row["Categorie"],
                                "Titre": row["Nom"],
                                "Description": "Abonnement automatique",
                                "Montant": float(row["Montant"]),
                                "Paye_Par": paye_par,
                                "Imputation": row["Imputation"],
                                "Compte_Cible": "",
                                "Projet_Epargne": "",
                                "Compte_Source": row["Compte_Source"]
                            })
                        
                        df = pd.concat([df, pd.DataFrame(new_transactions)], ignore_index=True)
                        save_data_to_sheet(TAB_DATA, df)
                        st.success(f"✅ {len(new_transactions)} abonnement(s) généré(s) !")
                        time.sleep(1)
                        st.rerun()
                    
                    st.markdown("---")
                
                # Affichage en vignettes 3 par ligne (pour avoir plus d'espace)
                st.markdown("#### 📋 Liste des abonnements")
                
                for i in range(0, len(abo_list), 3):
                    cols = st.columns(3)
                    
                    for j, col in enumerate(cols):
                        if i + j < len(abo_list):
                            abo = abo_list[i + j]
                            
                            # Couleurs selon le statut
                            if abo["statut"]:
                                gradient = "linear-gradient(135deg, #10B981 0%, #059669 100%)"
                                badge = "✅ Payé"
                                badge_color = "#10B981"
                            else:
                                gradient = "linear-gradient(135deg, #F59E0B 0%, #D97706 100%)"
                                badge = "⏳ En attente"
                                badge_color = "#F59E0B"
                            
                            with col:
                                # Card avec header pour le logo
                                st.markdown(f"""
                                <div style="background: {gradient}; border-radius: 16px; padding: 0; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); overflow: hidden;">
                                    <div style="background: white; padding: 16px; text-align: center; border-bottom: 2px solid rgba(0,0,0,0.1);">
                                """, unsafe_allow_html=True)
                                
                                # Logo avec st.image (MÉTHODE QUI FONCTIONNE)
                                logo_url = get_company_logo_url(abo["nom"])
                                if logo_url:
                                    try:
                                        st.image(logo_url, width=80)
                                    except:
                                        st.markdown(f"<div style='font-size: 48px;'>💳</div>", unsafe_allow_html=True)
                                else:
                                    st.markdown(f"<div style='font-size: 48px;'>💳</div>", unsafe_allow_html=True)
                                
                                st.markdown("""
                                    </div>
                                    <div style="padding: 20px;">
                                """, unsafe_allow_html=True)
                                
                                st.markdown(f"""
                                        <div style="background: {badge_color}; color: white; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 12px; display: inline-block; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px;">{badge}</div>
                                        <div style="font-size: 18px; font-weight: 800; color: white; margin-bottom: 8px;">{abo['nom']}</div>
                                        <div style="font-size: 28px; font-weight: 900; color: white; margin-bottom: 8px;">{abo['montant']:.2f} €</div>
                                        <div style="font-size: 13px; color: rgba(255,255,255,0.9); font-weight: 600; margin-bottom: 4px;">📅 Le {abo['jour']} du mois</div>
                                        <div style="font-size: 12px; color: rgba(255,255,255,0.8); font-weight: 500;">🏷️ {abo['categorie']}</div>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Bouton Modifier
                                if st.button(f"✏️ Modifier", key=f"edit_abo_{abo['idx']}", use_container_width=True):
                                    st.session_state[f'editing_abo_{abo["idx"]}'] = not st.session_state.get(f'editing_abo_{abo["idx"]}', False)
                                
                                # Formulaire de modification
                                if st.session_state.get(f'editing_abo_{abo["idx"]}', False):
                                    with st.form(f"form_edit_{abo['idx']}"):
                                        st.markdown("**✏️ Modifier**")
                                        
                                        new_nom = st.text_input("Nom", value=abo['nom'], key=f"edit_nom_{abo['idx']}")
                                        new_montant = st.number_input("Montant (€)", value=abo['montant'], min_value=0.0, key=f"edit_montant_{abo['idx']}")
                                        new_jour = st.number_input("Jour", value=abo['jour'], min_value=1, max_value=31, key=f"edit_jour_{abo['idx']}")
                                        new_freq = st.selectbox("Fréquence", FREQUENCES, index=FREQUENCES.index(abo['frequence']) if abo['frequence'] in FREQUENCES else 0, key=f"edit_freq_{abo['idx']}")
                                        new_cat = st.selectbox("Catégorie", cats_memoire.get("Dépense", []), index=cats_memoire.get("Dépense", []).index(abo['categorie']) if abo['categorie'] in cats_memoire.get("Dépense", []) else 0, key=f"edit_cat_{abo['idx']}")
                                        
                                        if st.form_submit_button("💾 Enregistrer", use_container_width=True):
                                            # Mettre à jour l'abonnement
                                            df_abonnements.loc[abo['idx'], 'Nom'] = new_nom
                                            df_abonnements.loc[abo['idx'], 'Montant'] = new_montant
                                            df_abonnements.loc[abo['idx'], 'Jour'] = new_jour
                                            df_abonnements.loc[abo['idx'], 'Frequence'] = new_freq
                                            df_abonnements.loc[abo['idx'], 'Categorie'] = new_cat
                                            
                                            save_abonnements(df_abonnements)
                                            st.success(f"✅ {new_nom} modifié !")
                                            st.session_state[f'editing_abo_{abo["idx"]}'] = False
                                            time.sleep(1)
                                            st.rerun()
                                
                                # Bouton Supprimer
                                if st.button(f"🗑️ Supprimer", key=f"del_abo_{abo['idx']}", use_container_width=True):
                                    df_abonnements = df_abonnements.drop(abo['idx'])
                                    save_abonnements(df_abonnements)
                                    st.success(f"✅ {abo['nom']} supprimé")
                                    time.sleep(1)
                                    st.rerun()
            else:
                st.info("👋 Aucun abonnement pour le moment. Créez-en un ci-dessus !")
        else:
            st.info("👋 Aucun abonnement configuré. Commencez par en ajouter un !")

# 3. ANALYSE & BUDGET
with tabs[2]:
    page_header("Analyses & Budget")
    
    # ===== MODULE 2: MODE COMPARAISON M vs M-1 =====
    st.subheader("Comparaison Mensuelle")
    
    date_mois_actuel = datetime(annee_selection, mois_selection, 1)
    date_mois_precedent = date_mois_actuel - relativedelta(months=1)
    mois_prec = date_mois_precedent.month
    annee_prec = date_mois_precedent.year
    
    df_mois_prec = df[(df["Mois"] == mois_prec) & (df["Annee"] == annee_prec)]
    
    dep_actuel = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Dépense")]["Montant"].sum()
    dep_prec = df_mois_prec[(df_mois_prec["Qui_Connecte"] == user_actuel) & (df_mois_prec["Type"] == "Dépense")]["Montant"].sum()
    
    rev_actuel = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Revenu")]["Montant"].sum()
    rev_prec = df_mois_prec[(df_mois_prec["Qui_Connecte"] == user_actuel) & (df_mois_prec["Type"] == "Revenu")]["Montant"].sum()
    
    epg_actuel = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Épargne")]["Montant"].sum()
    epg_prec = df_mois_prec[(df_mois_prec["Qui_Connecte"] == user_actuel) & (df_mois_prec["Type"] == "Épargne")]["Montant"].sum()
    
    var_dep = ((dep_actuel - dep_prec) / dep_prec * 100) if dep_prec > 0 else 0
    var_rev = ((rev_actuel - rev_prec) / rev_prec * 100) if rev_prec > 0 else 0
    var_epg = ((epg_actuel - epg_prec) / epg_prec * 100) if epg_prec > 0 else 0
    
    comp1, comp2, comp3 = st.columns(3)
    comp1.metric("Dépenses", f"{dep_actuel:,.0f} €", f"{var_dep:+.1f}% vs M-1", delta_color="inverse")
    comp2.metric("Revenus", f"{rev_actuel:,.0f} €", f"{var_rev:+.1f}% vs M-1", delta_color="normal")
    comp3.metric("Épargne", f"{epg_actuel:,.0f} €", f"{var_epg:+.1f}% vs M-1", delta_color="normal")
    
    st.markdown("---")
    st.subheader("1. Flux Financiers (Sankey)")
    if not df_mois.empty:
        df_rev = df_mois[df_mois["Type"] == "Revenu"]; df_dep = df_mois[df_mois["Type"] == "Dépense"]
        rev_flows = df_rev.groupby(["Categorie", "Compte_Source"])["Montant"].sum().reset_index()
        dep_flows = df_dep.groupby(["Compte_Source", "Categorie"])["Montant"].sum().reset_index()
        
        labels = list(rev_flows["Categorie"].unique()) + list(rev_flows["Compte_Source"].unique()) + list(dep_flows["Compte_Source"].unique()) + list(dep_flows["Categorie"].unique())
        unique_labels = list(dict.fromkeys(labels))
        label_map = {name: i for i, name in enumerate(unique_labels)}
        
        src = []; tgt = []; val = []; cols = []
        for _, r in rev_flows.iterrows(): src.append(label_map[r["Categorie"]]); tgt.append(label_map[r["Compte_Source"]]); val.append(r["Montant"]); cols.append("green")
        for _, r in dep_flows.iterrows():
            if r["Compte_Source"] in label_map and r["Categorie"] in label_map: src.append(label_map[r["Compte_Source"]]); tgt.append(label_map[r["Categorie"]]); val.append(r["Montant"]); cols.append("red")
            
        if val:
            fig = go.Figure(data=[go.Sankey(node=dict(pad=15, thickness=20, line=dict(color="black", width=0.5), label=unique_labels, color="grey"), link=dict(source=src, target=tgt, value=val, color=cols))])
            st.plotly_chart(fig, use_container_width=True)
    else: st.info("Pas de données")

    st.markdown("---")
    st.subheader("2. Suivi Budgétaire")
    
    with st.expander("Configurer Budget"):
        with st.form("conf_bud"):
            c1, c2, c3, c4 = st.columns([2,2,2,1])
            s = c1.selectbox("Scope", ["Commun", "Pierre", "Elie"], key="s_b"); ca = c2.selectbox("Cat", cats_memoire.get("Dépense", []), key="ca_b"); mo = c3.number_input("Max €", key="mo_b")
            if c4.form_submit_button("Ajouter"):
                objectifs_list.append({"Scope": s, "Categorie": ca, "Montant": mo}); save_objectifs_from_df(pd.DataFrame(objectifs_list)); st.rerun()
                
        if objectifs_list:
            for i, o in enumerate(objectifs_list):
                c1, c2 = st.columns([4,1])
                c1.text(f"{o['Scope']} - {o['Categorie']} : {o['Montant']}€")
                if c2.button("X", key=f"del_obj_{i}"): objectifs_list.pop(i); save_objectifs_from_df(pd.DataFrame(objectifs_list)); st.rerun()

    df_b = pd.DataFrame(objectifs_list)
    if not df_b.empty:
        b_data = []
        for _, r in df_b.iterrows():
            mask = (df_mois["Type"] == "Dépense") & (df_mois["Categorie"] == r["Categorie"])
            if r["Scope"] == "Commun": mask = mask & (df_mois["Imputation"] == "Commun (50/50)")
            else: mask = mask & (df_mois["Imputation"] == "Perso") & (df_mois["Qui_Connecte"] == (r["Scope"] if r["Scope"] in USERS else user_actuel))
            real = df_mois[mask]["Montant"].sum()
            b_data.append({"Cat": r["Categorie"], "Scope": r["Scope"], "Budget": r["Montant"], "Réel": real, "Progression": min(real/r["Montant"] if r["Montant"]>0 else 0, 1.0), "%": f"{(real/r['Montant']*100 if r['Montant']>0 else 0):.0f}%"})
        
        st.dataframe(pd.DataFrame(b_data), column_config={"Progression": st.column_config.ProgressColumn("Etat", format="%.2f", min_value=0, max_value=1)}, use_container_width=True, hide_index=True)

# 4. PRÉVISIONNEL (MODULE 1: Cash-Flow)
with tabs[3]:
    page_header("Prévisionnel Cash-Flow")
    
    st.subheader("📈 Projection jusqu'à fin de mois")
    
    # Calcul du solde actuel
    solde_depart = sum([SOLDES_ACTUELS.get(c, 0) for c in comptes_disponibles if c != "Autre / Externe" and comptes_types_map.get(c) == "Courant"])
    
    # Abonnements restants
    abos_restants = 0
    if not df_abonnements.empty:
        abos_user = df_abonnements[(df_abonnements["Proprietaire"] == user_actuel) | (df_abonnements["Imputation"].str.contains("Commun", na=False))]
        for _, row in abos_user.iterrows():
            jour_abo = int(row["Jour"])
            if jour_abo > datetime.now().day:
                montant = float(row["Montant"])
                if "Commun" in str(row["Imputation"]):
                    montant = montant / 2
                abos_restants += montant
    
    # Projection
    depenses_moyennes_jour = dep / datetime.now().day if datetime.now().day > 0 else 0
    jours_restants = (datetime(annee_selection, mois_selection, 1) + relativedelta(months=1) - datetime.now()).days
    projection_depenses = depenses_moyennes_jour * jours_restants
    
    solde_fin_mois = solde_depart - abos_restants - projection_depenses
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Solde Actuel", f"{solde_depart:,.0f} €")
    col2.metric("Abos Restants", f"-{abos_restants:,.0f} €", delta_color="inverse")
    col3.metric("Dépenses Projetées", f"-{projection_depenses:,.0f} €", delta_color="inverse")
    
    color_fin = "#10B981" if solde_fin_mois > 0 else "#EF4444"
    gradient_fin = "linear-gradient(135deg, #10B981 0%, #059669 100%)" if solde_fin_mois > 0 else "linear-gradient(135deg, #EF4444 0%, #DC2626 100%)"
    col4.markdown(f"""
    <div style="background: {gradient_fin}; border-radius: 16px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
        <div style="font-size: 12px; color: rgba(255,255,255,0.9); font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Solde Projeté</div>
        <div style="font-size: 32px; font-weight: 800; color: white; margin-bottom: 4px;">{solde_fin_mois:,.0f} €</div>
        <div style="font-size: 13px; color: rgba(255,255,255,0.8); font-weight: 500;">Fin de mois</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Graphique de tendance
    dates_projection = pd.date_range(start=datetime.now(), end=datetime(annee_selection, mois_selection, 1) + relativedelta(months=1), freq='D')
    soldes_projection = [solde_depart - (depenses_moyennes_jour * i) for i in range(len(dates_projection))]
    
    df_proj = pd.DataFrame({"Date": dates_projection, "Solde": soldes_projection})
    fig_proj = px.line(df_proj, x="Date", y="Solde", title="Évolution projetée du solde", markers=True)
    fig_proj.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Seuil critique")
    st.plotly_chart(fig_proj, use_container_width=True)

# 5. ÉQUILIBRE (MODULE 2: Balance du couple)
with tabs[4]:
    page_header("Équilibre du Couple")
    
    st.subheader("Qui a payé quoi ?")
    
    # Calcul des dépenses communes
    df_commun = df_mois[df_mois["Imputation"].str.contains("Commun", na=False)]
    
    total_pierre = df_commun[df_commun["Paye_Par"] == "Pierre"]["Montant"].sum()
    total_elie = df_commun[df_commun["Paye_Par"] == "Elie"]["Montant"].sum()
    total_commun = total_pierre + total_elie
    
    moitie = total_commun / 2
    balance = total_pierre - moitie
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Pierre a payé", f"{total_pierre:,.0f} €")
    col2.metric("Elie a payé", f"{total_elie:,.0f} €")
    
    qui_doit = "Pierre" if balance < 0 else "Elie"
    montant_dette = abs(balance)
    balance_gradient = "linear-gradient(135deg, #10B981 0%, #059669 100%)" if balance == 0 else "linear-gradient(135deg, #F59E0B 0%, #D97706 100%)"
    
    col3.markdown(f"""
    <div style="background: {balance_gradient}; border-radius: 16px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
        <div style="font-size: 12px; color: rgba(255,255,255,0.9); font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">⚖️ Rééquilibrage</div>
        <div style="font-size: 24px; font-weight: 800; color: white; margin-bottom: 4px;">{qui_doit} doit {montant_dette:,.0f} €</div>
        <div style="font-size: 13px; color: rgba(255,255,255,0.8); font-weight: 500;">Pour équilibrer</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Répartition par catégorie
    st.subheader("Détail par catégorie")
    detail_data = []
    for cat in df_commun["Categorie"].unique():
        df_cat = df_commun[df_commun["Categorie"] == cat]
        p = df_cat[df_cat["Paye_Par"] == "Pierre"]["Montant"].sum()
        e = df_cat[df_cat["Paye_Par"] == "Elie"]["Montant"].sum()
        detail_data.append({"Catégorie": cat, "Pierre": p, "Elie": e, "Total": p+e})
    
    if detail_data:
        st.dataframe(pd.DataFrame(detail_data), use_container_width=True, hide_index=True)

# 6. PATRIMOINE
with tabs[5]:
    page_header("Patrimoine & Projets", "Gérez votre épargne et vos objectifs financiers")

    # ===== SECTION 1: PYRAMIDE DE L'ÉPARGNE =====
    st.markdown("### Pyramide de l'Épargne")

    total_epargne_user = sum([SOLDES_ACTUELS.get(c, 0) for c in comptes_disponibles if comptes_types_map.get(c) == "Épargne"])

    # Calcul des revenus mensuels
    revenus_par_mois = df[(df["Qui_Connecte"] == user_actuel) & (df["Type"] == "Revenu")].groupby(["Mois", "Annee"])["Montant"].sum()
    revenus_mensuels = revenus_par_mois.mean() if len(revenus_par_mois) > 0 else 0

    if revenus_mensuels == 0:
        st.info(
            "**Conseil** : Pour activer l'épargne de précaution, "
            "enregistrez d'abord vos revenus (Transactions → Nouvelle Saisie → Type: **Revenu**)."
        )
    else:
        epargne_precaution_cible = revenus_mensuels * 3
        epargne_precaution = min(total_epargne_user, epargne_precaution_cible)
        epargne_projets = max(0, total_epargne_user - epargne_precaution_cible)
        precaution_pct = (epargne_precaution / epargne_precaution_cible * 100) if epargne_precaution_cible > 0 else 0

        # Cards pyramide
        pyr1, pyr2, pyr3 = st.columns(3)

        with pyr1:
            gradient_prec = "linear-gradient(135deg, #10B981 0%, #059669 100%)" if precaution_pct >= 100 else "linear-gradient(135deg, #F59E0B 0%, #D97706 100%)"
            st.markdown(f"""
            <div style="background: {gradient_prec}; border-radius: 20px; padding: 28px; box-shadow: 0 8px 20px rgba(0,0,0,0.12); min-height: 240px;">
                <div style="background: rgba(255,255,255,0.25); color: white; font-size: 11px; font-weight: 700; padding: 6px 12px; border-radius: 20px; display: inline-block; margin-bottom: 16px;">Niveau 1</div>
                <div style="font-size: 16px; font-weight: 700; color: white; margin-bottom: 12px;">Épargne de Précaution</div>
                <div style="font-size: 36px; font-weight: 900; color: white; margin-bottom: 8px;">{epargne_precaution:,.0f} €</div>
                <div style="font-size: 14px; color: rgba(255,255,255,0.9); margin-bottom: 12px;">Objectif : {epargne_precaution_cible:,.0f} €</div>
                <div style="background: rgba(255,255,255,0.3); border-radius: 10px; height: 8px; margin-bottom: 8px;">
                    <div style="background: white; height: 100%; width: {precaution_pct:.1f}%; border-radius: 10px;"></div>
                </div>
                <div style="font-size: 13px; color: white;">{precaution_pct:.0f}% atteint</div>
            </div>
            """, unsafe_allow_html=True)

        with pyr2:
            gradient_proj = "linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)"
            st.markdown(f"""
            <div style="background: {gradient_proj}; border-radius: 20px; padding: 28px; box-shadow: 0 8px 20px rgba(0,0,0,0.12); min-height: 240px;">
                <div style="background: rgba(255,255,255,0.25); color: white; font-size: 11px; font-weight: 700; padding: 6px 12px; border-radius: 20px; display: inline-block; margin-bottom: 16px;">Niveau 2</div>
                <div style="font-size: 16px; font-weight: 700; color: white; margin-bottom: 12px;">Projets Court Terme</div>
                <div style="font-size: 36px; font-weight: 900; color: white; margin-bottom: 8px;">{epargne_projets:,.0f} €</div>
                <div style="font-size: 14px; color: rgba(255,255,255,0.9);">Voyages, équipements, loisirs</div>
            </div>
            """, unsafe_allow_html=True)

        with pyr3:
            investissement = df[(df["Qui_Connecte"] == user_actuel) & (df["Type"] == "Investissement")]["Montant"].sum()
            gradient_inv = "linear-gradient(135deg, #8B5CF6 0%, #6D28D9 100%)"
            st.markdown(f"""
            <div style="background: {gradient_inv}; border-radius: 20px; padding: 28px; box-shadow: 0 8px 20px rgba(0,0,0,0.12); min-height: 240px;">
                <div style="background: rgba(255,255,255,0.25); color: white; font-size: 11px; font-weight: 700; padding: 6px 12px; border-radius: 20px; display: inline-block; margin-bottom: 16px;">Niveau 3</div>
                <div style="font-size: 16px; font-weight: 700; color: white; margin-bottom: 12px;">Investissements</div>
                <div style="font-size: 36px; font-weight: 900; color: white; margin-bottom: 8px;">{investissement:,.0f} €</div>
                <div style="font-size: 14px; color: rgba(255,255,255,0.9);">Bourse, Crypto, Immobilier</div>
            </div>
            """, unsafe_allow_html=True)

        # Conseil personnalisé
        st.write("")
        if epargne_precaution < epargne_precaution_cible:
            manquant = epargne_precaution_cible - epargne_precaution
            st.warning(f"**Conseil** : Il vous manque **{manquant:,.0f}€** pour sécuriser 3 mois de salaire. Priorisez cette épargne de précaution !")
        elif epargne_projets > revenus_mensuels * 6:
            st.success(f"**Bravo !** Excellente santé financière. Vous pourriez diversifier vers des investissements long terme.")
        else:
            st.info(f"**Bien joué !** Votre épargne de précaution est sécurisée. Continuez à épargner pour vos projets !")

    st.markdown("---")

    # ===== SECTION 2: PROJETS D'ÉPARGNE =====
    st.markdown("### Mes Projets d'Épargne")

    col_add, col_space = st.columns([3, 1])
    with col_add:
        with st.expander("Créer un Nouveau Projet", expanded=False):
            with st.form("new_project_form"):
                proj_col1, proj_col2 = st.columns(2)
                nom_projet = proj_col1.text_input("Nom du projet", placeholder="Ex: Voyage en Italie", key=f"np_{i}_{j}")
                cible_projet = proj_col2.number_input("Montant cible (€)", min_value=0.0, step=100.0, key=f"tp_{i}_{j}")

                if st.form_submit_button("Créer le Projet", type="primary", use_container_width=True):
                    if nom_projet:
                        projets_config[nom_projet] = {"Cible": cible_projet, "Date_Fin": ""}
                        save_projets_targets(projets_config)
                        st.success(f"Projet '{nom_projet}' créé !")
                        time.sleep(1)
                        st.rerun()

    st.write("")

    # Affichage des projets en cards cliquables (3 par ligne)
    if projets_config:
        projets_list = list(projets_config.items())

        for i in range(0, len(projets_list), 3):
            cols = st.columns(3)

            for j, col in enumerate(cols):
                if i + j < len(projets_list):
                    projet_nom, projet_data = projets_list[i + j]

                    saved = df[(df["Projet_Epargne"] == projet_nom) & (df["Type"] == "Épargne")]["Montant"].sum() if not df.empty else 0
                    target = float(projet_data["Cible"])
                    progression = (saved / target * 100) if target > 0 else 0

                    # Couleur selon progression
                    if progression >= 100:
                        gradient = "linear-gradient(135deg, #10B981 0%, #059669 100%)"
                        badge = "Atteint"
                        badge_color = "#10B981"
                    elif progression >= 75:
                        gradient = "linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)"
                        badge = "Presque !"
                        badge_color = "#3B82F6"
                    elif progression >= 50:
                        gradient = "linear-gradient(135deg, #F59E0B 0%, #D97706 100%)"
                        badge = "En cours"
                        badge_color = "#F59E0B"
                    else:
                        gradient = "linear-gradient(135deg, #EF4444 0%, #DC2626 100%)"
                        badge = "Démarrage"
                        badge_color = "#EF4444"

                    # Message d'aide si aucune épargne
                    if saved == 0:
                        help_text = """
                        <div style="background: rgba(255,255,255,0.2); border-radius: 10px; padding: 10px; margin-top: 8px;">
                            <div style="font-size: 11px; color: white; font-weight: 600; margin-bottom: 4px;">Comment épargner :</div>
                            <div style="font-size: 10px; color: rgba(255,255,255,0.9); line-height: 1.4;">
                                Transactions → Type: <strong>Épargne</strong><br>
                                Projet: {projet_nom}
                            </div>
                        </div>
                        """
                    else:
                        help_text = ""

                    # Gestion de la barre de progression
                    if progression == 0:
                        progression_html = f"""
                        <div style="background: rgba(255,255,255,0.2); border-radius: 12px; padding: 10px; margin-bottom: 10px; text-align: center;">
                            <div style="font-size: 12px; color: rgba(255,255,255,0.9); font-weight: 600;">
                                💡 Commencez à épargner pour ce projet en enregistrant une transaction de type <strong>Épargne</strong> !
                            </div>
                        </div>
                        <div style="font-size: 14px; color: white; font-weight: 700; text-align: center; margin-bottom: 8px;">0%</div>
                        """
                    else:
                        progression_html = f"""
                        <div style="background: rgba(255,255,255,0.3); border-radius: 12px; height: 10px; overflow: hidden; margin-bottom: 10px;">
                            <div style="background: white; height: 100%; width: {progression:.1f}%; border-radius: 12px; transition: width 0.3s; box-shadow: 0 2px 8px rgba(255,255,255,0.4);"></div>
                        </div>
                        <div style="font-size: 14px; color: white; font-weight: 700; text-align: center; margin-bottom: 8px;">{progression:.1f}%</div>
                        """

                    with col:
                        st.markdown(f"""
                        <div style="background: {gradient}; border-radius: 20px; padding: 24px; margin-bottom: 20px; box-shadow: 0 8px 20px rgba(0,0,0,0.15); cursor: pointer; transition: transform 0.2s; min-height: 260px; position: relative; overflow: hidden;">
                            <div style="background: {badge_color}; color: white; font-size: 10px; font-weight: 700; padding: 5px 12px; border-radius: 15px; display: inline-block; margin-bottom: 14px; text-transform: uppercase; letter-spacing: 0.8px;">{badge}</div>
                            <div style="font-size: 20px; font-weight: 800; color: white; margin-bottom: 10px; line-height: 1.3;">{projet_nom}</div>
                            <div style="font-size: 32px; font-weight: 900; color: white; margin-bottom: 8px;">{saved:,.0f} €</div>
                            <div style="font-size: 14px; color: rgba(255,255,255,0.9); font-weight: 600; margin-bottom: 14px;">sur {target:,.0f} €</div>

                            {progression_html}

                            {help_text}
                        </div>
                        """, unsafe_allow_html=True)

                        if st.button(f"Supprimer", key=f"del_proj_{i}_{j}", use_container_width=True):
                            del projets_config[projet_nom]
                            save_projets_targets(projets_config)
                            st.success(f"Projet '{projet_nom}' supprimé")
                            time.sleep(1)
                            st.rerun()
    else:
        st.info("Aucun projet d'épargne. Créez-en un ci-dessus pour commencer à suivre vos objectifs !")

    st.markdown("---")

    # ===== SECTION 3: RELEVÉ DE COMPTES =====
    st.markdown("### Ajustement des Soldes")
    st.caption("Synchronisez vos soldes réels avec vos relevés bancaires")

    with st.form("releve_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        date_releve = col1.date_input("Date du relevé", datetime.today(), key="dr")
        compte_releve = col2.selectbox("Compte", comptes_disponibles, key="cr")
        montant_releve = col3.number_input("Solde réel (€)", step=0.01, key="mr")

        if st.form_submit_button("Enregistrer le Relevé", type="primary", use_container_width=True):
            new_releve = pd.DataFrame([{
                "Date": date_releve,
                "Mois": date_releve.month,
                "Annee": date_releve.year,
                "Compte": compte_releve,
                "Montant": montant_releve,
                "Proprietaire": user_actuel
            }])
            df_patrimoine = pd.concat([df_patrimoine, new_releve], ignore_index=True)
            save_data_to_sheet(TAB_PATRIMOINE, df_patrimoine)
            st.success(f"Relevé enregistré pour {compte_releve} : {montant_releve:,.2f} €")
            time.sleep(1)
            st.rerun()

# 5. CONFIG
with tabs[6]:
    page_header("Configuration")
    
    config_tabs = st.tabs(["Comptes", "Catégories", "Mots-Clés Auto"])
    
   # COMPTES
    with config_tabs[0]:
        st.markdown("### Gestion des Comptes Bancaires")
        st.caption(f"Vous gérez les comptes de **{user_actuel}**")
        
        # Formulaire d'ajout avec toggle pour compte commun
        with st.expander("Ajouter un Nouveau Compte", expanded=False):
            with st.form("add_compte_form"):
                compte_col1, compte_col2 = st.columns(2)
                
                nom_compte = compte_col1.text_input(
                    "Nom du Compte", 
                    placeholder="Ex: Compte Courant BNP",
                    key="nom_nouveau_compte"
                )
                
                type_compte = compte_col2.selectbox(
                    "Type de Compte",
                    TYPES_COMPTE,
                    key="type_nouveau_compte"
                )
                
                # Option compte commun (optionnel)
                est_commun = st.checkbox(
                    "Ce compte est partagé avec l'autre personne (Commun)",
                    value=False,
                    key="commun_check"
                )
                
                if st.form_submit_button("Créer le Compte", type="primary", use_container_width=True):
                    if nom_compte:
                        # Déterminer le propriétaire
                        proprio = "Commun" if est_commun else user_actuel
                        
                        # Initialiser si nécessaire
                        if proprio not in comptes_structure:
                            comptes_structure[proprio] = []
                        
                        # Vérifier que le compte n'existe pas déjà
                        if nom_compte not in comptes_structure[proprio]:
                            comptes_structure[proprio].append(nom_compte)
                            comptes_types_map[nom_compte] = type_compte
                            save_comptes_struct(comptes_structure, comptes_types_map)
                            st.success(f"✅ Compte '{nom_compte}' créé avec succès !")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"⚠️ Un compte avec ce nom existe déjà")
                    else:
                        st.error("⚠️ Veuillez entrer un nom de compte")
        
        st.markdown("---")
        
        # Affichage des comptes de l'utilisateur connecté uniquement
        st.markdown(f"#### Mes Comptes Personnels ({user_actuel})")
        
        comptes_user = comptes_structure.get(user_actuel, [])
        
        if comptes_user:
            # Affichage en cards (2 par ligne pour plus de lisibilité)
            for i in range(0, len(comptes_user), 2):
                cols = st.columns(2)
                
                for j, col in enumerate(cols):
                    if i + j < len(comptes_user):
                        compte_nom = comptes_user[i + j]
                        compte_type = comptes_types_map.get(compte_nom, "Courant")
                        solde_compte = SOLDES_ACTUELS.get(compte_nom, 0.0)
                        
                        # Couleur selon le type
                        if compte_type == "Épargne":
                            gradient = "linear-gradient(135deg, #0066FF 0%, #00D4FF 100%)"
                            icon = "💎"
                        else:
                            gradient = "linear-gradient(135deg, #10B981 0%, #059669 100%)" if solde_compte >= 0 else "linear-gradient(135deg, #EF4444 0%, #DC2626 100%)"
                            icon = "💳"
                        
                        with col:
                            st.markdown(f"""
                            <div style="background: {gradient}; border-radius: 16px; padding: 20px; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); position: relative; overflow: hidden;">
                                <div style="position: absolute; top: 10px; right: 15px; font-size: 32px; opacity: 0.3;">{icon}</div>
                                <div style="background: rgba(255,255,255,0.25); color: white; font-size: 10px; font-weight: 700; padding: 4px 10px; border-radius: 12px; display: inline-block; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.8px;">{compte_type}</div>
                                <div style="font-size: 16px; color: rgba(255,255,255,0.95); font-weight: 600; margin-bottom: 8px;">{compte_nom}</div>
                                <div style="font-size: 28px; font-weight: 800; color: white; margin-bottom: 4px;">{solde_compte:,.2f} €</div>
                                <div style="font-size: 12px; color: rgba(255,255,255,0.8); font-weight: 500;">Propriétaire : {user_actuel}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Bouton pour voir les mouvements
                            if st.button(f"Voir les mouvements", key=f"voir_mvt_{compte_nom}", use_container_width=True):
                                st.session_state[f'show_movements_{compte_nom}'] = not st.session_state.get(f'show_movements_{compte_nom}', False)
                            
                            # Afficher les mouvements si demandé
                            if st.session_state.get(f'show_movements_{compte_nom}', False):
                                # Filtrer les transactions du compte
                                df_compte = df[
                                    (df["Compte_Source"] == compte_nom) | 
                                    (df["Compte_Cible"] == compte_nom)
                                ].copy().sort_values(by="Date", ascending=False)
                                
                                if not df_compte.empty:
                                    # Ajouter une colonne pour indiquer le sens
                                    df_compte['Sens'] = df_compte.apply(
                                        lambda row: '➡️ Débit' if row['Compte_Source'] == compte_nom else '⬅️ Crédit',
                                        axis=1
                                    )
                                    
                                    # Calculer le nombre de transactions
                                    nb_transactions = len(df_compte)
                                    total_debits = df_compte[df_compte['Compte_Source'] == compte_nom]['Montant'].sum()
                                    total_credits = df_compte[df_compte['Compte_Cible'] == compte_nom]['Montant'].sum()
                                    
                                    st.markdown(f"""
                                    <div style="background: #F5F7FA; border-radius: 12px; padding: 16px; margin: 12px 0;">
                                        <div style="font-size: 14px; font-weight: 700; color: #0A1929; margin-bottom: 12px;">
                                            📈 Résumé du compte
                                        </div>
                                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; font-size: 12px;">
                                            <div>
                                                <div style="color: #6B7280; font-weight: 600;">Transactions</div>
                                                <div style="font-size: 18px; font-weight: 800; color: #0A1929;">{nb_transactions}</div>
                                            </div>
                                            <div>
                                                <div style="color: #6B7280; font-weight: 600;">Débits</div>
                                                <div style="font-size: 18px; font-weight: 800; color: #EF4444;">-{total_debits:,.0f} €</div>
                                            </div>
                                            <div>
                                                <div style="color: #6B7280; font-weight: 600;">Crédits</div>
                                                <div style="font-size: 18px; font-weight: 800; color: #10B981;">+{total_credits:,.0f} €</div>
                                            </div>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    # Afficher les dernières transactions (max 10)
                                    st.markdown("**Dernières transactions :**")
                                    df_display = df_compte[['Date', 'Titre', 'Categorie', 'Montant', 'Sens']].head(10)
                                    st.dataframe(
                                        df_display,
                                        use_container_width=True,
                                        hide_index=True,
                                        column_config={
                                            "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                                            "Titre": st.column_config.TextColumn("Titre", width="medium"),
                                            "Categorie": st.column_config.TextColumn("Catégorie", width="small"),
                                            "Montant": st.column_config.NumberColumn("Montant", format="%.2f €"),
                                            "Sens": st.column_config.TextColumn("Type", width="small")
                                        }
                                    )
                                    
                                    if len(df_compte) > 10:
                                        st.caption(f"Affichage de 10 transactions sur {len(df_compte)} au total")
                                else:
                                    st.info("Aucune transaction enregistrée pour ce compte")
                            
                            # Bouton suppression en dessous
                            if st.button(f"Supprimer ce compte", key=f"del_compte_{compte_nom}", use_container_width=True):
                                comptes_structure[user_actuel].remove(compte_nom)
                                if compte_nom in comptes_types_map:
                                    del comptes_types_map[compte_nom]
                                save_comptes_struct(comptes_structure, comptes_types_map)
                                st.success(f"Compte '{compte_nom}' supprimé")
                                time.sleep(1)
                                st.rerun()
        else:
            st.info(f"Vous n'avez pas encore de compte personnel. Créez-en un ci-dessus !")
        
        # Section Comptes Communs (si existants)
        comptes_communs = comptes_structure.get("Commun", [])
        
        if comptes_communs:
            st.markdown("---")
            st.markdown("#### Comptes Communs")
            st.caption("Ces comptes sont partagés entre Pierre et Elie")
            
            for i in range(0, len(comptes_communs), 2):
                cols = st.columns(2)
                
                for j, col in enumerate(cols):
                    if i + j < len(comptes_communs):
                        compte_nom = comptes_communs[i + j]
                        compte_type = comptes_types_map.get(compte_nom, "Courant")
                        solde_compte = SOLDES_ACTUELS.get(compte_nom, 0.0)
                        
                        # Couleur spéciale pour comptes communs
                        gradient = "linear-gradient(135deg, #8B5CF6 0%, #6D28D9 100%)"
                        icon = "🤝"
                        
                        with col:
                            st.markdown(f"""
                            <div style="background: {gradient}; border-radius: 16px; padding: 20px; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); position: relative; overflow: hidden;">
                                <div style="position: absolute; top: 10px; right: 15px; font-size: 32px; opacity: 0.3;">{icon}</div>
                                <div style="background: rgba(255,255,255,0.25); color: white; font-size: 10px; font-weight: 700; padding: 4px 10px; border-radius: 12px; display: inline-block; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.8px;">{compte_type} - COMMUN</div>
                                <div style="font-size: 16px; color: rgba(255,255,255,0.95); font-weight: 600; margin-bottom: 8px;">{compte_nom}</div>
                                <div style="font-size: 28px; font-weight: 800; color: white; margin-bottom: 4px;">{solde_compte:,.2f} €</div>
                                <div style="font-size: 12px; color: rgba(255,255,255,0.8); font-weight: 500;">Propriétaires : Pierre & Elie</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Bouton pour voir les mouvements
                            if st.button(f"Voir les mouvements", key=f"voir_mvt_commun_{compte_nom}", use_container_width=True):
                                st.session_state[f'show_movements_commun_{compte_nom}'] = not st.session_state.get(f'show_movements_commun_{compte_nom}', False)
                            
                            # Afficher les mouvements si demandé
                            if st.session_state.get(f'show_movements_commun_{compte_nom}', False):
                                # Filtrer les transactions du compte
                                df_compte = df[
                                    (df["Compte_Source"] == compte_nom) | 
                                    (df["Compte_Cible"] == compte_nom)
                                ].copy().sort_values(by="Date", ascending=False)
                                
                                if not df_compte.empty:
                                    # Ajouter une colonne pour indiquer le sens
                                    df_compte['Sens'] = df_compte.apply(
                                        lambda row: '➡️ Débit' if row['Compte_Source'] == compte_nom else '⬅️ Crédit',
                                        axis=1
                                    )
                                    
                                    # Calculer le nombre de transactions
                                    nb_transactions = len(df_compte)
                                    total_debits = df_compte[df_compte['Compte_Source'] == compte_nom]['Montant'].sum()
                                    total_credits = df_compte[df_compte['Compte_Cible'] == compte_nom]['Montant'].sum()
                                    
                                    st.markdown(f"""
                                    <div style="background: #F5F7FA; border-radius: 12px; padding: 16px; margin: 12px 0;">
                                        <div style="font-size: 14px; font-weight: 700; color: #0A1929; margin-bottom: 12px;">
                                            📈 Résumé du compte
                                        </div>
                                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; font-size: 12px;">
                                            <div>
                                                <div style="color: #6B7280; font-weight: 600;">Transactions</div>
                                                <div style="font-size: 18px; font-weight: 800; color: #0A1929;">{nb_transactions}</div>
                                            </div>
                                            <div>
                                                <div style="color: #6B7280; font-weight: 600;">Débits</div>
                                                <div style="font-size: 18px; font-weight: 800; color: #EF4444;">-{total_debits:,.0f} €</div>
                                            </div>
                                            <div>
                                                <div style="color: #6B7280; font-weight: 600;">Crédits</div>
                                                <div style="font-size: 18px; font-weight: 800; color: #10B981;">+{total_credits:,.0f} €</div>
                                            </div>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    # Afficher les dernières transactions (max 10)
                                    st.markdown("**Dernières transactions :**")
                                    df_display = df_compte[['Date', 'Titre', 'Categorie', 'Montant', 'Sens']].head(10)
                                    st.dataframe(
                                        df_display,
                                        use_container_width=True,
                                        hide_index=True,
                                        column_config={
                                            "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                                            "Titre": st.column_config.TextColumn("Titre", width="medium"),
                                            "Categorie": st.column_config.TextColumn("Catégorie", width="small"),
                                            "Montant": st.column_config.NumberColumn("Montant", format="%.2f €"),
                                            "Sens": st.column_config.TextColumn("Type", width="small")
                                        }
                                    )
                                    
                                    if len(df_compte) > 10:
                                        st.caption(f"Affichage de 10 transactions sur {len(df_compte)} au total")
                                else:
                                    st.info("Aucune transaction enregistrée pour ce compte")
                            
                            if st.button(f"🗑️ Supprimer ce compte commun", key=f"del_compte_commun_{compte_nom}", use_container_width=True):
                                comptes_structure["Commun"].remove(compte_nom)
                                if compte_nom in comptes_types_map:
                                    del comptes_types_map[compte_nom]
                                save_comptes_struct(comptes_structure, comptes_types_map)
                                st.success(f"Compte commun '{compte_nom}' supprimé")
                                time.sleep(1)
                                st.rerun()
                                
# CATÉGORIES
    with config_tabs[1]:
        st.subheader("Catégories")
        typ = st.selectbox("Type", TYPES, key="tcat")
        cats = cats_memoire.get(typ, [])
        new_c = st.text_input("Nouvelle Cat", key="ncat")
        if st.button("Ajouter Cat", key="bcat"):
            if typ not in cats_memoire: cats_memoire[typ] = []
            cats_memoire[typ].append(new_c); save_config_cats(cats_memoire); st.rerun()
            
        for c in cats:
            col_a, col_b = st.columns([4,1])
            col_a.text(c)
            if col_b.button("X", key=f"del_cat_{typ}_{c}"): cats_memoire[typ].remove(c); save_config_cats(cats_memoire); st.rerun()
    
    # MODULE 4: Gestion des mots-clés
    with config_tabs[2]:
        st.subheader("Mots-Clés Automatiques")
        st.info("Quand vous tapez un mot-clé dans le titre, l'app remplit automatiquement la catégorie et le compte.")
        
        with st.form("add_mc"):
            mc1, mc2 = st.columns(2)
            mc = mc1.text_input("Mot-Clé (ex: Uber)", key="mc_new")
            cat_mc = mc2.selectbox("Catégorie", [c for cats in cats_memoire.values() for c in cats], key="cat_mc")
            
            mc3, mc4 = st.columns(2)
            type_mc = mc3.selectbox("Type", TYPES, key="type_mc")
            compte_mc = mc4.selectbox("Compte", comptes_disponibles, key="compte_mc")
            
            if st.form_submit_button("Ajouter Mot-Clé"):
                mots_cles_map[mc.lower()] = {"Categorie": cat_mc, "Type": type_mc, "Compte": compte_mc}
                save_mots_cles(mots_cles_map); st.rerun()
        
        if mots_cles_map:
            st.write("**Mots-clés configurés:**")
            mc_data = []
            for mc, data in mots_cles_map.items():
                mc_data.append({"Mot": mc, "Cat": data["Categorie"], "Type": data["Type"], "Compte": data["Compte"]})
            
            df_mc = pd.DataFrame(mc_data)
            st.dataframe(df_mc, use_container_width=True, hide_index=True)
            
            for mc in list(mots_cles_map.keys()):
                col_a, col_b = st.columns([4,1])
                col_a.text(f"{mc} → {mots_cles_map[mc]['Categorie']}")
                if col_b.button("X", key=f"del_mc_{mc}"):
                    del mots_cles_map[mc]; save_mots_cles(mots_cles_map); st.rerun()





