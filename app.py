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

# ==========================================
# 1. CONFIGURATION ET CONSTANTES
# ==========================================

SHEET_NAME = "Budget_Couple_DB"
TAB_DATA = "Data"
TAB_CONFIG = "Config"
TAB_OBJECTIFS = "Objectifs"
TAB_PATRIMOINE = "Patrimoine"
TAB_COMPTES = "Comptes"
TAB_ABONNEMENTS = "Abonnements"
TAB_PROJETS = "Projets_Config"
TAB_MOTS_CLES = "Mots_Cles"

USERS = ["Pierre", "Elie"]
TYPES = ["Dépense", "Revenu", "Virement Interne", "Épargne", "Investissement"]
IMPUTATIONS = ["Perso", "Commun (50/50)", "Commun (Autre %)", "Avance/Cadeau"]
FREQUENCES = ["Mensuel", "Annuel", "Trimestriel", "Hebdomadaire"]
TYPES_COMPTE = ["Courant", "Épargne"]
MOIS_FR = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

# Définition des colonnes
COLS_DATA = [
    "Date", "Mois", "Annee", "Qui_Connecte", "Type", "Categorie", 
    "Titre", "Description", "Montant", "Paye_Par", "Imputation", 
    "Compte_Cible", "Projet_Epargne", "Compte_Source"
]
COLS_PAT = ["Date", "Mois", "Annee", "Compte", "Montant", "Proprietaire"]

# ==========================================
# 2. STYLE CSS PREMIUM (DESIGN BANQUE)
# ==========================================

def apply_custom_style():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        :root {
            --primary: #2C3E50;
            --primary-light: #34495E;
            --accent: #2980B9;
            --bg-main: #F8F9FA;
            --bg-card: #FFFFFF;
            --text-primary: #1F2937;
            --text-secondary: #6B7280;
            --border: #E5E7EB;
        }

        .stApp {
            background-color: var(--bg-main);
            font-family: 'Inter', sans-serif;
            color: var(--text-primary);
        }
        
        .main .block-container {
            padding-top: 2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 100% !important;
        }
        
        #MainMenu, footer, header {visibility: hidden;}

        /* TABS */
        .stTabs [data-baseweb="tab-list"] {
            gap: 24px;
            background-color: transparent;
            padding: 0px;
            border-bottom: 2px solid var(--border);
            margin-bottom: 24px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 48px;
            background-color: transparent;
            border: none;
            color: var(--text-secondary);
            font-weight: 600;
            font-size: 15px;
            padding: 0 10px;
        }
        .stTabs [aria-selected="true"] {
            color: var(--primary) !important;
            border-bottom: 3px solid var(--primary) !important;
        }

        /* CARDS */
        div[data-testid="stMetric"], div.stDataFrame, div.stForm, div[data-testid="stExpander"] {
            background-color: var(--bg-card);
            padding: 24px;
            border-radius: 12px;
            border: 1px solid var(--border) !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }
        
        /* SIDEBAR */
        section[data-testid="stSidebar"] {
            background-color: var(--bg-card);
            border-right: 1px solid var(--border);
        }

        /* INPUTS */
        .stTextInput input, .stNumberInput input, .stSelectbox > div > div {
            border-radius: 8px !important;
            border-color: var(--border) !important;
            background-color: #FFFFFF !important;
        }

        /* BOUTONS */
        div.stButton > button {
            background-color: var(--primary) !important;
            color: white !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
            border: none !important;
            padding: 8px 20px !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
        }
        
        /* LISTE TRANSACTIONS HOME - FIXE POUR EVITER L'AFFICHAGE DU CODE */
        .tx-card {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #F3F4F6;
        }
        
        /* BADGES CATEGORIES */
        .cat-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin: 0 6px 6px 0;
            border: 1px solid transparent;
        }
        .cat-badge.depense { background-color: #FFF1F2; color: #E11D48; border-color: #FECDD3; }
        .cat-badge.revenu { background-color: #ECFDF5; color: #059669; border-color: #A7F3D0; }
        .cat-badge.epargne { background-color: #EFF6FF; color: #2563EB; border-color: #BFDBFE; }
    </style>
    """, unsafe_allow_html=True)

def page_header(title, subtitle=None):
    if subtitle:
        st.markdown(f"""<div style="margin-bottom: 25px;"><h2 style='font-size:28px; font-weight:700; color:#2C3E50; margin-bottom:6px;'>{title}</h2><p style='font-size:14px; color:#6B7280; font-weight:400;'>{subtitle}</p></div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"<h2 style='font-size:28px; font-weight:700; color:#2C3E50; margin-bottom:25px;'>{title}</h2>", unsafe_allow_html=True)

# ==========================================
# 3. CONNEXION GOOGLE SHEETS
# ==========================================

@st.cache_resource
def get_gspread_client():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        return gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope))
    except Exception as e:
        st.error(f"Erreur technique : {e}"); return None

def get_worksheet(client, sheet_name, tab_name):
    try:
        sh = client.open(sheet_name)
        try: return sh.worksheet(tab_name)
        except: return sh.add_worksheet(title=tab_name, rows="100", cols="20")
    except Exception as e:
        st.error(f"Erreur d'accès à l'onglet {tab_name} : {e}"); st.stop()

# ==========================================
# 4. GESTION DES DONNÉES
# ==========================================

@st.cache_data(ttl=600, show_spinner=False)
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

def save_data_to_sheet(tab_name, df):
    client = get_gspread_client()
    ws = get_worksheet(client, SHEET_NAME, tab_name)
    df_save = df.copy()
    if "Date" in df_save.columns: df_save["Date"] = df_save["Date"].astype(str)
    ws.clear()
    if not df_save.empty: ws.update([df_save.columns.values.tolist()] + df_save.values.tolist())
    else: ws.update([df_save.columns.values.tolist()])
    st.cache_data.clear()

@st.cache_data(ttl=600, show_spinner=False)
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

# ==========================================
# 5. LOGIQUE MÉTIER & CALCULS
# ==========================================

