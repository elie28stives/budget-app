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
TAB_MOTS_CLES = "Mots_Cles"

USERS = ["Pierre", "Elie"]
TYPES = ["Dépense", "Revenu", "Virement Interne", "Épargne", "Investissement"]
IMPUTATIONS = ["Perso", "Commun (50/50)", "Commun (Autre %)", "Avance/Cadeau"]
FREQUENCES = ["Mensuel", "Annuel", "Trimestriel", "Hebdomadaire"]
TYPES_COMPTE = ["Courant", "Épargne"]
MOIS_FR = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

# --- DEFINITION VARIABLES GLOBALES ---
COLS_DATA = ["Date", "Mois", "Annee", "Qui_Connecte", "Type", "Categorie", "Titre", "Description", "Montant", "Paye_Par", "Imputation", "Compte_Cible", "Projet_Epargne", "Compte_Source"]
COLS_PAT = ["Date", "Mois", "Annee", "Compte", "Montant", "Proprietaire"]

# --- STYLE CSS (REVOLUT-INSPIRED, SANS EMOJIS) ---
def apply_custom_style():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        :root {
            --primary: #FF6B35;
            --primary-dark: #E55A2B;
            --bg-main: #F5F7FA;
            --bg-card: #FFFFFF;
            --text-primary: #0A1929;
            --text-secondary: #6B7280;
            --border: #E5E7EB;
        }

        .stApp {
            background: var(--bg-main);
            font-family: 'Inter', sans-serif;
            color: var(--text-primary);
        }
        
        .main .block-container {
            padding: 2rem 3rem !important;
            max-width: 1400px;
        }
        
        #MainMenu, footer, header {visibility: hidden;}

        /* TABS */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0;
            background: var(--bg-card);
            border-radius: 12px;
            padding: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
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
        }
        .stTabs [aria-selected="true"] {
            background: var(--primary) !important;
            color: white !important;
        }

        /* CARDS */
        div[data-testid="stMetric"] {
            background: var(--bg-card);
            padding: 20px;
            border-radius: 16px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }

        /* SIDEBAR */
        section[data-testid="stSidebar"] {
            background: var(--bg-card);
            border-right: 1px solid var(--border);
        }

        /* BOUTONS */
        div.stButton > button {
            background: var(--primary) !important;
            color: white !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            border: none !important;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
        }
        
        /* FORMULAIRES */
        div.stForm {
            background: var(--bg-card);
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
    </style>
    """, unsafe_allow_html=True)

def page_header(title, subtitle=None):
    if subtitle:
        st.markdown(f"""<div style="margin-bottom: 2rem;"><h2 style='font-size:32px; font-weight:800; color:#0A1929; margin-bottom:8px;'>{title}</h2><p style='font-size:16px; color:#6B7280; font-weight:500;'>{subtitle}</p></div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"<h2 style='font-size:32px; font-weight:800; color:#0A1929; margin-bottom:2rem;'>{title}</h2>", unsafe_allow_html=True)

# --- CONNEXION ---
@st.cache_resource
def get_gspread_client():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_dict: creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        return gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]))
    except Exception as e:
        st.error(f"Erreur technique : {e}"); return None

def get_worksheet(client, sheet_name, tab_name):
    sh = client.open(sheet_name)
    try: return sh.worksheet(tab_name)
    except: return sh.add_worksheet(title=tab_name, rows="100", cols="20")

# --- DATA ---
@st.cache_data(ttl=600)
def load_data_from_sheet(tab_name, colonnes):
    client = get_gspread_client()
    if not client: return pd.DataFrame(columns=colonnes)
    ws = get_worksheet(client, SHEET_NAME, tab_name)
    df = pd.DataFrame(ws.get_all_records())
    if df.empty: return pd.DataFrame(columns=colonnes)
    if "Date" in df.columns: df["Date"] = pd.to_datetime(df["Date"], errors='coerce').dt.date
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

