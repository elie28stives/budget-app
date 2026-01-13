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
IMPUTATIONS = ["Perso", "Commun (50/50)", "Avance/Cadeau"]
FREQUENCES = ["Mensuel", "Annuel", "Trimestriel", "Hebdomadaire"]
MOIS_FR = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

# --- STYLE CSS (DESIGN SYSTEM PRO - ORANGE CLAUDE) ---
def apply_custom_style():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        
        :root {
            --primary: #DA7756;
            --primary-hover: #C56243;
            --bg-page: #F8F9FA;
            --bg-card: #FFFFFF;
            --text-main: #1F2937;
            --text-sub: #6B7280;
            --border: #E5E7EB;
        }

        .stApp {
            background-color: var(--bg-page);
            font-family: 'Inter', sans-serif;
            color: var(--text-main);
        }
        
        /* Navigation (Tabs) */
        .stTabs [data-baseweb="tab-list"] {
            gap: 20px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 10px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            background-color: transparent;
            border: none;
            color: var(--text-sub);
            font-weight: 600;
            font-size: 14px;
        }
        .stTabs [aria-selected="true"] {
            color: var(--primary) !important;
            border-bottom: 2px solid var(--primary) !important;
        }

        /* Cartes & Containers */
        div[data-testid="stMetric"], div.stDataFrame, div.stForm, div.block-container > div {
            background-color: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
        }

        /* Headers */
        h1, h2, h3 {
            color: var(--text-main) !important;
            font-weight: 800 !important;
            letter-spacing: -0.5px;
        }
        
        /* Boutons */
        div.stButton > button {
            background-color: var(--primary) !important;
            color: white !important;
            border-radius: 6px;
            font-weight: 600;
            border: none;
            padding: 10px 20px;
            transition: background-color 0.2s;
        }
        div.stButton > button:hover {
            background-color: var(--primary-hover) !important;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: var(--bg-card);
            border-right: 1px solid var(--border);
        }
        
        /* Inputs */
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"], .stDateInput input, .stTextArea textarea {
            background-color: #F9FAFB !important;
            border: 1px solid var(--border) !important;
            color: var(--text-main) !important;
            border-radius: 6px !important;
        }
        
    </style>
    """, unsafe_allow_html=True)

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

# --- DATA LOADING ---
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
        load_data_from_sheet(TAB_COMPTES, ["Proprietaire", "Compte"]),
        load_data_from_sheet(TAB_OBJECTIFS, ["Scope", "Categorie", "Montant"]),
        load_data_from_sheet(TAB_ABONNEMENTS, ["Nom", "Montant", "Jour", "Categorie", "Compte_Source", "Proprietaire", "Imputation", "Frequence"]),
        load_data_from_sheet(TAB_PROJETS, ["Projet", "Cible", "Date_Fin"])
    )

# --- WRITING ---
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
    df_cats, df_comptes, df_objs, df_abos, df_projets = load_configs_cached()
    cats = {k: [] for k in TYPES}
    if not df_cats.empty:
        for _, row in df_cats.iterrows():
            if row["Type"] in cats and row["Categorie"] not in cats[row["Type"]]:
                cats[row["Type"]].append(row["Categorie"])
    defaults = {
        "Dépense": ["Alimentation", "Loyer", "Prêt Immo", "Énergie", "Transport", "Santé", "Resto/Bar", "Shopping", "Cinéma", "Activités", "Autre"],
        "Revenu": ["Salaire", "Primes", "Ventes", "Aides", "Autre"],
        "Épargne": ["Virement Mensuel", "Cagnotte", "Autre"],
        "Investissement": ["Bourse", "Assurance Vie", "Crypto", "Autre"],
        "Virement Interne": ["Alimentation Compte", "Autre"]
    }
    for t, l in defaults.items():
        if t not in cats: cats[t] = []
        for c in l:
            if c not in cats[t]: cats[t].append(c)

    comptes = {"Pierre": ["Compte Courant Pierre"], "Elie": ["Compte Courant Elie"], "Commun": []}
    if not df_comptes.empty:
        comptes = {}
        for _, row in df_comptes.iterrows():
            if row["Proprietaire"] not in comptes: comptes[row["Proprietaire"]] = []
            comptes[row["Proprietaire"]].append(row["Compte"])
            
    objs = {"Commun": {}, "Perso": {}}
    if not df_objs.empty:
        for _, row in df_objs.iterrows():
            s = row["Scope"]; c = row["Categorie"]; m = row["Montant"]
            if s not in objs: objs[s] = {}
            objs[s][c] = float(m) if m else 0.0
            
    projets_data = {}
    if not df_projets.empty:
        for _, row in df_projets.iterrows():
            projets_data[row["Projet"]] = {"Cible": float(row["Cible"]), "Date_Fin": row["Date_Fin"]}
            
    return cats, comptes, objs, df_abos, projets_data

def save_config_cats(d): save_data_to_sheet(TAB_CONFIG, pd.DataFrame([{"Type": t, "Categorie": c} for t, l in d.items() for c in l]))
def save_comptes_struct(d): save_data_to_sheet(TAB_COMPTES, pd.DataFrame([{"Proprietaire": p, "Compte": c} for p, l in d.items() for c, l in d.items() for c in l]))
def save_objectifs(d): save_data_to_sheet(TAB_OBJECTIFS, pd.DataFrame([{"Scope": s, "Categorie": c, "Montant": m} for s, l in d.items() for c, m in l.items()]))
def save_abonnements(df): save_data_to_sheet(TAB_ABONNEMENTS, df)
def save_projets_targets(d): 
    rows = []
    for p, data in d.items():
        rows.append({"Projet": p, "Cible": data["Cible"], "Date_Fin": data["Date_Fin"]})
    save_data_to_sheet(TAB_PROJETS, pd.DataFrame(rows))


# --- APP START ---
st.set_page_config(page_title="Ma Banque Pro", layout="wide", page_icon="🏦", initial_sidebar_state="expanded")
apply_custom_style()

COLS_DATA = ["Date", "Mois", "Annee", "Qui_Connecte", "Type", "Categorie", "Titre", "Description", "Montant", "Paye_Par", "Imputation", "Compte_Cible", "Projet_Epargne", "Compte_Source"]
df = load_data_from_sheet(TAB_DATA, COLS_DATA)
COLS_PAT = ["Date", "Mois", "Annee", "Compte", "Montant", "Proprietaire"]
df_patrimoine = load_data_from_sheet(TAB_PATRIMOINE, COLS_PAT)

cats_memoire, comptes_structure, objectifs, df_abonnements, projets_config = process_configs()
def get_comptes_autorises(user): return comptes_structure.get(user, []) + comptes_structure.get("Commun", []) + ["Autre / Externe"]
all_my_accounts = get_comptes_autorises("Pierre") + get_comptes_autorises("Elie")
SOLDES_ACTUELS = calculer_soldes_reels(df, df_patrimoine, list(set(all_my_accounts)))

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### Mon Profil")
    user_actuel = st.selectbox("Utilisateur", USERS, label_visibility="collapsed")
    comptes_disponibles = get_comptes_autorises(user_actuel)
    st.markdown("---")
    st.markdown("### Mes Soldes")
    for cpt in comptes_disponibles:
        if cpt == "Autre / Externe": continue
        solde = SOLDES_ACTUELS.get(cpt, 0.0)
        col_text = "#10B981" if solde >= 0 else "#EF4444"
        st.markdown(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
                <div style="font-size: 12px; color: #6B7280; font-weight: 600; margin-bottom: 4px;">{cpt}</div>
                <div style="font-size: 18px; font-weight: 800; color: {col_text};">{solde:,.2f} €</div>
            </div>
            """, unsafe_allow_html=True
        )
    st.markdown("---")
    if st.button("Actualiser"): clear_cache(); st.rerun()

