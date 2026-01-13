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

        .stApp {
            background-color: var(--bg-page);
            font-family: 'Inter', sans-serif;
            color: var(--text-main);
        }
        
        .main .block-container {
            padding-top: 2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 100%;
        }
        
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        .stTabs [data-baseweb="tab-list"] {
            gap: 15px;
            border-bottom: 2px solid var(--border);
            padding-bottom: 0px;
            margin-bottom: 20px;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            background-color: transparent;
            border: none;
            color: var(--text-sub);
            font-weight: 600;
            font-size: 15px;
            padding: 0 15px;
            border-radius: 6px 6px 0 0;
        }
        
        .stTabs [data-baseweb="tab"]:hover {
            color: var(--primary) !important;
            background-color: rgba(218, 119, 86, 0.05);
        }
        
        .stTabs [aria-selected="true"] {
            color: var(--primary) !important;
            border-bottom: 3px solid var(--primary) !important;
        }

        .page-title {
            color: var(--text-main);
            font-size: 28px;
            font-weight: 800;
            letter-spacing: -0.5px;
            margin-bottom: 5px;
        }
        .page-subtitle {
            color: var(--text-sub);
            font-size: 14px;
            font-weight: 400;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 15px;
        }
        
        div[data-testid="stMetric"], div.stDataFrame, div.stForm, div.block-container > div {
            background-color: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
        }
        
        div.stButton > button {
            background-color: var(--primary) !important;
            color: white !important;
            border-radius: 8px;
            font-weight: 600;
            border: none;
            padding: 10px 20px;
            box-shadow: 0 2px 5px rgba(218, 119, 86, 0.2);
        }
        
        section[data-testid="stSidebar"] {
            background-color: #FFFFFF;
            border-right: 1px solid var(--border);
        }
        
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"], .stDateInput input, .stTextArea textarea {
            background-color: #ffffff !important;
            border: 1px solid var(--border) !important;
            color: var(--text-main) !important;
            border-radius: 8px !important;
        }
    </style>
    """, unsafe_allow_html=True)

def page_header(title, subtitle):
    st.markdown(f"<div class='page-title'>{title}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='page-subtitle'>{subtitle}</div>", unsafe_allow_html=True)

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
        load_data_from_sheet(TAB_PROJETS, ["Projet", "Cible", "Date_Fin"])
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
    if df_cats.empty:
        defaults = {
            "Dépense": ["Alimentation", "Loyer", "Prêt Immo", "Énergie", "Transport", "Santé", "Resto/Bar", "Shopping", "Cinéma", "Activités"],
            "Revenu": ["Salaire", "Primes", "Ventes", "Aides"],
            "Épargne": ["Virement Mensuel", "Cagnotte"],
            "Investissement": ["Bourse", "Assurance Vie", "Crypto"],
            "Virement Interne": ["Alimentation Compte"]
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
            
    return cats, comptes, objs_list, df_abos, projets_data, comptes_types

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


# --- APP START ---
st.set_page_config(page_title="Ma Banque V50", layout="wide", page_icon="🏦", initial_sidebar_state="expanded")
apply_custom_style()

COLS_DATA = ["Date", "Mois", "Annee", "Qui_Connecte", "Type", "Categorie", "Titre", "Description", "Montant", "Paye_Par", "Imputation", "Compte_Cible", "Projet_Epargne", "Compte_Source"]
df = load_data_from_sheet(TAB_DATA, COLS_DATA)
COLS_PAT = ["Date", "Mois", "Annee", "Compte", "Montant", "Proprietaire"]
df_patrimoine = load_data_from_sheet(TAB_PATRIMOINE, COLS_PAT)

cats_memoire, comptes_structure, objectifs_list, df_abonnements, projets_config, comptes_types_map = process_configs()
def get_comptes_autorises(user): return comptes_structure.get(user, []) + comptes_structure.get("Commun", []) + ["Autre / Externe"]
all_my_accounts = get_comptes_autorises("Pierre") + get_comptes_autorises("Elie")
SOLDES_ACTUELS = calculer_soldes_reels(df, df_patrimoine, list(set(all_my_accounts)))

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h3 style='margin-bottom:20px;'>Mon Espace</h3>", unsafe_allow_html=True)
    user_actuel = st.selectbox("Utilisateur", USERS, label_visibility="collapsed")
    comptes_disponibles = get_comptes_autorises(user_actuel)
    
    total_courant = 0; total_epargne = 0
    list_courant = []; list_epargne = []
    for cpt in comptes_disponibles:
        if cpt == "Autre / Externe": continue
        val = SOLDES_ACTUELS.get(cpt, 0.0)
        ctype = comptes_types_map.get(cpt, "Courant")
        if ctype == "Épargne": total_epargne += val; list_epargne.append((cpt, val))
        else: total_courant += val; list_courant.append((cpt, val))

    st.markdown("---")
    def draw_account_card(name, val, is_saving=False):
        color_bar = "#10B981" if val >= 0 else "#EF4444"
        bg_card = "#FFFFFF"
        if is_saving: color_bar = "#DA7756"; bg_card = "#FFFBF9"
        st.markdown(f"""<div style="background-color: {bg_card}; border-radius: 8px; border: 1px solid #E5E7EB; padding: 10px 12px; margin-bottom: 8px; border-left: 4px solid {color_bar}; box-shadow: 0 1px 2px rgba(0,0,0,0.03);"><div style="font-size: 11px; color: #6B7280; font-weight: 600; text-transform: uppercase;">{name}</div><div style="font-size: 16px; font-weight: 800; color: #1F2937; margin-top: 2px;">{val:,.2f} €</div></div>""", unsafe_allow_html=True)

    st.markdown(f"**COMPTES COURANTS** <span style='float:right; font-size:12px; color:#6B7280;'>{total_courant:,.0f}€</span>", unsafe_allow_html=True)
    for name, val in list_courant: draw_account_card(name, val, False)
    st.write("")
    st.markdown(f"**ÉPARGNE** <span style='float:right; font-size:12px; color:#6B7280;'>{total_epargne:,.0f}€</span>", unsafe_allow_html=True)
    for name, val in list_epargne: draw_account_card(name, val, True)
    st.markdown("---")
    if st.button("🔄 Actualiser"): clear_cache(); st.rerun()

# --- MAIN ---
c_filt1, c_filt2, c_filt3 = st.columns([1, 1, 4])
with c_filt1:
    date_jour = datetime.now()
    mois_nom = st.selectbox("Mois", MOIS_FR, index=date_jour.month-1)
    mois_selection = MOIS_FR.index(mois_nom) + 1
with c_filt2:
    annee_selection = st.number_input("Année", value=date_jour.year)

df_mois = df[(df["Mois"] == mois_selection) & (df["Annee"] == annee_selection)]

# --- NAVIGATION STABLE ---
PAGES = ["Synthèse", "Nouvelle Transaction", "Trésorerie & Relevés", "Rapports & Tendances", "Suivi Budgétaire", "Charges Fixes", "Journal", "Projets & Épargne", "Configuration & Budgets"]
selected_page = st.radio("Navigation", PAGES, horizontal=True, label_visibility="collapsed")

# 0. SYNTHESE
if selected_page == "Synthèse":
    page_header(f"Synthèse - {mois_nom} {annee_selection}", "Vue d'ensemble de vos finances en temps réel")
    k1, k2, k3, k4 = st.columns(4)
    rev = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Revenu")]["Montant"].sum()
    dep = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Dépense") & (df_mois["Imputation"] == "Perso")]["Montant"].sum()
    epg = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Épargne")]["Montant"].sum()
    com = df_mois[df_mois["Imputation"] == "Commun (50/50)"]["Montant"].sum() / 2
    k1.metric("Entrées", f"{rev:,.0f} €"); k2.metric("Sorties Perso", f"{dep:,.0f} €"); k3.metric("Ma Part (50% Commun)", f"{com:,.0f} €"); k4.metric("Épargne", f"{epg:,.0f} €")
    st.markdown("---")
    c_p1, c_p2 = st.columns(2)
    with c_p1:
        st.markdown("### Répartition Dépenses")
        if not df_mois.empty:
            fig_pie = px.pie(df_mois[df_mois["Type"]=="Dépense"], values="Montant", names="Categorie", hole=0.6, color_discrete_sequence=['#DA7756', '#1A1A2E', '#6B7280', '#9CA3AF', '#D1D5DB'])
            fig_pie.update_layout(showlegend=True)
            st.plotly_chart(fig_pie, use_container_width=True)
        else: st.info("Pas de données ce mois-ci")
    with c_p2:
        st.markdown("### Évolution Mensuelle")
        if not df.empty:
            df_trend = df[df["Type"] == "Dépense"].copy()
            df_trend["Periode"] = df_trend["Annee"].astype(str) + "-" + df_trend["Mois"].astype(str).str.zfill(2)
            df_chart = df_trend.groupby(["Periode"])["Montant"].sum().reset_index()
            fig = px.bar(df_chart, x="Periode", y="Montant", color_discrete_sequence=['#DA7756'])
            st.plotly_chart(fig, use_container_width=True)

# 1. SAISIR
elif selected_page == "Nouvelle Transaction":
    page_header("Nouvelle Transaction", "Enregistrez une dépense, un revenu ou un virement")
    
    c1, c2, c3 = st.columns(3)
    date_op = c1.date_input("Date", datetime.today(), key="date_transaction")
    type_op = c2.selectbox("Type", TYPES, key="type_transaction")
    montant_op = c3.number_input("Montant (€)", min_value=0.0, step=0.01, key="montant_transaction")
    
    c4, c5 = st.columns(2)
    titre_op = c4.text_input("Titre", placeholder="Libellé...", key="titre_transaction")
    
    cat_finale = ""
    if type_op == "Virement Interne": 
        c5.info("Virement de fonds")
        cat_finale = "Virement"
    else:
        cats = cats_memoire.get(type_op, [])
        cat_sel = c5.selectbox("Catégorie", cats + ["Autre (nouvelle)"], key="cat_transaction")
        
        if cat_sel == "Autre (nouvelle)":
            cat_finale = c5.text_input("Nom de la catégorie", placeholder="Ex: Cadeaux...", key="cat_autre_transaction")
        else:
            cat_finale = cat_sel
    
    st.write("")
    
    c_src = ""; c_tgt = ""; p_epg = ""; p_par = user_actuel; imput = "Perso"
    
    if type_op == "Épargne":
        st.markdown("**Mouvement d'Épargne**")
        ce1, ce2, ce3 = st.columns(3)
        c_src = ce1.selectbox("Compte Source (Débit)", comptes_disponibles, key="epargne_src")
        c_tgt = ce2.selectbox("Compte Cible (Destination)", comptes_disponibles, key="epargne_tgt")
        projs = list(projets_config.keys()) + ["Nouveau", "Aucun projet"]
        p_sel = ce3.selectbox("Projet lié", projs, key="epargne_projet")
        
        if p_sel == "Nouveau":
            p_epg = st.text_input("Nom Nouveau Projet", key="epargne_nouveau_projet")
        elif p_sel == "Aucun projet":
            p_epg = ""
        else:
            p_epg = p_sel
        
        st.markdown("**Récurrence (optionnel)**")
        rec_col1, rec_col2, rec_col3 = st.columns(3)
        recurrence_epargne = rec_col1.selectbox("Fréquence", ["Aucune", "Mensuel", "Trimestriel", "Annuel"], key="rec_epargne")
        if recurrence_epargne != "Aucune":
            jour_rec_epargne = rec_col2.number_input("Jour du mois", min_value=1, max_value=31, value=1, key="jour_rec_epargne")
            date_fin_rec_epargne = rec_col3.date_input("Jusqu'au", value=datetime.today() + relativedelta(years=1), key="date_fin_rec_epargne")
        p_par = user_actuel; imput = "Perso"
        
    elif type_op == "Virement Interne":
        st.markdown("**Virement Interne**")
        cv1, cv2 = st.columns(2)
        c_src = cv1.selectbox("Compte Débit", comptes_disponibles, key="virement_src")
        c_tgt = cv2.selectbox("Compte Crédit", comptes_disponibles, key="virement_tgt")
        st.markdown("**Récurrence (optionnel)**")
        rec_v_col1, rec_v_col2, rec_v_col3 = st.columns(3)
        recurrence_virement = rec_v_col1.selectbox("Fréquence", ["Aucune", "Mensuel", "Trimestriel", "Annuel"], key="rec_virement")
        if recurrence_virement != "Aucune":
            jour_rec_virement = rec_v_col2.number_input("Jour du mois", min_value=1, max_value=31, value=1, key="jour_rec_virement")
            date_fin_rec_virement = rec_v_col3.date_input("Jusqu'au", value=datetime.today() + relativedelta(years=1), key="date_fin_rec_virement")
        p_epg = ""; p_par = "Virement"; imput = "Neutre"
        
    else:
        st.markdown("**Détails Paiement**")
        cc1, cc2, cc3 = st.columns(3)
        c_src = cc1.selectbox("Compte", comptes_disponibles, key="depense_compte")
        p_par = cc2.selectbox("Payé par", ["Pierre", "Elie", "Commun"], key="depense_par")
        imput = cc3.radio("Imputation", IMPUTATIONS, key="depense_imput")
        
        if imput == "Commun (Autre %)":
            st.markdown("**Répartition personnalisée**")
            pct_col1, pct_col2 = st.columns(2)
            pct_pierre = pct_col1.slider("% Pierre", min_value=0, max_value=100, value=60, step=5, key="pct_pierre")
            pct_elie = 100 - pct_pierre
            pct_col2.metric("% Elie", f"{pct_elie}%")
            imput = f"Commun ({pct_pierre}/{pct_elie})"
        
        c_tgt = ""; p_epg = ""
    
    st.write("")
    desc = st.text_area("Note", height=60, key="desc_transaction")
    
    if st.button("Enregistrer", use_container_width=True, type="primary", key="btn_enregistrer_transaction"):
        if not cat_finale: 
            st.error("Veuillez sélectionner ou créer une catégorie")
        elif not c_src and type_op != "Revenu":
            st.error("Veuillez sélectionner un compte source")
        else:
            if not titre_op: titre_op = cat_finale
            
            # SAUVEGARDE UNIVERSELLE CATÉGORIE
            if type_op != "Virement Interne" and cat_finale not in cats_memoire.get(type_op, []):
                if type_op not in cats_memoire: cats_memoire[type_op] = []
                cats_memoire[type_op].append(cat_finale)
                save_config_cats(cats_memoire)
            
            if type_op == "Épargne" and p_epg and p_epg not in projets_config:
                projets_config[p_epg] = {"Cible": 0.0, "Date_Fin": ""}
                save_projets_targets(projets_config)
            
            new_row = {"Date": date_op, "Mois": date_op.month, "Annee": date_op.year, "Qui_Connecte": user_actuel, "Type": type_op, "Categorie": cat_finale, "Titre": titre_op, "Description": desc, "Montant": montant_op, "Paye_Par": p_par, "Imputation": imput, "Compte_Cible": c_tgt, "Projet_Epargne": p_epg, "Compte_Source": c_src}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_data_to_sheet(TAB_DATA, df)
            st.success("Transaction enregistrée !")
            time.sleep(1); st.rerun()

# 2. TRESORERIE
elif selected_page == "Trésorerie & Relevés":
    page_header("Trésorerie & Relevés", "Recalez vos soldes avec la réalité de la banque")
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
elif selected_page == "Rapports & Tendances":
    page_header("Rapports & Tendances", "Analysez vos flux et l'évolution de vos dépenses")
    vue = st.radio("Vue", ["Flux (Sankey)", "Tendances (Ligne)"], horizontal=True)
    if vue == "Flux (Sankey)":
        if not df_mois.empty:
            df_rev = df_mois[df_mois["Type"] == "Revenu"]
            rev_flows = df_rev.groupby(["Categorie", "Compte_Source"])["Montant"].sum().reset_index()
            df_dep = df_mois[df_mois["Type"] == "Dépense"]
            dep_flows = df_dep.groupby(["Compte_Source", "Categorie"])["Montant"].sum().reset_index()
            all_labels = list(rev_flows["Categorie"].unique()) + list(rev_flows["Compte_Source"].unique()) + list(dep_flows["Compte_Source"].unique()) + list(dep_flows["Categorie"].unique())
            unique_labels = list(dict.fromkeys(all_labels))
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

# 4. BUDGET
elif selected_page == "Suivi Budgétaire":
    page_header(f"Suivi Budgétaire {mois_nom}", "Comparez vos dépenses réelles à vos objectifs")
    with st.expander("Configurer mes objectifs budgétaires", expanded=False):
        st.markdown("**Ajouter un objectif**")
        with st.form("add_objectif_budget"):
            c_obj1, c_obj2, c_obj3, c_obj4 = st.columns([2, 2, 2, 1])
            scope_new = c_obj1.selectbox("Pour qui ?", ["Commun", "Pierre", "Elie"], key="scope_new_obj")
            cat_new = c_obj2.selectbox("Catégorie", cats_memoire.get("Dépense", []), key="cat_new_obj")
            montant_new = c_obj3.number_input("Montant (€)", min_value=0.0, step=10.0, key="montant_new_obj")
            if c_obj4.form_submit_button("Ajouter", use_container_width=True):
                if cat_new and montant_new > 0:
                    objectifs_list.append({"Scope": scope_new, "Categorie": cat_new, "Montant": montant_new})
                    save_objectifs_from_df(pd.DataFrame(objectifs_list))
                    st.success("Objectif ajouté !"); time.sleep(0.5); st.rerun()
        st.markdown("---")
        if objectifs_list:
            for scope in ["Commun", "Pierre", "Elie"]:
                scope_objs = [obj for obj in objectifs_list if obj.get("Scope") == scope]
                if scope_objs:
                    st.markdown(f"**{scope}**")
                    for idx, obj in enumerate(scope_objs):
                        col_o1, col_o2, col_o3, col_o4 = st.columns([3, 2, 1, 1])
                        with col_o1: st.write(obj['Categorie'])
                        with col_o2: 
                            new_amount = st.number_input("Montant", value=float(obj['Montant']), min_value=0.0, step=10.0, key=f"edit_obj_{scope}_{idx}", label_visibility="collapsed")
                        with col_o3:
                            if new_amount != float(obj['Montant']):
                                if st.button("Sauv.", key=f"save_obj_{scope}_{idx}"):
                                    for i, o in enumerate(objectifs_list):
                                        if o['Scope'] == scope and o['Categorie'] == obj['Categorie']: objectifs_list[i]['Montant'] = new_amount; break
                                    save_objectifs_from_df(pd.DataFrame(objectifs_list)); st.rerun()
                        with col_o4:
                            if st.button("Suppr", key=f"del_obj_{scope}_{idx}"):
                                for i, o in enumerate(objectifs_list):
                                    if o['Scope'] == scope and o['Categorie'] == obj['Categorie']: objectifs_list.pop(i); break
                                save_objectifs_from_df(pd.DataFrame(objectifs_list)); st.rerun()
                    st.markdown("---")

    st.markdown("---")
    df_budget = pd.DataFrame(objectifs_list)
    if not df_budget.empty:
        budget_data = []
        for _, row in df_budget.iterrows():
            scope = row["Scope"]; cat = row["Categorie"]; cible = float(row["Montant"])
            mask = (df_mois["Type"] == "Dépense") & (df_mois["Categorie"] == cat)
            if scope == "Commun": mask = mask & (df_mois["Imputation"] == "Commun (50/50)")
            elif scope in ["Pierre", "Elie"]: mask = mask & (df_mois["Imputation"] == "Perso") & (df_mois["Qui_Connecte"] == scope)
            else: mask = mask & (df_mois["Imputation"] == "Perso") & (df_mois["Qui_Connecte"] == user_actuel)
            reel = df_mois[mask]["Montant"].sum()
            ratio = reel / cible if cible > 0 else 0
            budget_data.append({"Catégorie": cat, "Scope": scope, "Budget": cible, "Réel": reel, "Reste": cible - reel, "Progression": min(ratio, 1.0), "%": f"{ratio*100:.0f}%"})
        df_display = pd.DataFrame(budget_data)
        col_budget = st.columns(2)
        
        cfg = {
            "Progression": st.column_config.ProgressColumn("Conso", format="%.0f%%", min_value=0, max_value=1),
            "Budget": st.column_config.NumberColumn(format="%.0f€"),
            "Réel": st.column_config.NumberColumn(format="%.0f€"),
            "Reste": st.column_config.NumberColumn(format="%.0f€"),
            "%": st.column_config.TextColumn("Niveau") 
        }
        
        with col_budget[0]:
            st.markdown("**Commun**"); df_c = df_display[df_display["Scope"] == "Commun"]
            if not df_c.empty: st.dataframe(df_c, column_config=cfg, hide_index=True, use_container_width=True)
            df_perso = df_display[df_display["Scope"] == "Perso"]
            if not df_perso.empty: st.markdown(f"**Perso ({user_actuel})**"); st.dataframe(df_perso, column_config=cfg, hide_index=True, use_container_width=True)
        with col_budget[1]:
            st.markdown("**Pierre**"); df_p = df_display[df_display["Scope"] == "Pierre"]
            if not df_p.empty: st.dataframe(df_p, column_config=cfg, hide_index=True, use_container_width=True)
            st.markdown("**Elie**"); df_e = df_display[df_display["Scope"] == "Elie"]
            if not df_e.empty: st.dataframe(df_e, column_config=cfg, hide_index=True, use_container_width=True)
    else: st.info("Aucun budget configuré.")

# 5. CHARGES FIXES (V50 - LOGIQUE ANTI-DOUBLON INTELLIGENTE)
elif selected_page == "Charges Fixes":
    page_header("Charges Fixes & Abonnements", "Gérez vos dépenses récurrentes")
    
    if not df_abonnements.empty:
        # Filtrage des abonnements concernés
        my_abos = df_abonnements[
            (df_abonnements["Proprietaire"] == user_actuel) | 
            (df_abonnements["Imputation"].str.contains("Commun", na=False))
        ].copy()
        
        if not my_abos.empty:
            # 1. TABLEAU DE BORD INTELLIGENT
            st.markdown("### État du mois en cours")
            
            # Préparation des données pour le tableau
            abo_status_data = []
            abos_to_generate = []
            
            for idx, row in my_abos.iterrows():
                # Vérification : est-ce que cet abo est déjà dans le journal du mois ?
                is_done = False
                if not df_mois.empty:
                    # On vérifie par le TITRE et le MONTANT (pour éviter les doublons même si date diffère légèrement)
                    check = df_mois[
                        (df_mois["Titre"] == row["Nom"]) & 
                        (df_mois["Montant"] == float(row["Montant"]))
                    ]
                    if not check.empty:
                        is_done = True
                
                status_icon = "✅ Payé" if is_done else "⏳ En attente"
                if not is_done:
                    abos_to_generate.append(row)
                
                abo_status_data.append({
                    "Abonnement": row["Nom"],
                    "Montant": f"{row['Montant']}€",
                    "Jour": row["Jour"],
                    "État": status_icon,
                    "ID": idx # Pour suppression
                })
            
            # Affichage du tableau de statut
            st.dataframe(
                pd.DataFrame(abo_status_data).drop(columns=["ID"]), 
                use_container_width=True,
                hide_index=True
            )
            
            # 2. BOUTON D'ACTION CONTEXTUEL
            if abos_to_generate:
                count = len(abos_to_generate)
                if st.button(f"Générer les {count} manquants", type="primary", use_container_width=True):
                    new_rows = []
                    for row in abos_to_generate:
                        # Logique de date
                        try: d = datetime(annee_selection, mois_selection, int(row["Jour"])).date()
                        except: d = datetime(annee_selection, mois_selection, 28).date()
                        
                        paye = "Commun" if "Commun" in str(row["Imputation"]) else row["Proprietaire"]
                        freq = row.get("Frequence", "Mensuel")
                        
                        new_rows.append({
                            "Date": d, 
                            "Mois": mois_selection, 
                            "Annee": annee_selection, 
                            "Qui_Connecte": row["Proprietaire"], 
                            "Type": "Dépense", 
                            "Categorie": row["Categorie"], 
                            "Titre": row["Nom"], 
                            "Description": f"Abonnement {freq} (Auto)", 
                            "Montant": float(row["Montant"]), 
                            "Paye_Par": paye, 
                            "Imputation": row["Imputation"], 
                            "Compte_Cible": "", 
                            "Projet_Epargne": "", 
                            "Compte_Source": row["Compte_Source"]
                        })
                    
                    if new_rows:
                        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
                        save_data_to_sheet(TAB_DATA, df)
                        st.success(f"{count} opérations ajoutées !")
                        time.sleep(1)
                        st.rerun()
            else:
                st.success("Tout est à jour pour ce mois ! 🎉")

            st.markdown("---")
            st.markdown("### Gestion")
            
            # Liste pour suppression (plus discret en bas)
            for abo in abo_status_data:
                c1, c2 = st.columns([4, 1])
                c1.text(f"{abo['Abonnement']} ({abo['Montant']})")
                if c2.button("Suppr", key=f"del_abo_{abo['ID']}"):
                    df_abonnements = df_abonnements.drop(abo['ID'])
                    save_abonnements(df_abonnements)
                    st.rerun()

    else:
        st.info("Aucun abonnement configuré")
        
    st.markdown("---")
    
    # Formulaire d'ajout (inchangé)
    with st.expander("Ajouter un nouvel abonnement", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        nom_abo = c1.text_input("Nom", key="nom_abo"); mt_abo = c2.number_input("Montant", key="mt_abo"); j_abo = c3.number_input("Jour", 1, 31, 1, key="j_abo"); freq_abo = c4.selectbox("Fréquence", FREQUENCES, key="freq_abo")
        c5, c6, c7 = st.columns(3)
        cat_abo = c5.selectbox("Catégorie", cats_memoire.get("Dépense", []), key="cat_abo"); cpt_abo = c6.selectbox("Compte", comptes_disponibles, key="cpt_abo"); imp_abo = c7.radio("Imputation", IMPUTATIONS, key="imp_abo")
        if imp_abo == "Commun (Autre %)":
            pct_col1, pct_col2 = st.columns(2); p_pierre = pct_col1.slider("% Pierre", 0, 100, 60, 5, key="pct_p_abo"); imp_abo = f"Commun ({p_pierre}/{100-p_pierre})"
        if st.button("Créer", type="primary", use_container_width=True, key="btn_add_abo"):
            if nom_abo and mt_abo > 0:
                row = pd.DataFrame([{"Nom": nom_abo, "Montant": mt_abo, "Jour": j_abo, "Categorie": cat_abo, "Compte_Source": cpt_abo, "Proprietaire": user_actuel, "Imputation": imp_abo, "Frequence": freq_abo}])
                df_abonnements = pd.concat([df_abonnements, row], ignore_index=True); save_abonnements(df_abonnements); st.success("Créé !"); time.sleep(1); st.rerun()

# 6. JOURNAL
elif selected_page == "Journal":
    page_header("Journal des Opérations", "Consultez, recherchez et supprimez vos transactions")
    search = st.text_input("Rechercher...", placeholder="Ex: Auchan, 50, Loyer...")
    if not df.empty:
        df_e = df.copy().sort_values(by="Date", ascending=False)
        if search: df_e = df_e[df_e.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]
        df_e.insert(0, "Suppr", False)
        if "Date" in df_e.columns: df_e["Date"] = pd.to_datetime(df_e["Date"])
        ed = st.data_editor(df_e, use_container_width=True, hide_index=True, column_config={"Suppr": st.column_config.CheckboxColumn("Suppr", width="small")})
        if st.button("Supprimer les lignes sélectionnées", type="primary"):
            df_final = ed[ed["Suppr"]==False].drop(columns=["Suppr"])
            save_data_to_sheet(TAB_DATA, df_final); st.success("Lignes supprimées !"); time.sleep(1); st.rerun()

# 7. PROJETS
elif selected_page == "Projets & Épargne":
    page_header("Projets & Épargne", "Suivez la progression de vos objectifs financiers")
    with st.expander("Configurer"):
        with st.form("conf_proj"):
            c1, c2, c3 = st.columns(3)
            projs_exist = list(projets_config.keys()) + ["Nouveau"]
            p_sel = c1.selectbox("Projet", projs_exist)
            p_nom = st.text_input("Nom") if p_sel == "Nouveau" else p_sel
            cible = c2.number_input("Cible (€)", step=100.0)
            d_fin = c3.date_input("Date Fin", datetime.today() + relativedelta(years=1))
            if st.form_submit_button("Sauvegarder"):
                projets_config[p_nom] = {"Cible": cible, "Date_Fin": str(d_fin)}; save_projets_targets(projets_config); st.rerun()
    if projets_config:
        for p, data in projets_config.items():
            target = data["Cible"]; saved = df[(df["Projet_Epargne"] == p) & (df["Type"] == "Épargne")]["Montant"].sum() if not df.empty else 0.0
            st.markdown(f"### {p}")
            c_j1, c_j2 = st.columns([3, 1])
            with c_j1:
                df_p = df[(df["Projet_Epargne"] == p) & (df["Type"] == "Épargne")].copy()
                if not df_p.empty:
                    df_p = df_p.sort_values("Date"); df_p["Cumul"] = df_p["Montant"].cumsum()
                    fig = px.area(df_p, x="Date", y="Cumul", title="Progression"); fig.add_hline(y=target, line_dash="dot", annotation_text="Cible")
                    st.plotly_chart(fig, use_container_width=True)
                else: st.info("Pas encore d'épargne.")
            with c_j2:
                st.metric("Cagnotte", f"{saved:,.0f} €"); st.metric("Cible", f"{target:,.0f} €")
                pct = saved/target if target > 0 else 0
                st.progress(min(pct, 1.0))

# 8. CONFIG
elif selected_page == "Configuration & Budgets":
    page_header("Configuration & Budgets", "Gérez vos comptes et catégories")
    st.markdown("### 1. Gestion des Catégories")
    type_cat_selected = st.selectbox("Type de transaction", TYPES, key="type_cat_manage")
    current_cats = cats_memoire.get(type_cat_selected, [])
    col_add1, col_add2 = st.columns([3, 1])
    with col_add1: new_cat_name = st.text_input("Nouvelle catégorie", key="new_cat_input", placeholder="Ex: Cadeaux...")
    with col_add2: 
        st.write("")
        if st.button("Ajouter", use_container_width=True, key="add_cat_btn"):
            if new_cat_name and new_cat_name not in current_cats:
                if type_cat_selected not in cats_memoire: cats_memoire[type_cat_selected] = []
                cats_memoire[type_cat_selected].append(new_cat_name); save_config_cats(cats_memoire); st.success("Ajouté !"); time.sleep(0.5); st.rerun()
    st.markdown("---")
    if current_cats:
        for idx, cat in enumerate(current_cats):
            col_cat1, col_cat2, col_cat3, col_cat4 = st.columns([1, 5, 1, 1])
            with col_cat1: st.write(f"**{idx+1}**")
            with col_cat2: st.write(cat)
            with col_cat4:
                if st.button("Suppr", key=f"del_{type_cat_selected}_{cat}"):
                    cats_memoire[type_cat_selected].remove(cat); save_config_cats(cats_memoire); st.success("Supprimé"); time.sleep(0.5); st.rerun()
    else: st.caption("Aucune catégorie")
    
    st.markdown("### 2. Gestion des Comptes")
    with st.form("add_account_clean"):
        c_add1, c_add2, c_add3, c_add4 = st.columns([2, 1, 1, 1])
        n = c_add1.text_input("Nom du compte")
        p = c_add2.selectbox("Propriétaire", ["Pierre", "Elie", "Commun"])
        t = c_add3.selectbox("Type", TYPES_COMPTE)
        if c_add4.form_submit_button("Ajouter", use_container_width=True):
            if n and n not in comptes_structure.get(p, []): 
                if p not in comptes_structure: comptes_structure[p] = []
                comptes_structure[p].append(n); comptes_types_map[n] = t
                save_comptes_struct(comptes_structure, comptes_types_map); st.rerun()
    st.write("")
    col_p, col_e, col_c = st.columns(3)
    def display_accounts_list(owner_name, col):
        with col:
            st.markdown(f"**{owner_name}**")
            accounts = comptes_structure.get(owner_name, [])
            if accounts:
                for acc in accounts:
                    c_row1, c_row2 = st.columns([4, 1])
                    c_row1.caption(acc)
                    if c_row2.button("Suppr", key=f"del_acc_{acc}"):
                        comptes_structure[owner_name].remove(acc); save_comptes_struct(comptes_structure, comptes_types_map); st.rerun()
            else: st.caption("Aucun compte")
    display_accounts_list("Pierre", col_p); display_accounts_list("Elie", col_e); display_accounts_list("Commun", col_c)
