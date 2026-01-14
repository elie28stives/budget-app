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

# --- DEFINITION VARIABLES GLOBALES (Pour stabilité) ---
COLS_DATA = ["Date", "Mois", "Annee", "Qui_Connecte", "Type", "Categorie", "Titre", "Description", "Montant", "Paye_Par", "Imputation", "Compte_Cible", "Projet_Epargne", "Compte_Source"]
COLS_PAT = ["Date", "Mois", "Annee", "Compte", "Montant", "Proprietaire"]

# --- STYLE CSS (PROPRE & SANS EMOJIS) ---
def apply_custom_style():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        :root {
            --primary: #2C3E50;
            --primary-light: #34495E;
            --accent: #2980B9;
            --bg-main: #F4F6F8;
            --bg-card: #FFFFFF;
            --text-primary: #1A1C1E;
            --text-secondary: #6B7280;
            --border: #E5E7EB;
        }

        .stApp {
            background: var(--bg-main);
            font-family: 'Inter', sans-serif;
            color: var(--text-primary);
        }
        
        .main .block-container {
            padding-top: 1.5rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 100% !important;
        }
        
        #MainMenu, footer, header {visibility: hidden;}

        /* TABS SOBRES */
        .stTabs [data-baseweb="tab-list"] {
            gap: 20px;
            background: transparent;
            padding: 0px;
            border-bottom: 2px solid var(--border);
            margin-bottom: 20px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 40px;
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-weight: 600;
            font-size: 14px;
            padding: 0 10px;
        }
        .stTabs [aria-selected="true"] {
            color: var(--primary) !important;
            border-bottom: 3px solid var(--primary) !important;
        }

        /* CARTES */
        div[data-testid="stMetric"], div.stDataFrame, div.stForm {
            background: var(--bg-card);
            padding: 20px;
            border-radius: 8px;
            border: 1px solid var(--border) !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
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
            border-radius: 6px !important;
            font-weight: 600 !important;
            border: none !important;
            box-shadow: none !important;
        }
        div.stButton > button:hover {
            background: var(--primary-light) !important;
        }
        
        h1, h2, h3 { color: var(--text-primary) !important; font-family: 'Inter', sans-serif !important; }
    </style>
    """, unsafe_allow_html=True)

def page_header(title, subtitle=None):
    st.markdown(f"<h2 style='font-size:24px; font-weight:800; color:#2C3E50; margin-bottom:5px;'>{title}</h2>", unsafe_allow_html=True)
    if subtitle:
        st.markdown(f"<p style='font-size:14px; color:#6B7280; margin-bottom:20px;'>{subtitle}</p>", unsafe_allow_html=True)

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
    # Chargement unique pour stabilité
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
            if r["Type"] in cats: cats[r["Type"]].append(r["Categorie"])
            
    comptes, c_types = {}, {}
    if not data[1].empty:
        for _, r in data[1].iterrows():
            if r["Proprietaire"] not in comptes: comptes[r["Proprietaire"]] = []
            comptes[r["Proprietaire"]].append(r["Compte"])
            c_types[r["Compte"]] = r.get("Type", "Courant")
            
    projets = {}
    if not data[4].empty:
        for _, r in data[4].iterrows(): projects[r["Projet"]] = {"Cible": float(r["Cible"]), "Date_Fin": r["Date_Fin"]}
        
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
st.set_page_config(page_title="Banque", layout="wide", page_icon=None)
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
    
    # Affichage Soldes (Texte simple)
    st.markdown("**COMPTES COURANTS**")
    for cpt in comptes_user:
        if comptes_types_map.get(cpt) == "Courant":
            val = soldes.get(cpt, 0.0)
            col = "green" if val >= 0 else "red"
            st.markdown(f"{cpt}<br><span style='color:{col}; font-weight:bold;'>{val:,.2f} €</span>", unsafe_allow_html=True)
            st.write("")
            
    st.markdown("**EPARGNE**")
    for cpt in comptes_user:
        if comptes_types_map.get(cpt) == "Épargne":
            val = soldes.get(cpt, 0.0)
            st.markdown(f"{cpt}<br><span style='color:#2980B9; font-weight:bold;'>{val:,.2f} €</span>", unsafe_allow_html=True)
            st.write("")

    st.markdown("---")
    date_jour = datetime.now()
    mois_nom = st.selectbox("Mois", MOIS_FR, index=date_jour.month-1)
    mois_selection = MOIS_FR.index(mois_nom) + 1
    annee_selection = st.number_input("Année", value=date_jour.year)
    df_mois = df[(df["Mois"] == mois_selection) & (df["Annee"] == annee_selection)]
    
    st.markdown("---")
    if st.button("Actualiser"): st.cache_data.clear(); st.rerun()

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
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Revenus", f"{rev:,.0f} €")
    k2.metric("Dépenses", f"{(dep+com):,.0f} €")
    k3.metric("Epargne", f"{epg:,.0f} €")
    k4.metric("Reste à Vivre", f"{rav:,.0f} €", delta="Fin de mois" if rav > 0 else "Attention")
    
    st.markdown("---")
    
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("Dernières Transactions")
        recent = df[df['Qui_Connecte'] == user_actuel].sort_values(by='Date', ascending=False).head(5)
        if not recent.empty:
            for _, r in recent.iterrows():
                col_mt = "red" if r['Type'] == "Dépense" else "green"
                sig = "-" if r['Type'] == "Dépense" else "+"
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; margin-bottom:10px; border-bottom:1px solid #eee; padding-bottom:5px;">
                    <div>
                        <div style="font-weight:bold;">{r['Titre']}</div>
                        <div style="font-size:12px; color:grey;">{r['Date']} • {r['Categorie']}</div>
                    </div>
                    <div style="color:{col_mt}; font-weight:bold;">{sig}{r['Montant']:.2f}€</div>
                </div>
                """, unsafe_allow_html=True)
        else: st.info("Aucune activité récente.")
        
    with c2:
        st.subheader("Suivi Budget")
        objs = [o for o in objectifs_list if o["Scope"] in ["Perso", user_actuel]]
        df_f = df_mois[(df_mois["Type"]=="Dépense") & (df_mois["Imputation"]=="Perso") & (df_mois["Qui_Connecte"]==user_actuel)]
        if objs:
            for o in objs:
                r = df_f[df_f["Categorie"]==o["Categorie"]]["Montant"].sum()
                b = float(o["Montant"])
                if b > 0 and r/b > 0.75:
                    st.write(f"**{o['Categorie']}** : {r:.0f} / {b:.0f} €"); st.progress(min(r/b, 1.0))
        else: st.success("Aucune alerte budget")

