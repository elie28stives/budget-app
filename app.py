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
        # Correction ligne 309 ici
        abos_user = df_abonnements[(df_abonnements["Proprietaire"] == user_actuel) | (df_abonnements["Imputation"].str.contains("Commun", na=False))]
        for _, row in abos_user.iterrows():
            charges_fixes += float(row["Montant"]) / (2 if "Commun" in str(row["Imputation"]) else 1)
    
    rav = rev - charges_fixes - dep - com
    rav_col = "#10B981" if rav > 0 else "#EF4444"
    rav_gradient = "linear-gradient(135deg, #10B981 0%, #059669 100%)" if rav > 0 else "linear-gradient(135deg, #EF4444 0%, #DC2626 100%)"
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Revenus", f"{rev:,.0f} €")
    k2.metric("Charges Fixes", f"{charges_fixes:,.0f} €")
    k3.metric("Dépenses Variables", f"{(dep+com):,.0f} €")
    k4.metric("Epargne", f"{epg:,.0f} €")
    k5.markdown(f"""<div style="background: {rav_gradient}; border-radius: 16px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); position: relative; overflow: hidden; color:white; text-align:center;"><div style="font-size:12px; font-weight:600; text-transform:uppercase;">RESTE À VIVRE</div><div style="font-size:32px; font-weight:800;">{rav:,.0f} €</div></div>""", unsafe_allow_html=True)
    
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
                        <div style="font-size:12px; color:grey;">{r['Date']} - {r['Categorie']}</div>
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
        with st.expander("Nouveau", expanded=False):
            with st.form("new_abo"):
                c1, c2, c3, c4 = st.columns(4)
                n = c1.text_input("Nom"); m = c2.number_input("Montant"); j = c3.number_input("Jour", 1, 31)
                c = st.selectbox("Cat", cats_memoire.get("Dépense", [])); cp = st.selectbox("Cpt", comptes_user); imp = st.selectbox("Imp", IMPUTATIONS); f = c4.selectbox("Freq", FREQUENCES)
                if st.form_submit_button("Ajouter"):
                    df_abonnements = pd.concat([df_abonnements, pd.DataFrame([{"Nom": n, "Montant": m, "Jour": j, "Categorie": c, "Compte_Source": cp, "Proprietaire": user_actuel, "Imputation": imp, "Frequence": f}])], ignore_index=True); save_abonnements(df_abonnements); st.rerun()
        
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
    an1, an2, an3 = st.tabs(["Graphiques", "Equilibre", "Prévisionnel"])
    with an1:
        if not df_mois.empty:
            fig = px.pie(df_mois[df_mois["Type"]=="Dépense"], values="Montant", names="Categorie", hole=0.6)
            st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Flux (Sankey)")
        if not df_mois.empty:
            df_r = df_mois[df_mois["Type"]=="Revenu"]; df_d = df_mois[df_mois["Type"]=="Dépense"]
            rf = df_r.groupby(["Categorie", "Compte_Source"])["Montant"].sum().reset_index()
            df_d = df_d.groupby(["Compte_Source", "Categorie"])["Montant"].sum().reset_index()
            lbs = list(set(rf["Categorie"].tolist()+rf["Compte_Source"].tolist()+df_d["Compte_Source"].tolist()+df_d["Categorie"].tolist()))
            lmap = {n:i for i,n in enumerate(lbs)}
            s,t,v,c = [],[],[],[]
            for _,r in rf.iterrows(): s.append(lmap[r["Categorie"]]); t.append(lmap[r["Compte_Source"]]); v.append(r["Montant"]); c.append("green")
            for _,r in df_d.iterrows(): 
                if r["Compte_Source"] in lmap: s.append(lmap[r["Compte_Source"]]); t.append(lmap[r["Categorie"]]); v.append(r["Montant"]); c.append("red")
            if v:
                fig = go.Figure(data=[go.Sankey(node=dict(pad=15, thickness=20, label=lbs, color="black"), link=dict(source=s, target=t, value=v, color=c))])
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

    with an3:
        solde_dep = sum([SOLDES_ACTUELS.get(c,0) for c in comptes_disponibles if comptes_types_map.get(c)=="Courant"])
        abos_r = 0
        if not df_abonnements.empty:
            au = df_abonnements[(df_abonnements["Proprietaire"]==user_actuel)|(df_abonnements["Imputation"].str.contains("Commun", na=False))]
            for _,r in au.iterrows():
                if int(r["Jour"]) > datetime.now().day: abos_r += float(r["Montant"])/(2 if "Commun" in str(r["Imputation"]) else 1)
        dmoy = dep / max(1, datetime.now().day); jrest = 30 - datetime.now().day
        proj = solde_dep - abos_r - (dmoy * jrest)
        c1,c2,c3 = st.columns(3)
        c1.metric("Actuel", f"{solde_dep:,.0f} €"); c2.metric("Abos restants", f"-{abos_r:,.0f} €"); c3.metric("Fin de mois", f"{proj:,.0f} €")

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
            
    st.subheader("Relevé de compte")
    with st.form("rel"):
        c1, c2 = st.columns(2); d = c1.date_input("Date"); c = c2.selectbox("Compte", comptes_disponibles); m = st.number_input("Solde Réel")
        if st.form_submit_button("Enregistrer"):
            df_patrimoine = pd.concat([df_patrimoine, pd.DataFrame([{"Date": d, "Mois": d.month, "Annee": d.year, "Compte": c, "Montant": m, "Proprietaire": user_actuel}])], ignore_index=True); save_data_to_sheet(TAB_PATRIMOINE, df_patrimoine); st.rerun()

