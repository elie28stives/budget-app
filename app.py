import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import io
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
IMPUTATIONS = ["Perso", "Commun (50/50)", "Commun (Autre %)", "Avance/Cadeau"]
FREQUENCES = ["Mensuel", "Annuel", "Trimestriel", "Hebdomadaire"]
TYPES_COMPTE = ["Courant", "Épargne"]
MOIS_FR = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

# --- STYLE CSS (DESIGN SYSTEM PRO) ---
def apply_custom_style():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        :root {
            --primary: #DA7756;
            --primary-hover: #C56243;
            --bg-page: #F8F9FA;
            --bg-card: #FFFFFF;
            --text-main: #1F2937;
            --text-sub: #6B7280;
            --border: #E5E7EB;
        }
        .stApp { background-color: white; font-family: 'Inter', sans-serif; color: var(--text-main); }
        .main .block-container { padding-top: 1rem !important; padding-left: 2rem !important; padding-right: 2rem !important; max-width: 100%; }
        #MainMenu, footer, header {visibility: hidden;}
        .stTabs [data-baseweb="tab-list"] { gap: 20px; border-bottom: 1px solid #E0E0E0; }
        .stTabs [data-baseweb="tab"] { height: 50px; background-color: transparent; border: none; color: var(--text-sub); font-weight: 600; font-size: 14px; text-transform: uppercase; }
        .stTabs [aria-selected="true"] { color: var(--primary) !important; border-bottom: 3px solid var(--primary) !important; }
        div[data-testid="stMetric"], div.stDataFrame, div.stForm, div.block-container > div { border: 1px solid #E0E0E0 !important; border-radius: 8px !important; box-shadow: none !important; }
        section[data-testid="stSidebar"] { background-color: #F8F9FA; border-right: 1px solid #E0E0E0; }
        div.stButton > button { background-color: var(--primary) !important; color: white !important; border-radius: 4px; font-weight: 600; border: none; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

def page_header(title):
    st.markdown(f"<h2 style='font-size:22px; font-weight:400; color:#202124; margin-bottom:20px;'>{title}</h2>", unsafe_allow_html=True)

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

@st.cache_data(ttl=600)
def load_data_from_sheet(tab_name, colonnes):
    client = get_gspread_client()
    if not client: return pd.DataFrame(columns=colonnes)
    ws = get_worksheet(client, SHEET_NAME, tab_name)
    df = pd.DataFrame(ws.get_all_records())
    if df.empty: return pd.DataFrame(columns=colonnes)
    if "Date" in df.columns: df["Date"] = pd.to_datetime(df["Date"], errors='coerce').dt.date
    return df

@st.cache_data(ttl=600)
def load_configs_cached():
    return (load_data_from_sheet(TAB_CONFIG, ["Type", "Categorie"]), load_data_from_sheet(TAB_COMPTES, ["Proprietaire", "Compte", "Type"]), load_data_from_sheet(TAB_OBJECTIFS, ["Scope", "Categorie", "Montant"]), load_data_from_sheet(TAB_ABONNEMENTS, ["Nom", "Montant", "Jour", "Categorie", "Compte_Source", "Proprietaire", "Imputation", "Frequence"]), load_data_from_sheet(TAB_PROJETS, ["Projet", "Cible", "Date_Fin"]))

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

# --- CALCULS ---
def calculer_soldes_reels(df_transac, df_patri, comptes_list):
    soldes = {}
    for compte in comptes_list:
        releve, date_releve = 0.0, pd.to_datetime("2000-01-01").date()
        if not df_patri.empty:
            df_c = df_patri[df_patri["Compte"] == compte]
            if not df_c.empty:
                last = df_c.sort_values(by="Date", ascending=False).iloc[0]
                releve, date_releve = float(last["Montant"]), last["Date"]
        if not df_transac.empty:
            df_t = df_transac[df_transac["Date"] > date_releve]
            in_val = df_t[(df_t["Compte_Source"] == compte) & (df_t["Type"] == "Revenu")]["Montant"].sum() + df_t[(df_t["Compte_Cible"] == compte) & (df_t["Type"].isin(["Virement Interne", "Épargne"]))]["Montant"].sum()
            out_val = df_t[(df_t["Compte_Source"] == compte) & (df_t["Type"].isin(["Dépense", "Investissement", "Virement Interne", "Épargne"]))]["Montant"].sum()
            soldes[compte] = releve + in_val - out_val
        else: soldes[compte] = releve
    return soldes

def process_configs():
    df_cats, df_comptes, df_objs, df_abos, df_projets = load_configs_cached()
    cats = {k: [] for k in TYPES}
    if not df_cats.empty:
        for _, row in df_cats.iterrows():
            if row["Type"] in cats: cats[row["Type"]].append(row["Categorie"])
    comptes, c_types = {}, {}
    if not df_comptes.empty:
        for _, row in df_comptes.iterrows():
            if row["Proprietaire"] not in comptes: comptes[row["Proprietaire"]] = []
            comptes[row["Proprietaire"]].append(row["Compte"])
            c_types[row["Compte"]] = row.get("Type", "Courant")
    return cats, comptes, df_objs.to_dict('records'), df_abos, projects_data := {r["Projet"]: {"Cible": float(r["Cible"]), "Date_Fin": r["Date_Fin"]} for _, r in df_projets.iterrows()}, c_types

# --- APP START ---
st.set_page_config(page_title="Ma Banque Pro", layout="wide", page_icon="🏦", initial_sidebar_state="expanded")
apply_custom_style()

df = load_data_from_sheet(TAB_DATA, ["Date", "Mois", "Annee", "Qui_Connecte", "Type", "Categorie", "Titre", "Description", "Montant", "Paye_Par", "Imputation", "Compte_Cible", "Projet_Epargne", "Compte_Source"])
df_patrimoine = load_data_from_sheet(TAB_PATRIMOINE, ["Date", "Mois", "Annee", "Compte", "Montant", "Proprietaire"])
cats_memoire, comptes_structure, objectifs_list, df_abonnements, projets_config, comptes_types_map = process_configs()
all_accounts = [c for l in comptes_structure.values() for c in l] + ["Autre / Externe"]
SOLDES_ACTUELS = calculer_soldes_reels(df, df_patrimoine, list(set(all_accounts)))

with st.sidebar:
    st.markdown("### Menu")
    user_actuel = st.selectbox("Utilisateur", USERS)
    st.markdown("---")
    tc = sum(SOLDES_ACTUELS.get(c,0) for c in (comptes_structure.get(user_actuel,[]) + comptes_structure.get("Commun",[])) if comptes_types_map.get(c)=="Courant")
    te = sum(SOLDES_ACTUELS.get(c,0) for c in (comptes_structure.get(user_actuel,[]) + comptes_structure.get("Commun",[])) if comptes_types_map.get(c)=="Épargne")
    st.metric("Total Courant", f"{tc:,.0f} €")
    st.metric("Total Épargne", f"{te:,.0f} €")
    st.markdown("---")
    mois_nom = st.selectbox("Mois", MOIS_FR, index=datetime.now().month-1)
    annee_selection = st.number_input("Année", value=datetime.now().year)
    mois_selection = MOIS_FR.index(mois_nom) + 1
    if st.button("Actualiser", use_container_width=True): clear_cache(); st.rerun()

df_mois = df[(df["Mois"] == mois_selection) & (df["Annee"] == annee_selection)]
tabs = st.tabs(["Synthèse", "Transactions", "Analyse & Budget", "Patrimoine", "Configuration"])

# 1. SYNTHESE (RESTE A VIVRE AJOUTÉ)
with tabs[0]:
    page_header(f"Bilan {mois_nom} {annee_selection}")
    rev = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Revenu")]["Montant"].sum()
    dep_perso = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Dépense") & (df_mois["Imputation"] == "Perso")]["Montant"].sum()
    part_com = df_mois[df_mois["Imputation"] == "Commun (50/50)"]["Montant"].sum() / 2
    
    # CALCUL RESTE A VIVRE
    abos_prevus = df_abonnements[(df_abonnements["Proprietaire"] == user_actuel) | (df_abonnements["Imputation"]=="Commun (50/50)")]["Montant"].sum()
    reste_a_vivre = rev - (dep_perso + part_com)
    
    c1, c2, c3 = st.columns([1, 1, 2])
    c1.metric("Entrées", f"{rev:,.0f} €")
    c2.metric("Sorties", f"{dep_perso + part_com:,.0f} €")
    with c3:
        st.markdown(f"**Reste à vivre : {reste_a_vivre:,.0f} €**")
        st.progress(max(0, min(1.0, reste_a_vivre/rev if rev > 0 else 0)))
        st.caption("Argent disponible après toutes dépenses et part commune.")

# 2. TRANSACTIONS (EXPORT EXCEL AJOUTÉ)
with tabs[1]:
    st.subheader("Journal & Saisie")
    with st.expander("Nouvelle Transaction"):
        with st.form("new_t"):
            col1, col2, col3 = st.columns(3)
            d_ = col1.date_input("Date")
            t_ = col2.selectbox("Type", TYPES)
            m_ = col3.number_input("Montant €")
            tit_ = st.text_input("Titre")
            if st.form_submit_button("Enregistrer"):
                new_row = {"Date": d_, "Mois": d_.month, "Annee": d_.year, "Qui_Connecte": user_actuel, "Type": t_, "Categorie": "Autre", "Titre": tit_, "Description": "", "Montant": m_, "Paye_Par": user_actuel, "Imputation": "Perso", "Compte_Cible": "", "Projet_Epargne": "", "Compte_Source": ""}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True); save_data_to_sheet(TAB_DATA, df); st.rerun()
    
    search = st.text_input("Rechercher...")
    df_f = df_mois[df_mois.apply(lambda r: search.lower() in str(r).lower(), axis=1)] if search else df_mois
    st.dataframe(df_f, use_container_width=True)
    
    # EXPORT EXCEL
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_f.to_excel(writer, index=False, sheet_name='Sheet1')
    st.download_button(label="Exporter en Excel", data=output.getvalue(), file_name=f"Budget_{mois_nom}_{annee_selection}.xlsx", mime="application/vnd.ms-excel")

# 3. ANALYSE (COMPARAISON M-1 AJOUTÉ)
with tabs[2]:
    page_header("Analyse & Performance")
    
    # CALCUL COMPARAISON M-1
    prev_month = (date(annee_selection, mois_selection, 1) - relativedelta(months=1))
    df_prev = df[(df["Mois"] == prev_month.month) & (df["Annee"] == prev_month.year)]
    dep_now = df_mois[df_mois["Type"]=="Dépense"]["Montant"].sum()
    dep_prev = df_prev[df_prev["Type"]=="Dépense"]["Montant"].sum()
    
    diff = dep_now - dep_prev
    st.metric("Évolution vs mois dernier", f"{dep_now:,.0f} €", delta=f"{diff:,.0f} €", delta_color="inverse")

    st.subheader("Détail par catégorie")
    if not df_mois.empty:
        fig = px.bar(df_mois[df_mois["Type"]=="Dépense"].groupby("Categorie")["Montant"].sum().reset_index(), x="Categorie", y="Montant", color_discrete_sequence=['#DA7756'])
        st.plotly_chart(fig, use_container_width=True)

# 4. PATRIMOINE
with tabs[3]:
    page_header("Projets & Relevés")
    for p, d in projets_config.items():
        saved = df[(df["Projet_Epargne"] == p) & (df["Type"] == "Épargne")]["Montant"].sum() if not df.empty else 0
        st.write(f"**{p}** ({saved:.0f} / {d['Cible']:.0f} €)")
        st.progress(min(1.0, saved/d['Cible'] if d['Cible']>0 else 0))

# 5. CONFIG
with tabs[4]:
    page_header("Paramètres")
    st.write("Gérez vos comptes et catégories via le Google Sheet directement ou via les formulaires de saisie.")