# 2. OPÉRATIONS
with tabs[1]:
    op1, op2, op3 = st.tabs(["Saisie", "Journal", "Abonnements"])
    with op1:
        with st.form("add_op"):
            c1, c2, c3 = st.columns(3)
            date_op = c1.date_input("Date", datetime.today())
            type_op = c2.selectbox("Type", TYPES)
            montant_op = c3.number_input("Montant", min_value=0.0, step=0.01)
            c4, c5 = st.columns(2)
            titre_op = c4.text_input("Titre")
            
            cat_finale = "Autre"
            if titre_op and mots_cles_map:
                for mc, data in mots_cles_map.items():
                    if mc in titre_op.lower() and data["Type"] == type_op:
                        cat_finale = data["Categorie"]; break
            
            cats = cats_memoire.get(type_op, [])
            idx = cats.index(cat_finale) if cat_finale in cats else 0
            cat_sel = c5.selectbox("Catégorie", cats + ["Autre"], index=idx)
            
            cc1, cc2, cc3 = st.columns(3)
            c_src = cc1.selectbox("Compte", comptes_user)
            imput = cc2.radio("Imputation", IMPUTATIONS, horizontal=True)
            
            if st.form_submit_button("Valider"):
                new = {"Date": date_op, "Mois": date_op.month, "Annee": date_op.year, "Qui_Connecte": user_actuel, "Type": type_op, "Categorie": cat_sel, "Titre": titre_op, "Description": "", "Montant": montant_op, "Paye_Par": user_actuel, "Imputation": imput, "Compte_Cible": "", "Projet_Epargne": "", "Compte_Source": c_src}
                df = pd.concat([df, pd.DataFrame([new])], ignore_index=True); save_data_to_sheet(TAB_DATA, df); st.success("OK"); time.sleep(1); st.rerun()

    with op2:
        search = st.text_input("Rechercher")
        if not df.empty:
            df_e = df.copy().sort_values(by="Date", ascending=False)
            if search: df_e = df_e[df_e.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
            st.download_button("Excel", to_excel_download(df_e), "export.xlsx")
            df_e.insert(0, "X", False)
            ed = st.data_editor(df_e, hide_index=True, column_config={"X": st.column_config.CheckboxColumn("Suppr", width="small")})
            if st.button("Supprimer sélection"): save_data_to_sheet(TAB_DATA, ed[ed["X"]==False].drop(columns=["X"])); st.rerun()

    with op3:
        st.subheader("Abonnements")
        if not df_abonnements.empty:
            my_abos = df_abonnements[(df_abonnements["Proprietaire"]==user_actuel)|(df_abonnements["Imputation"].str.contains("Commun", na=False))].copy()
            to_gen = []
            for idx, r in my_abos.iterrows():
                paid = not df_mois[(df_mois["Titre"]==r["Nom"])&(df_mois["Montant"]==float(r["Montant"]))].empty
                st.write(f"{'✅' if paid else '⏳'} **{r['Nom']}** - {r['Montant']}€ (Jour {r['Jour']})")
                if not paid: to_gen.append(r)
            
            if to_gen and st.button(f"Générer {len(to_gen)} manquants"):
                new_t = []
                for r in to_gen:
                    try: d = datetime(annee_selection, mois_selection, int(r["Jour"])).date()
                    except: d = datetime(annee_selection, mois_selection, 28).date()
                    new_t.append({"Date": d, "Mois": mois_selection, "Annee": annee_selection, "Qui_Connecte": r["Proprietaire"], "Type": "Dépense", "Categorie": r["Categorie"], "Titre": r["Nom"], "Description": "Auto", "Montant": float(r["Montant"]), "Paye_Par": r["Proprietaire"], "Imputation": r["Imputation"], "Compte_Cible": "", "Projet_Epargne": "", "Compte_Source": r["Compte_Source"]})
                df = pd.concat([df, pd.DataFrame(new_t)], ignore_index=True); save_data_to_sheet(TAB_DATA, df); st.rerun()

# 3. ANALYSES
with tabs[2]:
    an1, an2 = st.tabs(["Graphiques", "Equilibre"])
    with an1:
        if not df_mois.empty:
            fig = px.pie(df_mois[df_mois["Type"]=="Dépense"], values="Montant", names="Categorie", hole=0.6)
            st.plotly_chart(fig, use_container_width=True)
    with an2:
        df_c = df_mois[df_mois["Imputation"].str.contains("Commun", na=False)]
        pp = df_c[df_c["Paye_Par"]=="Pierre"]["Montant"].sum(); ep = df_c[df_c["Paye_Par"]=="Elie"]["Montant"].sum()
        dif = (pp - ep)/2
        c1,c2 = st.columns(2)
        c1.metric("Pierre", f"{pp:.0f} €"); c2.metric("Elie", f"{ep:.0f} €")
        if dif > 0: st.info(f"Elie doit {abs(dif):.0f} € à Pierre")
        elif dif < 0: st.info(f"Pierre doit {abs(dif):.0f} € à Elie")
        else: st.success("Equilibré")

# 4. PATRIMOINE
with tabs[3]:
    st.subheader("Projets")
    with st.expander("Nouveau"):
        n = st.text_input("Nom", key="pn"); t = st.number_input("Cible", key="pt")
        if st.button("Créer", key="pb"): projets_config[n] = {"Cible": t, "Date_Fin": ""}; save_projets_targets(projets_config); st.rerun()
    
    for p, d in projets_config.items():
        s = df[(df["Projet_Epargne"]==p)&(df["Type"]=="Épargne")]["Montant"].sum()
        t = float(d["Cible"])
        st.write(f"**{p}** : {s:.0f} / {t:.0f} €"); st.progress(min(s/t if t>0 else 0, 1.0))

# 5. REGLAGES
with tabs[4]:
    st.subheader("Comptes")
    with st.form("ac"):
        n = st.text_input("Nom"); p = st.selectbox("Proprio", ["Pierre","Elie","Commun"]); ty = st.selectbox("Type", TYPES_COMPTE)
        if st.form_submit_button("Ajouter"):
            if p not in comptes_structure: comptes_structure[p]=[]
            comptes_structure[p].append(n); comptes_types_map[n]=ty; save_comptes_struct(comptes_structure, comptes_types_map); st.rerun()
    
    st.subheader("Catégories")
    ty = st.selectbox("Type", TYPES, key="st"); nc = st.text_input("Cat")
    if st.button("Ajouter Cat"): cats_memoire.setdefault(ty, []).append(nc); save_config_cats(cats_memoire); st.rerun()