# --- MAIN ---
c_filt1, c_filt2, c_filt3 = st.columns([2, 2, 6])
with c_filt1:
    date_jour = datetime.now()
    mois_nom = st.selectbox("Période", MOIS_FR, index=date_jour.month-1, label_visibility="collapsed")
    mois_selection = MOIS_FR.index(mois_nom) + 1
with c_filt2:
    annee_selection = st.number_input("Année", value=date_jour.year, label_visibility="collapsed")

df_mois = df[(df["Mois"] == mois_selection) & (df["Annee"] == annee_selection)]
tabs = st.tabs(["Tableau de Bord", "Saisir", "Mes Comptes", "Analyses", "Budget", "Abonnements", "Historique", "Projets", "Paramètres"])

# 0. DASHBOARD
with tabs[0]:
    st.markdown(f"## Synthèse - {mois_nom} {annee_selection}")
    k1, k2, k3, k4 = st.columns(4)
    rev = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Revenu")]["Montant"].sum()
    dep = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Dépense") & (df_mois["Imputation"] == "Perso")]["Montant"].sum()
    epg = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Épargne")]["Montant"].sum()
    com = df_mois[df_mois["Imputation"] == "Commun (50/50)"]["Montant"].sum() / 2
    
    k1.metric("Entrées", f"{rev:,.0f} €"); k2.metric("Sorties Perso", f"{dep:,.0f} €"); k3.metric("Part Commun", f"{com:,.0f} €"); k4.metric("Épargne", f"{epg:,.0f} €")
    
    st.markdown("---")
    
    c_p1, c_p2 = st.columns(2)
    with c_p1:
        st.markdown("### Répartition Dépenses")
        if not df_mois.empty:
            # Couleurs sobres
            fig_pie = px.pie(df_mois[df_mois["Type"]=="Dépense"], values="Montant", names="Categorie", hole=0.6, 
                             color_discrete_sequence=['#DA7756', '#1A1A2E', '#6B7280', '#9CA3AF', '#D1D5DB'])
            fig_pie.update_layout(showlegend=True)
            st.plotly_chart(fig_pie, use_container_width=True)
        else: st.info("Pas de données ce mois-ci")

    with c_p2:
        st.markdown("### Santé du Budget")
        def get_budget_alerts(scope):
            objs = objectifs.get(scope, {})
            mask = (df_mois["Type"] == "Dépense")
            if scope == "Commun": mask = mask & (df_mois["Imputation"] == "Commun (50/50)")
            else: mask = mask & (df_mois["Imputation"] == "Perso") & (df_mois["Qui_Connecte"] == user_actuel)
            df_f = df_mois[mask]
            alerts = []
            for c, b in objs.items():
                if b > 0:
                    r = df_f[df_f["Categorie"] == c]["Montant"].sum()
                    alerts.append((c, b, r, r/b))
            return sorted(alerts, key=lambda x: x[3], reverse=True)[:4]

        alerts = get_budget_alerts("Perso")
        if alerts:
            for c, b, r, pct in alerts:
                st.write(f"**{c}** : {r:.0f}€ / {b:.0f}€")
                st.progress(min(pct, 1.0))
        else: st.write("Aucun budget défini.")