# Initialisation du session state pour la fluidité de la saisie
def init_session_state():
    if 'op_date' not in st.session_state: st.session_state.op_date = datetime.today()
    if 'op_type' not in st.session_state: st.session_state.op_type = "Dépense"
    if 'op_montant' not in st.session_state: st.session_state.op_montant = 0.0
    if 'op_titre' not in st.session_state: st.session_state.op_titre = ""

def to_excel_download(df):
    output = BytesIO()
    df_export = df.copy()
    if "Date" in df_export.columns:
        df_export["Date"] = df_export["Date"].astype(str)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Transactions')
    return output.getvalue()

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
            v_out = df_t[(df_t["Compte_Source"] == compte) & (df_t["Type"].isin(["Virement Interne", "Épargne"]))]["Montant"].sum()
            credits = df_t[(df_t["Compte_Source"] == compte) & (df_t["Type"] == "Revenu")]["Montant"].sum()
            v_in = df_t[(df_t["Compte_Cible"] == compte) & (df_t["Type"].isin(["Virement Interne", "Épargne"]))]["Montant"].sum()
            mouvements = credits + v_in - debits - v_out
        soldes[compte] = releve + mouvements
    return soldes

def process_configs():
    data = load_configs_cached()
    df_cats, df_comptes, df_objs, df_abos, df_projets, df_mots_cles = data
    
    cats = {k: [] for k in TYPES}
    if not df_cats.empty:
        for _, row in df_cats.iterrows():
            if row["Type"] in cats and row["Categorie"] not in cats[row["Type"]]:
                cats[row["Type"]].append(row["Categorie"])
    if not cats["Dépense"]: cats["Dépense"] = ["Alimentation", "Loyer", "Autre"]
        
    comptes = {"Pierre": [], "Elie": [], "Commun": []}
    comptes_types = {}
    if not df_comptes.empty:
        for _, row in df_comptes.iterrows():
            if row["Proprietaire"] not in comptes: comptes[row["Proprietaire"]] = []
            comptes[row["Proprietaire"]].append(row["Compte"])
            c_type = row.get("Type", "Courant")
            comptes_types[row["Compte"]] = c_type
            
    objs_list = df_objs.to_dict('records') if not df_objs.empty else []
            
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

# Save Functions
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


# ==========================================
# 6. APPLICATION STREAMLIT
# ==========================================

st.set_page_config(page_title="Ma Banque V69", layout="wide", page_icon=None)
apply_custom_style()
init_session_state()

# Chargement initial des données
df = load_data_from_sheet(TAB_DATA, COLS_DATA)
df_patrimoine = load_data_from_sheet(TAB_PATRIMOINE, COLS_PAT)
cats_memoire, comptes_structure, objectifs_list, df_abonnements, projets_config, comptes_types_map, mots_cles_map = process_configs()

