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

# Définition des colonnes pour éviter les erreurs de chargement
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
            --primary: #2C3E50;       /* Bleu Nuit Profond */
            --primary-light: #34495E; /* Gris Bleu */
            --accent: #2980B9;        /* Bleu Action */
            --bg-main: #F4F6F8;       /* Gris très clair pro */
            --bg-card: #FFFFFF;
            --text-primary: #1A1C1E;
            --text-secondary: #6B7280;
            --border: #E5E7EB;
            --success: #10B981;
            --danger: #EF4444;
        }

        .stApp {
            background-color: var(--bg-main);
            font-family: 'Inter', sans-serif;
            color: var(--text-primary);
        }
        
        /* FULL WIDTH - UTILISATION MAXIMALE DE L'ECRAN */
        .main .block-container {
            padding-top: 2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 100% !important;
        }
        
        #MainMenu, footer, header {visibility: hidden;}

        /* --- TABS STYLE --- */
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
            transition: color 0.2s;
        }
        
        .stTabs [aria-selected="true"] {
            color: var(--primary) !important;
            border-bottom: 3px solid var(--primary) !important;
        }

        /* --- CARDS & CONTAINERS --- */
        div[data-testid="stMetric"], div.stDataFrame, div.stForm, div[data-testid="stExpander"] {
            background-color: var(--bg-card);
            padding: 24px;
            border-radius: 12px;
            border: 1px solid var(--border) !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }
        
        /* --- SIDEBAR --- */
        section[data-testid="stSidebar"] {
            background-color: var(--bg-card);
            border-right: 1px solid var(--border);
        }
        
        section[data-testid="stSidebar"] h3 {
            color: var(--primary);
            font-size: 18px;
            font-weight: 700;
        }

        /* --- BOUTONS --- */
        div.stButton > button {
            background-color: var(--primary) !important;
            color: white !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
            font-size: 14px !important;
            border: none !important;
            padding: 10px 24px !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
            transition: all 0.2s ease;
        }
        
        div.stButton > button:hover {
            background-color: var(--primary-light) !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        }
        
        /* --- INPUTS --- */
        .stTextInput input, .stNumberInput input, .stSelectbox > div > div {
            border-radius: 8px !important;
            border-color: var(--border) !important;
            background-color: #FFFFFF !important;
            color: var(--text-primary) !important;
        }

        /* --- TEXTE --- */
        h1, h2, h3 { 
            color: var(--text-primary) !important; 
            font-family: 'Inter', sans-serif !important; 
            font-weight: 700 !important;
        }
        
        /* --- TABLEAUX --- */
        .stDataFrame { 
            border: 1px solid var(--border); 
            border-radius: 8px; 
        }
    </style>
    """, unsafe_allow_html=True)

def page_header(title, subtitle=None):
    if subtitle:
        st.markdown(f"""
        <div style="margin-bottom: 25px;">
            <h2 style='font-size:28px; font-weight:700; color:#2C3E50; margin-bottom:6px;'>{title}</h2>
            <p style='font-size:15px; color:#6B7280; font-weight:400;'>{subtitle}</p>
        </div>
        """, unsafe_allow_html=True)
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
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Erreur technique de connexion : {e}")
        return None

def get_worksheet(client, sheet_name, tab_name):
    try:
        sh = client.open(sheet_name)
        try: ws = sh.worksheet(tab_name)
        except: ws = sh.add_worksheet(title=tab_name, rows="100", cols="20")
        return ws
    except Exception as e:
        st.error(f"Erreur d'accès à l'onglet {tab_name} : {e}"); st.stop()

# ==========================================
# 4. GESTION DES DONNÉES (CACHE & LOAD)
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
    # Chargement en bloc pour gagner du temps et de la performance
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
    # Traitement des données chargées
    data = load_configs_cached()
    df_cats, df_comptes, df_objs, df_abos, df_projets, df_mots_cles = data
    
    cats = {k: [] for k in TYPES}
    if not df_cats.empty:
        for _, row in df_cats.iterrows():
            if row["Type"] in cats and row["Categorie"] not in cats[row["Type"]]:
                cats[row["Type"]].append(row["Categorie"])
    if not cats["Dépense"]: # Valeurs par défaut si vide
        cats["Dépense"] = ["Alimentation", "Loyer", "Autre"]
        
    comptes = {"Pierre": [], "Elie": [], "Commun": []}
    comptes_types = {}
    if not df_comptes.empty:
        for _, row in df_comptes.iterrows():
            if row["Proprietaire"] not in comptes: comptes[row["Proprietaire"]] = []
            comptes[row["Proprietaire"]].append(row["Compte"])
            c_type = row.get("Type", "Courant")
            if not c_type: c_type = "Courant"
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

# Fonctions de sauvegarde spécifiques
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
# 6. APPLICATION STREAMLIT (LE CŒUR)
# ==========================================

st.set_page_config(page_title="Banque", layout="wide", page_icon=None)
apply_custom_style()

# Chargement initial des données
df = load_data_from_sheet(TAB_DATA, COLS_DATA)
df_patrimoine = load_data_from_sheet(TAB_PATRIMOINE, COLS_PAT)
cats_memoire, comptes_structure, objectifs_list, df_abonnements, projets_config, comptes_types_map, mots_cles_map = process_configs()

# --- SIDEBAR (MENU & FILTRES) ---
with st.sidebar:
    st.markdown("### Menu Principal")
    user_actuel = st.selectbox("Utilisateur", USERS)
    
    st.markdown("---")
    
    # ---------------------------------------------------------
    # CALCUL CENTRALISÉ DES COMPTES (CORRECTION BUG V66.1)
    # ---------------------------------------------------------
    # On filtre les comptes visibles pour l'utilisateur connecté
    comptes_user_only = comptes_structure.get(user_actuel, [])
    comptes_communs = comptes_structure.get("Commun", [])
    
    # Liste pour les menus déroulants (uniquement ce que je peux voir)
    comptes_visibles = comptes_user_only + comptes_communs
    
    # Liste pour les calculs internes (inclut les comptes externes/autres)
    comptes_disponibles = list(set(comptes_visibles + ["Autre / Externe"]))
    
    # Calcul des soldes en temps réel
    soldes = calculer_soldes_reels(df, df_patrimoine, comptes_disponibles)
    
    total_courant = 0
    total_epargne = 0
    list_courant = []
    list_epargne = []
    
    for cpt in comptes_visibles:
        val = soldes.get(cpt, 0.0)
        ctype = comptes_types_map.get(cpt, "Courant")
        if ctype == "Épargne": 
            total_epargne += val
            list_epargne.append((cpt, val))
        else: 
            total_courant += val
            list_courant.append((cpt, val))

    # Fonction d'affichage des mini-cartes
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

    st.markdown(f"**COMPTES COURANTS ({total_courant:,.0f}€)**")
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
    
    # Filtrage du DataFrame principal par date
    df_mois = df[(df["Mois"] == mois_selection) & (df["Annee"] == annee_selection)]

    st.markdown("---")
    if st.button("Actualiser les données", use_container_width=True): 
        clear_cache()
        st.rerun()

# --- STRUCTURE DES ONGLETS ---
tabs = st.tabs(["Accueil", "Opérations", "Analyses", "Patrimoine", "Réglages"])

# ==========================================
# TAB 1: ACCUEIL (DASHBOARD)
# ==========================================
with tabs[0]:
    page_header("Synthèse du mois", f"Vue d'ensemble pour {user_actuel}")
    
    # Calculs indicateurs
    rev = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Revenu")]["Montant"].sum()
    dep = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Dépense") & (df_mois["Imputation"] == "Perso")]["Montant"].sum()
    epg = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Épargne")]["Montant"].sum()
    com = df_mois[df_mois["Imputation"] == "Commun (50/50)"]["Montant"].sum() / 2
    
    # Calcul Reste à Vivre (avec Abonnements)
    charges_fixes = 0.0
    if not df_abonnements.empty:
        abos_user = df_abonnements[(df_abonnements["Proprietaire"] == user_actuel) | (df_abonnements["Imputation"].str.contains("Commun", na=False))]
        for _, row in abos_user.iterrows():
            charges_fixes += float(row["Montant"]) / (2 if "Commun" in str(row["Imputation"]) else 1)
    
    rav = rev - charges_fixes - dep - com
    
    # Couleurs dynamiques
    rav_gradient = "linear-gradient(135deg, #10B981 0%, #059669 100%)" if rav > 0 else "linear-gradient(135deg, #EF4444 0%, #DC2626 100%)"
    
    # Affichage des métriques
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
    
    # SECTION DU BAS : Dernières Transactions & Alertes
    c1, c2 = st.columns([3, 2])
    with c1:
        # En-tête avec titre et filtre sur la même ligne
        c_titre, c_filtre = st.columns([1, 1])
        with c_titre:
            st.subheader("Activités")
        with c_filtre:
            # Filtre horizontal compact
            filtre_tx = st.radio(
                "Filtre transactions", 
                ["Tout", "Sorties", "Entrées"], 
                horizontal=True, 
                label_visibility="collapsed",
                key="filtre_activite_home"
            )

        # 1. Récupération des transactions de l'utilisateur
        tx_data = df[df['Qui_Connecte'] == user_actuel].sort_values(by='Date', ascending=False)

        # 2. Application du filtre
        if filtre_tx == "Sorties":
            tx_data = tx_data[tx_data['Type'].isin(["Dépense", "Virement Interne", "Épargne", "Investissement"])]
        elif filtre_tx == "Entrées":
            tx_data = tx_data[tx_data['Type'] == "Revenu"]
        
        # 3. On garde les 5 dernières après filtrage
        recent = tx_data.head(5)
        
        # 4. Affichage style "Liste Bancaire" propre
        if not recent.empty:
            for _, r in recent.iterrows():
                # Détermination du style (Couleur et Signe)
                is_depense = r['Type'] in ["Dépense", "Virement Interne", "Épargne", "Investissement"]
                
                # Couleurs douces pour le fond de l'icône
                bg_icon = "#FFF1F2" if is_depense else "#ECFDF5"  # Rouge pastel / Vert pastel
                # Couleur du texte montant
                txt_color = "#E11D48" if is_depense else "#059669"
                signe = "-" if is_depense else "+"
                # Icône selon le type
                icon = "💸" if is_depense else "💰"
                if r['Type'] == "Épargne": icon = "🐷"
                if r['Type'] == "Virement Interne": icon = "🔄"

                # HTML Card pour un rendu parfait
                st.markdown(f"""
                <div style="
                    display: flex; 
                    align-items: center; 
                    justify-content: space-between; 
                    padding: 12px 0; 
                    border-bottom: 1px solid #F3F4F6;">
                    
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <div style="
                            width: 42px; 
                            height: 42px; 
                            border-radius: 10px; 
                            background-color: {bg_icon}; 
                            display: flex; 
                            align-items: center; 
                            justify-content: center; 
                            font-size: 20px;">
                            {icon}
                        </div>
                        <div>
                            <div style="font-weight: 600; color: #1F2937; font-size: 14px;">{r['Titre']}</div>
                            <div style="font-size: 12px; color: #9CA3AF;">{r['Date'].strftime('%d/%m')} • {r['Categorie']}</div>
                        </div>
                    </div>

                    <div style="font-weight: 700; font-size: 15px; color: {txt_color};">
                        {signe} {r['Montant']:,.2f} €
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            # Petit bouton discret pour voir tout
            if st.button("Voir tout l'historique", key="btn_see_all_home", use_container_width=True):
                # Astuce pour switcher d'onglet (nécessite de recharger ou de juste informer l'utilisateur)
                st.info("Allez dans l'onglet 'Opérations' pour voir l'historique complet.")
                
        else:
            st.info("Aucune transaction trouvée pour ce filtre.")
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
        
        if not has_alert:
            st.success("Aucune alerte. Budget maîtrisé !")