# 1. SAISIR (CORRIGÉ V33)
with tabs[1]:
    st.markdown("## Nouvelle Opération")
    with st.form("add_op", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        date_op = c1.date_input("Date", datetime.today())
        type_op = c2.selectbox("Type", TYPES)
        montant_op = c3.number_input("Montant (€)", min_value=0.0, step=0.01)
        
        c4, c5 = st.columns(2)
        titre_op = c4.text_input("Titre", placeholder="Libellé...")
        
        cat_finale = "Autre"
        if type_op == "Virement Interne": 
            c5.info("Virement de fonds")
        else:
            # RESTAURATION DE LA LOGIQUE D'AJOUT CATÉGORIE
            cats = cats_memoire.get(type_op, ["Autre"])
            # Ajout de l'option explicite pour créer
            cats_options = cats + ["➕ Nouvelle..."]
            cat_sel = c5.selectbox("Catégorie", cats_options)
            
            if cat_sel == "➕ Nouvelle...":
                cat_finale = c5.text_input("Nom de la nouvelle catégorie")
            elif cat_sel == "Autre":
                cat_finale = c5.text_input("Préciser Autre :")
            else:
                cat_finale = cat_sel
            
        c6, c7, c8 = st.columns(3)
        c_src = ""; c_tgt = ""; p_epg = ""; p_par = user_actuel; imput = "Perso"
        
        if type_op == "Épargne":
            c_src = c6.selectbox("Source", comptes_disponibles)
            c_tgt = c7.selectbox("Vers Epargne", comptes_disponibles)
            projs = list(projets_config.keys()) + ["Nouveau"]
            p_sel = c8.selectbox("Projet", projs)
            p_epg = st.text_input("Nom Projet") if p_sel == "Nouveau" else p_sel
        elif type_op == "Virement Interne":
            c_src = c6.selectbox("Débit", comptes_disponibles)
            c_tgt = c7.selectbox("Crédit", comptes_disponibles)
            p_par = "Virement"; imput = "Neutre"
        else:
            c_src = c6.selectbox("Compte", comptes_disponibles)
            p_par = c7.selectbox("Payé par", ["Pierre", "Elie", "Commun"])
            imput = c8.radio("Imputation", IMPUTATIONS)
            
        desc = st.text_area("Note", height=60)
        
        if st.form_submit_button("Enregistrer", use_container_width=True):
            if not cat_finale: cat_finale = "Autre"
            if not titre_op: titre_op = cat_finale
            
            # SAUVEGARDE DE LA NOUVELLE CATEGORIE
            if type_op != "Virement Interne" and cat_finale not in cats_memoire.get(type_op, []):
                 if type_op not in cats_memoire: cats_memoire[type_op] = []
                 cats_memoire[type_op].append(cat_finale)
                 save_config_cats(cats_memoire)
            
            if type_op == "Épargne" and p_epg and p_epg not in projets_config:
                projets_config[p_epg] = {"Cible": 0.0, "Date_Fin": ""}
                save_projets_targets(projets_config)
            
            new_row = {"Date": date_op, "Mois": date_op.month, "Annee": date_op.year, "Qui_Connecte": user_actuel, "Type": type_op, "Categorie": cat_finale, "Titre": titre_op, "Description": desc, "Montant": montant_op, "Paye_Par": p_par, "Imputation": imput, "Compte_Cible": c_tgt, "Projet_Epargne": p_epg, "Compte_Source": c_src}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True); save_data_to_sheet(TAB_DATA, df)
            st.success("Enregistré"); time.sleep(1); st.rerun()