def process_configs():
    data = (
        load_data_from_sheet(TAB_CONFIG, ["Type", "Categorie"]),
        load_data_from_sheet(TAB_COMPTES, ["Proprietaire", "Compte", "Type"]),
        load_data_from_sheet(TAB_OBJECTIFS, ["Scope", "Categorie", "Montant"]),
        load_data_from_sheet(TAB_ABONNEMENTS, ["Nom", "Montant", "Jour", "Categorie", "Compte_Source", "Proprietaire", "Imputation", "Frequence"]),
        load_data_from_sheet(TAB_PROJETS, ["Projet", "Cible", "Date_Fin"]),
        load_data_from_sheet(TAB_MOTS_CLES, ["Mot_Cle", "Categorie", "Type", "Compte"])
    )
    
    cats = {k: [] for k in TYPES}
    if not data[0].empty:
        for _, r in data[0].iterrows():
            if r["Type"] in cats and r["Categorie"] not in cats[r["Type"]]: cats[r["Type"]].append(r["Categorie"])
            
    comptes, c_types = {}, {}
    if not data[1].empty:
        for _, r in data[1].iterrows():
            if r["Proprietaire"] not in comptes: comptes[r["Proprietaire"]] = []
            comptes[r["Proprietaire"]].append(r["Compte"])
            c_types[r["Compte"]] = r.get("Type", "Courant")
            
    projets = {}
    if not data[4].empty:
        for _, r in data[4].iterrows(): projets[r["Projet"]] = {"Cible": float(r["Cible"]), "Date_Fin": r["Date_Fin"]}
        
    mots = {r["Mot_Cle"].lower(): {"Categorie": r["Categorie"], "Type": r["Type"], "Compte": r["Compte"]} for _, r in data[5].iterrows()} if not data[5].empty else {}
    
    return cats, comptes, data[2].to_dict('records'), data[3], projets, c_types, mots

def calculer_soldes_reels(df_transac, df_patri, comptes_list):
    soldes = {}
    for compte in comptes_list:
        releve, date_releve = 0.0, pd.to_datetime("2000-01-01").date()
        if not df_patri.empty:
            df_c = df_patri[df_patri["Compte"] == compte]
            if not df_c.empty:
                last = df_c.sort_values(by="Date", ascending=False).iloc[0]
                releve, date_releve = float(last["Montant"]), last["Date"]
        mouv = 0.0
        if not df_transac.empty:
            df_t = df_transac[df_transac["Date"] > date_releve]
            debits = df_t[(df_t["Compte_Source"] == compte) & (df_t["Type"].isin(["Dépense", "Investissement"]))]["Montant"].sum()
            v_out = df_t[(df_t["Compte_Source"] == compte) & (df_t["Type"].isin(["Virement Interne", "Épargne"]))]["Montant"].sum()
            credits = df_t[(df_t["Compte_Source"] == compte) & (df_t["Type"] == "Revenu")]["Montant"].sum()
            v_in = df_t[(df_t["Compte_Cible"] == compte) & (df_t["Type"].isin(["Virement Interne", "Épargne"]))]["Montant"].sum()
            mouv = credits + v_in - debits - v_out
        soldes[compte] = releve + mouv
    return soldes

def to_excel_download(df):
    output = BytesIO()
    df_export = df.copy()
    if "Date" in df_export.columns: df_export["Date"] = df_export["Date"].astype(str)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Transactions')
    return output.getvalue()

# Fonctions de sauvegarde
def save_config_cats(d): save_data_to_sheet(TAB_CONFIG, pd.DataFrame([{"Type": t, "Categorie": c} for t, l in d.items() for c in l]))
def save_comptes_struct(d, types_map): 
    rows = []
    for p, l in d.items():
        for c in l: rows.append({"Proprietaire": p, "Compte": c, "Type": types_map.get(c, "Courant")})
    save_data_to_sheet(TAB_COMPTES, pd.DataFrame(rows))
def save_objectifs_from_df(df_obj): save_data_to_sheet(TAB_OBJECTIFS, df_obj)
def save_abonnements(df): save_data_to_sheet(TAB_ABONNEMENTS, df)
def save_projets_targets(d): 
    rows = []
    for p, data in d.items(): rows.append({"Projet": p, "Cible": data["Cible"], "Date_Fin": data["Date_Fin"]})
    save_data_to_sheet(TAB_PROJETS, pd.DataFrame(rows))