# ==========================================
# TAB 2: OPÉRATIONS (SAISIE, JOURNAL, ABOS)
# ==========================================
with tabs[1]:
    op1, op2, op3 = st.tabs(["Saisie", "Journal", "Abonnements"])
    
    # 1. SAISIE DE TRANSACTION
    with op1:
        with st.form("add_op"):
            c1, c2, c3 = st.columns(3)
            date_op = c1.date_input("Date", datetime.today(), key="d_op")
            type_op = c2.selectbox("Type", TYPES, key="t_op")
            montant_op = c3.number_input("Montant (€)", min_value=0.0, step=0.01, key="m_op")
            
            c4, c5 = st.columns(2)
            titre_op = c4.text_input("Titre", placeholder="Ex: Auchan", key="tit_op")
            
            # Logique Mots-Clés
            cat_finale = "Autre"
            compte_auto = None
            if titre_op and mots_cles_map:
                for mc, data in mots_cles_map.items():
                    if mc in titre_op.lower() and data["Type"] == type_op:
                        cat_finale = data["Categorie"]
                        compte_auto = data["Compte"]
                        break
            
            cats = cats_memoire.get(type_op, [])
            idx_cat = cats.index(cat_finale) if cat_finale in cats else 0
            cat_sel = c5.selectbox("Catégorie", cats + ["Autre"], index=idx_cat)
            
            st.write("")
            cc1, cc2, cc3 = st.columns(3)
            # Compte source
            idx_cpt = comptes_visibles.index(compte_auto) if (compte_auto and compte_auto in comptes_visibles) else 0
            c_src = cc1.selectbox("Compte", comptes_visibles, index=idx_cpt)
            imput = cc2.radio("Imputation", IMPUTATIONS, horizontal=True)
            
            # Champs conditionnels
            c_tgt = ""
            p_epg = ""
            paye_par = user_actuel
            
            if type_op == "Épargne":
                c_tgt = st.selectbox("Vers Compte Épargne", [c for c in comptes_visibles if comptes_types_map.get(c) == "Épargne"])
                p_sel = st.selectbox("Pour Projet", ["Aucun"] + list(projets_config.keys()))
                if p_sel != "Aucun": p_epg = p_sel
            elif type_op == "Virement Interne":
                c_tgt = st.selectbox("Vers Compte", comptes_visibles)
                imput = "Neutre"
            
            if st.form_submit_button("Valider la transaction"):
                new_row = {
                    "Date": date_op, "Mois": date_op.month, "Annee": date_op.year,
                    "Qui_Connecte": user_actuel, "Type": type_op, "Categorie": cat_sel,
                    "Titre": titre_op, "Description": "", "Montant": montant_op,
                    "Paye_Par": paye_par, "Imputation": imput, "Compte_Cible": c_tgt,
                    "Projet_Epargne": p_epg, "Compte_Source": c_src
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_data_to_sheet(TAB_DATA, df)
                st.success("Enregistré !")
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

    # 3. ABONNEMENTS
    with op3:
        st.subheader("Gestion des Abonnements")
        with st.expander("Ajouter un abonnement"):
            with st.form("new_abo"):
                a1, a2, a3 = st.columns(3)
                n = a1.text_input("Nom"); m = a2.number_input("Montant"); j = a3.number_input("Jour", 1, 31)
                a4, a5 = st.columns(2)
                c = a4.selectbox("Catégorie", cats_memoire.get("Dépense", [])); cp = a5.selectbox("Compte débité", comptes_visibles)
                if st.form_submit_button("Créer"):
                    new_abo = pd.DataFrame([{"Nom": n, "Montant": m, "Jour": j, "Categorie": c, "Compte_Source": cp, "Proprietaire": user_actuel, "Imputation": "Perso", "Frequence": "Mensuel"}])
                    df_abonnements = pd.concat([df_abonnements, new_abo], ignore_index=True)
                    save_abonnements(df_abonnements); st.rerun()
        
        # Liste
        if not df_abonnements.empty:
            my_abos = df_abonnements[df_abonnements["Proprietaire"] == user_actuel]
            if not my_abos.empty:
                for idx, r in my_abos.iterrows():
                    c1, c2, c3 = st.columns([3, 2, 1])
                    c1.write(f"**{r['Nom']}** ({r['Montant']}€)")
                    c2.write(f"Le {r['Jour']} du mois")
                    if c3.button("Suppr", key=f"del_abo_{idx}"):
                        df_abonnements = df_abonnements.drop(idx)
                        save_abonnements(df_abonnements)
                        st.rerun()

# ==========================================
# TAB 3: ANALYSES
# ==========================================
with tabs[2]:
    an1, an2 = st.tabs(["Vue Globale", "Équilibre Couple"])
    
    with an1:
        if not df_mois.empty:
            fig = px.pie(df_mois[df_mois["Type"]=="Dépense"], values="Montant", names="Categorie", title="Répartition des Dépenses", hole=0.5)
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
                
    with an2:
        df_c = df_mois[df_mois["Imputation"].str.contains("Commun", na=False)]
        pp = df_c[df_c["Paye_Par"]=="Pierre"]["Montant"].sum()
        ep = df_c[df_c["Paye_Par"]=="Elie"]["Montant"].sum()
        diff = (pp - ep)/2
        
        c1, c2 = st.columns(2)
        c1.metric("Pierre a payé", f"{pp:,.0f} €")
        c2.metric("Elie a payé", f"{ep:,.0f} €")
        
        if diff > 0: st.info(f"Elie doit {abs(diff):,.0f} € à Pierre")
        elif diff < 0: st.info(f"Pierre doit {abs(diff):,.0f} € à Elie")
        else: st.success("Comptes équilibrés")

# ==========================================
# TAB 4: PATRIMOINE (MES COMPTES)
# ==========================================
with tabs[3]:
    page_header("Mes Comptes & Patrimoine")
    
    # 1. Sélection de compte
    acc_choice = st.selectbox("Sélectionner un compte", comptes_visibles)
    
    # 2. Info Compte
    if acc_choice:
        solde_acc = soldes.get(acc_choice, 0.0)
        col_solde = "green" if solde_acc >= 0 else "red"
        st.markdown(f"## Solde : <span style='color:{col_solde}'>{solde_acc:,.2f} €</span>", unsafe_allow_html=True)
        
        # 3. Historique spécifique
        st.markdown("#### Historique des transactions")
        mask_acc = (df["Compte_Source"] == acc_choice) | (df["Compte_Cible"] == acc_choice)
        df_acc = df[mask_acc].sort_values(by="Date", ascending=False).head(10)
        
        if not df_acc.empty:
            st.dataframe(
                df_acc[["Date", "Titre", "Montant", "Type", "Categorie"]], 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                    "Montant": st.column_config.NumberColumn("Montant", format="%.2f €")
                }
            )
        else:
            st.info("Aucune transaction.")
            
    st.markdown("---")
    
    # Sous-onglets
    st1, st2 = st.tabs(["Épargne & Projets", "Relevés"])
    with st1:
        for p, d in projets_config.items():
            s = df[(df["Projet_Epargne"]==p)&(df["Type"]=="Épargne")]["Montant"].sum()
            t = float(d["Cible"])
            st.write(f"**{p}** : {s:.0f} / {t:.0f} €"); st.progress(min(s/t if t>0 else 0, 1.0))
        
        with st.expander("Nouveau Projet"):
            n = st.text_input("Nom", key="pn"); t = st.number_input("Cible", key="pt")
            if st.button("Créer", key="pb"): projets_config[n] = {"Cible": t, "Date_Fin": ""}; save_projets_targets(projets_config); st.rerun()

    with st2:
        with st.form("rel"):
            c1, c2 = st.columns(2); d = c1.date_input("Date"); m = st.number_input("Solde Réel")
            if st.form_submit_button("Enregistrer"):
                df_patrimoine = pd.concat([df_patrimoine, pd.DataFrame([{"Date": d, "Mois": d.month, "Annee": d.year, "Compte": acc_choice, "Montant": m, "Proprietaire": user_actuel}])], ignore_index=True); save_data_to_sheet(TAB_PATRIMOINE, df_patrimoine); st.rerun()