# 2. MES COMPTES
with tabs[2]:
    st.markdown("## Faire un Relevé")
    with st.form("releve"):
        c1, c2 = st.columns(2)
        d_rel = c1.date_input("Date", datetime.today())
        c_rel = c2.selectbox("Compte", comptes_disponibles)
        m_rel = st.number_input("Solde Réel (€)", step=0.01)
        if st.form_submit_button("Valider"):
            prop = "Commun" if "Joint" in c_rel or "Commun" in c_rel else user_actuel
            row = pd.DataFrame([{"Date": d_rel, "Mois": d_rel.month, "Annee": d_rel.year, "Compte": c_rel, "Montant": m_rel, "Proprietaire": prop}])
            df_patrimoine = pd.concat([df_patrimoine, row], ignore_index=True); save_data_to_sheet(TAB_PATRIMOINE, df_patrimoine); st.success("OK"); time.sleep(1); st.rerun()

# 3. ANALYSES
with tabs[3]:
    st.markdown("## Analyses")
    vue = st.radio("Vue", ["Flux (Sankey)", "Tendances (Ligne)"], horizontal=True)
    
    if vue == "Flux (Sankey)":
        if not df_mois.empty:
            df_rev = df_mois[df_mois["Type"] == "Revenu"]
            rev_flows = df_rev.groupby(["Categorie", "Compte_Source"])["Montant"].sum().reset_index()
            df_dep = df_mois[df_mois["Type"] == "Dépense"]
            dep_flows = df_dep.groupby(["Compte_Source", "Categorie"])["Montant"].sum().reset_index()
            
            all_labels = list(rev_flows["Categorie"].unique()) + list(rev_flows["Compte_Source"].unique()) + list(dep_flows["Categorie"].unique())
            unique_labels = list(set(all_labels))
            label_map = {name: i for i, name in enumerate(unique_labels)}
            
            sources = []; targets = []; values = []; colors = []
            for _, row in rev_flows.iterrows():
                sources.append(label_map[row["Categorie"]]); targets.append(label_map[row["Compte_Source"]]); values.append(row["Montant"]); colors.append("#10B981")
            for _, row in dep_flows.iterrows():
                if row["Compte_Source"] in label_map and row["Categorie"] in label_map:
                    sources.append(label_map[row["Compte_Source"]]); targets.append(label_map[row["Categorie"]]); values.append(row["Montant"]); colors.append("#EF4444")
            
            if values:
                fig = go.Figure(data=[go.Sankey(node=dict(pad=15, thickness=20, line=dict(color="black", width=0.5), label=unique_labels, color="#1A1A2E"), link=dict(source=sources, target=targets, value=values, color=colors))])
                st.plotly_chart(fig, use_container_width=True)
            else: st.warning("Pas assez de données")
    else:
        if not df.empty:
            df_t = df[df["Type"] == "Dépense"].copy()
            df_t["Periode"] = df_t["Annee"].astype(str) + "-" + df_t["Mois"].astype(str).str.zfill(2)
            df_chart = df_t.groupby(["Periode", "Categorie"])["Montant"].sum().reset_index()
            fig = px.line(df_chart, x="Periode", y="Montant", color="Categorie", markers=True, color_discrete_sequence=px.colors.qualitative.Prism)
            st.plotly_chart(fig, use_container_width=True)

