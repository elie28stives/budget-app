import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
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
MOIS_FR = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

# --- STYLE CSS (DESIGN V30 - CLAUDE ORANGE & CLEAN) ---
def apply_custom_style():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
        
        /* COULEURS VARIABLES */
        :root {
            --claude-orange: #F36B2D; /* L'orange "Claude" */
            --bg-light: #F9FAFB;
            --text-dark: #1A1A2E;
            --text-grey: #6B7280;
        }

        /* FOND GLOBAL ET POLICE */
        .stApp {
            background-color: var(--bg-light);
            font-family: 'Outfit', sans-serif;
            color: var(--text-dark);
        }
        
        /* SIDEBAR PROPRE */
        section[data-testid="stSidebar"] {
            background-color: #FFFFFF;
            border-right: 1px solid #E5E7EB;
        }
        section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
             color: var(--text-dark) !important;
        }
        
        /* TITRES PRINCIPAUX EN ORANGE */
        .orange-header {
            color: var(--claude-orange) !important;
            font-weight: 800;
        }
        h1, h2, h3 {
            color: var(--text-dark); /* Par défaut foncé */
        }

        /* CARTES (METRICS, FORMS, DATAFRAMES) */
        div[data-testid="stMetric"], div.stDataFrame, div.stForm, div.block-container > div {
            background-color: #FFFFFF !important;
            border-radius: 16px !important;
            border: 1px solid #E5E7EB !important;
            padding: 20px !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
            color: var(--text-dark) !important;
        }
        
        /* METRICS SPECIFIQUES */
        div[data-testid="stMetricLabel"] {
            color: var(--text-grey) !important;
            font-size: 0.9rem !important;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600;
        }
        div[data-testid="stMetricValue"] {
            color: var(--text-dark) !important;
            font-weight: 800 !important;
        }

        /* BOUTONS ORANGE CLAUDE */
        div.stButton > button {
            background-color: var(--claude-orange) !important;
            color: white !important;
            border: none;
            border-radius: 12px;
            padding: 12px 24px;
            font-weight: 700;
            transition: all 0.2s ease;
            box-shadow: 0 4px 10px rgba(243, 107, 45, 0.2);
        }
        div.stButton > button:hover {
            background-color: #E05A1C !important; /* Un peu plus foncé au survol */
            transform: translateY(-2px);
            box-shadow: 0 6px 15px rgba(243, 107, 45, 0.3);
        }

        /* INPUTS PROPRES */
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"], .stDateInput input, .stTextArea textarea {
            background-color: #F3F4F6 !important; /* Gris très clair */
            color: var(--text-dark) !important;
            border-radius: 10px !important;
            border: 1px solid transparent !important;
        }
        /* Focus orange */
        .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
            border: 1px solid var(--claude-orange) !important;
             box-shadow: 0 0 0 1px var(--claude-orange) !important;
        }

        /* ONGLETS (TABS) */
        button[data-baseweb="tab"] {
            color: var(--text-grey) !important;
            font-weight: 600;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
             color: var(--claude-orange) !important;
             border-bottom-color: var(--claude-orange) !important;
        }

        /* BARRES DE PROGRESSION ORANGE */
        .stProgress > div > div > div > div {
            background-color: var(--claude-orange) !important;
        }
        
        /* EXPANDERS */
        .streamlit-expanderHeader {
            background-color: #FFFFFF !important;
            border-radius: 12px !important;
            color: var(--text-dark) !important;
            border: 1px solid #E5E7EB;
        }

        /* ALERTES INFO/SUCCESS */
        div[data-testid="stAlert"] {
            background-color: #FFF7ED; /* Fond orange très pâle */
            color: #9A3412 !important; /* Texte orange foncé */
            border: 1px solid #FFEDD5;
            border-radius: 12px;
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
        st.error(f"⚠️ Erreur connexion : {e}")
        return None

def get_worksheet(client, sheet_name, tab_name):
    try:
        sh = client.open(sheet_name)
        try: ws = sh.worksheet(tab_name)
        except: ws = sh.add_worksheet(title=tab_name, rows="100", cols="20")
        return ws
    except Exception as e:
        st.error(f"Erreur onglet {tab_name}: {e}"); st.stop()

# --- LECTURE ---
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
        load_data_from_sheet(TAB_ABONNEMENTS, ["Nom", "Montant", "Jour", "Categorie", "Compte_Source", "Proprietaire", "Imputation"]),
        load_data_from_sheet(TAB_PROJETS, ["Projet", "Cible", "Date_Fin"])
    )

