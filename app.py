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
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div {
            background: var(--bg-main) !important;
            border: 1.5px solid var(--border) !important;
            border-radius: 12px !important;
            font-size: 15px !important;
            font-weight: 500 !important;
            padding: 12px 16px !important;
            transition: all 0.2s;
        }
        
        .stTextInput input:focus, .stNumberInput input:focus {
            border-color: var(--primary) !important;
            box-shadow: 0 0 0 3px rgba(255, 107, 53, 0.1) !important;
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
    """Génère un fichier Excel téléchargeable"""
    output = BytesIO()
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Transactions')
    except ImportError:
        output = BytesIO()
        output.write(df.to_csv(index=False).encode('utf-8'))
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

# --- SIDEBAR (DATE A GAUCHE) ---
with st.sidebar:
    st.markdown("<h3 style='margin-bottom:20px;'>Menu</h3>", unsafe_allow_html=True)
    user_actuel = st.selectbox("Utilisateur", USERS)
    
    st.markdown("---")
    st.markdown("**Période**")
    date_jour = datetime.now()
    mois_nom = st.selectbox("Mois", MOIS_FR, index=date_jour.month-1)
    mois_selection = MOIS_FR.index(mois_nom) + 1
    annee_selection = st.number_input("Année", value=date_jour.year)
    
    df_mois = df[(df["Mois"] == mois_selection) & (df["Annee"] == annee_selection)]
    
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
            
            # ===== MODULE 3: EXPORT EXCEL =====
            try:
                excel_data = to_excel_download(df_e)
                file_ext = ".xlsx"
                mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            except:
                excel_data = BytesIO(df_e.to_csv(index=False).encode('utf-8'))
                file_ext = ".csv"
                mime_type = "text/csv"
            
            col_export.download_button(
                label="📥 Export",
                data=excel_data,
                file_name=f"transactions_{datetime.now().strftime('%Y%m%d')}{file_ext}",
                mime=mime_type,
                key="dl_excel",
                use_container_width=True
            )
            
            df_e.insert(0, "Suppr", False)
            ed = st.data_editor(df_e, use_container_width=True, hide_index=True, column_config={"Suppr": st.column_config.CheckboxColumn("Suppr", width="small")}, key="ed_j")
            if st.button("Supprimer sélection", type="primary", key="del_j"):
                save_data_to_sheet(TAB_DATA, ed[ed["Suppr"]==False].drop(columns=["Suppr"])); st.rerun()

    # --- ABONNEMENTS ---
    with subtabs[2]:
        if not df_abonnements.empty:
            my_abos = df_abonnements[(df_abonnements["Proprietaire"] == user_actuel) | (df_abonnements["Imputation"].str.contains("Commun", na=False))].copy()
            if not my_abos.empty:
                abo_data = []
                for idx, row in my_abos.iterrows():
                    is_done = False
                    if not df_mois.empty:
                        if not df_mois[(df_mois["Titre"]==row["Nom"]) & (df_mois["Montant"]==float(row["Montant"]))].empty: is_done = True
                    abo_data.append({"Nom": row["Nom"], "Montant": row["Montant"], "Statut": "✅" if is_done else "⏳", "ID": idx, "Row": row})
                
                st.dataframe(pd.DataFrame(abo_data).drop(columns=["ID", "Row"]), use_container_width=True, hide_index=True)
                
                to_gen = [a["Row"] for a in abo_data if a["Statut"] == "⏳"]
                if to_gen:
                    if st.button(f"Générer {len(to_gen)} manquants", type="primary", key="gen_abo"):
                        new_rows = []
                        for row in to_gen:
                            try: d = datetime(annee_selection, mois_selection, int(row["Jour"])).date()
                            except: d = datetime(annee_selection, mois_selection, 28).date()
                            paye = "Commun" if "Commun" in str(row["Imputation"]) else row["Proprietaire"]
                            new_rows.append({"Date": d, "Mois": mois_selection, "Annee": annee_selection, "Qui_Connecte": row["Proprietaire"], "Type": "Dépense", "Categorie": row["Categorie"], "Titre": row["Nom"], "Description": "Abo Auto", "Montant": float(row["Montant"]), "Paye_Par": paye, "Imputation": row["Imputation"], "Compte_Cible": "", "Projet_Epargne": "", "Compte_Source": row["Compte_Source"]})
                        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True); save_data_to_sheet(TAB_DATA, df); st.rerun()
                
                st.markdown("---")
                st.write("Gestion:")
                for a in abo_data:
                    c1, c2 = st.columns([4,1])
                    c1.text(a["Nom"])
                    if c2.button("Suppr", key=f"del_abo_{a['ID']}"):
                        df_abonnements = df_abonnements.drop(a['ID']); save_abonnements(df_abonnements); st.rerun()
        
        st.markdown("---")
        with st.expander("Nouveau"):
            c1, c2, c3, c4 = st.columns(4)
            n = c1.text_input("Nom", key="na"); m = c2.number_input("Montant", key="ma"); j = c3.number_input("Jour", 1, 31, 1, key="ja"); f = c4.selectbox("Freq", FREQUENCES, key="fa")
            c5, c6, c7 = st.columns(3)
            c = c5.selectbox("Cat", cats_memoire.get("Dépense", []), key="ca"); cp = c6.selectbox("Cpt", comptes_disponibles, key="cpa"); i = c7.radio("Imp", IMPUTATIONS, key="ia")
            if i == "Commun (Autre %)": p = st.slider("%P", 0, 100, 50, key="pa"); i = f"Commun ({p}/{100-p})"
            if st.button("Ajouter Abo", key="ba"):
                df_abonnements = pd.concat([df_abonnements, pd.DataFrame([{"Nom": n, "Montant": m, "Jour": j, "Categorie": c, "Compte_Source": cp, "Proprietaire": user_actuel, "Imputation": i, "Frequence": f}])], ignore_index=True)
                save_abonnements(df_abonnements); st.rerun()