# 4. BUDGET (CORRIGÉ V33)
with tabs[4]:
    st.markdown(f"## Budget {mois_nom}")
    
    def get_budget_df(scope):
        objs = objectifs.get(scope, {})
        mask = (df_mois["Type"] == "Dépense")
        if scope == "Commun": mask = mask & (df_mois["Imputation"] == "Commun (50/50)")
        else: mask = mask & (df_mois["Imputation"] == "Perso") & (df_mois["Qui_Connecte"] == user_actuel)
        df_f = df_mois[mask]
        
        # ON FUSIONNE LES CATEGORIES DU BUDGET ET CELLES DÉPENSÉES
        cats_budget = set(objs.keys())
        cats_spent = set(df_f["Categorie"].unique())
        all_cats = list(cats_budget.union(cats_spent))
        
        data = []
        for c in all_cats:
            b = float(objs.get(c, 0.0))
            r = df_f[df_f["Categorie"] == c]["Montant"].sum()
            if b > 0 or r > 0: # On affiche si budget ou dépense
                status = "🟢"
                if b > 0:
                    pct = r/b
                    if pct > 0.75: status = "🟠"
                    if pct > 1.0: status = "🔴"
                elif r > 0 and b == 0:
                    status = "⚠️" # Dépense hors budget
                
                data.append({"Catégorie": c, "Budget": b, "Réel": r, "Reste": b-r, "État": status})
        return pd.DataFrame(data)

    c1, c2 = st.columns(2)
    with c1:
        st.write("### Commun")
        df_c = get_budget_df("Commun")
        if not df_c.empty: st.dataframe(df_c, hide_index=True, use_container_width=True)
    with c2:
        st.write("### Perso")
        df_p = get_budget_df("Perso")
        if not df_p.empty: st.dataframe(df_p, hide_index=True, use_container_width=True)

# 5. ABONNEMENTS
with tabs[5]:
    st.markdown("## Abonnements")
    with st.expander("➕ Créer"):
        with st.form("new_abo"):
            c1, c2, c3, c4 = st.columns(4)
            nom = c1.text_input("Nom")
            mt = c2.number_input("Montant")
            j = c3.number_input("Jour", 1, 31, 1)
            freq = c4.selectbox("Fréquence", FREQUENCES)
            c5, c6, c7 = st.columns(3)
            cat = c5.selectbox("Catégorie", cats_memoire.get("Dépense", []))
            cpt = c6.selectbox("Compte", comptes_disponibles)
            imp = c7.radio("Imputation", IMPUTATIONS)
            if st.form_submit_button("Ajouter"):
                row = pd.DataFrame([{"Nom": nom, "Montant": mt, "Jour": j, "Categorie": cat, "Compte_Source": cpt, "Proprietaire": user_actuel, "Imputation": imp, "Frequence": freq}])
                df_abonnements = pd.concat([df_abonnements, row], ignore_index=True); save_abonnements(df_abonnements); st.rerun()
    
    if not df_abonnements.empty:
        my_abos = df_abonnements[(df_abonnements["Proprietaire"] == user_actuel) | (df_abonnements["Imputation"] == "Commun (50/50)")]
        st.dataframe(my_abos, use_container_width=True, hide_index=True)
        if st.button("Générer dépenses du mois"):
            new_rows = []
            for _, row in my_abos.iterrows():
                if row.get("Frequence") == "Mensuel" or not row.get("Frequence"):
                    try: d = datetime(annee_selection, mois_selection, int(row["Jour"])).date()
                    except: d = datetime(annee_selection, mois_selection, 28).date()
                    new_rows.append({"Date": d, "Mois": mois_selection, "Annee": annee_selection, "Qui_Connecte": user_actuel, "Type": "Dépense", "Categorie": row["Categorie"], "Titre": row["Nom"], "Description": "Abonnement Auto", "Montant": float(row["Montant"]), "Paye_Par": user_actuel, "Imputation": row["Imputation"], "Compte_Cible": "", "Projet_Epargne": "", "Compte_Source": row["Compte_Source"]})
            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True); save_data_to_sheet(TAB_DATA, df); st.success("Généré"); time.sleep(1); st.rerun()