# ==========================================
# TAB 5: RÉGLAGES
# ==========================================
with tabs[4]:
    page_header("Réglages")
    
    # GESTION DES COMPTES
    st.subheader("Gestion des Comptes")
    with st.expander("Ajouter un compte", expanded=False):
        with st.form("add_cpt_clean"):
            c1, c2 = st.columns(2)
            n_new = c1.text_input("Nom du compte")
            t_new = c2.selectbox("Type", TYPES_COMPTE)
            is_comm = st.checkbox("Compte Commun ?")
            if st.form_submit_button("Valider"):
                p_new = "Commun" if is_comm else user_actuel
                if p_new not in comptes_structure: comptes_structure[p_new] = []
                comptes_structure[p_new].append(n_new)
                comptes_types_map[n_new] = t_new
                save_comptes_struct(comptes_structure, comptes_types_map)
                st.success("Compte ajouté")
                time.sleep(1)
                st.rerun()

    st.markdown("#### Vos comptes actifs")
    # Affiche uniquement les comptes que l'utilisateur a le droit de modifier (Les siens + Commun)
    props_to_show = [user_actuel, "Commun"]
    for prop in props_to_show:
        if prop in comptes_structure and comptes_structure[prop]:
            st.markdown(f"**{prop}**")
            for acc in comptes_structure[prop]:
                col_txt, col_btn = st.columns([4, 1])
                with col_txt: st.write(f"- {acc} ({comptes_types_map.get(acc, 'Courant')})")
                with col_btn:
                    if st.button("Supprimer", key=f"del_{acc}"):
                        comptes_structure[prop].remove(acc); save_comptes_struct(comptes_structure, comptes_types_map); st.rerun()

    st.markdown("---")
    t1, t2 = st.tabs(["Catégories", "Mots-Clés"])
    with t1:
        ty = st.selectbox("Type", TYPES, key="sc_type"); new_c = st.text_input("Nouvelle catégorie")
        if st.button("Ajouter"): cats_memoire.setdefault(ty, []).append(new_c); save_config_cats(cats_memoire); st.rerun()
    with t2:
        with st.form("amc"):
            # CORRECTION DE LA VARIABLE ICI
            all_categories = [c for l in cats_memoire.values() for c in l]
            
            m = st.text_input("Mot-clé"); c = st.selectbox("Catégorie", all_categories); ty = st.selectbox("Type", TYPES, key="tmc"); co = st.selectbox("Compte", comptes_disponibles)
            if st.form_submit_button("Lier"): mots_cles_map[m.lower()] = {"Categorie":c,"Type":ty,"Compte":co}; save_mots_cles(mots_cles_map); st.rerun()