# --- ECRITURE ---
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

# --- CALCUL SOLDES ---
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

# --- CONFIG PROCESSING ---
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
            
    projets_targets = {}
    if not df_projets.empty:
        for _, row in df_projets.iterrows():
            projets_targets[row["Projet"]] = float(row["Cible"])
    return cats, comptes, objs, df_abos, projets_targets

def save_config_cats(d): save_data_to_sheet(TAB_CONFIG, pd.DataFrame([{"Type": t, "Categorie": c} for t, l in d.items() for c in l]))
def save_comptes_struct(d): save_data_to_sheet(TAB_COMPTES, pd.DataFrame([{"Proprietaire": p, "Compte": c} for p, l in d.items() for c, l in d.items() for c in l]))
def save_objectifs(d): save_data_to_sheet(TAB_OBJECTIFS, pd.DataFrame([{"Scope": s, "Categorie": c, "Montant": m} for s, l in d.items() for c, m in l.items()]))
def save_abonnements(df): save_data_to_sheet(TAB_ABONNEMENTS, df)
def save_projets_targets(d): save_data_to_sheet(TAB_PROJETS, pd.DataFrame([{"Projet": p, "Cible": c, "Date_Fin": ""} for p, c in d.items()]))


# --- APP START ---
st.set_page_config(page_title="Ma Banque Orange", layout="wide", page_icon="🏦", initial_sidebar_state="expanded")
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
    st.markdown("<h2 class='orange-header'>Mon Profil</h2>", unsafe_allow_html=True)
    user_actuel = st.selectbox("Utilisateur", USERS, label_visibility="collapsed")
    comptes_disponibles = get_comptes_autorises(user_actuel)
    st.markdown("---")
    st.markdown("<h3 class='orange-header'>💰 Mes Soldes</h3>", unsafe_allow_html=True)
    for cpt in comptes_disponibles:
        if cpt == "Autre / Externe": continue
        solde = SOLDES_ACTUELS.get(cpt, 0.0)
        # Style perso pour les soldes dans la sidebar (Clean white box)
        st.markdown(
            f"""
            <div style="background: #FFFFFF; border-radius: 12px; padding: 12px; margin-bottom: 12px; border: 1px solid #E5E7EB; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="font-size: 0.85rem; color: #6B7280; font-weight: 600; margin-bottom: 4px;">{cpt}</div>
                <div style="font-size: 1.4rem; font-weight: 800; color: {'#10B981' if solde>=0 else '#EF4444'};">{solde:,.2f} €</div>
            </div>
            """, unsafe_allow_html=True
        )
    st.markdown("---")
    if st.button("🔄 Actualiser"): clear_cache(); st.rerun()

# --- MAIN ---
c_filt1, c_filt2 = st.columns([1, 5])
with c_filt1:
    date_jour = datetime.now()
    mois_nom = st.selectbox("Période", MOIS_FR, index=date_jour.month-1, label_visibility="collapsed")
    mois_selection = MOIS_FR.index(mois_nom) + 1
    annee_selection = date_jour.year

df_mois = df[(df["Mois"] == mois_selection) & (df["Annee"] == annee_selection)]
tabs = st.tabs(["Tableau de Bord", "➕ Saisir", "Mes Comptes", "Analyse", "Budget", "Abonnements", "Historique", "Projets", "Paramètres"])

