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

# --- STYLE CSS (PAYPAL / FINTECH STYLE) ---
def apply_custom_style():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=PayPal+Sans:wght@300;400;500;700&family=Inter:wght@400;600&display=swap');
        
        :root {
            --pp-blue: #003087; /* PayPal Dark Blue */
            --pp-light-blue: #0070BA; /* PayPal Action Blue */
            --bg-body: #F5F7FA;
            --bg-card: #FFFFFF;
            --text-dark: #2C2E2F;
            --text-grey: #6C7378;
            --radius: 12px;
        }

        .stApp {
            background-color: var(--bg-body);
            font-family: 'Inter', sans-serif;
            color: var(--text-dark);
        }
        
        /* FULL WIDTH FIX */
        .main .block-container {
            padding-top: 1rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 100% !important;
        }
        
        #MainMenu, footer, header {visibility: hidden;}

        /* --- NAVIGATION BAR STYLE --- */
        .stTabs [data-baseweb="tab-list"] {
            background-color: var(--bg-card);
            padding: 10px 20px;
            border-radius: 50px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            gap: 15px;
            margin-bottom: 25px;
            display: flex;
            justify-content: center;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 45px;
            border: none;
            background: transparent;
            color: var(--text-grey);
            font-weight: 600;
            font-size: 15px;
            border-radius: 25px;
            padding: 0 25px;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: var(--pp-blue) !important;
            color: white !important;
            box-shadow: 0 4px 12px rgba(0, 48, 135, 0.3);
        }

        /* --- CARDS --- */
        div[data-testid="stMetric"], div.stDataFrame, div.stForm {
            background-color: var(--bg-card);
            border: 1px solid #EAECED;
            border-radius: 16px;
            padding: 24px !important;
            box-shadow: 0 2px 6px rgba(0,0,0,0.02);
        }

        /* --- METRICS --- */
        [data-testid="stMetricLabel"] {
            color: var(--text-grey);
            font-size: 14px;
            font-weight: 500;
            text-transform: uppercase;
        }
        [data-testid="stMetricValue"] {
            color: var(--text-dark);
            font-family: 'Inter', sans-serif;
            font-weight: 700;
            font-size: 32px;
        }

        /* --- BUTTONS --- */
        div.stButton > button {
            background-color: var(--pp-light-blue) !important;
            color: white !important;
            border-radius: 25px !important;
            font-weight: 600 !important;
            padding: 12px 30px !important;
            border: none !important;
            box-shadow: 0 4px 10px rgba(0, 112, 186, 0.2) !important;
            transition: transform 0.2s !important;
        }
        div.stButton > button:hover {
            transform: translateY(-2px);
            background-color: #005EA6 !important;
        }

        /* --- INPUTS --- */
        .stTextInput input, .stNumberInput input, .stSelectbox [data-baseweb="select"] {
            border-radius: 8px !important;
            border: 1px solid #CBD2D6 !important;
            height: 48px !important;
            background-color: white !important;
        }
        
        /* HIDE SIDEBAR (We use top nav) */
        section[data-testid="stSidebar"] {
            display: none;
        }
        
        /* HEADERS */
        h1, h2, h3 {
            color: var(--pp-blue) !important;
            font-weight: 700 !important;
        }
    </style>
    """, unsafe_allow_html=True)

# --- CONNEXION & DATA (MOTEUR INCHANGÉ) ---
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
    df_cats, df_comptes, df_objs, df_abos, df_projets, df_mots_cles = (
        load_data_from_sheet(TAB_CONFIG, ["Type", "Categorie"]),
        load_data_from_sheet(TAB_COMPTES, ["Proprietaire", "Compte", "Type"]),
        load_data_from_sheet(TAB_OBJECTIFS, ["Scope", "Categorie", "Montant"]),
        load_data_from_sheet(TAB_ABONNEMENTS, ["Nom", "Montant", "Jour", "Categorie", "Compte_Source", "Proprietaire", "Imputation", "Frequence"]),
        load_data_from_sheet(TAB_PROJETS, ["Projet", "Cible", "Date_Fin"]),
        load_data_from_sheet(TAB_MOTS_CLES, ["Mot_Cle", "Categorie", "Type", "Compte"])
    )
    cats = {k: [] for k in TYPES}
    if not df_cats.empty:
        for _, r in df_cats.iterrows():
            if r["Type"] in cats: cats[r["Type"]].append(r["Categorie"])
    comptes, c_types = {}, {}
    if not df_comptes.empty:
        for _, r in df_comptes.iterrows():
            if r["Proprietaire"] not in comptes: comptes[r["Proprietaire"]] = []
            comptes[r["Proprietaire"]].append(r["Compte"]); c_types[r["Compte"]] = r.get("Type", "Courant")
    projects_dict = {}
    if not df_projets.empty:
        for _, r in df_projets.iterrows(): projects_dict[r["Projet"]] = {"Cible": float(r["Cible"]), "Date_Fin": r["Date_Fin"]}
    mots_cles = {r["Mot_Cle"].lower(): {"Categorie": r["Categorie"], "Type": r["Type"], "Compte": r["Compte"]} for _, r in df_mots_cles.iterrows()} if not df_mots_cles.empty else {}
    return cats, comptes, df_objs.to_dict('records'), df_abos, projects_dict, c_types, mots_cles

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
            mouv = (df_t[(df_t["Compte_Source"] == compte) & (df_t["Type"] == "Revenu")]["Montant"].sum() + 
                    df_t[(df_t["Compte_Cible"] == compte) & (df_t["Type"].isin(["Virement Interne", "Épargne"]))]["Montant"].sum() -
                    df_t[(df_t["Compte_Source"] == compte) & (df_t["Type"].isin(["Dépense", "Investissement", "Virement Interne", "Épargne"]))]["Montant"].sum())
        soldes[compte] = releve + mouv
    return soldes

def to_excel_download(df):
    output = BytesIO()
    df_export = df.copy()
    if "Date" in df_export.columns: df_export["Date"] = df_export["Date"].astype(str)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Transactions')
    return output.getvalue()

def save_comptes_struct(d, types_map): 
    rows = []
    for p, l in d.items():
        for c in l:
            rows.append({"Proprietaire": p, "Compte": c, "Type": types_map.get(c, "Courant")})
    save_data_to_sheet(TAB_COMPTES, pd.DataFrame(rows))
def save_config_cats(d): save_data_to_sheet(TAB_CONFIG, pd.DataFrame([{"Type": t, "Categorie": c} for t, l in d.items() for c in l]))
def save_mots_cles(d):
    rows = []
    for mc, data in d.items():
        rows.append({"Mot_Cle": mc, "Categorie": data["Categorie"], "Type": data["Type"], "Compte": data["Compte"]})
    save_data_to_sheet(TAB_MOTS_CLES, pd.DataFrame(rows))
def save_objectifs_from_df(df_obj): save_data_to_sheet(TAB_OBJECTIFS, df_obj)
def save_abonnements(df): save_data_to_sheet(TAB_ABONNEMENTS, df)
def save_projets_targets(d): 
    rows = []
    for p, data in d.items():
        rows.append({"Projet": p, "Cible": data["Cible"], "Date_Fin": data["Date_Fin"]})
    save_data_to_sheet(TAB_PROJETS, pd.DataFrame(rows))

# --- APP START ---
st.set_page_config(page_title="Ma Banque", layout="wide", page_icon="💳")
apply_custom_style()

df = load_data_from_sheet(TAB_DATA, ["Date", "Mois", "Annee", "Qui_Connecte", "Type", "Categorie", "Titre", "Description", "Montant", "Paye_Par", "Imputation", "Compte_Cible", "Projet_Epargne", "Compte_Source"])
df_patrimoine = load_data_from_sheet(TAB_PATRIMOINE, ["Date", "Mois", "Annee", "Compte", "Montant", "Proprietaire"])
cats_memoire, comptes_structure, objectifs_list, df_abonnements, projets_config, comptes_types_map, mots_cles_map = process_configs()

# --- TOP NAVIGATION BAR (NO SIDEBAR) ---
# Conteneur Header
with st.container():
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
    with c1:
        st.markdown("<h2 style='margin-top:0;'>💳 Ma Banque</h2>", unsafe_allow_html=True)
    with c2:
        user_actuel = st.selectbox("👤 Utilisateur", USERS, label_visibility="collapsed")
    with c3:
        current_month = datetime.now().month
        mois_nom = st.selectbox("📅 Mois", MOIS_FR, index=current_month-1, label_visibility="collapsed")
        mois_selection = MOIS_FR.index(mois_nom) + 1
    with c4:
        annee_selection = st.number_input("Année", value=datetime.now().year, label_visibility="collapsed")

# Filtrage global
df_mois = df[(df["Mois"] == mois_selection) & (df["Annee"] == annee_selection)]
comptes_user = comptes_structure.get(user_actuel, []) + comptes_structure.get("Commun", [])
all_accounts_calc = list(set(comptes_user + ["Autre / Externe"]))
soldes = calculer_soldes_reels(df, df_patrimoine, all_accounts_calc)

# --- TABS REORGANISÉS "PAYPAL STYLE" ---
# 1. Accueil (Dashboard + Activité récente)
# 2. Envoyer & Recevoir (Transactions + Abonnements)
# 3. Portefeuille (Comptes + Patrimoine + Équilibre)
# 4. Insights (Graphiques + Budget)
# 5. Plus (Config)

main_tabs = st.tabs(["Accueil", "Envoyer & Recevoir", "Portefeuille", "Analyses", "Réglages"])

# --- TAB 1: ACCUEIL ---
with main_tabs[0]:
    # Cartes de synthèse
    rev = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Revenu")]["Montant"].sum()
    dep_perso = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Dépense") & (df_mois["Imputation"] == "Perso")]["Montant"].sum()
    part_com = df_mois[df_mois["Imputation"] == "Commun (50/50)"]["Montant"].sum() / 2
    
    # Reste à vivre
    charges_fixes = 0.0
    if not df_abonnements.empty:
        abos = df_abonnements[(df_abonnements["Proprietaire"] == user_actuel) | (df_abonnements["Imputation"].str.contains("Commun"))]
        charges_fixes = sum(float(r["Montant"])/(2 if "Commun" in str(r["Imputation"]) else 1) for _, r in abos.iterrows())
    rav = rev - charges_fixes - dep_perso - part_com

    st.markdown(f"### Bonjour, {user_actuel}")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Solde Disponible (Courant)", f"{sum(soldes.get(c,0) for c in comptes_user if comptes_types_map.get(c)=='Courant'):,.2f} €")
    k2.metric("Entrées ce mois", f"{rev:,.0f} €")
    k3.metric("Sorties Estimées", f"{charges_fixes + dep_perso + part_com:,.0f} €")
    
    # Carte Reste à Vivre stylisée
    rav_color = "#0070BA" if rav > 0 else "#D93644"
    k4.markdown(f"""
    <div style="background-color:{rav_color}; color:white; padding:15px; border-radius:12px; text-align:center;">
        <div style="font-size:12px; opacity:0.9;">Reste à Vivre</div>
        <div style="font-size:24px; font-weight:bold;">{rav:,.0f} €</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    
    # SECTION 5 DERNIÈRES TRANSACTIONS (DEMANDE SPÉCIFIQUE)
    st.subheader("Activité Récente")
    recent_tx = df[df['Qui_Connecte'] == user_actuel].sort_values(by='Date', ascending=False).head(5)
    
    if not recent_tx.empty:
        for idx, row in recent_tx.iterrows():
            col_icon, col_details, col_amount = st.columns([1, 6, 2])
            with col_icon:
                st.markdown("💸" if row['Type'] == "Dépense" else "💰")
            with col_details:
                st.write(f"**{row['Titre']}**")
                st.caption(f"{row['Date']} • {row['Categorie']}")
            with col_amount:
                color = "red" if row['Type'] == "Dépense" else "green"
                st.markdown(f"<div style='color:{color}; font-weight:bold; text-align:right;'>{'-' if row['Type']=='Dépense' else '+'}{row['Montant']:.2f} €</div>", unsafe_allow_html=True)
            st.markdown("<hr style='margin:5px 0; opacity:0.5;'>", unsafe_allow_html=True)
    else:
        st.info("Aucune activité récente.")