def save_mots_cles(d):
    rows = []
    for mc, data in d.items(): rows.append({"Mot_Cle": mc, "Categorie": data["Categorie"], "Type": data["Type"], "Compte": data["Compte"]})
    save_data_to_sheet(TAB_MOTS_CLES, pd.DataFrame(rows))

# --- APP START ---
st.set_page_config(page_title="Ma Banque V63", layout="wide", page_icon=None)
apply_custom_style()

# Chargement données
df = load_data_from_sheet(TAB_DATA, COLS_DATA)
df_patrimoine = load_data_from_sheet(TAB_PATRIMOINE, COLS_PAT)
cats_memoire, comptes_structure, objectifs_list, df_abonnements, projets_config, comptes_types_map, mots_cles_map = process_configs()

# --- SIDEBAR (Menu) ---
with st.sidebar:
    st.markdown("### Menu")
    user_actuel = st.selectbox("Utilisateur", USERS)
    
    st.markdown("---")
    comptes_user = comptes_structure.get(user_actuel, []) + comptes_structure.get("Commun", [])
    comptes_disponibles = list(set(comptes_user + ["Autre / Externe"]))
    soldes = calculer_soldes_reels(df, df_patrimoine, comptes_disponibles)
    
    total_courant = 0
    total_epargne = 0
    
    st.markdown("**COMPTES COURANTS**")
    for cpt in comptes_user:
        if comptes_types_map.get(cpt) == "Courant":
            val = soldes.get(cpt, 0.0)
            total_courant += val
            col = "green" if val >= 0 else "red"
            st.markdown(f"{cpt}<br><span style='color:{col}; font-weight:bold;'>{val:,.2f} €</span>", unsafe_allow_html=True)
            st.write("")
            
    st.markdown("**EPARGNE**")
    for cpt in comptes_user:
        if comptes_types_map.get(cpt) == "Épargne":
            val = soldes.get(cpt, 0.0)
            total_epargne += val
            st.markdown(f"{cpt}<br><span style='color:#2980B9; font-weight:bold;'>{val:,.2f} €</span>", unsafe_allow_html=True)
            st.write("")

    st.markdown("---")
    date_jour = datetime.now()
    mois_nom = st.selectbox("Mois", MOIS_FR, index=date_jour.month-1)
    mois_selection = MOIS_FR.index(mois_nom) + 1
    annee_selection = st.number_input("Année", value=date_jour.year)
    df_mois = df[(df["Mois"] == mois_selection) & (df["Annee"] == annee_selection)]
    
    st.markdown("---")
    if st.button("Actualiser", use_container_width=True): st.cache_data.clear(); st.rerun()

# --- TABS PRINCIPAUX ---
tabs = st.tabs(["Accueil", "Opérations", "Analyses", "Patrimoine", "Réglages"])

# 1. ACCUEIL
with tabs[0]:
    page_header(f"Synthèse - {mois_nom}", f"Compte de {user_actuel}")
    
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
    rav_col = "#10B981" if rav > 0 else "#EF4444"
    rav_gradient = "linear-gradient(135deg, #10B981 0%, #059669 100%)" if rav > 0 else "linear-gradient(135deg, #EF4444 0%, #DC2626 100%)"
    
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Revenus", f"{rev:,.0f} €")
    k2.metric("Charges Fixes", f"{charges_fixes:,.0f} €")
    k3.metric("Dépenses Variables", f"{(dep+com):,.0f} €")
    k4.metric("Epargne", f"{epg:,.0f} €")
    k5.markdown(f"""<div style="background: {rav_gradient}; border-radius: 16px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); position: relative; overflow: hidden; color:white; text-align:center;"><div style="font-size:12px; font-weight:600; text-transform:uppercase;">RESTE À VIVRE</div><div style="font-size:32px; font-weight:800;">{rav:,.0f} €</div></div>""", unsafe_allow_html=True)
    
    st.markdown("---")
    
    c1, c2 = st.columns(
