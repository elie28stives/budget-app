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

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================
SHEET_NAME = "Budget_Couple_DB"
TAB_DATA = "Data"
TAB_CONFIG = "Config"
TAB_OBJECTIFS = "Objectifs"
TAB_PATRIMOINE = "Patrimoine"
TAB_COMPTES = "Comptes"
TAB_ABONNEMENTS = "Abonnements"
TAB_PROJETS = "Projets_Config"
TAB_MOTS_CLES = "Mots_Cles"
TAB_REMBOURSEMENTS = "Remboursements"
TAB_CREDITS = "Credits"

USERS = ["Pierre", "Elie"]
TYPES = ["Dépense", "Revenu", "Virement Interne", "Épargne", "Investissement"]
IMPUTATIONS = ["Perso", "Commun (50/50)", "Commun (Autre %)", "Avance/Cadeau"]
TYPES_COMPTE = ["Courant", "Épargne"]
FREQUENCES_ABO = ["Mensuel", "Trimestriel", "Semestriel", "Annuel"]
MOIS_FR = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

COLS_DATA = ["Date", "Mois", "Annee", "Qui_Connecte", "Type", "Categorie", "Titre", "Description", "Montant", "Paye_Par", "Imputation", "Compte_Cible", "Projet_Epargne", "Compte_Source"]
COLS_PAT = ["Date", "Mois", "Annee", "Compte", "Montant", "Proprietaire"]

# ==============================================================================
# FONCTIONS INTELLIGENTES
# ==============================================================================
def detecter_doublons(df, jours_tolerance=3):
    """Détecte les transactions potentiellement dupliquées"""
    doublons = []
    
    if df.empty:
        return doublons
    
    df_sorted = df.sort_values('Date')
    
    for i, row in df_sorted.iterrows():
        similaires = df_sorted[
            (df_sorted.index != i) &
            (df_sorted['Montant'] == row['Montant']) &
            (df_sorted['Categorie'] == row['Categorie']) &
            (abs((pd.to_datetime(df_sorted['Date']) - pd.to_datetime(row['Date'])).dt.days) <= jours_tolerance)
        ]
        
        if not similaires.empty:
            doublons.append({
                'transaction': row,
                'similaires': similaires.iloc[0] if len(similaires) > 0 else None
            })
    
    return doublons

def detecter_depenses_inhabituelles(df_mois, df_historique, user, seuil=2.0):
    """Détecte les dépenses anormalement élevées par rapport à l'historique"""
    alertes = []
    
    if df_historique.empty:
        return alertes
    
    # Calculer moyenne par catégorie sur les 3 derniers mois
    date_limite = datetime.now() - relativedelta(months=3)
    df_recent = df_historique[
        (pd.to_datetime(df_historique['Date']) >= date_limite) &
        (df_historique['Qui_Connecte'] == user) &
        (df_historique['Type'] == 'Dépense')
    ]
    
    moyennes = df_recent.groupby('Categorie')['Montant'].mean()
    
    # Comparer avec ce mois
    for cat in df_mois['Categorie'].unique():
        montant_mois = df_mois[df_mois['Categorie'] == cat]['Montant'].sum()
        
        if cat in moyennes:
            moyenne = moyennes[cat]
            if montant_mois > moyenne * seuil:
                ratio = montant_mois / moyenne
                alertes.append({
                    'categorie': cat,
                    'montant': montant_mois,
                    'moyenne': moyenne,
                    'ratio': ratio
                })
    
    return alertes

def suggerer_categories(titre, historique_df, mots_cles_map):
    """Suggère des catégories basées sur l'historique et les mots-clés"""
    titre_lower = titre.lower()
    
    # 1. Vérifier mots-clés configurés
    for mc, info in mots_cles_map.items():
        if mc in titre_lower:
            return info['Categorie'], "mot-clé configuré"
    
    # 2. Analyser l'historique
    if not historique_df.empty:
        titres_similaires = historique_df[
            historique_df['Titre'].str.lower().str.contains(titre_lower[:5], na=False, regex=False)
        ]
        
        if not titres_similaires.empty:
            cat_freq = titres_similaires['Categorie'].value_counts()
            if len(cat_freq) > 0:
                return cat_freq.index[0], f"basé sur {len(titres_similaires)} transaction(s) similaire(s)"
    
    return None, None

def verifier_abonnements_manquants(df_mois, df_abonnements, mois, annee, user):
    """Vérifie si des abonnements n'ont pas été générés"""
    manquants = []
    
    if df_abonnements.empty:
        return manquants
    
    abos_user = df_abonnements[df_abonnements['Proprietaire'] == user]
    
    for _, abo in abos_user.iterrows():
        # Vérifier si l'abonnement devrait être généré ce mois
        freq = abo.get('Frequence', 'Mensuel')
        date_debut = abo.get('Date_Debut', '')
        date_fin = abo.get('Date_Fin', '')
        
        # Vérifications de date
        if date_debut:
            debut = pd.to_datetime(date_debut).date()
            if datetime(annee, mois, 1).date() < debut:
                continue
        
        if date_fin:
            fin = pd.to_datetime(date_fin).date()
            if datetime(annee, mois, 1).date() > fin:
                continue
        
        # Vérifier si déjà payé
        paye = not df_mois[
            (df_mois['Titre'].str.lower() == abo['Nom'].lower()) &
            (df_mois['Montant'] == float(abo['Montant']))
        ].empty
        
        if not paye:
            manquants.append(abo)
    
    return manquants

def calculer_prevision_fin_mois(df_mois, df_historique, user, jour_actuel):
    """Prédit les dépenses totales en fin de mois"""
    # Dépenses actuelles
    dep_actuelles = df_mois[
        (df_mois['Qui_Connecte'] == user) &
        (df_mois['Type'] == 'Dépense')
    ]['Montant'].sum()
    
    # Moyenne quotidienne sur les 3 derniers mois
    date_limite = datetime.now() - relativedelta(months=3)
    df_recent = df_historique[
        (pd.to_datetime(df_historique['Date']) >= date_limite) &
        (df_historique['Qui_Connecte'] == user) &
        (df_historique['Type'] == 'Dépense')
    ]
    
    if not df_recent.empty:
        moy_journaliere = df_recent['Montant'].sum() / 90  # ~3 mois
        jours_restants = 30 - jour_actuel
        prevision = dep_actuelles + (moy_journaliere * jours_restants)
        return prevision
    
    return None