# 6. HISTO
with tabs[6]:
    st.markdown("## Historique")
    search = st.text_input("🔍 Rechercher...", placeholder="Ex: Auchan, 50, Loyer...")
    if not df.empty:
        df_e = df.copy().sort_values(by="Date", ascending=False)
        if search: df_e = df_e[df_e.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]
        df_e.insert(0, "Del", False)
        if "Date" in df_e.columns: df_e["Date"] = pd.to_datetime(df_e["Date"])
        ed = st.data_editor(df_e, use_container_width=True, hide_index=True, column_config={"Del": st.column_config.CheckboxColumn("Suppr", width="small")})
        if st.button("Sauvegarder"): save_data_to_sheet(TAB_DATA, ed[ed["Del"]==False].drop(columns=["Del"])); st.rerun()

# 7. PROJETS
with tabs[7]:
    st.markdown("## Projets")
    with st.expander("Configurer"):
        with st.form("conf_proj"):
            c1, c2, c3 = st.columns(3)
            projs_exist = list(projets_config.keys()) + ["Nouveau"]
            p_sel = c1.selectbox("Projet", projs_exist)
            p_nom = st.text_input("Nom") if p_sel == "Nouveau" else p_sel
            cible = c2.number_input("Cible (€)", step=100.0)
            d_fin = c3.date_input("Date Fin", datetime.today() + relativedelta(years=1))
            if st.form_submit_button("Sauvegarder"):
                projets_config[p_nom] = {"Cible": cible, "Date_Fin": str(d_fin)}
                save_projets_targets(projets_config); st.rerun()
    
    if projets_config:
        for p, data in projets_config.items():
            target = data["Cible"]
            saved = df[(df["Projet_Epargne"] == p) & (df["Type"] == "Épargne")]["Montant"].sum() if not df.empty else 0.0
            
            st.markdown(f"### {p}")
            c_j1, c_j2 = st.columns([3, 1])
            with c_j1:
                df_p = df[(df["Projet_Epargne"] == p) & (df["Type"] == "Épargne")].copy()
                if not df_p.empty:
                    df_p = df_p.sort_values("Date")
                    df_p["Cumul"] = df_p["Montant"].cumsum()
                    fig = px.area(df_p, x="Date", y="Cumul", title="Progression")
                    fig.add_hline(y=target, line_dash="dot", annotation_text="Cible")
                    st.plotly_chart(fig, use_container_width=True)
                else: st.info("Pas encore d'épargne.")
            with c_j2:
                st.metric("Cagnotte", f"{saved:,.0f} €")
                st.metric("Cible", f"{target:,.0f} €")
                pct = saved/target if target > 0 else 0
                st.progress(min(pct, 1.0))

# 8. PARAMETRES
with tabs[8]:
    st.markdown("## Comptes")
    n = st.text_input("Nom"); p = st.selectbox("Proprio", ["Pierre", "Elie", "Commun"])
    if st.button("Ajouter"):
        if n and n not in comptes_structure.get(p, []): 
            if p not in comptes_structure: comptes_structure[p] = []
            comptes_structure[p].append(n); save_comptes_struct(comptes_structure); st.rerun()
    cols = st.columns(3)
    for i, (pr, lst) in enumerate(comptes_structure.items()):
        with cols[i%3]:
            st.write(f"**{pr}**")
            for c in lst: 
                if st.button(f"🗑️ {c}", key=c): comptes_structure[pr].remove(c); save_comptes_struct(comptes_structure); st.rerun()