# 0. DASHBOARD
with tabs[0]:
    st.markdown(f"<h2 class='orange-header'>Synthèse - {mois_nom} {annee_selection}</h2>", unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    rev = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Revenu")]["Montant"].sum()
    dep = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Dépense") & (df_mois["Imputation"] == "Perso")]["Montant"].sum()
    epg = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Épargne")]["Montant"].sum()
    com = df_mois[df_mois["Imputation"] == "Commun (50/50)"]["Montant"].sum() / 2
    
    k1.metric("Entrées", f"{rev:,.0f} €"); k2.metric("Sorties Perso", f"{dep:,.0f} €"); k3.metric("Part Commun", f"{com:,.0f} €"); k4.metric("Épargne", f"{epg:,.0f} €")
    
    st.markdown("---")
    
    # CHARTS (Plotly Clean White)
    c_p1, c_p2 = st.columns(2)
    with c_p1:
        st.markdown("<h3 class='orange-header'>💸 Répartition Dépenses</h3>", unsafe_allow_html=True)
        if not df_mois.empty:
            # Palette de couleurs chaudes/orange
            colors_orange = ['#F36B2D', '#FB923C', '#FDBA74', '#FED7AA', '#FFEDD5', '#E5E7EB']
            fig_pie = px.pie(df_mois[df_mois["Type"]=="Dépense"], values="Montant", names="Categorie", hole=0.6, color_discrete_sequence=colors_orange)
            # Fond blanc standard pour lisibilité
            fig_pie.update_layout(font={"color": "#1A1A2E"})
            st.plotly_chart(fig_pie, use_container_width=True)
        else: st.info("Pas de données")

    with c_p2:
        st.markdown("<h3 class='orange-header'>🚨 Alertes Budget</h3>", unsafe_allow_html=True)
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

        alerts_perso = get_budget_alerts("Perso")
        if alerts_perso:
            for c, b, r, pct in alerts_perso:
                st.write(f"**{c}** ({r:.0f}€ / {b:.0f}€)")
                st.progress(min(pct, 1.0))
        else: st.write("Aucun budget défini ou pas de dépenses.")

# 1. SAISIR
with tabs[1]:
    st.markdown("<h2 class='orange-header'>Nouvelle Opération</h2>", unsafe_allow_html=True)
    with st.form("quick_add_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([1, 1, 1])
        date_op = c1.date_input("Date", datetime.today())
        type_op = c2.selectbox("Type", TYPES)
        montant_op = c3.number_input("Montant (€)", min_value=0.0, step=0.01)
        c4, c5 = st.columns([1, 1])
        titre_op = c4.text_input("Titre", placeholder="Ex: Courses Leclerc")
        cat_finale = "Autre"
        if type_op == "Virement Interne": c5.info("Virement de fonds (Neutre)")
        else:
            cats = cats_memoire.get(type_op, ["Autre"])
            cat_sel = c5.selectbox("Catégorie", cats)
            cat_finale = c5.text_input("Nouvelle catégorie :") if cat_sel == "Autre" else cat_sel
        c6, c7, c8 = st.columns([1, 1, 1])
        c_src = ""; c_tgt = ""; p_epg = ""; p_par = user_actuel; imput = "Perso"
        if type_op == "Épargne":
            c_src = c6.selectbox("Depuis", comptes_disponibles)
            c_tgt = c7.selectbox("Vers (Épargne)", comptes_disponibles)
            liste_projets = list(projets_config.keys()) + ["Autre / Nouveau"]
            p_sel = c8.selectbox("Pour quel projet ?", liste_projets)
            p_epg = st.text_input("Nom du nouveau projet") if p_sel == "Autre / Nouveau" else p_sel
        elif type_op == "Virement Interne":
            c_src = c6.selectbox("Débit (Source)", comptes_disponibles)
            c_tgt = c7.selectbox("Crédit (Cible)", comptes_disponibles)
            p_par = "Virement"; imput = "Neutre"
        else:
            c_src = c6.selectbox("Compte", comptes_disponibles)
            p_par = c7.selectbox("Qui paye ?", ["Pierre", "Elie", "Commun"])
            imput = c8.radio("Imputation", IMPUTATIONS)
        desc_op = st.text_area("Note", height=70)
        if st.form_submit_button("✅ Enregistrer", use_container_width=True):
            if not cat_finale: cat_finale = "Autre"
            if not titre_op: titre_op = cat_finale
            if type_op != "Virement Interne" and "Autre" in str(cat_sel) and cat_finale not in cats_memoire.get(type_op, []):
                 cats_memoire[type_op].append(cat_finale); save_config_cats(cats_memoire)
            if type_op == "Épargne" and p_epg and p_epg not in projets_config:
                projets_config[p_epg] = 0.0; save_projets_targets(projets_config)
            new_row = {"Date": date_op, "Mois": date_op.month, "Annee": date_op.year, "Qui_Connecte": user_actuel, "Type": type_op, "Categorie": cat_finale, "Titre": titre_op, "Description": desc_op, "Montant": montant_op, "Paye_Par": p_par, "Imputation": imput, "Compte_Cible": c_tgt, "Projet_Epargne": p_epg, "Compte_Source": c_src}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True); save_data_to_sheet(TAB_DATA, df)
            st.success(f"Opération ajoutée !"); time.sleep(1); st.rerun()

# 2. MES COMPTES
with tabs[2]:
    st.markdown("<h2 class='orange-header'>📝 Faire un Relevé</h2>", unsafe_allow_html=True)
    with st.form("releve_banque"):
        c1, c2 = st.columns(2)
        d_rel = c1.date_input("Date", datetime.today())
        c_rel = c2.selectbox("Compte", comptes_disponibles)
        m_rel = st.number_input("Solde réel (€)", step=0.01)
        if st.form_submit_button("Valider"):
            prop = "Commun" if "Joint" in c_rel or "Commun" in c_rel else user_actuel
            row = pd.DataFrame([{"Date": d_rel, "Mois": d_rel.month, "Annee": d_rel.year, "Compte": c_rel, "Montant": m_rel, "Proprietaire": prop}])
            df_patrimoine = pd.concat([df_patrimoine, row], ignore_index=True); save_data_to_sheet(TAB_PATRIMOINE, df_patrimoine); st.success("OK"); time.sleep(1); st.rerun()

# 3. ANALYSE
with tabs[3]:
    st.markdown("<h2 class='orange-header'>📊 Analyses</h2>", unsafe_allow_html=True)
    type_analyse = st.radio("Vue", ["Flux (Sankey)", "Tendances"], horizontal=True)
    if type_analyse == "Flux (Sankey)":
        if not df_mois.empty:
            df_rev = df_mois[df_mois["Type"] == "Revenu"]
            rev_flows = df_rev.groupby(["Categorie", "Compte_Source"])["Montant"].sum().reset_index()
            df_dep = df_mois[df_mois["Type"] == "Dépense"]
            dep_flows = df_dep.groupby(["Compte_Source", "Categorie"])["Montant"].sum().reset_index()
            all_labels = list(rev_flows["Categorie"].unique()) + list(rev_flows["Compte_Source"].unique()) + list(dep_flows["Compte_Source"].unique()) + list(dep_flows["Categorie"].unique())
            unique_labels = list(set(all_labels))
            label_map = {name: i for i, name in enumerate(unique_labels)}
            sources = []; targets = []; values = []; colors = []
            for _, row in rev_flows.iterrows():
                sources.append(label_map[row["Categorie"]]); targets.append(label_map[row["Compte_Source"]]); values.append(row["Montant"]); colors.append("rgba(16, 185, 129, 0.6)") # Vert
            for _, row in dep_flows.iterrows():
                if row["Compte_Source"] in label_map and row["Categorie"] in label_map:
                    sources.append(label_map[row["Compte_Source"]]); targets.append(label_map[row["Categorie"]]); values.append(row["Montant"]); colors.append("rgba(239, 68, 68, 0.6)") # Rouge
            if values:
                # Noeuds en orange claude ou gris foncé
                fig_sankey = go.Figure(data=[go.Sankey(node = dict(pad=15, thickness=20, line=dict(color="#1A1A2E", width=0.5), label=unique_labels, color="#F36B2D"), link=dict(source=sources, target=targets, value=values, color=colors))])
                # Fond blanc et texte foncé
                fig_sankey.update_layout(font={"color": "#1A1A2E", "size": 12})
                st.plotly_chart(fig_sankey, use_container_width=True)
            else: st.warning("Pas assez de données.")
    else:
        if not df.empty:
            df_trend = df[df["Type"] == "Dépense"].copy()
            df_trend["Periode"] = df_trend["Annee"].astype(str) + "-" + df_trend["Mois"].astype(str).str.zfill(2)
            df_chart = df_trend.groupby(["Periode", "Categorie"])["Montant"].sum().reset_index()
            fig_line = px.line(df_chart, x="Periode", y="Montant", color="Categorie", markers=True)
            # Fond blanc et texte foncé
            fig_line.update_layout(font={"color": "#1A1A2E"})
            st.plotly_chart(fig_line, use_container_width=True)

# 4. BUDGET
with tabs[4]:
    st.markdown(f"<h2 class='orange-header'>Budget - {mois_nom}</h2>", unsafe_allow_html=True)
    def get_budget_table(scope):
        objs = objectifs.get(scope, {})
        mask = (df_mois["Type"] == "Dépense")
        if scope == "Commun": mask = mask & (df_mois["Imputation"] == "Commun (50/50)")
        else: mask = mask & (df_mois["Imputation"] == "Perso") & (df_mois["Qui_Connecte"] == user_actuel)
        df_f = df_mois[mask]
        all_cats = list(set(objs.keys()).union(set(df_f["Categorie"].unique())))
        rows = []
        tp=0; tr=0
        for c in all_cats:
            p = float(objs.get(c, 0.0)); r = df_f[df_f["Categorie"] == c]["Montant"].sum()
            if p>0 or r>0: rows.append({"Catégorie": c, "Budget": p, "Réel": r, "Reste": p-r}); tp+=p; tr+=r
        return pd.DataFrame(rows), tp, tr
    def color_red(val): return f'color: {"#EF4444" if val < 0 else "#10B981"}; font-weight: 700;'
    format_dict = {"Budget": "{:.0f}€", "Réel": "{:.0f}€", "Reste": "{:.0f}€"}
    c1, c2 = st.columns(2)
    with c1:
        st.write("### 🏠 Commun"); df_tc, tpc, trc = get_budget_table("Commun"); st.metric("Reste", f"{tpc-trc:.0f} €", f"Obj: {tpc:.0f}")
        if not df_tc.empty: st.dataframe(df_tc.style.map(color_red, subset=['Reste']).format(format_dict), use_container_width=True, hide_index=True)
    with c2:
        st.write(f"### 👤 {user_actuel}"); df_tp, tpp, trp = get_budget_table("Perso"); st.metric("Reste", f"{tpp-trp:.0f} €", f"Obj: {tpp:.0f}")
        if not df_tp.empty: st.dataframe(df_tp.style.map(color_red, subset=['Reste']).format(format_dict), use_container_width=True, hide_index=True)

# 5. ABONNEMENTS
with tabs[5]:
    st.markdown("<h2 class='orange-header'>⚡ Abonnements</h2>", unsafe_allow_html=True)
    with st.expander("➕ Créer"):
        with st.form("new_abo"):
            ca1, ca2, ca3 = st.columns(3)
            nom_abo = ca1.text_input("Nom"); m_abo = ca2.number_input("Montant"); j_abo = ca3.number_input("Jour", 1, 31, 5)
            ca4, ca5, ca6 = st.columns(3)
            cat_abo = ca4.selectbox("Catégorie", cats_memoire.get("Dépense", [])); cpt_abo = ca5.selectbox("Compte", comptes_disponibles); imp_abo = ca6.radio("Imputation", IMPUTATIONS)
            if st.form_submit_button("Ajouter"):
                row = pd.DataFrame([{"Nom": nom_abo, "Montant": m_abo, "Jour": j_abo, "Categorie": cat_abo, "Compte_Source": cpt_abo, "Proprietaire": user_actuel, "Imputation": imp_abo}])
                df_abonnements = pd.concat([df_abonnements, row], ignore_index=True); save_abonnements(df_abonnements); st.rerun()
    if not df_abonnements.empty:
        my_abos = df_abonnements[(df_abonnements["Proprietaire"] == user_actuel) | (df_abonnements["Imputation"] == "Commun (50/50)")]
        st.dataframe(my_abos, use_container_width=True, hide_index=True)
        if st.button("🚀 Générer pour ce mois"):
            new_rows = []
            for _, row in my_abos.iterrows():
                try: d = datetime(annee_selection, mois_selection, int(row["Jour"])).date()
                except: d = datetime(annee_selection, mois_selection, 28).date()
                new_rows.append({"Date": d, "Mois": mois_selection, "Annee": annee_selection, "Qui_Connecte": user_actuel, "Type": "Dépense", "Categorie": row["Categorie"], "Titre": row["Nom"], "Description": "Auto", "Montant": float(row["Montant"]), "Paye_Par": user_actuel, "Imputation": row["Imputation"], "Compte_Cible": "", "Projet_Epargne": "", "Compte_Source": row["Compte_Source"]})
            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True); save_data_to_sheet(TAB_DATA, df); st.success("Généré !"); time.sleep(1); st.rerun()