# 5. REGLAGES
with tabs[4]:
    st.subheader("Gestion des Comptes")
    
    # Zone d'ajout
    with st.form("add_compte_new"):
        c1, c2, c3 = st.columns(3)
        n_c = c1.text_input("Nom du compte")
        p_c = c2.selectbox("Propriétaire", ["Pierre", "Elie", "Commun"])
        t_c = c3.selectbox("Type", TYPES_COMPTE)
        if st.form_submit_button("Ajouter ce compte"):
            if p_c not in comptes_structure: comptes_structure[p_c] = []
            comptes_structure[p_c].append(n_c)
            comptes_types_map[n_c] = t_c
            save_comptes_struct(comptes_structure, comptes_types_map)
            st.success(f"Compte {n_c} ajouté")
            time.sleep(1)
            st.rerun()

    st.markdown("---")
    st.subheader("Vos comptes actifs")
    
    # Affichage et suppression par propriétaire
    for proprietaire in ["Pierre", "Elie", "Commun"]:
        if proprietaire in comptes_structure and comptes_structure[proprietaire]:
            st.markdown(f"**{proprietaire}**")
            for compte in comptes_structure[proprietaire]:
                col_a, col_b = st.columns([4, 1])
                col_a.text(f"{compte} ({comptes_types_map.get(compte, 'Courant')})")
                if col_b.button("Supprimer", key=f"btn_del_{compte}"):
                    comptes_structure[proprietaire].remove(compte)
                    save_comptes_struct(comptes_structure, comptes_types_map)
                    st.rerun()
    
    st.markdown("---")
    st.subheader("Catégories & Mots-Clés")
    t1, t2 = st.tabs(["Catégories", "Mots-Clés Auto"])
    
    with t1:
        ty = st.selectbox("Type de flux", TYPES, key="st"); nc = st.text_input("Nouvelle catégorie")
        if st.button("Ajouter Catégorie"): cats_memoire.setdefault(ty, []).append(nc); save_config_cats(cats_memoire); st.rerun()
    
    with t2:
        with st.form("amc"):
            m = st.text_input("Mot-clé (ex: Uber)"); c = st.selectbox("Catégorie cible", [x for l in cats_memoire.values() for x in l]); ty = st.selectbox("Type", TYPES, key="tmc"); co = st.selectbox("Compte", comptes_disponibles)
            if st.form_submit_button("Lier mot-clé"): mots_cles_map[m.lower()] = {"Categorie":c,"Type":ty,"Compte":co}; save_mots_cles(mots_cles_map); st.rerun()