# --- TAB 2: ENVOYER & RECEVOIR ---
with main_tabs[1]:
    op1, op2, op3 = st.tabs(["Nouvelle Transaction", "Historique (Journal)", "Abonnements"])
    
    with op1:
        st.subheader("Saisir une opération")
        with st.form("quick_saisie", clear_on_submit=True):
            sc1, sc2, sc3 = st.columns(3)
            d_op = sc1.date_input("Date", datetime.today())
            t_op = sc2.selectbox("Type", TYPES)
            m_op = sc3.number_input("Montant €", min_value=0.0)
            titre = st.text_input("Libellé / Titre")
            
            # Suggestion auto
            cat_auto = "Autre"
            compte_auto = comptes_user[0] if comptes_user else "Autre / Externe"
            if titre and mots_cles_map:
                for k,v in mots_cles_map.items():
                    if k in titre.lower(): 
                        cat_auto = v["Categorie"]
                        if v["Compte"] in comptes_user: compte_auto = v["Compte"]
                        break

            sc4, sc5, sc6 = st.columns(3)
            c_sel = sc4.selectbox("Catégorie", cats_memoire.get(t_op, []) + ["Autre"], index=0)
            c_op = sc5.selectbox("Compte", comptes_user, index=comptes_user.index(compte_auto) if compte_auto in comptes_user else 0)
            im_op = sc6.radio("Imputation", IMPUTATIONS, horizontal=True)
            
            if st.form_submit_button("Valider le paiement", use_container_width=True):
                new = {"Date": d_op, "Mois": d_op.month, "Annee": d_op.year, "Qui_Connecte": user_actuel, "Type": t_op, "Categorie": c_sel, "Titre": titre, "Description": "", "Montant": m_op, "Paye_Par": user_actuel, "Imputation": im_op, "Compte_Cible": "", "Projet_Epargne": "", "Compte_Source": c_op}
                df = pd.concat([df, pd.DataFrame([new])], ignore_index=True); save_data_to_sheet(TAB_DATA, df); st.success("Transaction ajoutée !"); time.sleep(1); st.rerun()

    with op2:
        col_j1, col_j2 = st.columns([3, 1])
        search = col_j1.text_input("🔍 Rechercher dans l'historique...")
        df_j = df_mois[df_mois.apply(lambda r: search.lower() in str(r).lower(), axis=1)] if search else df_mois
        col_j2.write(""); col_j2.download_button("📥 Excel", to_excel_download(df_j), f"Journal_{mois_nom}.xlsx", use_container_width=True)
        
        df_j.insert(0, "🗑️", False)
        ed = st.data_editor(df_j, use_container_width=True, hide_index=True)
        if st.button("Supprimer la sélection"):
            save_data_to_sheet(TAB_DATA, ed[ed["🗑️"]==False].drop(columns=["🗑️"])); st.rerun()

    with op3:
        st.subheader("Gestion des abonnements")
        if not df_abonnements.empty:
            abo_list = []
            for idx, r in df_abonnements.iterrows():
                if r["Proprietaire"] == user_actuel or "Commun" in str(r["Imputation"]):
                    paid = not df_mois[(df_mois["Titre"]==r["Nom"]) & (df_mois["Montant"]==float(r["Montant"]))].empty
                    abo_list.append({"Nom": r["Nom"], "Prix": f"{r['Montant']}€", "Jour": r["Jour"], "Statut": "✅ Payé" if paid else "⏳ À venir", "ID": idx, "Data": r})
            
            st.dataframe(pd.DataFrame(abo_list).drop(columns=["ID", "Data"]), use_container_width=True, hide_index=True)
            
            manquants = [a["Data"] for a in abo_list if "À venir" in a["Statut"]]
            if manquants and st.button(f"Générer {len(manquants)} paiements automatiques"):
                new_abos = []
                for a in manquants:
                    d_a = date(annee_selection, mois_selection, min(int(a["Jour"]), 28))
                    new_abos.append({"Date": d_a, "Mois": mois_selection, "Annee": annee_selection, "Qui_Connecte": user_actuel, "Type": "Dépense", "Categorie": a["Categorie"], "Titre": a["Nom"], "Description": "Abo Auto", "Montant": float(a["Montant"]), "Paye_Par": user_actuel, "Imputation": a["Imputation"], "Compte_Cible": "", "Projet_Epargne": "", "Compte_Source": a["Compte_Source"]})
                df = pd.concat([df, pd.DataFrame(new_abos)], ignore_index=True); save_data_to_sheet(TAB_DATA, df); st.rerun()
            
            with st.expander("Supprimer un abonnement"):
                for a in abo_list:
                    c1, c2 = st.columns([4,1])
                    c1.text(f"{a['Nom']} ({a['Prix']})")
                    if c2.button("🗑️", key=f"del_abo_{a['ID']}"):
                        df_abonnements = df_abonnements.drop(a['ID']); save_abonnements(df_abonnements); st.rerun()
        
        with st.expander("➕ Créer un abonnement"):
            with st.form("new_abo"):
                n = st.text_input("Nom"); m = st.number_input("Montant"); j = st.number_input("Jour", 1, 31)
                c = st.selectbox("Cat", cats_memoire.get("Dépense", [])); cp = st.selectbox("Cpt", comptes_user)
                if st.form_submit_button("Ajouter"):
                    df_abonnements = pd.concat([df_abonnements, pd.DataFrame([{"Nom": n, "Montant": m, "Jour": j, "Categorie": c, "Compte_Source": cp, "Proprietaire": user_actuel, "Imputation": "Perso", "Frequence": "Mensuel"}])], ignore_index=True); save_abonnements(df_abonnements); st.rerun()