# 6. HISTO
with tabs[6]:
    st.markdown("<h2 class='orange-header'>Historique</h2>", unsafe_allow_html=True)
    search_term = st.text_input("🔍 Rechercher...", placeholder="Ex: McDo")
    if not df.empty:
        df_e = df.copy().sort_values(by="Date", ascending=False); df_e.insert(0, "Del", False)
        if "Date" in df_e.columns: df_e["Date"] = pd.to_datetime(df_e["Date"])
        if search_term: df_e = df_e[df_e.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)]
        ed = st.data_editor(df_e, use_container_width=True, hide_index=True, num_rows="fixed", column_config={"Del": st.column_config.CheckboxColumn("🗑️", width="small"), "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY")})
        if st.button("Valider Histo"): save_data_to_sheet(TAB_DATA, ed[ed["Del"]==False].drop(columns=["Del"])); st.rerun()

# 7. PROJETS
with tabs[7]:
    st.markdown("<h2 class='orange-header'>🎯 Objectifs</h2>", unsafe_allow_html=True)
    with st.expander("⚙️ Configurer"):
        with st.form("config_projet"):
            c_p1, c_p2 = st.columns(2)
            projets_existants = set(projets_config.keys())
            if not df.empty: projets_existants.update(df[df["Projet_Epargne"] != ""]["Projet_Epargne"].unique())
            proj_sel = c_p1.selectbox("Projet", list(projets_existants) + ["Nouveau..."])
            proj_nom = st.text_input("Nom du nouveau projet") if proj_sel == "Nouveau..." else proj_sel
            target_val = c_p2.number_input("Objectif (€)", min_value=0.0, step=100.0)
            if st.form_submit_button("Définir"):
                if proj_nom: projets_config[proj_nom] = target_val; save_projets_targets(projets_config); st.rerun()
    if projets_config:
        for proj, target in projets_config.items():
            if target > 0:
                saved = df[(df["Projet_Epargne"] == proj) & (df["Type"] == "Épargne")]["Montant"].sum() if not df.empty else 0.0
                percent = min(saved / target, 1.0)
                col_j1, col_j2 = st.columns([3, 1])
                with col_j1:
                    st.write(f"**{proj}** ({saved:,.0f}€ / {target:,.0f}€)")
                    st.progress(percent)
                with col_j2: st.metric("Reste", f"{target-saved:,.0f} €")
    else: st.info("Aucun projet.")

# 8. PARAMETRES
with tabs[8]:
    st.markdown("<h2 class='orange-header'>Comptes</h2>", unsafe_allow_html=True)
    n = st.text_input("Nom"); p = st.selectbox("Proprio", ["Pierre", "Elie", "Commun"])
    if st.button("Ajouter Compte"): 
        if n and n not in comptes_structure.get(p, []): 
            if p not in comptes_structure: comptes_structure[p] = []
            comptes_structure[p].append(n); save_comptes_struct(comptes_structure); st.rerun()
    cols = st.columns(3)
    for i, (pr, lst) in enumerate(comptes_structure.items()):
        with cols[i%3]:
            st.write(f"**{pr}**")
            for c in lst: 
                if st.button(f"🗑️ {c}", key=c): comptes_structure[pr].remove(c); save_comptes_struct(comptes_structure); st.rerun()