# --- SIDEBAR (MENU & FILTRES) ---
with st.sidebar:
    st.markdown("### Menu Principal")
    user_actuel = st.selectbox("Utilisateur", USERS)
    
    st.markdown("---")
    
    # 1. Calcul des comptes dispos
    comptes_user_only = comptes_structure.get(user_actuel, [])
    comptes_communs = comptes_structure.get("Commun", [])
    comptes_visibles = comptes_user_only + comptes_communs
    comptes_disponibles = list(set(comptes_visibles + ["Autre / Externe"]))
    
    soldes = calculer_soldes_reels(df, df_patrimoine, comptes_disponibles)
    
    list_courant = []
    list_epargne = []
    total_courant = 0
    total_epargne = 0
    
    for cpt in comptes_visibles:
        val = soldes.get(cpt, 0.0)
        ctype = comptes_types_map.get(cpt, "Courant")
        if ctype == "Épargne": 
            total_epargne += val
            list_epargne.append((cpt, val))
        else: 
            total_courant += val
            list_courant.append((cpt, val))

    def draw_account_card(name, val, is_saving=False):
        if is_saving:
            gradient = "linear-gradient(135deg, #0066FF 0%, #00D4FF 100%)"
        else:
            gradient = "linear-gradient(135deg, #10B981 0%, #059669 100%)" if val >= 0 else "linear-gradient(135deg, #EF4444 0%, #DC2626 100%)"
        
        st.markdown(f"""
        <div style="background: {gradient}; border-radius: 12px; padding: 15px; margin-bottom: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); color:white;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div style="font-size: 11px; font-weight: 600; text-transform: uppercase;">{name}</div>
                <div style="font-size: 16px; font-weight: 800;">{val:,.2f} €</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"**COURANTS ({total_courant:,.0f}€)**")
    for n, v in list_courant: draw_account_card(n, v, False)
    
    st.write("")
    st.markdown(f"**ÉPARGNE ({total_epargne:,.0f}€)**")
    for n, v in list_epargne: draw_account_card(n, v, True)

    st.markdown("---")
    st.markdown("**Période**")
    date_jour = datetime.now()
    mois_nom = st.selectbox("Mois", MOIS_FR, index=date_jour.month-1)
    mois_selection = MOIS_FR.index(mois_nom) + 1
    annee_selection = st.number_input("Année", value=date_jour.year)
    
    df_mois = df[(df["Mois"] == mois_selection) & (df["Annee"] == annee_selection)]

    st.markdown("---")
    if st.button("Actualiser les données", use_container_width=True): 
        clear_cache()
        st.rerun()

# --- TABS PRINCIPAUX ---
tabs = st.tabs(["Accueil", "Opérations", "Analyses", "Patrimoine", "Réglages"])

# ==========================================
# TAB 1: ACCUEIL (DASHBOARD)
# ==========================================
with tabs[0]:
    page_header("Synthèse du mois", f"Vue d'ensemble pour {user_actuel}")
    
    rev = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Revenu")]["Montant"].sum()
    dep = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Dépense") & (df_mois["Imputation"] == "Perso")]["Montant"].sum()
    epg = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Épargne")]["Montant"].sum()
    com = df_mois[df_mois["Imputation"] == "Commun (50/50)"]["Montant"].sum() / 2
    
    charges_fixes = 0.0
    if not df_abonnements.empty:
        abos_user = df_abonnements[(df_abonnements["Proprietaire"] == user_actuel) | (df_abonnements["Imputation"].str.contains("Commun", na=False))]
        for _, row in abos_user.iterrows():
            charges_fixes += float(row["Montant"]) / (2 if "Commun" in str(row["Imputation"]) else 1)
    
    rav = rev - charges_fixes - dep - com
    rav_gradient = "linear-gradient(135deg, #10B981 0%, #059669 100%)" if rav > 0 else "linear-gradient(135deg, #EF4444 0%, #DC2626 100%)"
    
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Revenus", f"{rev:,.0f} €")
    k2.metric("Charges Fixes", f"{charges_fixes:,.0f} €", delta=None, delta_color="inverse")
    k3.metric("Dépenses Variables", f"{(dep + com):,.0f} €", delta=None, delta_color="inverse")
    k4.metric("Épargne", f"{epg:,.0f} €", delta=None, delta_color="normal")
    k5.markdown(f"""
    <div style="background: {rav_gradient}; border-radius: 12px; padding: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); color:white; text-align:center;">
        <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; margin-bottom: 4px;">Reste à Vivre</div>
        <div style="font-size: 28px; font-weight: 800;">{rav:,.0f} €</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    c1, c2 = st.columns([3, 2])
    with c1:
        h_col1, h_col2 = st.columns([1, 1])
        with h_col1: st.subheader("Activités")
        with h_col2: 
            filtre_tx = st.radio("Filtre", ["Tout", "Sorties", "Entrées"], horizontal=True, label_visibility="collapsed", key="filt_home")

        tx_data = df[df['Qui_Connecte'] == user_actuel].sort_values(by='Date', ascending=False)
        if filtre_tx == "Sorties": tx_data = tx_data[tx_data['Type'].isin(["Dépense", "Virement Interne", "Épargne", "Investissement"])]
        elif filtre_tx == "Entrées": tx_data = tx_data[tx_data['Type'] == "Revenu"]
        
        recent = tx_data.head(5)
        
        if not recent.empty:
            for _, r in recent.iterrows():
                is_dep = r['Type'] in ["Dépense", "Virement Interne", "Épargne", "Investissement"]
                bg_icon = "#FFF1F2" if is_dep else "#ECFDF5"
                txt_color = "#E11D48" if is_dep else "#059669"
                signe = "-" if is_dep else "+"
                icon_char = "💸" if is_dep else "💰"
                if r['Type'] == "Épargne": icon_char = "🐷"
                if r['Type'] == "Virement Interne": icon_char = "↔️"
                
                # HTML CORRECTEMENT FORMATÉ (SANS INDENTATION INTERNE QUI CASSE LE RENDU)
                html_card = f"""
<div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #F3F4F6;">
    <div style="display: flex; align-items: center; gap: 15px;">
        <div style="width: 40px; height: 40px; border-radius: 10px; background-color: {bg_icon}; display: flex; align-items: center; justify-content: center; font-size: 18px;">
            {icon_char}
        </div>
        <div>
            <div style="font-weight: 600; color: #1F2937; font-size: 14px;">{r['Titre']}</div>
            <div style="font-size: 12px; color: #6B7280;">{r['Date'].strftime('%d/%m')} • {r['Categorie']}</div>
        </div>
    </div>
    <div style="font-weight: 700; font-size: 15px; color: {txt_color};">
        {signe} {r['Montant']:,.2f} €
    </div>
</div>
"""
                st.markdown(html_card, unsafe_allow_html=True)
        else:
            st.info("Aucune activité.")
            
    with c2:
        st.subheader("Alertes Budget")
        objs_perso = [o for o in objectifs_list if o["Scope"] in ["Perso", user_actuel]]
        mask = (df_mois["Type"] == "Dépense") & (df_mois["Imputation"] == "Perso") & (df_mois["Qui_Connecte"] == user_actuel)
        df_f = df_mois[mask]
        
        has_alert = False
        for obj in objs_perso:
            cat = obj["Categorie"]
            budget = float(obj["Montant"])
            if budget > 0:
                r = df_f[df_f["Categorie"] == cat]["Montant"].sum()
                if r/budget > 0.75:
                    has_alert = True
                    st.write(f"**{cat}** : {r:.0f} / {budget:.0f} €")
                    st.progress(min(r/budget, 1.0))
        if not has_alert: st.success("Budget maîtrisé !")

# ================= TAB 2: OPÉRATIONS (SAISIE DYNAMIQUE) =================
with tabs[1]:
    op1, op2, op3 = st.tabs(["Saisie", "Journal", "Abonnements"])
    
    # 1. SAISIE DE TRANSACTION (SANS ST.FORM POUR LA DYNAMIQUE)
    with op1:
        st.subheader("Nouvelle Transaction")
        
        # Champs principaux (Hors Formulaire pour interactivité)
        c1, c2, c3 = st.columns(3)
        date_op = c1.date_input("Date", datetime.today(), key="s_date")
        type_op = c2.selectbox("Type", TYPES, key="s_type") # Le changement ici recharge la page et met à jour les catégories
        montant_op = c3.number_input("Montant (€)", min_value=0.0, step=0.01, key="s_montant")
        
        c4, c5 = st.columns(2)
        titre_op = c4.text_input("Titre (ex: Auchan)", key="s_titre")
        
        # Auto-completion Mots-clés
        cat_finale = "Autre"
        compte_auto = None
        if titre_op and mots_cles_map:
            for mc, data in mots_cles_map.items():
                if mc in titre_op.lower() and data["Type"] == type_op:
                    cat_finale = data["Categorie"]
                    compte_auto = data["Compte"]
                    break
        
        # Catégories dynamiques selon le Type
        cats = cats_memoire.get(type_op, [])
        cat_options = cats + ["Autre (nouvelle)"]
        # Index par défaut
        idx_cat = cats.index(cat_finale) if cat_finale in cats else 0
        cat_sel = c5.selectbox("Catégorie", cat_options, index=idx_cat, key="s_cat")
        
        # Champ Nouvelle Catégorie
        final_cat_val = cat_sel
        if cat_sel == "Autre (nouvelle)":
            final_cat_val = st.text_input("Nom de la nouvelle catégorie", key="s_new_cat")
        
        st.write("")
        cc1, cc2, cc3 = st.columns(3)
        # Compte Source (Pré-rempli si mot clé)
        idx_cpt = comptes_visibles.index(compte_auto) if (compte_auto and compte_auto in comptes_visibles) else 0
        c_src = cc1.selectbox("Compte Source", comptes_visibles, index=idx_cpt, key="s_src")
        
        # Imputation
        imput = cc2.radio("Imputation", IMPUTATIONS, horizontal=True, key="s_imp")
        
        # Slider si Autre % (DYNAMIQUE)
        final_imput = imput
        if imput == "Commun (Autre %)":
            part_pierre = cc3.slider("Part Pierre (%)", 0, 100, 50, key="s_slide")
            final_imput = f"Commun ({part_pierre}/{100-part_pierre})"
        elif type_op == "Virement Interne":
            final_imput = "Neutre"
            
        # Champs conditionnels selon type (DYNAMIQUE)
        c_tgt = ""
        p_epg = ""
        
        if type_op == "Épargne":
            st.info("Détails Épargne")
            col_e1, col_e2 = st.columns(2)
            c_tgt = col_e1.selectbox("Vers Compte Épargne", [c for c in comptes_visibles if comptes_types_map.get(c) == "Épargne"], key="s_tgt_e")
            p_sel = col_e2.selectbox("Pour Projet", ["Aucun"] + list(projets_config.keys()), key="s_prj")
            if p_sel != "Aucun": p_epg = p_sel
            
        elif type_op == "Virement Interne":
            st.info("Détails Virement")
            c_tgt = st.selectbox("Vers Compte", comptes_visibles, key="s_tgt_v")
            
        st.write("")
        # Bouton de validation final
        if st.button("Valider la transaction", type="primary", use_container_width=True):
            # 1. Sauvegarde catégorie
            if cat_sel == "Autre (nouvelle)" and final_cat_val:
                if type_op not in cats_memoire: cats_memoire[type_op] = []
                if final_cat_val not in cats_memoire[type_op]:
                    cats_memoire[type_op].append(final_cat_val)
                    save_config_cats(cats_memoire)
            
            # 2. Sauvegarde Projet
            if type_op == "Épargne" and p_epg and p_epg not in projets_config:
                projets_config[p_epg] = {"Cible": 0.0, "Date_Fin": ""}
                save_projets_targets(projets_config)
                
            # 3. Sauvegarde Transaction
            new_row = {
                "Date": date_op, "Mois": date_op.month, "Annee": date_op.year,
                "Qui_Connecte": user_actuel, "Type": type_op, "Categorie": final_cat_val,
                "Titre": titre_op, "Description": "", "Montant": montant_op,
                "Paye_Par": user_actuel, "Imputation": final_imput, 
                "Compte_Cible": c_tgt, "Projet_Epargne": p_epg, "Compte_Source": c_src
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_data_to_sheet(TAB_DATA, df)
            st.success("Transaction enregistrée !")
            time.sleep(0.5)
            st.rerun()

    # 2. JOURNAL
    with op2:
        search = st.text_input("Rechercher dans l'historique...", key="search_j")
        if not df.empty:
            df_e = df.copy().sort_values(by="Date", ascending=False)
            if search: df_e = df_e[df_e.apply(lambda r: str(r).lower().find(search.lower()) > -1, axis=1)]
            
            st.download_button("Télécharger Excel", to_excel_download(df_e), "journal.xlsx")
            
            df_e.insert(0, "Suppr", False)
            ed = st.data_editor(df_e, hide_index=True, column_config={"Suppr": st.column_config.CheckboxColumn("Supprimer", width="small")})
            
            if st.button("Confirmer la suppression"):
                to_keep = ed[ed["Suppr"] == False].drop(columns=["Suppr"])
                save_data_to_sheet(TAB_DATA, to_keep)
                st.success("Lignes supprimées")
                st.rerun()

    # 3. ABONNEMENTS (AVEC MODIFICATION)
    with op3:
        st.subheader("Gestion des Abonnements")
        
        # Ajout
        with st.expander("Ajouter un abonnement"):
            with st.form("new_abo"):
                a1, a2, a3 = st.columns(3)
                n = a1.text_input("Nom"); m = a2.number_input("Montant"); j = a3.number_input("Jour", 1, 31)
                a4, a5 = st.columns(2)
                c = a4.selectbox("Catégorie", cats_memoire.get("Dépense", [])); cp = a5.selectbox("Compte débité", comptes_visibles)
                i_abo = st.selectbox("Imputation", IMPUTATIONS)
                
                if st.form_submit_button("Créer"):
                    new_abo = pd.DataFrame([{"Nom": n, "Montant": m, "Jour": j, "Categorie": c, "Compte_Source": cp, "Proprietaire": user_actuel, "Imputation": i_abo, "Frequence": "Mensuel"}])
                    df_abonnements = pd.concat([df_abonnements, new_abo], ignore_index=True)
                    save_abonnements(df_abonnements); st.rerun()
        
        # Liste & Modification
        if not df_abonnements.empty:
            my_abos = df_abonnements[df_abonnements["Proprietaire"] == user_actuel]
            if not my_abos.empty:
                # Génération transactions
                to_gen = []
                for idx, r in my_abos.iterrows():
                    paid = not df_mois[(df_mois["Titre"]==r["Nom"])&(df_mois["Montant"]==float(r["Montant"]))].empty
                    if not paid: to_gen.append(r)
                
                if to_gen:
                    if st.button(f"Générer {len(to_gen)} abonnements manquants", use_container_width=True):
                        nt = []
                        for r in to_gen:
                            try: d = datetime(annee_selection, mois_selection, int(r["Jour"])).date()
                            except: d = datetime(annee_selection, mois_selection, 28).date()
                            nt.append({"Date": d, "Mois": mois_selection, "Annee": annee_selection, "Qui_Connecte": r["Proprietaire"], "Type": "Dépense", "Categorie": r["Categorie"], "Titre": r["Nom"], "Description": "Auto", "Montant": float(r["Montant"]), "Paye_Par": r["Proprietaire"], "Imputation": r["Imputation"], "Compte_Cible": "", "Projet_Epargne": "", "Compte_Source": r["Compte_Source"]})
                        df = pd.concat([df, pd.DataFrame(nt)], ignore_index=True); save_data_to_sheet(TAB_DATA, df); st.rerun()

                # Affichage Cartes
                for idx, r in my_abos.iterrows():
                    with st.container():
                        c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                        
                        # Mode lecture
                        if not st.session_state.get(f"edit_mode_{idx}", False):
                            c1.write(f"**{r['Nom']}**"); c2.write(f"{r['Montant']}€ (J{r['Jour']})")
                            if c3.button("Modif", key=f"btn_edit_{idx}"):
                                st.session_state[f"edit_mode_{idx}"] = True
                                st.rerun()
                            if c4.button("Suppr", key=f"btn_del_{idx}"):
                                df_abonnements = df_abonnements.drop(idx); save_abonnements(df_abonnements); st.rerun()
                        
                        # Mode édition
                        else:
                            with st.form(f"edit_form_{idx}"):
                                en = st.text_input("Nom", value=r['Nom'])
                                em = st.number_input("Montant", value=float(r['Montant']))
                                ej = st.number_input("Jour", value=int(r['Jour']))
                                c_ok, c_cancel = st.columns(2)
                                if c_ok.form_submit_button("Sauver"):
                                    df_abonnements.at[idx, 'Nom'] = en
                                    df_abonnements.at[idx, 'Montant'] = em
                                    df_abonnements.at[idx, 'Jour'] = ej
                                    save_abonnements(df_abonnements)
                                    st.session_state[f"edit_mode_{idx}"] = False
                                    st.rerun()
                                if c_cancel.form_submit_button("Annuler"):
                                    st.session_state[f"edit_mode_{idx}"] = False
                                    st.rerun()
                        st.markdown("---")

# ================= TAB 3: ANALYSES =================
with tabs[2]:
    an1, an2 = st.tabs(["Vue Globale", "Objectifs & Budgets"])
    
    with an1:
        if not df_mois.empty:
            fig = px.pie(df_mois[df_mois["Type"]=="Dépense"], values="Montant", names="Categorie", title="Répartition Dépenses", hole=0.5)
            st.plotly_chart(fig, use_container_width=True)
            
            # Sankey
            df_rev = df_mois[df_mois["Type"] == "Revenu"]; df_dep = df_mois[df_mois["Type"] == "Dépense"]
            rf = df_rev.groupby(["Categorie", "Compte_Source"])["Montant"].sum().reset_index()
            df_d = df_dep.groupby(["Compte_Source", "Categorie"])["Montant"].sum().reset_index()
            labels = list(set(rf["Categorie"].tolist() + rf["Compte_Source"].tolist() + df_d["Compte_Source"].tolist() + df_d["Categorie"].tolist()))
            lmap = {n: i for i, n in enumerate(labels)}
            s, t, v, c = [], [], [], []
            for _, r in rf.iterrows(): 
                s.append(lmap[r["Categorie"]]); t.append(lmap[r["Compte_Source"]]); v.append(r["Montant"]); c.append("green")
            for _, r in df_d.iterrows():
                if r["Compte_Source"] in lmap: s.append(lmap[r["Compte_Source"]]); t.append(lmap[r["Categorie"]]); v.append(r["Montant"]); c.append("red")
            if v:
                fig_s = go.Figure(data=[go.Sankey(node=dict(pad=15, thickness=20, label=labels, color="black"), link=dict(source=s, target=t, value=v, color=c))])
                st.plotly_chart(fig_s, use_container_width=True)
                
        # Equilibre
        df_c = df_mois[df_mois["Imputation"].str.contains("Commun", na=False)]
        pp = df_c[df_c["Paye_Par"]=="Pierre"]["Montant"].sum()
        ep = df_c[df_c["Paye_Par"]=="Elie"]["Montant"].sum()
        diff = (pp - ep)/2
        
        st.markdown("### Équilibre")
        c1, c2 = st.columns(2)
        c1.metric("Pierre a payé", f"{pp:,.0f} €")
        c2.metric("Elie a payé", f"{ep:,.0f} €")
        if diff > 0: st.info(f"Elie doit {abs(diff):,.0f} € à Pierre")
        elif diff < 0: st.info(f"Pierre doit {abs(diff):,.0f} € à Elie")
        else: st.success("Comptes équilibrés")

    with an2:
        st.markdown("### 🎯 Mes Budgets")
        with st.expander("Créer un budget", expanded=False):
            with st.form("new_obj"):
                c1,c2,c3 = st.columns(3); sc=c1.selectbox("Scope", ["Perso", "Commun"]); ca=c2.selectbox("Cat", cats_memoire.get("Dépense", [])); mt=c3.number_input("Max €")
                if st.form_submit_button("Ajouter"):
                    objectifs_list.append({"Scope": sc, "Categorie": ca, "Montant": mt}); save_objectifs_from_df(pd.DataFrame(objectifs_list)); st.rerun()
        
        if not objectifs_list:
            st.info("Aucun budget défini.")
        else:
            for i in range(0, len(objectifs_list), 2):
                cs = st.columns(2)
                for j, col in enumerate(cs):
                    if i+j < len(objectifs_list):
                        idx = i+j; o = objectifs_list[idx]
                        if o['Scope']=="Perso" and user_actuel not in USERS: continue
                        
                        msk = (df_mois["Type"]=="Dépense") & (df_mois["Categorie"]==o["Categorie"])
                        if o["Scope"]=="Perso": msk = msk & (df_mois["Imputation"]=="Perso") & (df_mois["Qui_Connecte"]==user_actuel)
                        else: msk = msk & (df_mois["Imputation"].str.contains("Commun"))
                        
                        real = df_mois[msk]["Montant"].sum(); targ = float(o["Montant"]); rat = real/targ if targ>0 else 0
                        bcol = "#EF4444" if rat>=1 else ("#F59E0B" if rat>=0.8 else "#10B981")
                        sttxt = "DÉPASSÉ" if rat>=1 else ("ATTENTION" if rat>=0.8 else "OK")
                        
                        # CARTE BUDGET HTML PROPRE
                        html_budget = f"""
<div style="background:white; border-radius:12px; padding:15px; border:1px solid #eee; margin-bottom:10px;">
    <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
        <div style="font-weight:bold;">{o['Categorie']}</div>
        <div style="font-size:12px; color:#888;">{o['Scope']}</div>
    </div>
    <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
        <div style="font-weight:bold; color:{bcol};">{real:.0f} €</div>
        <div style="font-size:12px;">sur {targ:.0f} €</div>
    </div>
    <div style="width:100%; background:#eee; height:6px; border-radius:3px;">
        <div style="width:{min(rat*100, 100)}%; background:{bcol}; height:100%; border-radius:3px;"></div>
    </div>
    <div style="text-align:right; font-size:10px; font-weight:bold; color:{bcol}; margin-top:5px;">{sttxt}</div>
</div>
"""
                        with col:
                            st.markdown(html_budget, unsafe_allow_html=True)
                            if st.button("Suppr", key=f"do_{idx}"):
                                objectifs_list.pop(idx); save_objectifs_from_df(pd.DataFrame(objectifs_list)); st.rerun()

# ================= TAB 4: PATRIMOINE =================
with tabs[3]:
    page_header("Patrimoine")
    
    acc_choice = st.selectbox("Compte", comptes_visibles)
    if acc_choice:
        sl = soldes.get(acc_choice, 0.0)
        cl = "green" if sl>=0 else "red"
        st.markdown(f"## <span style='color:{cl}'>{sl:,.2f} €</span>", unsafe_allow_html=True)
        mk = (df["Compte_Source"]==acc_choice)|(df["Compte_Cible"]==acc_choice)
        st.dataframe(df[mk].sort_values(by="Date", ascending=False).head(10)[["Date","Titre","Montant","Type"]], use_container_width=True, hide_index=True)

    st.markdown("---")
    s1, s2 = st.tabs(["Projets", "Ajustement"])
    
    with st1:
        # --- EN-TÊTE & CRÉATION ---
        c_titre, c_new = st.columns([2, 1])
        with c_titre:
            st.subheader("🎯 Objectifs d'Épargne")
        with c_new:
            # Bouton pour ouvrir le formulaire de création
            if st.button("➕ Nouveau Projet", use_container_width=True):
                st.session_state['show_new_proj'] = not st.session_state.get('show_new_proj', False)

        # Formulaire de création (s'affiche si cliqué)
        if st.session_state.get('show_new_proj', False):
            with st.container():
                st.markdown("""<div style="background:#f8fafc; padding:15px; border-radius:10px; border:1px solid #e2e8f0; margin-bottom:20px;">
                <div style="font-weight:bold; margin-bottom:10px; color:#2C3E50;">Nouveau Projet</div>""", unsafe_allow_html=True)
                with st.form("create_proj_form"):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    n_p = c1.text_input("Nom du projet (ex: Voyage Japon)")
                    t_p = c2.number_input("Cible (€)", min_value=1.0, step=50.0)
                    o_p = c3.selectbox("Pour qui ?", ["Commun", user_now])
                    
                    if st.form_submit_button("Valider la création", type="primary"):
                        if n_p and n_p not in projets_config:
                            projets_config[n_p] = {"Cible": t_p, "Date_Fin": "", "Proprietaire": o_p}
                            # Sauvegarde
                            rows = []
                            for k, v in projets_config.items(): 
                                rows.append({"Projet": k, "Cible": v["Cible"], "Date_Fin": v["Date_Fin"], "Proprietaire": v.get("Proprietaire", "Commun")})
                            save_data(TAB_PROJETS, pd.DataFrame(rows))
                            st.session_state['show_new_proj'] = False
                            st.success(f"Projet {n_p} créé !")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("Nom invalide ou déjà existant")
                st.markdown("</div>", unsafe_allow_html=True)

        # --- FILTRES ---
        filter_owner = st.radio("Afficher :", ["Tout", "Commun", "Perso"], horizontal=True, label_visibility="collapsed")
        st.write("")

        # --- LISTE DES PROJETS ---
        if not projets_config:
            st.info("Aucun projet d'épargne en cours.")
        
        else:
            # Tri : On met les projets les plus proches du but en premier ? Non, alphabétique c'est mieux pour retrouver
            for p_name, p_data in projets_config.items():
                
                # Logique de Filtrage
                proprio = p_data.get("Proprietaire", "Commun")
                if filter_owner == "Commun" and proprio != "Commun": continue
                if filter_owner == "Perso" and proprio == "Commun": continue
                
                # Calculs
                saved = df[(df["Projet_Epargne"] == p_name) & (df["Type"] == "Épargne")]["Montant"].sum()
                target = float(p_data["Cible"])
                reste = max(0, target - saved)
                progress = min(saved / target if target > 0 else 0, 1.0)
                pct = progress * 100
                
                # Couleurs dynamiques
                bar_color = "#10B981" if progress >= 1.0 else "#3B82F6" # Vert si fini, Bleu sinon
                bg_badge = "#EFF6FF" if proprio == "Commun" else "#FFF7ED" # Bleu pale Commun, Orange pale Perso
                txt_badge = "#1E40AF" if proprio == "Commun" else "#9A3412"

                # --- MODE ÉDITION ---
                if st.session_state.get(f"edit_mode_{p_name}", False):
                    with st.container():
                        st.markdown(f"""<div style="border:2px solid #3B82F6; border-radius:12px; padding:15px; margin-bottom:15px; background:white;">
                        <div style="font-weight:bold; color:#3B82F6; margin-bottom:10px;">Modification : {p_name}</div>""", unsafe_allow_html=True)
                        
                        c_edit1, c_edit2 = st.columns(2)
                        new_target = c_edit1.number_input("Nouvelle Cible (€)", value=target, key=f"nt_{p_name}")
                        new_prop = c_edit2.selectbox("Propriétaire", ["Commun", user_now], index=0 if proprio=="Commun" else 1, key=f"np_{p_name}")
                        
                        col_save, col_cancel = st.columns([1, 1])
                        if col_save.button("💾 Sauvegarder", key=f"save_{p_name}", use_container_width=True):
                            projets_config[p_name]["Cible"] = new_target
                            projets_config[p_name]["Proprietaire"] = new_prop
                            # Sauvegarde
                            rows = []
                            for k, v in projets_config.items(): 
                                rows.append({"Projet": k, "Cible": v["Cible"], "Date_Fin": v["Date_Fin"], "Proprietaire": v.get("Proprietaire", "Commun")})
                            save_data(TAB_PROJETS, pd.DataFrame(rows))
                            st.session_state[f"edit_mode_{p_name}"] = False
                            st.rerun()
                            
                        if col_cancel.button("Annuler", key=f"cancel_{p_name}", use_container_width=True):
                            st.session_state[f"edit_mode_{p_name}"] = False
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)

                # --- MODE AFFICHAGE (CARTE) ---
                else:
                    # Rendu HTML de la carte
                    st.markdown(f"""
                    <div style="
                        background-color: white;
                        border: 1px solid #E5E7EB;
                        border-radius: 12px;
                        padding: 16px;
                        margin-bottom: 12px;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
                    ">
                        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                            <div>
                                <div style="font-size: 16px; font-weight: 700; color: #1F2937;">{p_name}</div>
                                <span style="
                                    font-size: 10px; 
                                    font-weight: 600; 
                                    text-transform: uppercase; 
                                    background-color: {bg_badge}; 
                                    color: {txt_badge}; 
                                    padding: 2px 8px; 
                                    border-radius: 10px;">
                                    {proprio}
                                </span>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 18px; font-weight: 800; color: {bar_color};">{saved:,.0f} €</div>
                                <div style="font-size: 11px; color: #6B7280;">sur {target:,.0f} €</div>
                            </div>
                        </div>
                        
                        <div style="width: 100%; background-color: #F3F4F6; border-radius: 4px; height: 8px; margin-bottom: 8px; overflow:hidden;">
                            <div style="width: {pct}%; background-color: {bar_color}; height: 100%; border-radius: 4px; transition: width 0.5s;"></div>
                        </div>
                        
                        <div style="display: flex; justify-content: space-between; font-size: 12px; color: #6B7280;">
                            <div>{pct:.0f}% financé</div>
                            <div>Reste : <b>{reste:,.0f} €</b></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Boutons d'action (discrets sous la carte)
                    c_act1, c_act2, c_void = st.columns([1, 1, 4])
                    if c_act1.button("✏️", key=f"btn_mod_{p_name}", help="Modifier le projet"):
                        st.session_state[f"edit_mode_{p_name}"] = True
                        st.rerun()
                    
                    if c_act2.button("🗑️", key=f"btn_del_{p_name}", help="Supprimer définitivement"):
                        del projets_config[p_name]
                        rows = []
                        for k, v in projets_config.items(): 
                            rows.append({"Projet": k, "Cible": v["Cible"], "Date_Fin": v["Date_Fin"], "Proprietaire": v.get("Proprietaire", "Commun")})
                        save_data(TAB_PROJETS, pd.DataFrame(rows))
                        st.success("Supprimé")
                        time.sleep(0.5)
                        st.rerun()

# ================= TAB 5: RÉGLAGES (DESIGN PRO) =================
with tabs[4]:
    page_header("Centre de Configuration")
    
    # On utilise des sous-onglets plus larges pour respirer
    c_tab1, c_tab2, c_tab3 = st.tabs(["🏷️ Catégories", "💳 Comptes", "⚡ Automatisation"])
    
    # --- 1. GESTION DES CATÉGORIES (VISUEL & FLUIDE) ---
    with c_tab1:
        st.markdown("### Organisez vos dépenses")
        
        # Zone d'ajout (Card)
        with st.container():
            st.markdown("""<div style="background:white; padding:20px; border-radius:12px; border:1px solid #E5E7EB; margin-bottom:20px;">
            <div style="font-weight:600; margin-bottom:10px;">Ajouter une catégorie</div>""", unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([2, 3, 1])
            type_add = c1.selectbox("Type de flux", TYPES, key="add_cat_type", label_visibility="collapsed")
            name_add = c2.text_input("Nom de la catégorie", placeholder="ex: Pharmacie, Cadeaux...", key="add_cat_name", label_visibility="collapsed")
            
            if c3.button("Créer", use_container_width=True, type="primary"):
                if name_add:
                    if name_add not in cats_memoire.get(type_add, []):
                        cats_memoire.setdefault(type_add, []).append(name_add)
                        save_config_cats(cats_memoire)
                        st.success("Ajouté !")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.warning("Existe déjà")
            st.markdown("</div>", unsafe_allow_html=True)

        # Zone de Visualisation & Suppression (2 Colonnes)
        col_dep, col_rev = st.columns(2)
        
        with col_dep:
            st.markdown("#### 📉 Dépenses & Charges")
            # Affichage en "Nuage de tags" simulé
            cats_dep = cats_memoire.get("Dépense", [])
            if cats_dep:
                html_badges = ""
                for c in cats_dep:
                    html_badges += f'<span class="cat-badge depense">{c}</span>'
                st.markdown(html_badges, unsafe_allow_html=True)
            
            st.write("")
            # Suppression Dépenses
            to_del_dep = st.multiselect("Supprimer des catégories Dépense", cats_dep, placeholder="Choisir pour supprimer...")
            if to_del_dep:
                if st.button("🗑️ Confirmer suppression (Dépenses)", key="btn_del_dep"):
                    for c in to_del_dep: cats_memoire["Dépense"].remove(c)
                    save_config_cats(cats_memoire)
                    st.rerun()

        with col_rev:
            st.markdown("#### 📈 Revenus & Épargne")
            # Concaténation des autres types
            cats_other = cats_memoire.get("Revenu", []) + cats_memoire.get("Épargne", [])
            if cats_other:
                html_badges = ""
                for c in cats_other:
                    # Couleur selon le type (approximatif pour l'affichage groupé)
                    style = "revenu" if c in cats_memoire.get("Revenu", []) else "epargne"
                    html_badges += f'<span class="cat-badge {style}">{c}</span>'
                st.markdown(html_badges, unsafe_allow_html=True)
                
            st.write("")
            # Suppression Autres
            to_del_other = st.multiselect("Supprimer (Revenu/Épargne)", cats_other, placeholder="Choisir pour supprimer...")
            if to_del_other:
                if st.button("🗑️ Confirmer suppression (Autres)", key="btn_del_other"):
                    # On cherche dans quel type c'était
                    for c in to_del_other:
                        for t in ["Revenu", "Épargne", "Investissement"]:
                            if c in cats_memoire.get(t, []): cats_memoire[t].remove(c)
                    save_config_cats(cats_memoire)
                    st.rerun()

    # --- 2. GESTION DES COMPTES (STYLE CARTES) ---
    with c_tab2:
        st.markdown("### Vos Comptes Bancaires")
        
        # Formulaire d'ajout compact
        with st.expander("➕ Ouvrir un nouveau compte", expanded=False):
            with st.form("add_bank_account"):
                c1, c2, c3 = st.columns([3, 2, 2])
                n_acc = c1.text_input("Nom de la banque / Compte")
                t_acc = c2.selectbox("Type", TYPES_COMPTE)
                is_jt = c3.checkbox("Compte Commun ?")
                
                if st.form_submit_button("Ajouter ce compte", type="primary"):
                    target_user = "Commun" if is_jt else user_actuel
                    if n_acc not in comptes_structure.get(target_user, []):
                        comptes_structure.setdefault(target_user, []).append(n_acc)
                        comptes_types_map[n_acc] = t_acc
                        save_comptes_struct(comptes_structure, comptes_types_map)
                        st.success("Compte créé avec succès")
                        time.sleep(0.5)
                        st.rerun()
        
        st.write("")
        
        # Affichage des cartes de comptes
        my_accounts = comptes_structure.get(user_actuel, [])
        joint_accounts = comptes_structure.get("Commun", [])
        
        if my_accounts:
            st.caption(f"Comptes Personnels de {user_actuel}")
            for acc in my_accounts:
                c1, c2 = st.columns([4, 1])
                with c1:
                    icon = "💳" if comptes_types_map.get(acc) == "Courant" else "🐷"
                    st.markdown(f"""
                    <div style="padding:15px; background:white; border:1px solid #E5E7EB; border-radius:10px; display:flex; align-items:center; gap:15px;">
                        <div style="font-size:24px;">{icon}</div>
                        <div>
                            <div style="font-weight:700; color:#1F2937;">{acc}</div>
                            <div style="font-size:12px; color:#6B7280;">{comptes_types_map.get(acc, 'Courant')}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    st.write("") # Spacer
                    if st.button("Suppr.", key=f"del_acc_{acc}"):
                        comptes_structure[user_actuel].remove(acc)
                        save_comptes_struct(comptes_structure, comptes_types_map)
                        st.rerun()
                        
        if joint_accounts:
            st.write("")
            st.caption("Comptes Communs")
            for acc in joint_accounts:
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"""
                    <div style="padding:15px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; display:flex; align-items:center; gap:15px;">
                        <div style="font-size:24px;">🤝</div>
                        <div>
                            <div style="font-weight:700; color:#1F2937;">{acc}</div>
                            <div style="font-size:12px; color:#6B7280;">Compte Joint • {comptes_types_map.get(acc, 'Courant')}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    st.write("")
                    if st.button("Suppr.", key=f"del_joint_{acc}"):
                        comptes_structure["Commun"].remove(acc)
                        save_comptes_struct(comptes_structure, comptes_types_map)
                        st.rerun()

    # --- 3. AUTOMATISATION (DATA EDITOR PUISSANT) ---
    with c_tab3:
        st.markdown("### ⚡ Mots-clés Automatiques")
        st.caption("Définissez des règles : si le titre contient 'X', alors Catégorie = 'Y'.")
        
        # Préparation des données pour l'éditeur
        # On transforme le dict en liste de dicts pour le DataFrame
        data_rules = []
        for kw, details in mots_cles_map.items():
            data_rules.append({
                "Mot-Clé (déclencheur)": kw,
                "Catégorie": details["Categorie"],
                "Compte": details["Compte"],
                "Type": details["Type"]
            })
        
        df_rules = pd.DataFrame(data_rules)
        
        # Configuration des colonnes pour l'éditeur
        all_cats_flat = [c for sublist in cats_memoire.values() for c in sublist]
        
        edited_df = st.data_editor(
            df_rules,
            num_rows="dynamic", # Permet d'ajouter des lignes directement !
            column_config={
                "Mot-Clé (déclencheur)": st.column_config.TextColumn(required=True),
                "Catégorie": st.column_config.SelectboxColumn(options=all_cats_flat, required=True),
                "Type": st.column_config.SelectboxColumn(options=TYPES, required=True),
                "Compte": st.column_config.SelectboxColumn(options=comptes_disponibles, required=True)
            },
            use_container_width=True,
            key="editor_rules"
        )
        
        # Bouton de sauvegarde globale des règles
        if st.button("💾 Sauvegarder les règles", type="primary"):
            # On reconstruit le dictionnaire à partir du DataFrame édité
            new_map = {}
            for _, row in edited_df.iterrows():
                if row["Mot-Clé (déclencheur)"]: # On évite les lignes vides
                    new_map[row["Mot-Clé (déclencheur)"].lower()] = {
                        "Categorie": row["Catégorie"],
                        "Type": row["Type"],
                        "Compte": row["Compte"]
                    }
            
            # Sauvegarde
            mots_cles_map = new_map
            save_mots_cles(mots_cles_map)
            st.success("Règles mises à jour avec succès !")
            time.sleep(1)
            st.rerun()