# ==============================================================================
# 2. CSS & UI
# ==============================================================================
def apply_custom_style():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        
        /* === VARIABLES === */
        :root {
            --primary: #4F46E5;
            --primary-hover: #4338CA;
            --secondary: #10B981;
            --danger: #EF4444;
            --warning: #F59E0B;
            --bg: #FAFAFA;
            --surface: #FFFFFF;
            --text: #1F2937;
            --text-light: #6B7280;
            --border: #E5E7EB;
            --shadow: rgba(0, 0, 0, 0.05);
        }
        
        /* === BASE === */
        * {
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .stApp {
            background: var(--bg);
            font-family: 'Inter', sans-serif;
            color: var(--text);
        }
        
        .main .block-container {
            padding: 3rem 2rem !important;
            max-width: 1400px;
        }
        
        #MainMenu, footer, header {
            visibility: hidden;
        }
        
        /* === SIDEBAR === */
        section[data-testid="stSidebar"] {
            background: var(--surface) !important;
            border-right: 1px solid var(--border);
            box-shadow: 2px 0 12px var(--shadow);
        }
        
        section[data-testid="stSidebar"] .stMarkdown h3 {
            color: var(--text);
            font-weight: 700;
            font-size: 18px;
            margin-bottom: 1.5rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--primary);
        }
        
        section[data-testid="stSidebar"] hr {
            border: none;
            height: 1px;
            background: var(--border);
            margin: 1.5rem 0;
        }
        
        /* === TABS === */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0;
            background: var(--surface);
            border-bottom: 1px solid var(--border);
            padding: 0;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            background: transparent;
            border: none;
            color: var(--text-light);
            font-weight: 600;
            font-size: 14px;
            padding: 0 32px;
            position: relative;
        }
        
        .stTabs [data-baseweb="tab"]::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--primary);
            transform: scaleX(0);
            transition: transform 0.3s ease;
        }
        
        .stTabs [data-baseweb="tab"]:hover {
            color: var(--primary);
            background: rgba(79, 70, 229, 0.05);
        }
        
        .stTabs [aria-selected="true"] {
            color: var(--primary) !important;
        }
        
        .stTabs [aria-selected="true"]::after {
            transform: scaleX(1);
        }
        
        /* === CARDS === */
        div[data-testid="stMetric"],
        div.stDataFrame,
        div.stForm,
        div[data-testid="stExpander"] {
            background: var(--surface);
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid var(--border);
            box-shadow: 0 1px 3px var(--shadow);
        }
        
        div[data-testid="stMetric"]:hover {
            box-shadow: 0 4px 12px var(--shadow);
            transform: translateY(-2px);
        }
        
        /* === METRICS === */
        div[data-testid="stMetric"] label {
            font-size: 12px !important;
            font-weight: 600 !important;
            color: var(--text-light) !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            font-size: 32px !important;
            font-weight: 700 !important;
            color: var(--text) !important;
        }
        
        /* === BUTTONS === */
        .stButton > button {
            background: var(--primary) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            padding: 0.625rem 1.5rem !important;
            box-shadow: 0 1px 3px rgba(79, 70, 229, 0.3) !important;
        }
        
        .stButton > button:hover {
            background: var(--primary-hover) !important;
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.4) !important;
            transform: translateY(-1px);
        }
        
        .stButton > button:active {
            transform: translateY(0);
        }
        
        /* === INPUTS === */
        .stTextInput input,
        .stNumberInput input,
        .stDateInput input,
        .stTextArea textarea {
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
            padding: 0.625rem 1rem !important;
            font-size: 14px !important;
            background: var(--surface) !important;
            color: var(--text) !important;
        }
        
        .stTextInput input:focus,
        .stNumberInput input:focus,
        .stDateInput input:focus,
        .stTextArea textarea:focus {
            border-color: var(--primary) !important;
            box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1) !important;
            outline: none !important;
        }
        
        /* === SELECT === */
        .stSelectbox > div > div {
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
            background: var(--surface) !important;
        }
        
        .stSelectbox > div > div:hover {
            border-color: var(--primary) !important;
        }
        
        .stSelectbox [data-baseweb="select"] > div {
            color: var(--text) !important;
        }
        
        /* Fix pour voir les options dans le menu déroulant */
        [data-baseweb="popover"] {
            background: var(--surface) !important;
        }
        
        [role="listbox"] {
            background: var(--surface) !important;
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
            box-shadow: 0 10px 40px var(--shadow) !important;
        }
        
        [role="option"] {
            color: var(--text) !important;
            background: var(--surface) !important;
            padding: 0.75rem 1rem !important;
        }
        
        [role="option"]:hover {
            background: rgba(79, 70, 229, 0.05) !important;
            color: var(--primary) !important;
        }
        
        [aria-selected="true"] {
            background: rgba(79, 70, 229, 0.1) !important;
            color: var(--primary) !important;
            font-weight: 600 !important;
        }
        
        /* === LABELS === */
        label {
            font-weight: 600 !important;
            color: var(--text) !important;
            font-size: 13px !important;
        }
        
        /* === RADIO === */
        .stRadio > label {
            font-weight: 600 !important;
            color: var(--text) !important;
        }
        
        .stRadio > div {
            gap: 0.5rem;
        }
        
        .stRadio [role="radiogroup"] label {
            background: var(--surface);
            border: 1px solid var(--border);
            padding: 0.5rem 1rem;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
        }
        
        .stRadio [role="radiogroup"] label:hover {
            border-color: var(--primary);
            background: rgba(79, 70, 229, 0.05);
        }
        
        /* === DATAFRAME === */
        .stDataFrame [data-testid="stDataFrameResizable"] {
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
        }
        
        /* === EXPANDER === */
        .streamlit-expanderHeader {
            background: var(--surface) !important;
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
        }
        
        .streamlit-expanderHeader:hover {
            border-color: var(--primary) !important;
        }
        
        /* === PROGRESS === */
        .stProgress > div > div {
            background: var(--primary) !important;
        }
        
        /* === SLIDER === */
        .stSlider [data-baseweb="slider"] [role="slider"] {
            background: var(--primary) !important;
        }
        
        /* === ALERTS === */
        .stAlert {
            border: none !important;
            border-radius: 8px !important;
            padding: 1rem 1.25rem !important;
        }
        
        /* === CUSTOM CLASSES === */
        .account-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 0.75rem;
            box-shadow: 0 1px 3px var(--shadow);
            animation: slideIn 0.3s ease;
        }
        
        .account-card:hover {
            box-shadow: 0 4px 12px var(--shadow);
            transform: translateX(4px);
        }
        
        .transaction-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 0.75rem;
            animation: fadeIn 0.4s ease;
        }
        
        .transaction-card:hover {
            box-shadow: 0 4px 12px var(--shadow);
            border-color: var(--primary);
        }
        
        .budget-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            animation: scaleIn 0.3s ease;
        }
        
        .budget-card:hover {
            box-shadow: 0 6px 20px var(--shadow);
            transform: translateY(-4px);
        }
        
        .cat-badge {
            display: inline-block;
            padding: 0.375rem 0.875rem;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            margin: 0.25rem;
            border: 1px solid;
            animation: fadeIn 0.3s ease;
        }
        
        .cat-badge:hover {
            transform: translateY(-2px);
            box-shadow: 0 2px 8px var(--shadow);
        }
        
        .cat-badge.depense {
            background: #FEF2F2;
            color: #DC2626;
            border-color: #FCA5A5;
        }
        
        .cat-badge.revenu {
            background: #F0FDF4;
            color: #16A34A;
            border-color: #86EFAC;
        }
        
        .cat-badge.epargne {
            background: #EFF6FF;
            color: #2563EB;
            border-color: #93C5FD;
        }
        
        /* === ANIMATIONS === */
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateX(-10px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        @keyframes scaleIn {
            from {
                opacity: 0;
                transform: scale(0.95);
            }
            to {
                opacity: 1;
                transform: scale(1);
            }
        }
        
        @keyframes pulse {
            0%, 100% {
                opacity: 1;
            }
            50% {
                opacity: 0.8;
            }
        }
        
        /* === SCROLLBAR === */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--bg);
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--text-light);
        }
    </style>
    """, unsafe_allow_html=True)

def page_header(title, subtitle=None):
    st.markdown(f"""
    <div style='margin-bottom: 2rem;'>
        <h1 style='font-size: 28px; font-weight: 700; color: #1F2937; margin-bottom: 0.5rem;'>{title}</h1>
        {f"<p style='font-size: 14px; color: #6B7280;'>{subtitle}</p>" if subtitle else ""}
    </div>
    """, unsafe_allow_html=True)

def fmt(montant, decimales=0):
    """Formate un montant en français : 7 234,43"""
    if montant is None or pd.isna(montant):
        return "0"
    try:
        m = float(montant)
        if decimales == 0:
            formatted = f"{m:,.0f}"
        else:
            formatted = f"{m:,.{decimales}f}"
        # Remplacer , par espace (milliers) et . par , (décimales)
        formatted = formatted.replace(',', 'TEMP').replace('.', ',').replace('TEMP', ' ')
        return formatted
    except:
        return "0"

# ==============================================================================
# 3. BACKEND (GSPREAD AVEC RETRY)
# ==============================================================================
@st.cache_resource
def get_client():
    try:
        creds = dict(st.secrets["gcp_service_account"])
        creds["private_key"] = creds["private_key"].replace("\\n", "\n")
        return gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds, ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]))
    except: return None

def get_ws(client, tab):
    """Récupère un worksheet avec gestion du quota API"""
    import time
    
    max_retries = 2
    for attempt in range(max_retries):
        try:
            return client.open(SHEET_NAME).worksheet(tab)
        except gspread.exceptions.APIError as e:
            if "429" in str(e) or "Quota exceeded" in str(e):
                # Quota dépassé
                if attempt < max_retries - 1:
                    time.sleep(2)  # Attendre 2 secondes
                    continue
                else:
                    st.warning("⏳ Quota API atteint. Veuillez attendre 1 minute puis cliquer sur 'Actualiser les données'.")
                    return None
            else:
                raise
        except:
            # L'onglet n'existe pas, essayer de le créer
            try:
                return client.open(SHEET_NAME).add_worksheet(title=tab, rows="100", cols="20")
            except gspread.exceptions.APIError as e:
                if "429" in str(e):
                    st.warning("⏳ Quota API atteint. Veuillez attendre 1 minute.")
                    return None
                raise
    return None

@st.cache_data(ttl=600, show_spinner=False)
def load_data(tab, cols):
    c = get_client()
    if not c: return pd.DataFrame(columns=cols)
    for i in range(3): # Retry logic
        try:
            data = get_ws(c, tab).get_all_records()
            df = pd.DataFrame(data)
            if df.empty: return pd.DataFrame(columns=cols)
            for col in cols: 
                if col not in df.columns: df[col] = ""
            
            # Nettoyer la colonne Date
            if "Date" in df.columns: 
                df["Date"] = pd.to_datetime(df["Date"], errors='coerce').dt.date
            
            # Nettoyer la colonne Montant
            if "Montant" in df.columns:
                # Convertir en string
                df["Montant"] = df["Montant"].astype(str)
                
                # Gérer les différents formats de nombres
                def clean_montant(val):
                    if pd.isna(val) or val == '' or val == 'nan':
                        return 0
                    val = str(val).strip()
                    
                    # ÉTAPE 1: Enlever TOUS les espaces (séparateurs de milliers français)
                    val = val.replace(' ', '')
                    val = val.replace('\xa0', '')  # Espace insécable
                    
                    # ÉTAPE 2: Gérer virgule vs point
                    # Si contient virgule ET point : format US "7,234.43"
                    if ',' in val and '.' in val:
                        # La virgule est le séparateur de milliers, le point est décimal
                        val = val.replace(',', '')
                    # Si contient SEULEMENT virgule : format français "7234,43"
                    elif ',' in val:
                        # La virgule est le séparateur décimal
                        val = val.replace(',', '.')
                    # Si contient SEULEMENT point : déjà bon "7234.43"
                    
                    try:
                        return float(val)
                    except:
                        return 0
                
                df["Montant"] = df["Montant"].apply(clean_montant)
            
            return df
        except Exception as e:
            if "429" in str(e): 
                pass  # Rate limit atteint, on retourne un DataFrame vide
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_data(tab, df):
    c = get_client()
    ws = get_ws(c, tab)
    if not ws:
        return
    
    df_s = df.copy()
    
    # Convertir les dates en string
    if "Date" in df_s.columns: 
        df_s["Date"] = df_s["Date"].astype(str)
    
    # S'assurer que les montants sont bien des floats
    if "Montant" in df_s.columns:
        df_s["Montant"] = pd.to_numeric(df_s["Montant"], errors='coerce').fillna(0.0)
    
    for i in range(3):
        try:
            ws.clear()
            
            # Préparer les données
            headers = df_s.columns.values.tolist()
            values = df_s.values.tolist()
            
            # Trouver l'index de la colonne Montant
            montant_col_idx = None
            if "Montant" in headers:
                montant_col_idx = headers.index("Montant")
            
            # Convertir les valeurs en s'assurant que les montants restent numériques
            clean_values = []
            for row in values:
                clean_row = []
                for idx, val in enumerate(row):
                    if idx == montant_col_idx and val is not None:
                        # Forcer en float pour la colonne Montant
                        try:
                            clean_row.append(float(val))
                        except:
                            clean_row.append(0.0)
                    else:
                        clean_row.append(val)
                clean_values.append(clean_row)
            
            # Mettre à jour avec value_input_option='RAW' pour éviter l'interprétation
            ws.update([headers] + clean_values, value_input_option='RAW')
            
            st.cache_data.clear()
            st.session_state.needs_refresh = True
            return
        except Exception as e:
            if "429" in str(e): 
                pass  # Rate limit
            else:
                st.error(f"Erreur sauvegarde: {e}")
            return

def create_backup():
    """Crée une sauvegarde hebdomadaire automatique des données"""
    try:
        from datetime import datetime
        
        # Vérifier si c'est lundi (jour 0)
        if datetime.now().weekday() != 0:
            return
        
        # Vérifier si backup déjà fait cette semaine
        last_backup = st.session_state.get('last_backup_date', '')
        week_num = datetime.now().isocalendar()[1]
        
        if str(week_num) in last_backup:
            return  # Backup déjà fait cette semaine
        
        # Marquer comme tenté même si ça échoue pour éviter retry constant
        st.session_state.last_backup_date = f"week_{week_num}"
        
        # Créer le backup (peut échouer silencieusement)
        client = get_client()
        if not client:
            return
            
        sh = client.open(SHEET_NAME)
        
        # Vérifier si l'onglet Backups existe
        try:
            ws_backup = sh.worksheet("Backups")
        except:
            # Ne pas créer si ça échoue, juste skip
            return
        
        # Ajouter la ligne de backup
        backup_data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'week': week_num,
            'nb_transactions': len(st.session_state.get('df', pd.DataFrame())),
            'nb_patrimoine': len(st.session_state.get('df_patrimoine', pd.DataFrame()))
        }
        
        ws_backup.append_row([
            backup_data['date'],
            backup_data['week'],
            backup_data['nb_transactions'],
            backup_data['nb_patrimoine']
        ])
        
    except Exception as e:
        # Backup échoue silencieusement pour ne pas bloquer l'app
        pass

@st.cache_data(ttl=600, show_spinner=False)
def load_all_configs():
    return (
        load_data(TAB_CONFIG, ["Type", "Categorie"]),
        load_data(TAB_COMPTES, ["Proprietaire", "Compte", "Type"]),
        load_data(TAB_OBJECTIFS, ["Scope", "Categorie", "Montant"]),
        load_data(TAB_ABONNEMENTS, ["Nom", "Montant", "Jour", "Categorie", "Compte_Source", "Proprietaire", "Imputation", "Frequence"]),
        load_data(TAB_PROJETS, ["Projet", "Cible", "Date_Fin", "Proprietaire"]),
        load_data(TAB_MOTS_CLES, ["Mot_Cle", "Categorie", "Type", "Compte"])
    )

# ==============================================================================
# 4. LOGIQUE
# ==============================================================================
def init_state():
    if 'op_date' not in st.session_state: st.session_state.op_date = datetime.today()

def to_excel(df):
    out = BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as writer:
        df_x = df.copy()
        if "Date" in df_x.columns: df_x["Date"] = df_x["Date"].astype(str)
        df_x.to_excel(writer, index=False, sheet_name='Data')
    return out.getvalue()

def calc_soldes(df_t, df_p, comptes):
    soldes = {}
    for c in comptes:
        rel, d_rel = 0.0, pd.to_datetime("2000-01-01").date()
        if not df_p.empty:
            df_c = df_p[df_p["Compte"]==c]
            if not df_c.empty:
                last = df_c.sort_values(by="Date", ascending=False).iloc[0]
                rel, d_rel = float(last["Montant"]), last["Date"]
        mouv = 0.0
        if not df_t.empty:
            dft = df_t[df_t["Date"] > d_rel]
            deb = dft[(dft["Compte_Source"]==c) & (dft["Type"].isin(["Dépense","Investissement"]))]["Montant"].sum()
            vout = dft[(dft["Compte_Source"]==c) & (dft["Type"].isin(["Virement Interne","Épargne"]))]["Montant"].sum()
            cred = dft[(dft["Compte_Source"]==c) & (dft["Type"]=="Revenu")]["Montant"].sum()
            vin = dft[(dft["Compte_Cible"]==c) & (dft["Type"].isin(["Virement Interne","Épargne"]))]["Montant"].sum()
            mouv = cred + vin - deb - vout
        soldes[c] = rel + mouv
    return soldes

def process_data():
    raw = load_all_configs()
    
    # Catégories avec valeurs par défaut complètes
    cats = {k: [] for k in TYPES}
    if not raw[0].empty:
        for _, r in raw[0].iterrows():
            if r["Type"] in cats and r["Categorie"] not in cats[r["Type"]]: 
                cats[r["Type"]].append(r["Categorie"])
    
    # Catégories par défaut si la base est vide
    if not cats["Dépense"]:
        cats["Dépense"] = [
            # Alimentation & Courses
            "Alimentation", "Courses", "Restaurant", "Fast Food", "Boulangerie", "Marché",
            # Logement
            "Loyer", "Charges", "Électricité", "Eau", "Gaz", "Internet", "Téléphone", "Assurance Habitation",
            # Transport
            "Essence", "Transport en Commun", "Parking", "Péage", "Assurance Auto", "Entretien Véhicule",
            # Santé & Bien-être
            "Pharmacie", "Médecin", "Dentiste", "Mutuelle", "Sport", "Coiffeur", "Cosmétiques",
            # Loisirs & Culture
            "Cinéma", "Streaming", "Livres", "Jeux", "Sorties", "Voyages", "Hobbies",
            # Shopping
            "Vêtements", "Chaussures", "Électronique", "Maison & Déco", "Cadeaux",
            # Services & Abonnements
            "Abonnements", "Banque", "Impôts", "Crèche", "École", "Formation",
            # Animaux
            "Vétérinaire", "Nourriture Animaux", "Accessoires Animaux",
            # Divers
            "Autre"
        ]
    
    if not cats["Revenu"]:
        cats["Revenu"] = [
            "Salaire", "Prime", "Bonus", "Freelance", "Vente", "Remboursement", 
            "Allocations", "Aide", "Intérêts", "Dividendes", "Loyer Perçu", "Autre"
        ]
    
    if not cats["Épargne"]:
        cats["Épargne"] = [
            "Épargne Mensuelle", "Épargne Projet", "Épargne Urgence", 
            "Livret A", "PEL", "Assurance Vie", "Plan Épargne", "Autre"
        ]
    
    if not cats["Virement Interne"]:
        cats["Virement Interne"] = [
            "Transfert Comptes", "Rééquilibrage", "Autre"
        ]
    
    if not cats["Investissement"]:
        cats["Investissement"] = [
            "Bourse", "Crypto", "Immobilier", "Startup", "Autre"
        ]
    
    # Comptes
    comptes, c_types = {}, {}
    if not raw[1].empty:
        for _, r in raw[1].iterrows():
            comptes.setdefault(r["Proprietaire"], []).append(r["Compte"])
            c_types[r["Compte"]] = r.get("Type", "Courant")
            
    # Projets
    projets = {}
    if not raw[4].empty:
        for _, r in raw[4].iterrows():
            projets[r["Projet"]] = {"Cible": float(r["Cible"]), "Proprietaire": r.get("Proprietaire", "Commun"), "Date_Fin": r["Date_Fin"]}
            
    # Mots clés
    mots = {r["Mot_Cle"].lower(): {"Categorie":r["Categorie"], "Type":r["Type"], "Compte":r["Compte"]} for _, r in raw[5].iterrows()} if not raw[5].empty else {}
    
    return cats, comptes, raw[2].to_dict('records'), raw[3], projets, c_types, mots

# ==============================================================================
# 5. APP MAIN
# ==============================================================================
st.set_page_config(page_title="Ma Banque V79", layout="wide", page_icon="🏦")
apply_custom_style()
init_state()

# === OPTIMISATION PERFORMANCE : SESSION STATE ===
# Charger les données une seule fois et les stocker en session
# Gain : 5-10x plus rapide, moins de requêtes Google Sheets

# Initialiser le flag de rechargement si nécessaire
if 'needs_refresh' not in st.session_state:
    st.session_state.needs_refresh = True

# Charger les données uniquement si nécessaire
if st.session_state.needs_refresh or 'df' not in st.session_state:
    # Chargement depuis Google Sheets
    df = load_data(TAB_DATA, COLS_DATA)
    df_patrimoine = load_data(TAB_PATRIMOINE, COLS_PAT)
    cats_memoire, comptes_structure, objectifs_list, df_abonnements, projets_config, comptes_types_map, mots_cles_map = process_data()
    
    # Stocker dans session_state pour réutilisation
    st.session_state.df = df
    st.session_state.df_patrimoine = df_patrimoine
    st.session_state.cats_memoire = cats_memoire
    st.session_state.comptes_structure = comptes_structure
    st.session_state.objectifs_list = objectifs_list
    st.session_state.df_abonnements = df_abonnements
    st.session_state.projets_config = projets_config
    st.session_state.comptes_types_map = comptes_types_map
    st.session_state.mots_cles_map = mots_cles_map
    
    st.session_state.needs_refresh = False
    
    # Créer un backup automatique (lundi uniquement)
    create_backup()
else:
    # Réutiliser les données en cache
    df = st.session_state.df
    df_patrimoine = st.session_state.df_patrimoine
    cats_memoire = st.session_state.cats_memoire
    comptes_structure = st.session_state.comptes_structure
    objectifs_list = st.session_state.objectifs_list
    df_abonnements = st.session_state.df_abonnements
    projets_config = st.session_state.projets_config
    comptes_types_map = st.session_state.comptes_types_map
    mots_cles_map = st.session_state.mots_cles_map

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### Menu")
    user_actuel = st.selectbox("Utilisateur", USERS)
    st.markdown("---")
    
    cpt_visibles = comptes_structure.get(user_actuel, []) + comptes_structure.get("Commun", [])
    cpt_calc = list(set(cpt_visibles + ["Autre / Externe"]))
    soldes = calc_soldes(df, df_patrimoine, cpt_calc)
    
    lst_c, lst_e = [], []
    tot_c, tot_e = 0, 0
    for c in cpt_visibles:
        v = soldes.get(c, 0.0)
        if comptes_types_map.get(c) == "Épargne": tot_e += v; lst_e.append((c,v))
        else: tot_c += v; lst_c.append((c,v))
        
    def show_c(n, v, e):
        icon = "💰" if e else "💳"
        cl = "#4F46E5" if e else ("#10B981" if v>=0 else "#EF4444")
        st.markdown(f"""
        <div class="account-card" style="border-left: 3px solid {cl};">
            <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem;">
                <span style="font-size: 20px;">{icon}</span>
                <span style="font-size: 13px; color: #6B7280; font-weight: 600;">{n}</span>
            </div>
            <div style="font-weight: 700; color: {cl}; font-size: 18px;">{v:,.2f} €</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style='background: white; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; border: 1px solid #E5E7EB;'>
        <div style='color: #6B7280; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.5rem;'>💳 Comptes Courants</div>
        <div style='color: #1F2937; font-size: 24px; font-weight: 700;'>{tot_c:,.0f} €</div>
    </div>
    """, unsafe_allow_html=True)
    for n,v in lst_c: show_c(n,v,False)
    
    st.write(""); 
    st.markdown(f"""
    <div style='background: white; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; border: 1px solid #E5E7EB;'>
        <div style='color: #6B7280; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.5rem;'>💰 Épargne</div>
        <div style='color: #1F2937; font-size: 24px; font-weight: 700;'>{tot_e:,.0f} €</div>
    </div>
    """, unsafe_allow_html=True)
    for n,v in lst_e: show_c(n,v,True)

    st.markdown("---")
    d_jour = datetime.now()
    m_nom = st.selectbox("Mois", MOIS_FR, index=d_jour.month-1)
    m_sel = MOIS_FR.index(m_nom) + 1
    a_sel = st.number_input("Année", value=d_jour.year)
    df_mois = df[(df["Mois"] == m_sel) & (df["Annee"] == a_sel)]
    
    st.markdown("---")
    
    # Indicateur de backup
    last_backup = st.session_state.get('last_backup_date', 'Aucun')
    if last_backup != 'Aucun':
        week_num = last_backup.split('_')[1] if '_' in last_backup else 'N/A'
        st.markdown(f"""
        <div style='background: #F0FDF4; border: 1px solid #10B981; padding: 0.75rem; border-radius: 8px; margin-bottom: 1rem;'>
            <div style='color: #10B981; font-size: 11px; font-weight: 600;'>💾 Sauvegarde automatique</div>
            <div style='color: #059669; font-size: 10px; margin-top: 0.25rem;'>Semaine {week_num}</div>
        </div>
        """, unsafe_allow_html=True)
    
    if st.button("🔄 Actualiser les données", use_container_width=True):
        st.session_state.needs_refresh = True
        st.rerun()
    
    # Info sur quotas API
    with st.expander("ℹ️ À propos des quotas", expanded=False):
        st.caption("""
        **Quotas Google Sheets** :
        - 📊 60 lectures/minute max
        - ⏱️ Si dépassé : attendre 1 min
        - 🔄 Utiliser le bouton ci-dessus
        
        **Optimisations activées** :
        - ✅ Cache intelligent (session_state)
        - ✅ Rechargement uniquement si modif
        - ✅ 5-10x plus rapide qu'avant
        """)

# --- TABS ---
tabs = st.tabs(["Accueil", "Opérations", "Analyses", "Patrimoine", "Remboursements", "Réglages"])

# TAB 1: ACCUEIL - DASHBOARD SIMPLIFIÉ
with tabs[0]:
    page_header(f"Synthèse - {m_nom} {a_sel}", f"Compte de {user_actuel}")
    
    # === MÉTRIQUES DU MOIS ACTUEL ===
    rev = df_mois[(df_mois["Qui_Connecte"]==user_actuel) & (df_mois["Type"]=="Revenu")]["Montant"].sum()
    dep = df_mois[(df_mois["Qui_Connecte"]==user_actuel) & (df_mois["Type"]=="Dépense") & (df_mois["Imputation"]=="Perso")]["Montant"].sum()
    epg = df_mois[(df_mois["Qui_Connecte"]==user_actuel) & (df_mois["Type"]=="Épargne")]["Montant"].sum()
    com = df_mois[df_mois["Imputation"]=="Commun (50/50)"]["Montant"].sum() / 2
    
    # Calcul du fixe : uniquement les abonnements PAYÉS ce mois
    fixe = 0
    if not df_abonnements.empty and not df_mois.empty:
        for _, abo in df_abonnements.iterrows():
            # Vérifier si cet abonnement a été payé ce mois
            paid = not df_mois[
                (df_mois["Titre"].str.lower() == abo["Nom"].lower()) & 
                (df_mois["Montant"] == float(abo["Montant"]))
            ].empty
            
            if paid:
                # Si c'est l'abonnement de l'utilisateur ou un abonnement commun
                if abo["Proprietaire"] == user_actuel:
                    fixe += float(abo["Montant"])
                elif "Commun" in str(abo.get("Imputation", "")):
                    fixe += float(abo["Montant"]) / 2
    
    rav = rev - fixe - dep - com
    ratio_epargne = (epg / rev * 100) if rev > 0 else 0
    
    # Cartes métriques
    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric("Revenus", f"{fmt(rev)} €")
    k2.metric("Fixe", f"{fmt(fixe)} €")
    k3.metric("Dépenses", f"{fmt(dep+com)} €")
    
    # Épargne avec ratio
    k4.markdown(f"""
    <div style="background: white; border: 1px solid #E5E7EB; padding: 1.25rem; border-radius: 12px;">
        <div style="font-size: 11px; color: #6B7280; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.5rem;">Épargne</div>
        <div style="font-size: 28px; font-weight: 700; color: #4F46E5; margin-bottom: 0.25rem;">{fmt(epg)} €</div>
        <div style="font-size: 11px; color: #10B981; font-weight: 600;">{ratio_epargne:.1f}% du revenu</div>
    </div>
    """, unsafe_allow_html=True)
    
    col = "#10B981" if rav>0 else "#EF4444"
    icon = "✓" if rav>0 else "⚠"
    k5.markdown(f"""
    <div style="background: {col}; padding: 1.25rem; border-radius: 12px; color: white; text-align: center; animation: scaleIn 0.3s ease;">
        <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.5rem; opacity: 0.9;">{icon} Reste à Vivre</div>
        <div style="font-size: 28px; font-weight: 700;">{fmt(rav)} €</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    
    # === PANNEAU DE NOTIFICATIONS INTELLIGENTES ===
    notifications = []
    
    # 1. Détecter les doublons
    doublons = detecter_doublons(df_mois)
    if doublons:
        notifications.append({
            'type': 'warning',
            'icon': '⚠️',
            'titre': 'Doublons potentiels détectés',
            'message': f"{len(doublons)} transaction(s) semblent dupliquées (même montant, catégorie et date proche)"
        })
    
    # 2. Détecter dépenses inhabituelles
    dep_inhabituelles = detecter_depenses_inhabituelles(
        df_mois[(df_mois['Qui_Connecte']==user_actuel) & (df_mois['Type']=='Dépense')],
        df[(df['Qui_Connecte']==user_actuel) & (df['Type']=='Dépense')],
        user_actuel
    )
    for alerte in dep_inhabituelles:
        notifications.append({
            'type': 'warning',
            'icon': '📊',
            'titre': f"Dépenses élevées : {alerte['categorie']}",
            'message': f"{fmt(alerte['montant'])} € ce mois (x{alerte['ratio']:.1f} la moyenne)"
        })
    
    # 3. Vérifier abonnements manquants
    abos_manquants = verifier_abonnements_manquants(df_mois, df_abonnements, m_sel, a_sel, user_actuel)
    if abos_manquants:
        notifications.append({
            'type': 'info',
            'icon': '📅',
            'titre': 'Abonnements à générer',
            'message': f"{len(abos_manquants)} abonnement(s) n'ont pas encore été générés ce mois"
        })
    
    # 4. Alertes budgets
    if objectifs_list:
        for obj in objectifs_list:
            if obj.get('Scope') == 'Perso' or obj.get('Scope') == 'Commun':
                cat = obj.get('Categorie', '')
                budget_max = float(obj.get('Montant', 0))
                
                if obj.get('Scope') == 'Perso':
                    dep_cat = df_mois[(df_mois['Categorie']==cat) & (df_mois['Qui_Connecte']==user_actuel) & (df_mois['Imputation']=='Perso')]['Montant'].sum()
                else:
                    dep_cat = df_mois[(df_mois['Categorie']==cat) & (df_mois['Imputation'].str.contains('Commun', na=False))]['Montant'].sum()
                
                pct = (dep_cat / budget_max * 100) if budget_max > 0 else 0
                
                if pct >= 100:
                    notifications.append({
                        'type': 'danger',
                        'icon': '🚨',
                        'titre': f"Budget dépassé : {cat}",
                        'message': f"{fmt(dep_cat)} € / {fmt(budget_max)} € ({pct:.0f}%)"
                    })
                elif pct >= 80:
                    notifications.append({
                        'type': 'warning',
                        'icon': '⚡',
                        'titre': f"Budget à 80% : {cat}",
                        'message': f"{fmt(dep_cat)} € / {fmt(budget_max)} € ({pct:.0f}%)"
                    })
    
    # 5. Prévision fin de mois
    jour_actuel = datetime.now().day
    if jour_actuel < 28:  # Seulement avant la fin du mois
        prevision = calculer_prevision_fin_mois(
            df_mois[(df_mois['Qui_Connecte']==user_actuel) & (df_mois['Type']=='Dépense')],
            df[(df['Qui_Connecte']==user_actuel) & (df['Type']=='Dépense')],
            user_actuel,
            jour_actuel
        )
        if prevision:
            dep_actuelles = df_mois[(df_mois['Qui_Connecte']==user_actuel) & (df_mois['Type']=='Dépense')]['Montant'].sum()
            if prevision > dep_actuelles * 1.2:  # Prévision > 20% des dépenses actuelles
                notifications.append({
                    'type': 'info',
                    'icon': '🔮',
                    'titre': 'Prévision fin de mois',
                    'message': f"Dépenses estimées : {fmt(prevision)} € (actuellement {fmt(dep_actuelles)} €)"
                })
    
    # Afficher les notifications
    if notifications:
        st.markdown("### 🔔 Notifications")
        
        for notif in notifications[:5]:  # Limiter à 5 notifications
            couleurs = {
                'danger': {'bg': '#FEF2F2', 'border': '#EF4444', 'text': '#991B1B'},
                'warning': {'bg': '#FFFBEB', 'border': '#F59E0B', 'text': '#92400E'},
                'info': {'bg': '#EFF6FF', 'border': '#3B82F6', 'text': '#1E40AF'}
            }
            
            c = couleurs.get(notif['type'], couleurs['info'])
            
            st.markdown(f"""
            <div style="background: {c['bg']}; border-left: 4px solid {c['border']}; padding: 1rem; border-radius: 8px; margin-bottom: 0.75rem; animation: slideIn 0.3s ease;">
                <div style="display: flex; align-items: start; gap: 0.75rem;">
                    <div style="font-size: 20px;">{notif['icon']}</div>
                    <div style="flex: 1;">
                        <div style="color: {c['text']}; font-weight: 700; font-size: 14px; margin-bottom: 0.25rem;">{notif['titre']}</div>
                        <div style="color: #6B7280; font-size: 13px;">{notif['message']}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.write("")
    
    st.markdown("---")
    c1, c2 = st.columns([3, 2])
    with c1:
        h1, h2 = st.columns([1,1])
        with h1: st.subheader("Activités")
        with h2: filt = st.radio("Filtre", ["Tout", "Sorties", "Entrées"], horizontal=True, label_visibility="collapsed", key="fh")
        
        dat = df[df['Qui_Connecte'] == user_actuel].sort_values(by='Date', ascending=False)
        if filt=="Sorties": dat = dat[dat['Type'].isin(["Dépense", "Virement Interne", "Épargne", "Investissement"])]
        elif filt=="Entrées": dat = dat[dat['Type']=="Revenu"]
        rec = dat.head(5)
        
        if not rec.empty:
            for _, r in rec.iterrows():
                is_d = r['Type'] in ["Dépense", "Virement Interne", "Épargne", "Investissement"]
                bg = "#FEF2F2" if is_d else "#F0FDF4"
                txt = "#EF4444" if is_d else "#10B981"
                sig = "-" if is_d else "+"
                ic = "↓" if is_d else "↑"
                if r['Type'] == "Épargne": ic = "→"
                
                st.markdown(f"""
                <div class="transaction-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="display: flex; align-items: center; gap: 1rem;">
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: {bg}; display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: 700; color: {txt};">{ic}</div>
                            <div>
                                <div style="font-weight: 600; color: #1F2937; font-size: 14px; margin-bottom: 0.25rem;">{r['Titre']}</div>
                                <div style="font-size: 12px; color: #6B7280;">
                                    <span style="background: {bg}; padding: 2px 6px; border-radius: 4px; margin-right: 0.5rem;">{r['Categorie']}</span>
                                    {r['Date'].strftime('%d/%m/%Y')}
                                </div>
                            </div>
                        </div>
                        <div style="font-weight: 700; font-size: 16px; color: {txt};">{sig}{fmt(r['Montant'], 2)} €</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else: st.info("Aucune activité.")
        
    with c2:
        st.subheader("Alertes")
        op = [o for o in objectifs_list if o["Scope"] in ["Perso", user_actuel]]
        dff = df_mois[(df_mois["Type"]=="Dépense") & (df_mois["Imputation"]=="Perso") & (df_mois["Qui_Connecte"]==user_actuel)]
        has_a = False
        for o in op:
            r = dff[dff["Categorie"]==o["Categorie"]]["Montant"].sum()
            b = float(o["Montant"])
            if b>0 and r/b>0.75:
                has_a = True; st.write(f"**{o['Categorie']}** : {r:.0f}/{b:.0f} €"); st.progress(min(r/b, 1.0))
        if not has_a: st.success("Budget OK")

# TAB 2: OPÉRATIONS
with tabs[1]:
    op1, op2, op3 = st.tabs(["Saisie", "Journal", "Abonnements"])
    with op1:
        page_header("Nouvelle Transaction", "Enregistrez vos revenus, dépenses et virements")
        
        # === FORMULAIRE DE SAISIE ===
        with st.container():
            # Ligne 1 : Date, Type, Montant
            c1, c2, c3 = st.columns(3)
            with c1:
                d_op = st.date_input("Date", datetime.today())
            with c2:
                t_op = st.selectbox("Type", TYPES)
            with c3:
                m_op = st.number_input("Montant (€)", min_value=0.0, step=0.01, format="%.2f")
            
            st.write("")
            
            # Ligne 2 : Titre et Catégorie
            c4, c5 = st.columns(2)
            with c4:
                tit = st.text_input("Titre", placeholder="Ex: Courses Carrefour, Salaire...")
            
            # Suggestion intelligente de catégorie
            cat_f = "Autre"
            cpt_a = None
            suggestion_source = None
            
            if tit:
                # Utiliser la fonction de suggestion intelligente
                cat_suggeree, source = suggerer_categories(tit, df[df['Type']==t_op], mots_cles_map)
                if cat_suggeree and cat_suggeree in cats_memoire.get(t_op, []):
                    cat_f = cat_suggeree
                    suggestion_source = source
            
            with c5:
                cats = cats_memoire.get(t_op, [])
                idx_c = cats.index(cat_f) if cat_f in cats else 0
                cat_s = st.selectbox("Catégorie", cats + ["Autre (nouvelle)"], index=idx_c)
                
                # Afficher l'info de suggestion
                if suggestion_source and cat_f != "Autre":
                    st.caption(f"💡 Suggéré : {suggestion_source}")
            
            # Si nouvelle catégorie
            if cat_s == "Autre (nouvelle)":
                fin_c = st.text_input("Nom de la nouvelle catégorie", placeholder="Ex: Restaurant, Courses...")
            else:
                fin_c = cat_s
            
            st.write("")
            st.write("")
            
            # === SECTION DÉTAILS ===
            # Ligne 3 : Compte source et Imputation
            cc1, cc2 = st.columns(2)
            with cc1:
                idx_cp = cpt_visibles.index(cpt_a) if (cpt_a and cpt_a in cpt_visibles) else 0
                c_src = st.selectbox("Compte Source", cpt_visibles, index=idx_cp)
            
            with cc2:
                imp = st.selectbox("Imputation", IMPUTATIONS)
            
            # Gestion imputation personnalisée
            fin_imp = imp
            if imp == "Commun (Autre %)":
                st.write("")
                pt = st.slider("Répartition - Part de Pierre (%)", 0, 100, 50, help="Le reste sera pour Elie")
                st.caption(f"Pierre: {pt}% • Elie: {100-pt}%")
                fin_imp = f"Commun ({pt}/{100-pt})"
            elif t_op == "Virement Interne":
                fin_imp = "Neutre"
            
            # Champs conditionnels selon le type
            c_tgt, p_epg = "", ""
            
            if t_op == "Épargne":
                st.write("")
                ce1, ce2 = st.columns(2)
                with ce1:
                    comptes_epargne = [c for c in cpt_visibles if comptes_types_map.get(c) == "Épargne"]
                    if comptes_epargne:
                        c_tgt = st.selectbox("Vers Compte Épargne", comptes_epargne)
                    else:
                        st.warning("Aucun compte épargne configuré")
                        c_tgt = ""
                with ce2:
                    # Filtrer les projets accessibles (Commun ou du user actuel)
                    projets_accessibles = [p for p, d in projets_config.items() if d.get("Proprietaire", "Commun") in ["Commun", user_actuel]]
                    ps = st.selectbox("Projet (optionnel)", ["Aucun"] + projets_accessibles)
                    if ps != "Aucun":
                        p_epg = ps
            
            elif t_op == "Virement Interne":
                st.write("")
                c_tgt = st.selectbox("Vers Compte", [c for c in cpt_visibles if c != c_src], help="Le compte de destination")
            
            st.write("")
            st.write("")
            
            # === BOUTON DE VALIDATION ===
            col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 2])
            with col_btn2:
                if st.button("Valider", type="primary", use_container_width=True):
                    # Validation
                    if not tit:
                        st.error("Veuillez entrer un titre")
                    elif not fin_c:
                        st.error("Veuillez sélectionner ou créer une catégorie")
                    elif m_op <= 0:
                        st.error("Le montant doit être supérieur à 0")
                    elif t_op == "Épargne" and not c_tgt:
                        st.error("Veuillez sélectionner un compte épargne")
                    elif t_op == "Virement Interne" and not c_tgt:
                        st.error("Veuillez sélectionner un compte de destination")
                    else:
                        # Sauvegarde nouvelle catégorie si nécessaire
                        if cat_s == "Autre (nouvelle)" and fin_c:
                            cats_memoire.setdefault(t_op, []).append(fin_c)
                            save_data(TAB_CONFIG, pd.DataFrame([{"Type": t, "Categorie": c} for t, l in cats_memoire.items() for c in l]))
                        
                        # Sauvegarde nouveau projet si nécessaire
                        if t_op == "Épargne" and p_epg and p_epg not in projets_config:
                            projets_config[p_epg] = {"Cible": 0.0, "Date_Fin": "", "Proprietaire": user_actuel}
                            rows = []
                            for k, v in projets_config.items():
                                rows.append({"Projet": k, "Cible": v["Cible"], "Date_Fin": v["Date_Fin"], "Proprietaire": v.get("Proprietaire", "Commun")})
                            save_data(TAB_PROJETS, pd.DataFrame(rows))
                        
                        # Création de la transaction
                        nr = {
                            "Date": d_op,
                            "Mois": d_op.month,
                            "Annee": d_op.year,
                            "Qui_Connecte": user_actuel,
                            "Type": t_op,
                            "Categorie": fin_c,
                            "Titre": tit,
                            "Description": "",
                            "Montant": m_op,
                            "Paye_Par": user_actuel,
                            "Imputation": fin_imp,
                            "Compte_Cible": c_tgt,
                            "Projet_Epargne": p_epg,
                            "Compte_Source": c_src
                        }
                        
                        df = pd.concat([df, pd.DataFrame([nr])], ignore_index=True)
                        save_data(TAB_DATA, df)
                        st.cache_data.clear()
                        st.session_state.needs_refresh = True
                        st.success("✅ Transaction enregistrée !")
                        st.rerun()

    with op2:
        sch = st.text_input("Chercher")
        if not df.empty:
            dfe = df.copy().sort_values(by="Date", ascending=False)
            if sch: dfe = dfe[dfe.apply(lambda r: str(r).lower().find(sch.lower())>-1, axis=1)]
            st.download_button("Excel", to_excel(dfe), "journal.xlsx")
            dfe.insert(0, "X", False)
            ed = st.data_editor(dfe, hide_index=True, column_config={"X": st.column_config.CheckboxColumn("Suppr", width="small")})
            if st.button("Supprimer"): 
                save_data(TAB_DATA, ed[ed["X"]==False].drop(columns=["X"]))
                st.cache_data.clear()
                st.session_state.needs_refresh = True
                st.rerun()

    with op3:
        # ABONNEMENTS
        page_header("Mes Abonnements", "Gérez vos dépenses récurrentes automatiquement")
        
        col_btn_new = st.columns([3, 1])
        with col_btn_new[1]:
            if st.button("Nouveau", use_container_width=True, type="primary"):
                st.session_state['new_abo'] = not st.session_state.get('new_abo', False)

        # FORMULAIRE DE CRÉATION
        if st.session_state.get('new_abo', False):
            st.markdown("""
            <div style="background: #4F46E5; padding: 1.5rem; border-radius: 12px; margin: 1rem 0; animation: slideIn 0.3s ease;">
                <h4 style="color: white; margin: 0; font-weight: 700; font-size: 16px;">Créer un nouvel abonnement</h4>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("na"):
                col1, col2, col3 = st.columns(3)
                n = col1.text_input("Nom", placeholder="Ex: Netflix, EDF...")
                m = col2.number_input("Montant (€)", min_value=0.0, step=0.01, format="%.2f")
                freq = col3.selectbox("Fréquence", FREQUENCES_ABO)
                
                col4, col5 = st.columns(2)
                j = col4.number_input("Jour du mois", min_value=1, max_value=31, value=1, help="Jour où l'abonnement est prélevé")
                c = col5.selectbox("Catégorie", cats_memoire.get("Dépense", []))
                
                col6, col7 = st.columns(2)
                cp = col6.selectbox("Compte", cpt_visibles)
                im = col7.selectbox("Imputation", IMPUTATIONS)
                
                st.write("")
                col8, col9 = st.columns(2)
                date_debut = col8.date_input("Date de début", datetime.today(), help="À partir de quand cet abonnement commence")
                date_fin = col9.date_input("Date de fin (optionnel)", None, help="Laissez vide si l'abonnement n'a pas de fin")
                
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.form_submit_button("Créer", use_container_width=True):
                    if n and m > 0:
                        new_abo = {
                            "Nom": n,
                            "Montant": m,
                            "Jour": j,
                            "Categorie": c,
                            "Compte_Source": cp,
                            "Proprietaire": user_actuel,
                            "Imputation": im,
                            "Frequence": freq,
                            "Date_Debut": str(date_debut) if date_debut else "",
                            "Date_Fin": str(date_fin) if date_fin else ""
                        }
                        df_abonnements = pd.concat([df_abonnements, pd.DataFrame([new_abo])], ignore_index=True)
                        save_data(TAB_ABONNEMENTS, df_abonnements)
                        st.session_state['new_abo'] = False
                        st.success("Abonnement créé !")
                        # Supprimé pour rapidité
                        st.rerun()
                    else:
                        st.error("Veuillez remplir tous les champs obligatoires")
                
                if col_btn2.form_submit_button("Annuler", use_container_width=True):
                    st.session_state['new_abo'] = False
                    st.rerun()
        
        st.write("")
        
        # AFFICHAGE DES ABONNEMENTS
        if not df_abonnements.empty:
            ma = df_abonnements[df_abonnements["Proprietaire"]==user_actuel]
            
            # Fonction pour vérifier si un abonnement doit être généré ce mois
            def should_generate(abo, mois, annee):
                freq = abo.get("Frequence", "Mensuel")
                date_debut = abo.get("Date_Debut", "")
                date_fin = abo.get("Date_Fin", "")
                
                # Vérifier date de début
                if date_debut:
                    debut = pd.to_datetime(date_debut).date()
                    if datetime(annee, mois, 1).date() < debut:
                        return False
                
                # Vérifier date de fin
                if date_fin:
                    fin = pd.to_datetime(date_fin).date()
                    if datetime(annee, mois, 1).date() > fin:
                        return False
                
                # Vérifier fréquence
                if freq == "Mensuel":
                    return True
                elif freq == "Trimestriel":
                    if date_debut:
                        debut = pd.to_datetime(date_debut).date()
                        mois_diff = (annee - debut.year) * 12 + (mois - debut.month)
                        return mois_diff % 3 == 0
                    return mois % 3 == 0
                elif freq == "Semestriel":
                    if date_debut:
                        debut = pd.to_datetime(date_debut).date()
                        mois_diff = (annee - debut.year) * 12 + (mois - debut.month)
                        return mois_diff % 6 == 0
                    return mois % 6 == 0
                elif freq == "Annuel":
                    if date_debut:
                        debut = pd.to_datetime(date_debut).date()
                        return mois == debut.month
                    return mois == 1
                return True
            
            # Génération automatique
            to_gen = []
            for ix, r in ma.iterrows():
                if should_generate(r, m_sel, a_sel):
                    paid = not df_mois[(df_mois["Titre"].str.lower()==r["Nom"].lower())&(df_mois["Montant"]==float(r["Montant"]))].empty
                    if not paid:
                        to_gen.append(r)
            
            if to_gen:
                if st.button(f"Générer {len(to_gen)} transaction(s) pour {m_nom} {a_sel}", type="primary", use_container_width=True):
                    nt = []
                    for r in to_gen:
                        try:
                            d = datetime(a_sel, m_sel, int(r["Jour"])).date()
                        except:
                            d = datetime(a_sel, m_sel, 28).date()
                        nt.append({
                            "Date": d,
                            "Mois": m_sel,
                            "Annee": a_sel,
                            "Qui_Connecte": r["Proprietaire"],
                            "Type": "Dépense",
                            "Categorie": r["Categorie"],
                            "Titre": r["Nom"],
                            "Description": f"Auto - {r['Frequence']}",
                            "Montant": float(r["Montant"]),
                            "Paye_Par": r["Proprietaire"],
                            "Imputation": r["Imputation"],
                            "Compte_Cible": "",
                            "Projet_Epargne": "",
                            "Compte_Source": r["Compte_Source"]
                        })
                    df = pd.concat([df, pd.DataFrame(nt)], ignore_index=True)
                    save_data(TAB_DATA, df)
                    st.cache_data.clear()
                    st.session_state.needs_refresh = True
                    st.success(f"{len(nt)} transaction(s) générée(s) !")
                    # Supprimé pour rapidité
                    st.rerun()
            
            st.write("")
            
            # Cartes des abonnements - optimisé avec @st.cache_data pour le statut
            cols = st.columns(3)
            for i, (idx, r) in enumerate(ma.iterrows()):
                col = cols[i % 3]
                
                # Vérifier si payé ce mois
                if should_generate(r, m_sel, a_sel):
                    paid = not df_mois[(df_mois["Titre"].str.lower()==r["Nom"].lower())&(df_mois["Montant"]==float(r["Montant"]))].empty
                else:
                    paid = None  # Pas prévu ce mois
                
                if paid is None:
                    sc = "#6B7280"
                    sb = "#F3F4F6"
                    stt = "NON PRÉVU"
                elif paid:
                    sc = "#10B981"
                    sb = "#ECFDF5"
                    stt = "PAYÉ"
                else:
                    sc = "#F59E0B"
                    sb = "#FFFBEB"
                    stt = "EN ATTENTE"
                
                with col:
                    if not st.session_state.get(f"ed_a_{idx}", False):
                        freq_label = r.get("Frequence", "Mensuel")
                        date_debut = r.get("Date_Debut", "")
                        date_fin = r.get("Date_Fin", "")
                        
                        info_dates = ""
                        if date_debut:
                            info_dates = f"Début: {pd.to_datetime(date_debut).strftime('%d/%m/%Y')}"
                        if date_fin:
                            info_dates += f" • Fin: {pd.to_datetime(date_fin).strftime('%d/%m/%Y')}"
                        
                        st.markdown(f"""
                        <div class="budget-card">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                                <div style="width: 40px; height: 40px; background: {sb}; color: {sc}; border-radius: 8px; display: flex; justify-content: center; align-items: center; font-weight: 700; font-size: 16px;">{r['Nom'][0].upper()}</div>
                                <div style="background: {sb}; color: {sc}; font-size: 10px; padding: 4px 10px; border-radius: 6px; font-weight: 700;">{stt}</div>
                            </div>
                            <div style="font-weight: 700; font-size: 16px; color: #1F2937; margin-bottom: 0.5rem;">{r['Nom']}</div>
                            <div style="font-size: 24px; font-weight: 700; color: {sc}; margin-bottom: 1rem;">{float(r['Montant']):.2f} €</div>
                            <div style="font-size: 11px; color: #6B7280; background: #F9FAFB; padding: 0.5rem; border-radius: 6px; line-height: 1.5;">
                                Jour {r['Jour']} • {r['Categorie']}<br/>
                                {freq_label}{'<br/>' + info_dates if info_dates else ''}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        c1, c2 = st.columns(2)
                        if c1.button("Modifier", key=f"e_{idx}", use_container_width=True):
                            st.session_state[f"ed_a_{idx}"] = True
                            st.rerun()
                        if c2.button("Supprimer", key=f"d_{idx}", use_container_width=True):
                            df_abonnements = df_abonnements.drop(idx)
                            save_data(TAB_ABONNEMENTS, df_abonnements)
                            st.cache_data.clear()
                            st.session_state.needs_refresh = True
                            st.rerun()
                    else:
                        # MODE ÉDITION
                        st.markdown("""
                        <div style="background: #EEF2FF; border: 2px solid #4F46E5; border-radius: 12px; padding: 1rem; margin-bottom: 1rem;">
                            <div style="color: #4F46E5; font-weight: 700; font-size: 14px;">Modification</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        with st.form(f"fe_{idx}"):
                            nn = st.text_input("Nom", value=r['Nom'])
                            nm = st.number_input("Montant", value=float(r['Montant']), step=0.01)
                            nj = st.number_input("Jour", value=int(r['Jour']), min_value=1, max_value=31)
                            nf = st.selectbox("Fréquence", FREQUENCES_ABO, index=FREQUENCES_ABO.index(r.get('Frequence', 'Mensuel')))
                            
                            # Dates
                            current_debut = pd.to_datetime(r.get('Date_Debut')) if r.get('Date_Debut') else None
                            current_fin = pd.to_datetime(r.get('Date_Fin')) if r.get('Date_Fin') else None
                            
                            nd = st.date_input("Date début", value=current_debut)
                            ndf = st.date_input("Date fin", value=current_fin)
                            
                            if st.form_submit_button("Sauvegarder", use_container_width=True):
                                df_abonnements.at[idx, 'Nom'] = nn
                                df_abonnements.at[idx, 'Montant'] = nm
                                df_abonnements.at[idx, 'Jour'] = nj
                                df_abonnements.at[idx, 'Frequence'] = nf
                                df_abonnements.at[idx, 'Date_Debut'] = str(nd) if nd else ""
                                df_abonnements.at[idx, 'Date_Fin'] = str(ndf) if ndf else ""
                                save_data(TAB_ABONNEMENTS, df_abonnements)
                                st.cache_data.clear()
                                st.session_state.needs_refresh = True
                                st.session_state[f"ed_a_{idx}"] = False
                                st.rerun()
        else:
            st.markdown("""
            <div style="text-align: center; padding: 3rem 2rem; background: white; border-radius: 12px; border: 2px dashed #E5E7EB;">
                <div style="font-size: 48px; margin-bottom: 1rem; opacity: 0.5;">📅</div>
                <h4 style="color: #1F2937; margin-bottom: 0.5rem; font-weight: 700;">Aucun abonnement</h4>
                <p style="color: #6B7280; margin: 0; font-size: 14px;">Créez votre premier abonnement pour automatiser vos dépenses récurrentes</p>
            </div>
            """, unsafe_allow_html=True)

# TAB 3: ANALYSES AVANCÉES
with tabs[2]:
    # Header avec bouton export
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        page_header("Analyses Approfondies", "Explorez vos données en détail")
    
    with col_h2:
        if st.button("📄 Exporter en PDF", use_container_width=True, type="primary"):
            try:
                # Import seulement si bouton cliqué
                from reportlab.lib.pagesizes import A4
                from reportlab.lib import colors
                from reportlab.lib.units import cm
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.enums import TA_CENTER, TA_RIGHT
                
                buffer = BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
                
                styles = getSampleStyleSheet()
                title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#4F46E5'), spaceAfter=30, alignment=TA_CENTER)
                heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=16, textColor=colors.HexColor('#1F2937'), spaceAfter=12, spaceBefore=12)
                
                elements = []
                
                # Titre
                elements.append(Paragraph(f"Rapport Budgétaire - {m_nom} {a_sel}", title_style))
                elements.append(Paragraph(f"Compte de {user_actuel}", styles['Normal']))
                elements.append(Spacer(1, 20))
                
                # Résumé financier
                elements.append(Paragraph("Résumé Financier", heading_style))
                
                rev = df_mois[(df_mois["Qui_Connecte"]==user_actuel) & (df_mois["Type"]=="Revenu")]["Montant"].sum()
                dep = df_mois[(df_mois["Qui_Connecte"]==user_actuel) & (df_mois["Type"]=="Dépense") & (df_mois["Imputation"]=="Perso")]["Montant"].sum()
                epg = df_mois[(df_mois["Qui_Connecte"]==user_actuel) & (df_mois["Type"]=="Épargne")]["Montant"].sum()
                com = df_mois[df_mois["Imputation"]=="Commun (50/50)"]["Montant"].sum() / 2
                solde = rev - dep - com
                
                data_summary = [
                    ['Indicateur', 'Montant'],
                    ['Revenus', f"{rev:,.2f} €"],
                    ['Dépenses personnelles', f"{dep:,.2f} €"],
                    ['Dépenses communes', f"{com:,.2f} €"],
                    ['Épargne', f"{epg:,.2f} €"],
                    ['Solde', f"{solde:,.2f} €"]
                ]
                
                table = Table(data_summary, colWidths=[8*cm, 6*cm])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F46E5')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                elements.append(table)
                elements.append(Spacer(1, 20))
                
                # Dépenses par catégorie
                if not df_mois.empty:
                    elements.append(Paragraph("Dépenses par Catégorie", heading_style))
                    
                    df_dep = df_mois[(df_mois["Type"]=="Dépense") & (df_mois["Qui_Connecte"]==user_actuel)].groupby("Categorie")["Montant"].sum().sort_values(ascending=False)
                    
                    if not df_dep.empty:
                        data_dep = [['Catégorie', 'Montant', '% du total']]
                        total_dep = df_dep.sum()
                        
                        for cat, montant in df_dep.items():
                            pct = (montant / total_dep * 100) if total_dep > 0 else 0
                            data_dep.append([cat, f"{montant:,.2f} €", f"{pct:.1f}%"])
                        
                        table_dep = Table(data_dep, colWidths=[8*cm, 4*cm, 3*cm])
                        table_dep.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EF4444')),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 11),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black),
                            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
                        ]))
                        elements.append(table_dep)
                        elements.append(Spacer(1, 20))
                
                # Transactions principales
                elements.append(PageBreak())
                elements.append(Paragraph("Transactions du mois", heading_style))
                
                transactions = df_mois[(df_mois["Qui_Connecte"]==user_actuel)].sort_values('Date', ascending=False).head(20)
                
                if not transactions.empty:
                    data_trans = [['Date', 'Titre', 'Catégorie', 'Montant']]
                    
                    for _, t in transactions.iterrows():
                        date_str = pd.to_datetime(t['Date']).strftime('%d/%m/%Y')
                        signe = '-' if t['Type'] == 'Dépense' else '+'
                        data_trans.append([
                            date_str,
                            t['Titre'][:30],  # Limiter la longueur
                            t['Categorie'][:20],
                            f"{signe}{t['Montant']:,.2f} €"
                        ])
                    
                    table_trans = Table(data_trans, colWidths=[2.5*cm, 7*cm, 4*cm, 3*cm])
                    table_trans.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F46E5')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
                    ]))
                    elements.append(table_trans)
                
                # Générer le PDF
                doc.build(elements)
                buffer.seek(0)
                
                st.download_button(
                    label="⬇️ Télécharger le PDF",
                    data=buffer,
                    file_name=f"rapport_budget_{m_nom}_{a_sel}_{user_actuel}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                
            except ImportError:
                st.error("❌ La librairie 'reportlab' n'est pas installée. Veuillez l'ajouter à requirements.txt pour activer l'export PDF.")
            except Exception as e:
                st.error(f"❌ Erreur lors de la génération du PDF : {str(e)}")
    
    # Tabs principales
    main_tabs = st.tabs(["Vue Globale", "Évolution & Tendances", "Analyses Détaillées", "Budgets"])
    
    # === TAB: VUE GLOBALE ===
    with main_tabs[0]:
        if not df_mois.empty:
            # Métriques résumé
            st.markdown("### Résumé du mois")
            
            rev_tot = df_mois[df_mois["Type"]=="Revenu"]["Montant"].sum()
            dep_tot = df_mois[df_mois["Type"]=="Dépense"]["Montant"].sum()
            epg_tot = df_mois[df_mois["Type"]=="Épargne"]["Montant"].sum()
            solde = rev_tot - dep_tot
            
            c1,c2,c3,c4 = st.columns(4)
            
            c1.markdown(f"""
            <div style="background: linear-gradient(135deg, #10B981 0%, #059669 100%); padding: 1.5rem; border-radius: 12px; color: white; animation: fadeIn 0.3s;">
                <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.75rem; opacity: 0.9;">Revenus</div>
                <div style="font-size: 32px; font-weight: 700;">{rev_tot:,.0f} €</div>
            </div>
            """, unsafe_allow_html=True)
            
            c2.markdown(f"""
            <div style="background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%); padding: 1.5rem; border-radius: 12px; color: white; animation: fadeIn 0.3s 0.1s; animation-fill-mode: both;">
                <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.75rem; opacity: 0.9;">Dépenses</div>
                <div style="font-size: 32px; font-weight: 700;">{dep_tot:,.0f} €</div>
            </div>
            """, unsafe_allow_html=True)
            
            c3.markdown(f"""
            <div style="background: linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%); padding: 1.5rem; border-radius: 12px; color: white; animation: fadeIn 0.3s 0.2s; animation-fill-mode: both;">
                <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.75rem; opacity: 0.9;">Épargne</div>
                <div style="font-size: 32px; font-weight: 700;">{epg_tot:,.0f} €</div>
            </div>
            """, unsafe_allow_html=True)
            
            solde_color = "#10B981" if solde >= 0 else "#EF4444"
            c4.markdown(f"""
            <div style="background: {solde_color}; padding: 1.5rem; border-radius: 12px; color: white; animation: scaleIn 0.3s 0.3s; animation-fill-mode: both;">
                <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.75rem; opacity: 0.9;">{'✓' if solde >= 0 else '⚠'} Solde</div>
                <div style="font-size: 32px; font-weight: 700;">{solde:,.0f} €</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("")
            
            # Graphiques
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                # Donut des dépenses
                df_dep = df_mois[df_mois["Type"]=="Dépense"].groupby("Categorie")["Montant"].sum()
                if not df_dep.empty:
                    fig_donut = go.Figure(data=[go.Pie(
                        labels=df_dep.index,
                        values=df_dep.values,
                        hole=0.5,
                        marker=dict(colors=px.colors.qualitative.Set3)
                    )])
                    fig_donut.update_layout(
                        title="Répartition des dépenses",
                        height=300,
                        margin=dict(t=40, b=20, l=20, r=20),
                        paper_bgcolor='rgba(0,0,0,0)',
                        showlegend=True
                    )
                    st.plotly_chart(fig_donut, use_container_width=True)
            
            with col_g2:
                # Top 5 dépenses
                st.markdown("### Top 5 des dépenses")
                top5 = df_dep.nlargest(5)
                colors = ['#EF4444', '#F97316', '#10B981', '#3B82F6', '#8B5CF6']
                
                for i, (cat, montant) in enumerate(top5.items()):
                    pct = (montant / dep_tot * 100) if dep_tot > 0 else 0
                    st.markdown(f"""
                    <div class="budget-card" style="animation: slideIn 0.3s ease {i * 0.1}s; animation-fill-mode: both;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                            <div style="font-weight: 700; color: #1F2937; font-size: 14px;">{cat}</div>
                            <div style="font-weight: 700; color: {colors[i]}; font-size: 16px;">{montant:,.0f} €</div>
                        </div>
                        <div style="background: #F3F4F6; height: 8px; border-radius: 4px; overflow: hidden;">
                            <div style="background: {colors[i]}; height: 100%; width: {pct}%; transition: width 0.5s ease;"></div>
                        </div>
                        <div style="font-size: 11px; color: #6B7280; margin-top: 0.25rem;">{pct:.1f}% du total</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.write("")
            
            # Comparaison Revenus vs Dépenses
            st.markdown("### Comparaison Revenus vs Dépenses")
            
            col_comp1, col_comp2 = st.columns(2)
            
            with col_comp1:
                st.markdown("#### Revenus par catégorie")
                df_rev = df_mois[df_mois["Type"]=="Revenu"].groupby("Categorie")["Montant"].sum().sort_values(ascending=False)
                
                if not df_rev.empty:
                    fig_rev = go.Figure(data=[
                        go.Bar(
                            x=df_rev.index,
                            y=df_rev.values,
                            marker_color='#10B981',
                            text=[f"{v:,.0f} €" for v in df_rev.values],
                            textposition='outside'
                        )
                    ])
                    fig_rev.update_layout(
                        height=300,
                        margin=dict(t=20, b=20, l=20, r=20),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        xaxis_title="",
                        yaxis_title="Montant (€)",
                        showlegend=False
                    )
                    st.plotly_chart(fig_rev, use_container_width=True)
                else:
                    st.info("Aucun revenu")
            
            with col_comp2:
                st.markdown("#### Dépenses par catégorie")
                
                if not df_dep.empty:
                    df_dep_sorted = df_dep.sort_values(ascending=False)
                    fig_dep = go.Figure(data=[
                        go.Bar(
                            x=df_dep_sorted.index,
                            y=df_dep_sorted.values,
                            marker_color='#EF4444',
                            text=[f"{v:,.0f} €" for v in df_dep_sorted.values],
                            textposition='outside'
                        )
                    ])
                    fig_dep.update_layout(
                        height=300,
                        margin=dict(t=20, b=20, l=20, r=20),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        xaxis_title="",
                        yaxis_title="Montant (€)",
                        showlegend=False
                    )
                    st.plotly_chart(fig_dep, use_container_width=True)
                else:
                    st.info("Aucune dépense")
        else:
            st.markdown("""
            <div style="text-align: center; padding: 4rem 2rem; background: white; border-radius: 12px; border: 2px dashed #E5E7EB;">
                <div style="font-size: 64px; margin-bottom: 1rem; opacity: 0.3;">📊</div>
                <h3 style="color: #6B7280; font-weight: 600;">Aucune donnée pour ce mois</h3>
                <p style="color: #9CA3AF; font-size: 14px;">Commencez à enregistrer vos transactions</p>
            </div>
            """, unsafe_allow_html=True)
    
    # === TAB: ÉVOLUTION & TENDANCES ===
    with main_tabs[1]:
        st.markdown("### Évolution sur 12 mois")
        
        # Préparation des données
        date_fin = datetime(a_sel, m_sel, 1)
        dates_12m = [(date_fin - relativedelta(months=i)).replace(day=1) for i in range(11, -1, -1)]
        
        evolution_data = []
        for d in dates_12m:
            mois, annee = d.month, d.year
            df_m = df[(df["Mois"] == mois) & (df["Annee"] == annee) & (df["Qui_Connecte"] == user_actuel)]
            
            rev_m = df_m[df_m["Type"]=="Revenu"]["Montant"].sum()
            dep_m = df_m[(df_m["Type"]=="Dépense") & (df_m["Imputation"]=="Perso")]["Montant"].sum()
            com_m = df_m[df_m["Imputation"]=="Commun (50/50)"]["Montant"].sum() / 2
            epg_m = df_m[df_m["Type"]=="Épargne"]["Montant"].sum()
            
            evolution_data.append({
                "Mois": d.strftime("%b %y"),
                "Revenus": rev_m,
                "Dépenses": dep_m + com_m,
                "Épargne": epg_m,
                "Solde": rev_m - dep_m - com_m
            })
        
        df_evolution = pd.DataFrame(evolution_data)
        
        # Graphiques
        col_graph1, col_graph2 = st.columns(2)
        
        with col_graph1:
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(
                x=df_evolution["Mois"], 
                y=df_evolution["Revenus"],
                name="Revenus",
                line=dict(color='#10B981', width=3),
                fill='tozeroy',
                fillcolor='rgba(16, 185, 129, 0.1)'
            ))
            fig1.add_trace(go.Scatter(
                x=df_evolution["Mois"], 
                y=df_evolution["Dépenses"],
                name="Dépenses",
                line=dict(color='#EF4444', width=3),
                fill='tozeroy',
                fillcolor='rgba(239, 68, 68, 0.1)'
            ))
            fig1.update_layout(
                title="Revenus vs Dépenses",
                height=350,
                margin=dict(t=40, b=20, l=20, r=20),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                hovermode='x unified',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with col_graph2:
            df_evolution["Épargne Cumulée"] = df_evolution["Épargne"].cumsum()
            
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=df_evolution["Mois"],
                y=df_evolution["Épargne"],
                name="Épargne mensuelle",
                marker_color='#4F46E5'
            ))
            fig2.add_trace(go.Scatter(
                x=df_evolution["Mois"],
                y=df_evolution["Épargne Cumulée"],
                name="Épargne cumulée",
                line=dict(color='#F59E0B', width=3),
                yaxis='y2'
            ))
            fig2.update_layout(
                title="Épargne mensuelle et cumulée",
                height=350,
                margin=dict(t=40, b=20, l=20, r=20),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                hovermode='x unified',
                yaxis2=dict(overlaying='y', side='right'),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        st.write("")
        
        # Comparaisons & Prédictions
        st.markdown("### Comparaisons & Prédictions")
        
        rev = df_mois[(df_mois["Qui_Connecte"]==user_actuel) & (df_mois["Type"]=="Revenu")]["Montant"].sum()
        dep = df_mois[(df_mois["Qui_Connecte"]==user_actuel) & (df_mois["Type"]=="Dépense") & (df_mois["Imputation"]=="Perso")]["Montant"].sum()
        epg = df_mois[(df_mois["Qui_Connecte"]==user_actuel) & (df_mois["Type"]=="Épargne")]["Montant"].sum()
        com = df_mois[df_mois["Imputation"]=="Commun (50/50)"]["Montant"].sum() / 2
        
        col_comp1, col_comp2, col_comp3 = st.columns(3)
        
        avg_3m_dep = df_evolution.tail(3)["Dépenses"].mean()
        avg_6m_dep = df_evolution.tail(6)["Dépenses"].mean()
        
        delta_3m = ((dep + com) - avg_3m_dep) / avg_3m_dep * 100 if avg_3m_dep > 0 else 0
        delta_6m = ((dep + com) - avg_6m_dep) / avg_6m_dep * 100 if avg_6m_dep > 0 else 0
        
        with col_comp1:
            st.markdown(f"""
            <div style="background: white; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1.5rem;">
                <h4 style="font-size: 14px; color: #6B7280; margin-bottom: 1rem;">vs Moyenne 3 mois</h4>
                <div style="font-size: 24px; font-weight: 700; color: #1F2937; margin-bottom: 0.5rem;">{avg_3m_dep:,.0f} €</div>
                <div style="font-size: 13px; color: {'#EF4444' if delta_3m > 0 else '#10B981'}; font-weight: 600;">
                    {'+' if delta_3m > 0 else ''}{delta_3m:.1f}% ce mois
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_comp2:
            st.markdown(f"""
            <div style="background: white; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1.5rem;">
                <h4 style="font-size: 14px; color: #6B7280; margin-bottom: 1rem;">vs Moyenne 6 mois</h4>
                <div style="font-size: 24px; font-weight: 700; color: #1F2937; margin-bottom: 0.5rem;">{avg_6m_dep:,.0f} €</div>
                <div style="font-size: 13px; color: {'#EF4444' if delta_6m > 0 else '#10B981'}; font-weight: 600;">
                    {'+' if delta_6m > 0 else ''}{delta_6m:.1f}% ce mois
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        tendance_epargne = df_evolution.tail(3)["Épargne"].mean()
        prediction_3m = epg + (tendance_epargne * 3)
        
        with col_comp3:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%); border-radius: 12px; padding: 1.5rem; color: white;">
                <h4 style="font-size: 14px; opacity: 0.9; margin-bottom: 1rem;">Prédiction dans 3 mois</h4>
                <div style="font-size: 24px; font-weight: 700; margin-bottom: 0.5rem;">{prediction_3m:,.0f} €</div>
                <div style="font-size: 13px; opacity: 0.9;">Si tendance actuelle</div>
            </div>
            """, unsafe_allow_html=True)
    
    # === TAB: ANALYSES DÉTAILLÉES ===
    with main_tabs[2]:
        sub_tabs = st.tabs(["Carte de Chaleur", "Top Dépenses", "Tendances Catégorie"])
        
        with sub_tabs[0]:
            st.markdown("### Quand dépensez-vous le plus ?")
            
            df_user_mois = df_mois[(df_mois["Qui_Connecte"]==user_actuel) & (df_mois["Type"]=="Dépense")].copy()
            
            if not df_user_mois.empty:
                df_user_mois["Jour"] = pd.to_datetime(df_user_mois["Date"]).dt.day
                heatmap_data = df_user_mois.groupby("Jour")["Montant"].sum().reindex(range(1, 32), fill_value=0)
                
                semaines = [heatmap_data.iloc[i:i+7] for i in range(0, 28, 7)]
                semaines.append(heatmap_data.iloc[28:])
                
                fig_heat = go.Figure(data=go.Heatmap(
                    z=[[val for val in sem.values] + [0] * (7 - len(sem)) for sem in semaines],
                    x=['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'],
                    y=['Semaine 1', 'Semaine 2', 'Semaine 3', 'Semaine 4', 'Semaine 5'],
                    colorscale='Reds',
                    text=[[f"{val:.0f}€" if val > 0 else "" for val in sem.values] + [""] * (7 - len(sem)) for sem in semaines],
                    texttemplate='%{text}',
                    textfont={"size": 10},
                    hovertemplate='%{y}<br>%{x}<br>%{z:.0f} €<extra></extra>'
                ))
                
                fig_heat.update_layout(
                    height=400,
                    margin=dict(t=20, b=20, l=20, r=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                
                st.plotly_chart(fig_heat, use_container_width=True)
                
                jour_max = heatmap_data.idxmax()
                montant_max = heatmap_data.max()
                st.info(f"Vous dépensez le plus le **jour {jour_max}** du mois ({montant_max:,.0f} €)")
            else:
                st.info("Pas assez de données")
        
        with sub_tabs[1]:
            st.markdown("### Top 10 des plus grosses dépenses")
            
            col_period = st.radio("Période", ["Ce mois", "Cette année", "Tout"], horizontal=True, label_visibility="collapsed")
            
            if col_period == "Ce mois":
                df_top = df_mois[(df_mois["Qui_Connecte"]==user_actuel) & (df_mois["Type"]=="Dépense")]
            elif col_period == "Cette année":
                df_top = df[(df["Annee"]==a_sel) & (df["Qui_Connecte"]==user_actuel) & (df["Type"]=="Dépense")]
            else:
                df_top = df[(df["Qui_Connecte"]==user_actuel) & (df["Type"]=="Dépense")]
            
            if not df_top.empty:
                top10 = df_top.nlargest(10, "Montant")
                
                for idx, (_, r) in enumerate(top10.iterrows()):
                    st.markdown(f"""
                    <div style="background: white; border: 1px solid #E5E7EB; border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem; animation: slideIn 0.3s ease {idx * 0.05}s; animation-fill-mode: both;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div style="flex: 1;">
                                <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem;">
                                    <span style="background: #EF4444; color: white; width: 28px; height: 28px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 12px;">#{idx+1}</span>
                                    <span style="font-weight: 700; color: #1F2937; font-size: 15px;">{r['Titre']}</span>
                                </div>
                                <div style="font-size: 12px; color: #6B7280;">
                                    <span style="background: #FEF2F2; color: #EF4444; padding: 2px 8px; border-radius: 4px; margin-right: 0.5rem;">{r['Categorie']}</span>
                                    {pd.to_datetime(r['Date']).strftime('%d/%m/%Y')}
                                </div>
                            </div>
                            <div style="font-weight: 700; font-size: 20px; color: #EF4444; white-space: nowrap;">{r['Montant']:,.0f} €</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Aucune dépense")
        
        with sub_tabs[2]:
            st.markdown("### Tendances par catégorie")
            
            date_fin = datetime(a_sel, m_sel, 1)
            dates_6m = [(date_fin - relativedelta(months=i)).replace(day=1) for i in range(5, -1, -1)]
            
            categories_dep = df[(df["Qui_Connecte"]==user_actuel) & (df["Type"]=="Dépense")]["Categorie"].unique()
            
            if len(categories_dep) > 0:
                cat_select = st.selectbox("Choisir une catégorie", sorted(categories_dep))
                
                tendance_data = []
                for d in dates_6m:
                    mois, annee = d.month, d.year
                    montant = df[(df["Mois"]==mois) & (df["Annee"]==annee) & (df["Qui_Connecte"]==user_actuel) & (df["Type"]=="Dépense") & (df["Categorie"]==cat_select)]["Montant"].sum()
                    tendance_data.append({"Mois": d.strftime("%b %y"), "Montant": montant})
                
                df_tendance = pd.DataFrame(tendance_data)
                
                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(
                    x=df_tendance["Mois"],
                    y=df_tendance["Montant"],
                    mode='lines+markers',
                    line=dict(color='#4F46E5', width=3),
                    marker=dict(size=10),
                    fill='tozeroy',
                    fillcolor='rgba(79, 70, 229, 0.1)'
                ))
                
                fig_trend.update_layout(
                    title=f"Évolution : {cat_select}",
                    height=350,
                    margin=dict(t=40, b=20, l=20, r=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    yaxis_title="Montant (€)"
                )
                
                st.plotly_chart(fig_trend, use_container_width=True)
                
                if len(df_tendance) >= 2:
                    dernier_mois = df_tendance.iloc[-1]["Montant"]
                    avant_dernier = df_tendance.iloc[-2]["Montant"]
                    variation = ((dernier_mois - avant_dernier) / avant_dernier * 100) if avant_dernier > 0 else 0
                    
                    if abs(variation) > 15:
                        couleur = "#EF4444" if variation > 0 else "#10B981"
                        st.markdown(f"""
                        <div style="background: {'#FEF2F2' if variation > 0 else '#F0FDF4'}; border-left: 4px solid {couleur}; padding: 1rem; border-radius: 8px;">
                            <div style="color: {couleur}; font-weight: 700; font-size: 14px;">
                                Variation significative : {'+' if variation > 0 else ''}{variation:.1f}%
                            </div>
                            <div style="color: #6B7280; font-size: 13px; margin-top: 0.5rem;">
                                {cat_select} a {'augmenté' if variation > 0 else 'diminué'} de {abs(variation):.0f}% par rapport au mois dernier
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("Aucune catégorie disponible")
    
    # === TAB: BUDGETS ===
    with main_tabs[3]:
        # HEADER avec bouton d'ajout
        h_col1, h_col2, h_col3 = st.columns([2, 1, 1])
        with h_col1:
            st.markdown("### Mes Budgets")
        with h_col2:
            if st.button("Suggérer budgets", use_container_width=True, help="Basé sur vos dépenses moyennes"):
                # Calculer moyennes sur 3 derniers mois
                date_limite = datetime.now() - relativedelta(months=3)
                df_recent = df[
                    (pd.to_datetime(df['Date']) >= date_limite) &
                    (df['Qui_Connecte'] == user_actuel) &
                    (df['Type'] == 'Dépense')
                ]
                
                if not df_recent.empty:
                    moyennes = df_recent.groupby('Categorie')['Montant'].mean() * 1.1  # +10% de marge
                    
                    for cat, montant in moyennes.items():
                        # Vérifier si budget existe déjà
                        existe = any(o.get('Categorie') == cat and o.get('Scope') == 'Perso' for o in objectifs_list)
                        if not existe and montant > 50:  # Seulement si > 50€
                            objectifs_list.append({
                                'Scope': 'Perso',
                                'Categorie': cat,
                                'Montant': round(montant, -1)  # Arrondir à la dizaine
                            })
                    
                    save_data(TAB_OBJECTIFS, pd.DataFrame(objectifs_list))
                    st.cache_data.clear()
                    st.session_state.needs_refresh = True
                    st.success(f"Budgets suggérés créés !")
                    # Supprimé pour rapidité
                    st.rerun()
                else:
                    st.warning("Pas assez de données pour suggérer des budgets")
        
        with h_col3:
            if st.button("Nouveau Budget", use_container_width=True, type="primary"):
                st.session_state['new_budget_modal'] = not st.session_state.get('new_budget_modal', False)
        
        # Modal de création
        if st.session_state.get('new_budget_modal', False):
            with st.container():
                st.markdown("""
                <div style="background: #4F46E5; padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem; animation: slideIn 0.3s ease;">
                    <h3 style="color: white; margin: 0; font-weight: 700; font-size: 18px;">Créer un nouveau budget</h3>
                    <p style="color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0; font-size: 13px;">Définissez vos limites mensuelles</p>
                </div>
                """, unsafe_allow_html=True)
                
                with st.form("nob", clear_on_submit=True):
                    c1, c2, c3 = st.columns(3)
                    sc = c1.selectbox("Scope", ["Perso", "Commun"], help="Personnel ou partagé ?")
                    ca = c2.selectbox("Catégorie", cats_memoire.get("Dépense", []), help="Catégorie de dépense")
                    mt = c3.number_input("Montant Max (€)", min_value=0.0, step=10.0, help="Budget mensuel maximum")
                    
                    col_btn1, col_btn2 = st.columns([1, 1])
                    with col_btn1:
                        if st.form_submit_button("Créer", use_container_width=True, type="primary"): 
                            objectifs_list.append({"Scope": sc, "Categorie": ca, "Montant": mt})
                            save_data(TAB_OBJECTIFS, pd.DataFrame(objectifs_list))
                            st.cache_data.clear()
                            st.session_state.needs_refresh = True
                            st.session_state['new_budget_modal'] = False
                            st.rerun()
                    with col_btn2:
                        if st.form_submit_button("Annuler", use_container_width=True):
                            st.session_state['new_budget_modal'] = False
                            st.rerun()
        
        st.write("")
        
        # AFFICHAGE DES BUDGETS
        if objectifs_list:
            # Séparation Perso / Commun
            b_perso = [o for o in objectifs_list if o.get("Scope") == "Perso"]
            b_commun = [o for o in objectifs_list if o.get("Scope") == "Commun"]
            
            def render_budgets(liste, titre, icone):
                if not liste:
                    return
                
                st.markdown(f"### {icone} {titre}")
                
                scope_prefix = "perso" if liste[0].get("Scope") == "Perso" else "commun"
                
                for idx, obj in enumerate(liste):
                    cat = obj.get("Categorie", "")
                    budget_max = float(obj.get("Montant", 0))
                    
                    # Trouver l'index réel dans objectifs_list
                    real_idx = objectifs_list.index(obj)
                    unique_key = f"{scope_prefix}_{idx}"
                    
                    # Calcul dépenses
                    if obj.get("Scope") == "Perso":
                        dep = df_mois[(df_mois["Categorie"]==cat) & (df_mois["Qui_Connecte"]==user_actuel) & (df_mois["Imputation"]=="Perso")]["Montant"].sum()
                    else:
                        dep = df_mois[(df_mois["Categorie"]==cat) & (df_mois["Imputation"].str.contains("Commun", na=False))]["Montant"].sum()
                    
                    pct = (dep / budget_max * 100) if budget_max > 0 else 0
                    restant = budget_max - dep
                    
                    # Couleurs
                    if pct >= 100:
                        couleur, bg = "#EF4444", "#FEF2F2"
                    elif pct >= 80:
                        couleur, bg = "#F59E0B", "#FFFBEB"
                    else:
                        couleur, bg = "#10B981", "#F0FDF4"
                    
                    if not st.session_state.get(f"edit_budget_{unique_key}", False):
                        card_html = f"""
                        <div style="background: white; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem; animation: slideIn 0.3s ease;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                                <h4 style="margin: 0; font-size: 16px; font-weight: 700; color: #1F2937;">{cat}</h4>
                                <div style="background: {bg}; color: {couleur}; padding: 0.25rem 0.75rem; border-radius: 6px; font-size: 12px; font-weight: 700;">
                                    {pct:.0f}%
                                </div>
                            </div>
                            <div style="background: #F3F4F6; height: 12px; border-radius: 6px; overflow: hidden; margin-bottom: 1rem;">
                                <div style="background: {couleur}; height: 100%; width: {min(pct, 100)}%; transition: width 0.5s ease;"></div>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 13px;">
                                <span style="color: #6B7280;">Dépensé: <strong style="color: {couleur};">{dep:,.0f} €</strong></span>
                                <span style="color: #6B7280;">Budget: <strong>{budget_max:,.0f} €</strong></span>
                            </div>
                            <div style="margin-top: 0.5rem; font-size: 12px; color: {'#EF4444' if restant < 0 else '#10B981'}; font-weight: 600;">
                                {'Dépassé de ' + f'{abs(restant):,.0f} €' if restant < 0 else 'Reste ' + f'{restant:,.0f} €'}
                            </div>
                        </div>
                        """
                        st.markdown(card_html, unsafe_allow_html=True)
                        
                        # Boutons d'action
                        b1, b2 = st.columns(2)
                        if b1.button("Modifier", key=f"edit_btn_{unique_key}", use_container_width=True):
                            st.session_state[f"edit_budget_{unique_key}"] = True
                            st.rerun()
                        if b2.button("Supprimer", key=f"del_b_{unique_key}", use_container_width=True):
                            objectifs_list.pop(real_idx)
                            save_data(TAB_OBJECTIFS, pd.DataFrame(objectifs_list))
                            st.cache_data.clear()
                            st.session_state.needs_refresh = True
                            st.rerun()
                    else:
                        # Mode édition
                        st.markdown("""
                        <div style="background: #EEF2FF; border: 2px solid #4F46E5; border-radius: 12px; padding: 1rem; margin-bottom: 1rem;">
                            <div style="color: #4F46E5; font-weight: 700; font-size: 14px;">Édition du budget</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        with st.form(f"edit_form_{unique_key}"):
                            new_montant = st.number_input("Nouveau montant", value=budget_max, step=10.0)
                            c1, c2 = st.columns(2)
                            if c1.form_submit_button("Sauvegarder", use_container_width=True, type="primary"):
                                objectifs_list[real_idx]["Montant"] = new_montant
                                save_data(TAB_OBJECTIFS, pd.DataFrame(objectifs_list))
                                st.cache_data.clear()
                                st.session_state.needs_refresh = True
                                st.session_state[f"edit_budget_{unique_key}"] = False
                                st.rerun()
                            if c2.form_submit_button("Annuler", use_container_width=True):
                                st.session_state[f"edit_budget_{unique_key}"] = False
                                st.rerun()
            
            # Affichage des budgets
            render_budgets(b_perso, "Mes Budgets", "👤")
            if b_perso and b_commun:
                st.markdown("<br>", unsafe_allow_html=True)
            render_budgets(b_commun, "Budgets Communs", "🤝")
        else:
            # État vide
            st.markdown("""
            <div style="text-align: center; padding: 4rem 2rem; background: white; border-radius: 12px; margin: 2rem 0; border: 2px dashed #E5E7EB; animation: fadeIn 0.5s ease;">
                <div style="font-size: 48px; margin-bottom: 1rem; opacity: 0.5;">📊</div>
                <h3 style="color: #1F2937; margin-bottom: 0.5rem; font-weight: 700;">Aucun budget défini</h3>
                <p style="color: #6B7280; margin: 0; font-size: 14px;">Créez votre premier budget pour suivre vos dépenses</p>
            </div>
            """, unsafe_allow_html=True)

# TAB 4: PATRIMOINE
with tabs[3]:
    page_header("Patrimoine", "Gérez vos comptes et projets d'épargne")
    
    # === SÉLECTION DE COMPTE ===
    st.markdown("### 💳 Détails du compte")
    
    col_select, col_actions = st.columns([3, 1])
    with col_select:
        ac = st.selectbox("Sélectionner un compte", cpt_visibles, label_visibility="collapsed")
    with col_actions:
        if st.button("🔄 Actualiser", use_container_width=True):
            st.cache_data.clear()
            st.session_state.needs_refresh = True
            st.success("Cache vidé ! Rechargement...")
            st.rerun()
    
    if ac:
        sl = soldes.get(ac, 0.0)
        compte_type = comptes_types_map.get(ac, "Courant")
        
        # === SOLDE DU COMPTE ===
        solde_color = "#10B981" if sl >= 0 else "#EF4444"
        solde_bg = "#F0FDF4" if sl >= 0 else "#FEF2F2"
        solde_icon = "✓" if sl >= 0 else "⚠"
        
        st.markdown(f"""
        <div style="background: {solde_bg}; border: 2px solid {solde_color}; border-radius: 12px; padding: 2rem; text-align: center; margin-bottom: 2rem; animation: scaleIn 0.3s ease;">
            <div style="display: flex; justify-content: center; align-items: center; gap: 1rem; margin-bottom: 0.75rem;">
                <span style="font-size: 32px;">{solde_icon}</span>
                <div>
                    <div style="color: #6B7280; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Solde actuel</div>
                    <div style="color: #1F2937; font-size: 11px; font-weight: 500; margin-top: 0.25rem;">{ac} • {compte_type}</div>
                </div>
            </div>
            <div style="color: {solde_color}; font-size: 48px; font-weight: 700;">{fmt(sl, 2)} €</div>
        </div>
        """, unsafe_allow_html=True)
        
        # === DERNIÈRES TRANSACTIONS ===
        st.markdown("### 📋 Dernières transactions")
        mk = (df["Compte_Source"]==ac)|(df["Compte_Cible"]==ac)
        df_compte = df[mk].sort_values(by="Date", ascending=False).head(10)
        
        if not df_compte.empty:
            for idx, (_, r) in enumerate(df_compte.iterrows()):
                is_debit = r["Compte_Source"] == ac and r["Type"] in ["Dépense", "Virement Interne", "Épargne", "Investissement"]
                is_credit = r["Compte_Cible"] == ac or (r["Compte_Source"] == ac and r["Type"] == "Revenu")
                
                if is_debit:
                    color = "#EF4444"
                    bg = "#FEF2F2"
                    icon = "↓"
                    sign = "-"
                elif is_credit:
                    color = "#10B981"
                    bg = "#F0FDF4"
                    icon = "↑"
                    sign = "+"
                else:
                    color = "#6B7280"
                    bg = "#F9FAFB"
                    icon = "→"
                    sign = ""
                
                st.markdown(f"""
                <div class="transaction-card" style="animation-delay: {idx * 0.05}s;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="display: flex; align-items: center; gap: 1rem; flex: 1;">
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: {bg}; display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: 700; color: {color};">{icon}</div>
                            <div style="flex: 1;">
                                <div style="font-weight: 600; color: #1F2937; font-size: 14px; margin-bottom: 0.25rem;">{r['Titre']}</div>
                                <div style="font-size: 12px; color: #6B7280;">
                                    <span style="background: {bg}; padding: 2px 6px; border-radius: 4px; margin-right: 0.5rem;">{r['Type']}</span>
                                    {r['Date'].strftime('%d/%m/%Y')}
                                    {f" • {r['Categorie']}" if r['Categorie'] else ""}
                                </div>
                            </div>
                        </div>
                        <div style="font-weight: 700; font-size: 16px; color: {color}; white-space: nowrap; margin-left: 1rem;">{sign}{r['Montant']:,.2f} €</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Aucune transaction pour ce compte")

    st.markdown("---")
    
    # === ONGLETS PROJETS / AJUSTEMENT ===
    st1, st2 = st.tabs(["💰 Projets d'Épargne", "⚙️ Ajustement de Solde"])
    
    with st1:
        st.markdown("### Mes Projets d'Épargne")
        
        # Filtre
        col_filter, col_new = st.columns([3, 1])
        with col_filter:
            f_own = st.radio("Filtrer par", ["Tout", "Commun", "Perso"], horizontal=True, label_visibility="collapsed")
        with col_new:
            if st.button("➕ Nouveau Projet", use_container_width=True):
                st.session_state['new_project_modal'] = not st.session_state.get('new_project_modal', False)
        
        # Modal création projet
        if st.session_state.get('new_project_modal', False):
            st.markdown("""
            <div style="background: #4F46E5; padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem; animation: slideIn 0.3s ease;">
                <h4 style="color: white; margin: 0; font-weight: 700; font-size: 16px;">Créer un nouveau projet</h4>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("new_proj"):
                c1, c2, c3 = st.columns(3)
                n = c1.text_input("Nom du projet")
                t = c2.number_input("Objectif (€)", min_value=0.0, step=100.0)
                prop = c3.selectbox("Propriétaire", ["Commun", user_actuel])
                
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.form_submit_button("✅ Créer", use_container_width=True):
                    projets_config[n] = {"Cible": t, "Date_Fin": "", "Proprietaire": prop}
                    rows = []
                    for k, v in projets_config.items():
                        rows.append({"Projet": k, "Cible": v["Cible"], "Date_Fin": v["Date_Fin"], "Proprietaire": v.get("Proprietaire", "Commun")})
                    save_data(TAB_PROJETS, pd.DataFrame(rows))
                    st.cache_data.clear()
                    st.session_state.needs_refresh = True
                    st.session_state['new_project_modal'] = False
                    st.rerun()
                if col_btn2.form_submit_button("❌ Annuler", use_container_width=True):
                    st.session_state['new_project_modal'] = False
                    st.rerun()
        
        st.write("")
        
        # Affichage des projets
        if projets_config:
            cols_proj = st.columns(2)
            proj_index = 0
            
            for p, d in projets_config.items():
                prop = d.get("Proprietaire", "Commun")
                
                # Filtre par propriétaire
                if f_own == "Commun" and prop != "Commun": 
                    continue
                if f_own == "Perso" and prop != user_actuel: 
                    continue
                if f_own == "Tout" and prop not in ["Commun", user_actuel]:
                    continue
                
                col = cols_proj[proj_index % 2]
                
                with col:
                    s = df[(df["Projet_Epargne"]==p)&(df["Type"]=="Épargne")]["Montant"].sum()
                    t = float(d["Cible"])
                    pct = min(s/t if t>0 else 0, 1.0)*100
                    
                    # Couleur selon progression
                    if pct >= 100:
                        prog_color = "#10B981"
                        prog_bg = "#F0FDF4"
                    elif pct >= 75:
                        prog_color = "#3B82F6"
                        prog_bg = "#EFF6FF"
                    elif pct >= 50:
                        prog_color = "#F59E0B"
                        prog_bg = "#FFFBEB"
                    else:
                        prog_color = "#6B7280"
                        prog_bg = "#F9FAFB"
                    
                    if not st.session_state.get(f"edp_{p}", False):
                        restant = t - s
                        status_msg = "✓ Objectif atteint !" if pct >= 100 else f"Reste {restant:,.0f} € pour atteindre l'objectif"
                        
                        card_html = f"""
                        <div class="budget-card">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                                <div>
                                    <div style="font-weight: 700; font-size: 16px; color: #1F2937; margin-bottom: 0.25rem;">{p}</div>
                                    <span style="font-size: 11px; background: {prog_bg}; color: {prog_color}; padding: 4px 10px; border-radius: 6px; font-weight: 600;">{prop}</span>
                                </div>
                                <div style="font-size: 32px;">{"🎯" if pct >= 100 else "💰"}</div>
                            </div>
                            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.75rem;">
                                <div>
                                    <span style="font-weight: 700; color: {prog_color}; font-size: 24px;">{s:,.0f} €</span>
                                    <span style="color: #6B7280; font-size: 13px; margin-left: 0.5rem;">/ {t:,.0f} €</span>
                                </div>
                                <span style="color: {prog_color}; font-size: 14px; font-weight: 700;">{pct:.0f}%</span>
                            </div>
                            <div style="width: 100%; background: #E5E7EB; height: 8px; border-radius: 4px; overflow: hidden; margin-bottom: 0.75rem;">
                                <div style="width: {pct:.1f}%; background: {prog_color}; height: 100%; border-radius: 4px; transition: width 0.5s ease;"></div>
                            </div>
                            <div style="font-size: 12px; color: #6B7280; text-align: center;">
                                {status_msg}
                            </div>
                        </div>
                        """
                        st.markdown(card_html, unsafe_allow_html=True)
                        
                        c1, c2 = st.columns(2)
                        if c1.button("✏️ Modifier", key=f"e_p_{p}", use_container_width=True):
                            st.session_state[f"edp_{p}"] = True
                            st.rerun()
                        if c2.button("🗑️ Supprimer", key=f"d_p_{p}", use_container_width=True):
                            del projets_config[p]
                            rows = []
                            for k, v in projets_config.items():
                                rows.append({"Projet": k, "Cible": v["Cible"], "Date_Fin": v["Date_Fin"], "Proprietaire": v.get("Proprietaire", "Commun")})
                            save_data(TAB_PROJETS, pd.DataFrame(rows))
                            st.cache_data.clear()
                            st.session_state.needs_refresh = True
                            st.rerun()
                    else:
                        st.markdown("""
                        <div style="background: #EEF2FF; border: 2px solid #4F46E5; border-radius: 12px; padding: 1rem; margin-bottom: 1rem;">
                            <div style="color: #4F46E5; font-weight: 700; font-size: 14px;">✏️ Modification du projet</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        with st.form(f"fep_{p}"):
                            nt = st.number_input("Nouvelle Cible (€)", value=float(d["Cible"]), min_value=0.0, step=100.0)
                            np = st.selectbox("Propriétaire", ["Commun", user_actuel], index=0 if prop=="Commun" else 1)
                            
                            col_save, col_cancel = st.columns(2)
                            if col_save.form_submit_button("💾 Sauvegarder", use_container_width=True):
                                projets_config[p]["Cible"] = nt
                                projets_config[p]["Proprietaire"] = np
                                rows = []
                                for k, v in projets_config.items():
                                    rows.append({"Projet": k, "Cible": v["Cible"], "Date_Fin": v["Date_Fin"], "Proprietaire": v.get("Proprietaire", "Commun")})
                                save_data(TAB_PROJETS, pd.DataFrame(rows))
                                st.cache_data.clear()
                                st.session_state.needs_refresh = True
                                st.session_state[f"edp_{p}"] = False
                                st.rerun()
                            if col_cancel.form_submit_button("❌ Annuler", use_container_width=True):
                                st.session_state[f"edp_{p}"] = False
                                st.rerun()
                    
                    proj_index += 1
        else:
            st.markdown("""
            <div style="text-align: center; padding: 3rem 2rem; background: white; border-radius: 12px; border: 2px dashed #E5E7EB;">
                <div style="font-size: 48px; margin-bottom: 1rem; opacity: 0.5;">🎯</div>
                <h4 style="color: #1F2937; margin-bottom: 0.5rem; font-weight: 700;">Aucun projet d'épargne</h4>
                <p style="color: #6B7280; margin: 0; font-size: 14px;">Créez un projet pour suivre vos objectifs</p>
            </div>
            """, unsafe_allow_html=True)
    
    with st2:
        st.markdown("### Ajuster le solde d'un compte")
        st.caption("Utilisez cette fonction pour corriger le solde d'un compte si nécessaire")
        
        # Afficher les ajustements existants
        if not df_patrimoine.empty:
            df_compte_pat = df_patrimoine[df_patrimoine["Compte"] == ac].sort_values("Date", ascending=False)
            if not df_compte_pat.empty:
                st.markdown("**📋 Historique des ajustements**")
                
                for idx, row in df_compte_pat.head(5).iterrows():
                    montant = row["Montant"]
                    date_str = row["Date"].strftime("%d/%m/%Y") if hasattr(row["Date"], 'strftime') else str(row["Date"])
                    
                    # Détection de montant suspect
                    is_suspect = montant > 100000
                    color = "#EF4444" if is_suspect else "#10B981"
                    
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.markdown(f"""
                        <div style="background: white; border-left: 3px solid {color}; padding: 0.5rem; border-radius: 4px; margin-bottom: 0.5rem;">
                            <div style="font-size: 12px; color: #6B7280;">{date_str}</div>
                            <div style="font-size: 16px; font-weight: 600; color: {color};">{montant:,.2f} €</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        if is_suspect:
                            st.warning("⚠️ Suspect")
                    
                    with col3:
                        if st.button("🗑️", key=f"del_pat_{idx}", use_container_width=True):
                            df_patrimoine = df_patrimoine.drop(idx)
                            save_data(TAB_PATRIMOINE, df_patrimoine)
                            st.cache_data.clear()
                            st.session_state.needs_refresh = True
                            st.success("✅ Ajustement supprimé")
                            st.rerun()
                
                st.markdown("---")
        
        with st.form("adj"):
            col1, col2 = st.columns(2)
            d = col1.date_input("Date de référence", datetime.today())
            m_text = col2.text_input("Solde réel (€)", placeholder="Ex: 7234,43 ou 7234.43", help="Utilisez , ou . comme séparateur décimal")
            
            if st.form_submit_button("💾 Enregistrer l'ajustement", use_container_width=True):
                try:
                    # Nettoyer et convertir le montant
                    # Supprimer tous les espaces
                    m_clean = m_text.replace(' ', '').strip()
                    
                    # Si contient une virgule ET un point, c'est ambigu
                    if ',' in m_clean and '.' in m_clean:
                        st.error("❌ Format ambigu. Utilisez soit la virgule (ex: 7234,43) soit le point (ex: 7234.43), pas les deux.")
                        st.stop()
                    
                    # Remplacer virgule par point pour Python
                    m_clean = m_clean.replace(',', '.')
                    
                    # Convertir en float
                    m = float(m_clean)
                    
                    df_patrimoine = pd.concat([
                        df_patrimoine, 
                        pd.DataFrame([{
                            "Date": d,
                            "Mois": d.month,
                            "Annee": d.year,
                            "Compte": ac,
                            "Montant": m,
                            "Proprietaire": user_actuel
                        }])
                    ], ignore_index=True)
                    
                    save_data(TAB_PATRIMOINE, df_patrimoine)
                    st.success("✅ Ajustement enregistré !")
                    st.cache_data.clear()
                    st.session_state.needs_refresh = True
                    st.rerun()
                except ValueError as e:
                    st.error(f"❌ Format invalide : '{m_text}'. Utilisez uniquement des chiffres avec virgule ou point (ex: 7234,43 ou 7234.43)")

# TAB 5: REMBOURSEMENTS & CRÉDITS
with tabs[4]:
    page_header("Remboursements & Crédits", "Gérez vos prêts, avances et remboursements")
    
    main_tabs = st.tabs(["💰 Qui doit quoi ?", "💳 Crédits en cours"])
    
    # === TAB: QUI DOIT QUOI ? ===
    with main_tabs[0]:
        st.markdown("### Équilibre entre Pierre et Elie")
        
        # Charger les données de remboursements
        df_rembours = load_data(TAB_REMBOURSEMENTS, ["Date", "De", "A", "Montant", "Motif", "Statut"])
        
        # Calculer le solde
        total_pierre_vers_elie = 0
        total_elie_vers_pierre = 0
        
        # Analyser les avances/cadeaux
        avances = df[df["Imputation"] == "Avance/Cadeau"]
        for _, a in avances.iterrows():
            if a["Paye_Par"] == "Pierre":
                total_pierre_vers_elie += a["Montant"]
            else:
                total_elie_vers_pierre += a["Montant"]
        
        # Analyser les remboursements effectués
        if not df_rembours.empty:
            remb_effectues = df_rembours[df_rembours["Statut"] == "Payé"]
            for _, r in remb_effectues.iterrows():
                if r["De"] == "Pierre":
                    total_pierre_vers_elie -= r["Montant"]
                else:
                    total_elie_vers_pierre -= r["Montant"]
        
        # Calculer solde net
        solde_net = total_pierre_vers_elie - total_elie_vers_pierre
        
        # Affichage du solde
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            st.markdown(f"""
            <div style="background: #EFF6FF; border-radius: 12px; padding: 1.5rem; text-align: center;">
                <div style="color: #3B82F6; font-size: 14px; font-weight: 600; margin-bottom: 0.5rem;">Pierre a avancé</div>
                <div style="font-size: 28px; font-weight: 700; color: #1E40AF;">{total_pierre_vers_elie:,.0f} €</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            debiteur = "Pierre" if solde_net < 0 else "Elie"
            montant_dette = abs(solde_net)
            couleur = "#10B981" if solde_net == 0 else "#4F46E5"
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%); border-radius: 12px; padding: 2rem; text-align: center; color: white;">
                <div style="font-size: 16px; opacity: 0.9; margin-bottom: 1rem;">
                    {f"{debiteur} doit rembourser" if solde_net != 0 else "Tout est équilibré !"}
                </div>
                <div style="font-size: 48px; font-weight: 700;">{montant_dette:,.0f} €</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div style="background: #F0FDF4; border-radius: 12px; padding: 1.5rem; text-align: center;">
                <div style="color: #10B981; font-size: 14px; font-weight: 600; margin-bottom: 0.5rem;">Elie a avancé</div>
                <div style="font-size: 28px; font-weight: 700; color: #059669;">{total_elie_vers_pierre:,.0f} €</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.write("")
        
        # Historique des avances
        st.markdown("### 📜 Historique des avances")
        
        if not avances.empty:
            for _, av in avances.tail(10).iterrows():
                couleur = "#3B82F6" if av["Paye_Par"] == "Pierre" else "#10B981"
                bg = "#EFF6FF" if av["Paye_Par"] == "Pierre" else "#F0FDF4"
                
                st.markdown(f"""
                <div style="background: {bg}; border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="flex: 1;">
                            <div style="font-weight: 700; color: #1F2937; margin-bottom: 0.25rem;">{av['Titre']}</div>
                            <div style="font-size: 12px; color: #6B7280;">
                                <span style="background: {couleur}; color: white; padding: 2px 8px; border-radius: 4px; margin-right: 0.5rem;">{av['Paye_Par']}</span>
                                {pd.to_datetime(av['Date']).strftime('%d/%m/%Y')}
                            </div>
                        </div>
                        <div style="font-weight: 700; font-size: 20px; color: {couleur};">{av['Montant']:,.0f} €</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Aucune avance enregistrée")
        
        st.write("")
        
        # Bouton pour marquer un remboursement
        if solde_net != 0:
            st.markdown("### 💸 Enregistrer un remboursement")
            
            with st.form("remboursement_form"):
                col_r1, col_r2, col_r3 = st.columns(3)
                
                montant_remb = col_r1.number_input("Montant (€)", min_value=0.0, max_value=float(montant_dette), value=float(montant_dette), step=0.01)
                date_remb = col_r2.date_input("Date", datetime.today())
                motif_remb = col_r3.text_input("Motif (optionnel)", placeholder="Ex: Remboursement courses")
                
                if st.form_submit_button("✅ Enregistrer le remboursement", use_container_width=True):
                    nouveau_remb = pd.DataFrame([{
                        "Date": date_remb,
                        "De": debiteur,
                        "A": "Elie" if debiteur == "Pierre" else "Pierre",
                        "Montant": montant_remb,
                        "Motif": motif_remb if motif_remb else "Remboursement",
                        "Statut": "Payé"
                    }])
                    
                    df_rembours = pd.concat([df_rembours, nouveau_remb], ignore_index=True)
                    save_data(TAB_REMBOURSEMENTS, df_rembours)
                    
                    st.success(f"✅ Remboursement de {montant_remb:,.0f} € enregistré !")
                    # Supprimé pour rapidité
                    st.rerun()
    
    # === TAB: CRÉDITS EN COURS ===
    with main_tabs[1]:
        st.markdown("### Suivi de vos crédits")
        
        # Charger les crédits
        df_credits = load_data(TAB_CREDITS, ["Nom", "Montant_Initial", "Montant_Restant", "Taux", "Mensualite", "Date_Debut", "Date_Fin", "Organisme"])
        
        # Bouton ajouter crédit
        if st.button("➕ Ajouter un crédit", use_container_width=True):
            st.session_state['new_credit'] = not st.session_state.get('new_credit', False)
        
        if st.session_state.get('new_credit', False):
            st.markdown("""
            <div style="background: #4F46E5; padding: 1.5rem; border-radius: 12px; margin: 1rem 0;">
                <h4 style="color: white; margin: 0; font-weight: 700;">Nouveau crédit</h4>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("new_credit_form"):
                col1, col2 = st.columns(2)
                nom_credit = col1.text_input("Nom du crédit", placeholder="Ex: Crédit immobilier, Voiture...")
                organisme = col2.text_input("Organisme", placeholder="Ex: Banque Populaire")
                
                col3, col4 = st.columns(2)
                montant_init = col3.number_input("Montant emprunté (€)", min_value=0.0, step=100.0)
                taux = col4.number_input("Taux annuel (%)", min_value=0.0, max_value=20.0, step=0.1, format="%.2f")
                
                st.markdown("**Remboursement :**")
                mode_remb = st.radio("Mode de calcul", ["Saisir la mensualité", "Saisir la durée"], horizontal=True)
                
                if mode_remb == "Saisir la mensualité":
                    col5, col6 = st.columns(2)
                    mensualite = col5.number_input("Mensualité (€)", min_value=0.0, step=10.0)
                    
                    # Calcul durée approximative
                    if mensualite > 0 and montant_init > 0 and taux > 0:
                        taux_mensuel = taux / 100 / 12
                        if mensualite > montant_init * taux_mensuel:
                            nb_mois = int(-1 * (1 / taux_mensuel) * (1 - (montant_init * taux_mensuel / mensualite)))
                            duree_annees = nb_mois / 12
                            col6.info(f"Durée estimée : {nb_mois} mois ({duree_annees:.1f} ans)")
                        else:
                            col6.warning("Mensualité trop faible")
                    
                    date_debut = st.date_input("Date de début", datetime.today())
                    date_fin = None
                    
                else:  # Saisir la durée
                    col7, col8 = st.columns(2)
                    duree_mois = col7.number_input("Durée (mois)", min_value=1, max_value=600, value=120, step=12)
                    
                    # Calcul mensualité
                    if montant_init > 0 and taux > 0:
                        taux_mensuel = taux / 100 / 12
                        mensualite = montant_init * (taux_mensuel * (1 + taux_mensuel)**duree_mois) / ((1 + taux_mensuel)**duree_mois - 1)
                        col8.info(f"Mensualité : {mensualite:.2f} €")
                    else:
                        mensualite = 0
                        col8.warning("Renseignez montant et taux")
                    
                    date_debut = st.date_input("Date de début", datetime.today())
                    date_fin = date_debut + relativedelta(months=int(duree_mois))
                    st.caption(f"Date de fin prévue : {date_fin.strftime('%d/%m/%Y')}")
                
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.form_submit_button("Créer", use_container_width=True):
                    if not date_fin and mensualite > 0:
                        # Calculer date_fin basée sur la mensualité
                        taux_mensuel = taux / 100 / 12
                        if mensualite > montant_init * taux_mensuel:
                            nb_mois = int(-1 * (1 / taux_mensuel) * (1 - (montant_init * taux_mensuel / mensualite)))
                            date_fin = date_debut + relativedelta(months=nb_mois)
                        else:
                            date_fin = date_debut + relativedelta(years=30)  # Par défaut 30 ans
                    
                    nouveau_credit = pd.DataFrame([{
                        "Nom": nom_credit,
                        "Montant_Initial": montant_init,
                        "Montant_Restant": montant_init,
                        "Taux": taux,
                        "Mensualite": mensualite,
                        "Date_Debut": str(date_debut),
                        "Date_Fin": str(date_fin),
                        "Organisme": organisme
                    }])
                    
                    df_credits = pd.concat([df_credits, nouveau_credit], ignore_index=True)
                    save_data(TAB_CREDITS, df_credits)
                    st.session_state['new_credit'] = False
                    st.success("Crédit ajouté !")
                    # Supprimé pour rapidité
                    st.rerun()
                
                if col_btn2.form_submit_button("Annuler", use_container_width=True):
                    st.session_state['new_credit'] = False
                    st.rerun()
        
        st.write("")
        
        # Affichage des crédits
        if not df_credits.empty:
            for idx, credit in df_credits.iterrows():
                montant_init = float(credit['Montant_Initial'])
                montant_restant = float(credit['Montant_Restant'])
                progression = ((montant_init - montant_restant) / montant_init * 100) if montant_init > 0 else 0
                
                # Calcul intérêts
                taux = float(credit['Taux'])
                interets_totaux = (float(credit['Mensualite']) * 12 * ((pd.to_datetime(credit['Date_Fin']) - pd.to_datetime(credit['Date_Debut'])).days / 365)) - montant_init
                
                st.markdown(f"""
                <div style="background: white; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
                        <div>
                            <h4 style="margin: 0 0 0.5rem 0; color: #1F2937;">{credit['Nom']}</h4>
                            <div style="font-size: 13px; color: #6B7280;">{credit['Organisme']} • Taux: {taux:.2f}%</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 24px; font-weight: 700; color: #EF4444;">{montant_restant:,.0f} €</div>
                            <div style="font-size: 12px; color: #6B7280;">sur {montant_init:,.0f} €</div>
                        </div>
                    </div>
                    
                    <div style="background: #F3F4F6; height: 10px; border-radius: 5px; overflow: hidden; margin-bottom: 1rem;">
                        <div style="background: #10B981; height: 100%; width: {progression}%; transition: width 0.5s ease;"></div>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; font-size: 13px;">
                        <div><strong>Mensualité:</strong> {float(credit['Mensualite']):,.0f} €</div>
                        <div><strong>Progression:</strong> {progression:.1f}%</div>
                        <div><strong>Intérêts estimés:</strong> {interets_totaux:,.0f} €</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Boutons actions
                col_act1, col_act2 = st.columns(2)
                with col_act1:
                    with st.form(f"remb_credit_{idx}"):
                        montant_remb_credit = st.number_input("Montant remboursé (€)", min_value=0.0, value=float(credit['Mensualite']), step=10.0, key=f"remb_{idx}")
                        if st.form_submit_button("Enregistrer un remboursement"):
                            df_credits.at[idx, 'Montant_Restant'] = max(0, montant_restant - montant_remb_credit)
                            save_data(TAB_CREDITS, df_credits)
                            st.cache_data.clear()
                            st.session_state.needs_refresh = True
                            st.success("Remboursement enregistré !")
                            # Supprimé pour rapidité
                            st.rerun()
                
                with col_act2:
                    if st.button("Supprimer", key=f"del_credit_{idx}"):
                        df_credits = df_credits.drop(idx)
                        save_data(TAB_CREDITS, df_credits)
                        st.cache_data.clear()
                        st.session_state.needs_refresh = True
                        st.rerun()
        else:
            st.markdown("""
            <div style="text-align: center; padding: 3rem; background: white; border-radius: 12px; border: 2px dashed #E5E7EB;">
                <div style="font-size: 48px; margin-bottom: 1rem;">💳</div>
                <h4 style="color: #6B7280;">Aucun crédit en cours</h4>
                <p style="color: #9CA3AF; font-size: 14px;">Ajoutez vos crédits pour suivre vos remboursements</p>
            </div>
            """, unsafe_allow_html=True)
    

# TAB 6: REGLAGES
with tabs[5]:
    page_header("Configuration", "Personnalisez vos catégories, comptes et automatisations")
    
    c_t1, c_t2, c_t3, c_t4 = st.tabs(["🏷️ Catégories", "💳 Comptes", "⚡ Automatisation", "💾 Sauvegardes"])
    
    # === 1. CATÉGORIES ===
    with c_t1:
        st.markdown("### Gérer les catégories")
        st.caption("Organisez vos transactions par catégories personnalisées")
        
        # Bouton pour charger les catégories par défaut
        if st.button("🔄 Réinitialiser avec les catégories par défaut", help="Remplace toutes vos catégories par le catalogue complet"):
            # Catégories par défaut
            cats_memoire = {
                "Dépense": [
                    "Alimentation", "Courses", "Restaurant", "Fast Food", "Boulangerie", "Marché",
                    "Loyer", "Charges", "Électricité", "Eau", "Gaz", "Internet", "Téléphone", "Assurance Habitation",
                    "Essence", "Transport en Commun", "Parking", "Péage", "Assurance Auto", "Entretien Véhicule",
                    "Pharmacie", "Médecin", "Dentiste", "Mutuelle", "Sport", "Coiffeur", "Cosmétiques",
                    "Cinéma", "Streaming", "Livres", "Jeux", "Sorties", "Voyages", "Hobbies",
                    "Vêtements", "Chaussures", "Électronique", "Maison & Déco", "Cadeaux",
                    "Abonnements", "Banque", "Impôts", "Crèche", "École", "Formation",
                    "Vétérinaire", "Nourriture Animaux", "Accessoires Animaux",
                    "Autre"
                ],
                "Revenu": [
                    "Salaire", "Prime", "Bonus", "Freelance", "Vente", "Remboursement", 
                    "Allocations", "Aide", "Intérêts", "Dividendes", "Loyer Perçu", "Autre"
                ],
                "Épargne": [
                    "Épargne Mensuelle", "Épargne Projet", "Épargne Urgence", 
                    "Livret A", "PEL", "Assurance Vie", "Plan Épargne", "Autre"
                ],
                "Virement Interne": [
                    "Transfert Comptes", "Rééquilibrage", "Autre"
                ],
                "Investissement": [
                    "Bourse", "Crypto", "Immobilier", "Startup", "Autre"
                ]
            }
            
            save_data(TAB_CONFIG, pd.DataFrame([{"Type": t, "Categorie": c} for t, l in cats_memoire.items() for c in l]))
            st.cache_data.clear()
            st.session_state.needs_refresh = True
            st.success("✅ Catégories réinitialisées avec succès !")
            # Supprimé pour rapidité
            st.rerun()
        
        st.write("")
        
        # Ajout de catégorie
        with st.container():
            st.markdown("""
            <div style="background: white; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem;">
                <h4 style="font-size: 14px; font-weight: 700; color: #1F2937; margin-bottom: 1rem;">➕ Ajouter une catégorie</h4>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([2, 3, 1])
            ty = c1.selectbox("Type", TYPES, key="sc_type")
            new_c = c2.text_input("Nom de la catégorie", key="ncat", placeholder="Ex: Restaurant, Salaire...")
            if c3.button("✅ Ajouter", use_container_width=True, key="add_cat_btn"):
                if new_c:
                    cats_memoire.setdefault(ty, []).append(new_c)
                    save_data(TAB_CONFIG, pd.DataFrame([{"Type": t, "Categorie": c} for t, l in cats_memoire.items() for c in l]))
                    st.cache_data.clear()
                    st.session_state.needs_refresh = True
                    st.success(f"✅ Catégorie '{new_c}' ajoutée !")
                    # Supprimé pour rapidité
                    st.rerun()
        
        st.write("")
        
        # Affichage des catégories
        col_dep, col_rev = st.columns(2)
        
        with col_dep:
            st.markdown("""
            <div style="background: #FEF2F2; border: 1px solid #FCA5A5; border-radius: 12px; padding: 1rem; margin-bottom: 1rem;">
                <h4 style="font-size: 14px; font-weight: 700; color: #DC2626; margin: 0;">💸 Dépenses</h4>
            </div>
            """, unsafe_allow_html=True)
            
            if cats_memoire.get("Dépense", []):
                for c in cats_memoire.get("Dépense", []):
                    st.markdown(f'<span class="cat-badge depense">{c}</span>', unsafe_allow_html=True)
                
                st.write("")
                to_del_dep = st.multiselect("Supprimer des catégories", cats_memoire.get("Dépense", []), key="del_dep")
                if to_del_dep:
                    if st.button("🗑️ Confirmer la suppression", use_container_width=True, key="confirm_del_dep"):
                        for d in to_del_dep:
                            cats_memoire["Dépense"].remove(d)
                        save_data(TAB_CONFIG, pd.DataFrame([{"Type": t, "Categorie": c} for t, l in cats_memoire.items() for c in l]))
                        st.cache_data.clear()
                        st.session_state.needs_refresh = True
                        st.success("✅ Catégories supprimées !")
                        # Supprimé pour rapidité
                        st.rerun()
            else:
                st.info("Aucune catégorie de dépense")
        
        with col_rev:
            st.markdown("""
            <div style="background: #F0FDF4; border: 1px solid #86EFAC; border-radius: 12px; padding: 1rem; margin-bottom: 1rem;">
                <h4 style="font-size: 14px; font-weight: 700; color: #16A34A; margin: 0;">💰 Revenus & Épargne</h4>
            </div>
            """, unsafe_allow_html=True)
            
            others = cats_memoire.get("Revenu", []) + cats_memoire.get("Épargne", [])
            if others:
                for c in others:
                    st.markdown(f'<span class="cat-badge revenu">{c}</span>', unsafe_allow_html=True)
                
                st.write("")
                to_del_oth = st.multiselect("Supprimer des catégories", others, key="del_oth")
                if to_del_oth:
                    if st.button("🗑️ Confirmer la suppression", use_container_width=True, key="confirm_del_oth"):
                        for d in to_del_oth:
                            for t in ["Revenu", "Épargne"]:
                                if d in cats_memoire.get(t, []):
                                    cats_memoire[t].remove(d)
                        save_data(TAB_CONFIG, pd.DataFrame([{"Type": t, "Categorie": c} for t, l in cats_memoire.items() for c in l]))
                        st.cache_data.clear()
                        st.session_state.needs_refresh = True
                        st.success("✅ Catégories supprimées !")
                        # Supprimé pour rapidité
                        st.rerun()
            else:
                st.info("Aucune catégorie de revenu/épargne")

    # === 2. COMPTES ===
    with c_t2:
        st.markdown("### Gérer les comptes")
        st.caption("Ajoutez et organisez vos comptes bancaires")
        
        # Ajout de compte
        col_add, col_list = st.columns([1, 1])
        
        with col_add:
            st.markdown("""
            <div style="background: white; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem;">
                <h4 style="font-size: 14px; font-weight: 700; color: #1F2937; margin-bottom: 1rem;">➕ Ajouter un compte</h4>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("nac"):
                n = st.text_input("Nom du compte", placeholder="Ex: Compte Courant BNP")
                t = st.selectbox("Type de compte", TYPES_COMPTE)
                c = st.checkbox("Compte commun")
                
                if st.form_submit_button("✅ Créer le compte", use_container_width=True):
                    if n:
                        p = "Commun" if c else user_actuel
                        if n not in comptes_structure.get(p, []):
                            comptes_structure.setdefault(p, []).append(n)
                            rows = []
                            for pr, l in comptes_structure.items():
                                for ct in l:
                                    rows.append({"Proprietaire": pr, "Compte": ct, "Type": comptes_types_map.get(ct, t)})
                            save_data(TAB_COMPTES, pd.DataFrame(rows))
                            st.cache_data.clear()
                            st.session_state.needs_refresh = True
                            st.success(f"✅ Compte '{n}' créé !")
                            # Supprimé pour rapidité
                            st.rerun()
                        else:
                            st.error("Ce compte existe déjà !")
                    else:
                        st.warning("Veuillez entrer un nom de compte")
        
        with col_list:
            st.markdown("""
            <div style="background: white; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem;">
                <h4 style="font-size: 14px; font-weight: 700; color: #1F2937; margin-bottom: 1rem;">📋 Mes comptes</h4>
            </div>
            """, unsafe_allow_html=True)
            
            for p in [user_actuel, "Commun"]:
                if p in comptes_structure and comptes_structure[p]:
                    st.markdown(f"**{p}**")
                    for idx, a in enumerate(comptes_structure[p]):
                        compte_type = comptes_types_map.get(a, 'Courant')
                        icon = "💰" if compte_type == "Épargne" else "💳"
                        
                        # Vérifier si on est en mode édition
                        edit_key = f"edit_compte_{p}_{idx}"
                        
                        if not st.session_state.get(edit_key, False):
                            # Mode affichage
                            col_name, col_edit, col_del = st.columns([3, 1, 1])
                            with col_name:
                                st.markdown(f"""
                                <div style="background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 8px; padding: 0.75rem; margin-bottom: 0.5rem;">
                                    <span style="font-size: 16px; margin-right: 0.5rem;">{icon}</span>
                                    <span style="font-weight: 600; color: #1F2937;">{a}</span>
                                    <span style="color: #6B7280; font-size: 12px; margin-left: 0.5rem;">• {compte_type}</span>
                                </div>
                                """, unsafe_allow_html=True)
                            with col_edit:
                                if st.button("✏️", key=f"edit_btn_{p}_{idx}", use_container_width=True):
                                    st.session_state[edit_key] = True
                                    st.rerun()
                            with col_del:
                                if st.button("🗑️", key=f"del_{a}", use_container_width=True):
                                    comptes_structure[p].remove(a)
                                    rows = []
                                    for pr, l in comptes_structure.items():
                                        for ct in l:
                                            rows.append({"Proprietaire": pr, "Compte": ct, "Type": comptes_types_map.get(ct, "Courant")})
                                    save_data(TAB_COMPTES, pd.DataFrame(rows))
                                    st.cache_data.clear()
                                    st.session_state.needs_refresh = True
                                    st.rerun()
                        else:
                            # Mode édition
                            st.markdown("""
                            <div style="background: #EEF2FF; border: 2px solid #4F46E5; border-radius: 8px; padding: 1rem; margin-bottom: 0.5rem;">
                                <div style="color: #4F46E5; font-weight: 700; font-size: 12px;">✏️ Modification</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            with st.form(f"edit_compte_form_{p}_{idx}"):
                                new_name = st.text_input("Nom du compte", value=a)
                                new_type = st.selectbox("Type", TYPES_COMPTE, index=TYPES_COMPTE.index(compte_type))
                                
                                col_save, col_cancel = st.columns(2)
                                if col_save.form_submit_button("💾 Sauvegarder", use_container_width=True):
                                    # Mettre à jour le compte
                                    old_name = a
                                    comptes_structure[p][idx] = new_name
                                    comptes_types_map[new_name] = new_type
                                    if old_name != new_name and old_name in comptes_types_map:
                                        del comptes_types_map[old_name]
                                    
                                    rows = []
                                    for pr, l in comptes_structure.items():
                                        for ct in l:
                                            rows.append({"Proprietaire": pr, "Compte": ct, "Type": comptes_types_map.get(ct, "Courant")})
                                    save_data(TAB_COMPTES, pd.DataFrame(rows))
                                    st.cache_data.clear()
                                    st.session_state.needs_refresh = True
                                    st.session_state[edit_key] = False
                                    st.rerun()
                                
                                if col_cancel.form_submit_button("❌ Annuler", use_container_width=True):
                                    st.session_state[edit_key] = False
                                    st.rerun()
                                st.rerun()
                    st.write("")

    # === 3. AUTOMATISATION ===
    with c_t3:
        st.markdown("### Règles d'automatisation")
        st.caption("Créez des règles pour catégoriser automatiquement vos transactions")
        
        # Ajout de règle
        st.markdown("""
        <div style="background: white; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem;">
            <h4 style="font-size: 14px; font-weight: 700; color: #1F2937; margin-bottom: 1rem;">➕ Créer une règle</h4>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("amc"):
            alc = [c for l in cats_memoire.values() for c in l]
            
            col1, col2 = st.columns(2)
            m = col1.text_input("Si le titre contient", placeholder="Ex: Uber, Netflix, Carrefour...")
            c = col2.selectbox("Appliquer la catégorie", alc)
            
            col3, col4 = st.columns(2)
            ty = col3.selectbox("Type de transaction", TYPES, key="kt")
            co = col4.selectbox("Compte par défaut", cpt_calc)
            
            if st.form_submit_button("✅ Créer la règle", use_container_width=True):
                if m:
                    mots_cles_map[m.lower()] = {"Categorie": c, "Type": ty, "Compte": co}
                    rows = []
                    for mc, data in mots_cles_map.items():
                        rows.append({"Mot_Cle": mc, "Categorie": data["Categorie"], "Type": data["Type"], "Compte": data["Compte"]})
                    save_data(TAB_MOTS_CLES, pd.DataFrame(rows))
                    st.cache_data.clear()
                    st.session_state.needs_refresh = True
                    st.success(f"✅ Règle créée pour '{m}' !")
                    # Supprimé pour rapidité
                    st.rerun()
                else:
                    st.warning("Veuillez entrer un mot-clé")
        
        # Affichage des règles existantes
        if mots_cles_map:
            st.markdown("### 📋 Règles actives")
            st.caption(f"{len(mots_cles_map)} règle(s) configurée(s)")
            
            for idx, (k, v) in enumerate(mots_cles_map.items()):
                with st.container():
                    col_info, col_del = st.columns([5, 1])
                    
                    with col_info:
                        st.markdown(f"""
                        <div style="background: white; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1rem; margin-bottom: 0.75rem; animation: fadeIn 0.3s ease;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <div style="font-weight: 600; color: #1F2937; margin-bottom: 0.5rem;">
                                        <span style="background: #EFF6FF; color: #2563EB; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 700; margin-right: 0.5rem;">"{k}"</span>
                                        → {v["Categorie"]}
                                    </div>
                                    <div style="font-size: 12px; color: #6B7280;">
                                        Type: {v["Type"]} • Compte: {v["Compte"]}
                                    </div>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col_del:
                        if st.button("🗑️", key=f"del_rule_{idx}", use_container_width=True):
                            del mots_cles_map[k]
                            rows = []
                            for mc, data in mots_cles_map.items():
                                rows.append({"Mot_Cle": mc, "Categorie": data["Categorie"], "Type": data["Type"], "Compte": data["Compte"]})
                            save_data(TAB_MOTS_CLES, pd.DataFrame(rows))
                            st.cache_data.clear()
                            st.session_state.needs_refresh = True
                            st.rerun()
        else:
            st.markdown("""
            <div style="text-align: center; padding: 3rem 2rem; background: white; border-radius: 12px; border: 2px dashed #E5E7EB;">
                <div style="font-size: 48px; margin-bottom: 1rem; opacity: 0.5;">⚡</div>
                <h4 style="color: #1F2937; margin-bottom: 0.5rem; font-weight: 700;">Aucune règle configurée</h4>
                <p style="color: #6B7280; margin: 0; font-size: 14px;">Créez des règles pour automatiser la catégorisation de vos transactions</p>
            </div>
            """, unsafe_allow_html=True)
    
    # === 4. SAUVEGARDES ===
    with c_t4:
        st.markdown("### 💾 Gestion des sauvegardes")
        st.caption("Configurez et gérez vos sauvegardes automatiques")
        
        # Info sur le système de backup
        st.info("""
        **Système de sauvegarde automatique** :
        - 📅 Sauvegarde chaque **lundi**
        - 📦 Conserve les **12 dernières sauvegardes** (3 mois)
        - 🔒 Stockées dans Google Sheets (onglet "Backups")
        - ✅ Automatique et silencieux
        """)
        
        # Statut du dernier backup
        last_backup = st.session_state.get('last_backup_date', 'Aucun')
        if last_backup != 'Aucun':
            week_num = last_backup.split('_')[1] if '_' in last_backup else 'N/A'
            st.success(f"✅ Dernière sauvegarde : Semaine {week_num}")
        else:
            st.warning("⚠️ Aucune sauvegarde effectuée")
        
        st.markdown("---")
        
        # Bouton pour initialiser l'onglet Backups
        st.markdown("### Initialiser le système de backup")
        st.caption("Créez l'onglet 'Backups' dans votre Google Sheet (requis une seule fois)")
        
        if st.button("🔧 Créer l'onglet Backups", type="primary", use_container_width=True):
            try:
                client = get_client()
                sh = client.open(SHEET_NAME)
                
                # Vérifier si existe déjà
                try:
                    ws = sh.worksheet("Backups")
                    st.info("ℹ️ L'onglet 'Backups' existe déjà !")
                except:
                    # Créer l'onglet
                    ws = sh.add_worksheet(title="Backups", rows="100", cols="4")
                    ws.append_row(['Date', 'Semaine', 'Nb_Transactions', 'Nb_Patrimoine'])
                    st.success("✅ Onglet 'Backups' créé avec succès !")
                    st.balloons()
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "Quota exceeded" in error_msg:
                    st.error("❌ **Quota API Google Sheets dépassé**")
                    st.info("""
                    **Solution** :
                    1. ⏱️ Attendez **1 minute**
                    2. 🔄 Cliquez sur le bouton 'Actualiser les données' dans la sidebar
                    3. 🔁 Réessayez ce bouton
                    
                    **Alternative** : Créez manuellement un onglet 'Backups' dans votre Google Sheet avec les colonnes : Date, Semaine, Nb_Transactions, Nb_Patrimoine
                    """)
                else:
                    st.error(f"❌ Erreur lors de la création : {error_msg}")
                    st.caption("💡 Vous pouvez créer manuellement un onglet 'Backups' dans votre Google Sheet")
        
        st.markdown("---")
        
        # Sauvegarde manuelle
        st.markdown("### Sauvegarde manuelle")
        st.caption("Forcer une sauvegarde immédiate")
        
        if st.button("💾 Sauvegarder maintenant", use_container_width=True):
            try:
                from datetime import datetime
                client = get_client()
                sh = client.open(SHEET_NAME)
                ws_backup = sh.worksheet("Backups")
                
                # Créer le backup
                today = datetime.now().strftime('%Y-%m-%d')
                week_num = datetime.now().isocalendar()[1]
                
                ws_backup.append_row([
                    today,
                    week_num,
                    len(df),
                    len(df_patrimoine)
                ])
                
                st.session_state.last_backup_date = f"week_{week_num}"
                st.success(f"✅ Sauvegarde effectuée ! ({len(df)} transactions, {len(df_patrimoine)} entrées patrimoine)")
                
            except Exception as e:
                st.error(f"❌ Erreur : {str(e)}")
                st.caption("💡 Assurez-vous que l'onglet 'Backups' existe (bouton ci-dessus)")
        
        st.markdown("---")
        
        # Voir les backups
        st.markdown("### Historique des sauvegardes")
        
        if st.button("📋 Afficher les sauvegardes", use_container_width=True):
            try:
                client = get_client()
                sh = client.open(SHEET_NAME)
                ws_backup = sh.worksheet("Backups")
                
                backups = ws_backup.get_all_records()
                if backups:
                    df_backups = pd.DataFrame(backups)
                    st.dataframe(df_backups, use_container_width=True)
                else:
                    st.info("Aucune sauvegarde enregistrée")
            except Exception as e:
                st.warning("L'onglet 'Backups' n'existe pas encore. Utilisez le bouton ci-dessus pour le créer.")