# 3. ANALYSE & BUDGET
with tabs[2]:
    page_header("Analyses & Budget")
    
    # ===== MODULE 2: MODE COMPARAISON M vs M-1 =====
    st.subheader("📊 Comparaison Mensuelle")
    
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
    
    st.subheader("💰 Qui a payé quoi ?")
    
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
    page_header("Patrimoine & Projets")
    
    # MODULE 3: Pyramide de l'épargne
    st.subheader("🔺 Pyramide de l'Épargne")
    
    total_epargne_user = sum([SOLDES_ACTUELS.get(c, 0) for c in comptes_disponibles if comptes_types_map.get(c) == "Épargne"])
    revenus_mensuels = df[(df["Qui_Connecte"] == user_actuel) & (df["Type"] == "Revenu")].groupby(["Mois", "Annee"])["Montant"].sum().mean()
    epargne_precaution_cible = revenus_mensuels * 3
    
    epargne_precaution = min(total_epargne_user, epargne_precaution_cible)
    epargne_projets = max(0, total_epargne_user - epargne_precaution_cible)
    
    pyr1, pyr2, pyr3 = st.columns(3)
    
    status_precaution = "✅ Atteint" if epargne_precaution >= epargne_precaution_cible else "⚠️ En cours"
    pyr1.metric("🛡️ Précaution (3 mois)", f"{epargne_precaution:,.0f} €", status_precaution)
    pyr2.metric("🎯 Projets Court Terme", f"{epargne_projets:,.0f} €")
    pyr3.metric("📈 Investissement Long Terme", "0 €", "À développer")
    
    if epargne_precaution < epargne_precaution_cible:
        st.warning(f"💡 Conseil : Il vous manque {epargne_precaution_cible - epargne_precaution:,.0f}€ pour sécuriser 3 mois de salaire.")
    elif epargne_projets > revenus_mensuels * 6:
        st.success("🎉 Excellente santé financière ! Vous pourriez commencer à investir.")
    
    st.markdown("---")
    
    st.subheader("1. Projets Épargne")
    if projets_config:
        for p, d in projets_config.items():
            saved = df[(df["Projet_Epargne"] == p) & (df["Type"] == "Épargne")]["Montant"].sum() if not df.empty else 0
            target = d["Cible"]
            c1, c2 = st.columns([3,1])
            with c1: st.write(f"**{p}**"); st.progress(min(saved/target if target>0 else 0, 1.0))
            with c2: st.write(f"{saved:.0f} / {target:.0f} €")
            
    with st.expander("Nouveau Projet"):
        n = st.text_input("Nom Projet", key="np"); t = st.number_input("Cible €", key="tp")
        if st.button("Créer Projet", key="bp"): projets_config[n] = {"Cible": t, "Date_Fin": ""}; save_projets_targets(projets_config); st.rerun()

    st.markdown("---")
    st.subheader("2. Relevé de Comptes (Ajustement)")
    with st.form("rel"):
        c1, c2 = st.columns(2); d = c1.date_input("Date", key="dr"); c = c2.selectbox("Cpt", comptes_disponibles, key="cr"); m = st.number_input("Solde Réel", key="mr")
        if st.form_submit_button("Valider"):
            df_patrimoine = pd.concat([df_patrimoine, pd.DataFrame([{"Date": d, "Mois": d.month, "Annee": d.year, "Compte": c, "Montant": m, "Proprietaire": user_actuel}])], ignore_index=True); save_data_to_sheet(TAB_PATRIMOINE, df_patrimoine); st.success("OK"); st.rerun()

# 5. CONFIG
with tabs[6]:
    page_header("Configuration")
    
    config_tabs = st.tabs(["Comptes", "Catégories", "Mots-Clés Auto"])
    
    # COMPTES
    with config_tabs[0]:
        st.subheader("Comptes")
        with st.form("add_cpt"):
            n = st.text_input("Nom", key="nc"); p = st.selectbox("Proprio", ["Pierre", "Elie", "Commun"], key="pc"); t = st.selectbox("Type", TYPES_COMPTE, key="tc")
            if st.form_submit_button("Ajouter"):
                if p not in comptes_structure: comptes_structure[p] = []
                comptes_structure[p].append(n); comptes_types_map[n] = t; save_comptes_struct(comptes_structure, comptes_types_map); st.rerun()
        
        for owner, accs in comptes_structure.items():
            st.write(f"**{owner}**")
            for a in accs:
                col_a, col_b = st.columns([4,1])
                col_a.text(a)
                if col_b.button("X", key=f"del_acc_{a}"): comptes_structure[owner].remove(a); save_comptes_struct(comptes_structure, comptes_types_map); st.rerun()

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
        st.subheader("🤖 Mots-Clés Automatiques")
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