# --- TAB 3: PORTEFEUILLE ---
with main_tabs[2]:
    p1, p2, p3 = st.tabs(["Mes Comptes", "Équilibre Couple", "Projets & Épargne"])
    
    with p1:
        st.subheader("Vos comptes")
        for cpt in comptes_user:
            sl = soldes.get(cpt, 0.0)
            tp = comptes_types_map.get(cpt, "Courant")
            col_bg = "#FFFFFF" if tp == "Courant" else "#F0F9FF"
            st.markdown(f"""
            <div style="background-color:{col_bg}; padding:20px; border-radius:12px; border:1px solid #E0E0E0; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-weight:bold; font-size:16px;">{cpt}</div>
                    <div style="color:grey; font-size:12px;">{tp}</div>
                </div>
                <div style="font-weight:bold; font-size:20px; color:{'#0070BA' if sl>=0 else '#D93644'};">{sl:,.2f} €</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.subheader("Ajustement")
        with st.form("rel"):
            c1, c2 = st.columns(2); d = c1.date_input("Date"); c = c2.selectbox("Compte", comptes_user); m = st.number_input("Solde Réel")
            if st.form_submit_button("Ajuster le solde"):
                df_patrimoine = pd.concat([df_patrimoine, pd.DataFrame([{"Date": d, "Mois": d.month, "Annee": d.year, "Compte": c, "Montant": m, "Proprietaire": user_actuel}])], ignore_index=True); save_data_to_sheet(TAB_PATRIMOINE, df_patrimoine); st.rerun()

    with p2:
        st.subheader("Balance des dépenses communes")
        df_c = df_mois[df_mois["Imputation"].str.contains("Commun")]
        p_pay = df_c[df_c["Paye_Par"] == "Pierre"]["Montant"].sum()
        e_pay = df_c[df_c["Paye_Par"] == "Elie"]["Montant"].sum()
        diff = (p_pay - e_pay) / 2
        
        col1, col2 = st.columns(2)
        col1.metric("Pierre a avancé", f"{p_pay:,.2f} €")
        col2.metric("Elie a avancé", f"{e_pay:,.2f} €")
        
        if diff > 0: st.info(f"👉 **Elie** doit rembourser **{abs(diff):,.2f} €** à Pierre")
        elif diff < 0: st.info(f"👉 **Pierre** doit rembourser **{abs(diff):,.2f} €** à Elie")
        else: st.success("Tout est équilibré !")

    with p3:
        st.subheader("Objectifs d'Épargne")
        for p, d in projets_config.items():
            sv = df[(df["Projet_Epargne"] == p) & (df["Type"] == "Épargne")]["Montant"].sum()
            st.write(f"**{p}**")
            st.progress(min(sv/d['Cible'] if d['Cible']>0 else 0, 1.0))
            st.caption(f"{sv:,.0f} / {d['Cible']:,.0f} €")
        
        with st.expander("Nouveau Projet"):
            n = st.text_input("Nom"); t = st.number_input("Cible €")
            if st.button("Créer"): projets_config[n] = {"Cible": t, "Date_Fin": ""}; save_projets_targets(projets_config); st.rerun()

# --- TAB 4: ANALYSES ---
with main_tabs[3]:
    st.subheader("Où va votre argent ?")
    if not df_mois.empty:
        df_dep = df_mois[df_mois["Type"]=="Dépense"]
        fig = px.sunburst(df_dep, path=['Categorie', 'Titre'], values='Montant', color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig, use_container_width=True)
    else: st.warning("Pas de données ce mois-ci")

    st.subheader("Prévisionnel Fin de Mois")
    solde_depart = sum([soldes.get(c, 0) for c in comptes_user if comptes_types_map.get(c) == "Courant"])
    abos_restants = 0
    if not df_abonnements.empty:
        abos = df_abonnements[(df_abonnements["Proprietaire"] == user_actuel) | (df_abonnements["Imputation"].str.contains("Commun"))]
        for _, row in abos.iterrows():
            if int(row["Jour"]) > datetime.now().day:
                abos_restants += float(row["Montant"])/(2 if "Commun" in str(row["Imputation"]) else 1)
    
    dep_moy = dep_perso / max(1, datetime.now().day)
    reste_jours = 30 - datetime.now().day
    proj = solde_depart - abos_restants - (dep_moy * max(0, reste_jours))
    
    c1, c2 = st.columns(2)
    c1.metric("Abonnements à venir", f"{abos_restants:,.0f} €")
    c2.metric("Solde Projeté (Fin de mois)", f"{proj:,.0f} €", delta_color="normal" if proj>0 else "inverse")

# --- TAB 5: RÉGLAGES ---
with main_tabs[4]:
    c_tab1, c_tab2, c_tab3 = st.tabs(["Comptes", "Catégories", "Automatisations"])
    
    with c_tab1:
        with st.form("add_cpt"):
            n_c = st.text_input("Nom"); p_c = st.selectbox("Propriétaire", ["Pierre", "Elie", "Commun"]); t_c = st.selectbox("Type", TYPES_COMPTE)
            if st.form_submit_button("Ajouter"):
                if p_c not in comptes_structure: comptes_structure[p_c] = []
                comptes_structure[p_c].append(n_c); save_comptes_struct(comptes_structure, {**comptes_types_map, n_c: t_c}); st.rerun()
        
        st.write("Vos comptes actuels :"); st.write(comptes_structure)

    with c_tab2:
        type_sel = st.selectbox("Type de flux", TYPES)
        new_cat = st.text_input("Nouvelle catégorie")
        if st.button("Ajouter"):
            if type_sel not in cats_memoire: cats_memoire[type_sel] = []
            cats_memoire[type_sel].append(new_cat); save_config_cats(cats_memoire); st.rerun()
        st.write("Catégories :", cats_memoire.get(type_sel, []))

    with c_tab3:
        st.subheader("Mots-clés")
        with st.form("add_mc"):
            mc = st.text_input("Mot-clé (ex: Uber)"); cat_mc = st.selectbox("Vers Catégorie", [c for cats in cats_memoire.values() for c in cats])
            typ_mc = st.selectbox("Vers Type", TYPES); cpt_mc = st.selectbox("Vers Compte", comptes_user)
            if st.form_submit_button("Créer règle"):
                mots_cles_map[mc.lower()] = {"Categorie": cat_mc, "Type": typ_mc, "Compte": cpt_mc}
                save_mots_cles(mots_cles_map); st.rerun()
