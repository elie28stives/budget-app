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

# --- STYLE CSS (REVOLUT-INSPIRED DESIGN) ---
def apply_custom_style():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        :root {
            --primary: #FF6B35;
            --primary-dark: #E55A2B;
            --success: #10B981;
            --warning: #F59E0B;
            --danger: #EF4444;
            --bg-main: #F5F7FA;
            --bg-card: #FFFFFF;
            --text-primary: #0A1929;
            --text-secondary: #6B7280;
            --border: #E5E7EB;
            --shadow: 0 1px 3px rgba(0,0,0,0.04);
            --shadow-lg: 0 4px 12px rgba(0,0,0,0.08);
        }

        .stApp {
            background: var(--bg-main);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            color: var(--text-primary);
        }
        
        .main .block-container {
            padding: 2rem 3rem !important;
            max-width: 1400px;
        }
        
        #MainMenu, footer, header {visibility: hidden;}

        /* TABS - Style Revolut */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0;
            background: var(--bg-card);
            border-radius: 12px;
            padding: 4px;
            box-shadow: var(--shadow);
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
            transition: all 0.2s;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background: rgba(255, 107, 53, 0.08);
            color: var(--primary);
        }
        .stTabs [aria-selected="true"] {
            background: var(--primary) !important;
            color: white !important;
            border: none !important;
        }

        /* MÉTRIQUES - Cards modernes */
        div[data-testid="stMetric"] {
            background: var(--bg-card);
            padding: 20px;
            border-radius: 16px;
            border: none !important;
            box-shadow: var(--shadow-lg) !important;
        }
        
        div[data-testid="stMetric"] label {
            font-size: 13px !important;
            font-weight: 600 !important;
            color: var(--text-secondary) !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            font-size: 32px !important;
            font-weight: 700 !important;
            color: var(--text-primary) !important;
        }

        /* SIDEBAR - Style app mobile */
        section[data-testid="stSidebar"] {
            background: var(--bg-card);
            border-right: 1px solid var(--border);
            padding-top: 1rem;
        }
        
        section[data-testid="stSidebar"] > div {
            padding: 0 1.5rem;
        }

        /* INPUTS - Minimalistes */
        .stTextInput input, .stNumberInput input {
            background: #FFFFFF !important;
            border: 1.5px solid var(--border) !important;
            border-radius: 12px !important;
            font-size: 15px !important;
            font-weight: 600 !important;
            color: #0A1929 !important;
            padding: 12px 16px !important;
            transition: all 0.2s;
        }
        
        .stTextInput input:focus, .stNumberInput input:focus {
            border-color: var(--primary) !important;
            box-shadow: 0 0 0 3px rgba(255, 107, 53, 0.1) !important;
        }
        
        /* SELECTBOX & UI FIXES */
        .stSelectbox, .stDateInput input, .stTextArea textarea {
            color: #0A1929 !important;
            font-weight: 600 !important;
        }
        
        div[data-baseweb="select"] > div {
            background-color: #FFFFFF !important;
            border-color: var(--border) !important;
            border-radius: 12px !important;
        }

        /* BOUTONS - Style Revolut */
        div.stButton > button {
            background: var(--primary) !important;
            color: white !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            font-size: 15px !important;
            border: none !important;
            padding: 12px 24px !important;
            box-shadow: 0 2px 8px rgba(255, 107, 53, 0.3) !important;
            transition: all 0.2s !important;
        }
        div.stButton > button:hover {
            background: var(--primary-dark) !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(255, 107, 53, 0.4) !important;
        }

        /* DATAFRAME */
        div.stDataFrame {
            background: var(--bg-card);
            border-radius: 16px !important;
            border: none !important;
            box-shadow: var(--shadow-lg) !important;
            overflow: hidden;
        }

        /* HEADERS */
        h1, h2, h3 { color: var(--text-primary) !important; font-family: 'Inter', sans-serif !important; font-weight: 700 !important; }
        h2 { font-size: 28px !important; margin-bottom: 1.5rem !important; }
        h3 { font-size: 20px !important; font-weight: 600 !important; margin-top: 2rem !important; }

        /* EXPANDER & FORMS */
        div[data-testid="stExpander"], div.stForm { 
            background: var(--bg-card); border: none !important; border-radius: 16px; box-shadow: var(--shadow-lg); 
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

@st.cache_data(ttl=600)
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
def to_excel_download(df):
    output = BytesIO()
    df_export = df.copy()
    if "Date" in df_export.columns: df_export["Date"] = df_export["Date"].astype(str)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Transactions')
    return output.getvalue()

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

def process_configs():
    df_cats, df_comptes, df_objs, df_abos, df_projets, df_mots_cles = load_configs_cached()
    cats = {k: [] for k in TYPES}
    if not df_cats.empty:
        for _, row in df_cats.iterrows():
            if row["Type"] in cats and row["Categorie"] not in cats[row["Type"]]: cats[row["Type"]].append(row["Categorie"])
    
    comptes, c_types = {}, {}
    if not df_comptes.empty:
        for _, row in df_comptes.iterrows():
            if row["Proprietaire"] not in comptes: comptes[row["Proprietaire"]] = []
            comptes[row["Proprietaire"]].append(row["Compte"])
            c_types[row["Compte"]] = row.get("Type", "Courant")
            
    projets_data = {}
    if not df_projets.empty:
        for _, row in df_projets.iterrows(): projets_data[row["Projet"]] = {"Cible": float(row["Cible"]), "Date_Fin": row["Date_Fin"]}
    
    mots_cles_dict = {}
    if not df_mots_cles.empty:
        for _, row in df_mots_cles.iterrows(): mots_cles_dict[row["Mot_Cle"].lower()] = {"Categorie": row["Categorie"], "Type": row["Type"], "Compte": row["Compte"]}
            
    return cats, comptes, df_objs.to_dict('records'), df_abos, projets_data, c_types, mots_cles_dict

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
st.set_page_config(page_title="Ma Banque V56.5", layout="wide", page_icon="🏦", initial_sidebar_state="expanded")
apply_custom_style()

df = load_data_from_sheet(TAB_DATA, COLS_DATA)
df_patrimoine = load_data_from_sheet(TAB_PATRIMOINE, COLS_PAT)
cats_memoire, comptes_structure, objectifs_list, df_abonnements, projets_config, comptes_types_map, mots_cles_map = process_configs()
def get_comptes_autorises(user): return comptes_structure.get(user, []) + comptes_structure.get("Commun", []) + ["Autre / Externe"]
all_my_accounts = get_comptes_autorises("Pierre") + get_comptes_autorises("Elie")
SOLDES_ACTUELS = calculer_soldes_reels(df, df_patrimoine, list(set(all_my_accounts)))

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h3 style='margin-bottom:20px;'>Menu</h3>", unsafe_allow_html=True)
    user_actuel = st.selectbox("Utilisateur", USERS)
    
    st.markdown("---")
    comptes_disponibles = get_comptes_autorises(user_actuel)
    total_courant = 0; total_epargne = 0
    list_courant = []; list_epargne = []
    
    for cpt in comptes_disponibles:
        if cpt == "Autre / Externe": continue
        val = SOLDES_ACTUELS.get(cpt, 0.0)
        ctype = comptes_types_map.get(cpt, "Courant")
        if ctype == "Épargne": total_epargne += val; list_epargne.append((cpt, val))
        else: total_courant += val; list_courant.append((cpt, val))

    def draw_account_card(name, val, is_saving=False):
        gradient = "linear-gradient(135deg, #0066FF 0%, #00D4FF 100%)" if is_saving else ("linear-gradient(135deg, #10B981 0%, #059669 100%)" if val >= 0 else "linear-gradient(135deg, #EF4444 0%, #DC2626 100%)")
        icon = "💎" if is_saving else "💳"
        st.markdown(f"""<div style="background: {gradient}; border-radius: 16px; padding: 20px; margin-bottom: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); position: relative; overflow: hidden;"><div style="position: absolute; top: 10px; right: 15px; font-size: 32px; opacity: 0.3;">{icon}</div><div style="font-size: 12px; color: rgba(255,255,255,0.9); font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">{name}</div><div style="font-size: 28px; font-weight: 800; color: white;">{val:,.2f} €</div></div>""", unsafe_allow_html=True)

    st.markdown(f"**COMPTES ({total_courant:,.0f}€)**"); 
    for n,v in list_courant: draw_account_card(n,v,False)
    st.write(""); st.markdown(f"**ÉPARGNE ({total_epargne:,.0f}€)**")
    for n,v in list_epargne: draw_account_card(n,v,True)

    st.markdown("---"); st.markdown("**Période**")
    date_jour = datetime.now()
    mois_nom = st.selectbox("Mois", MOIS_FR, index=date_jour.month-1)
    mois_selection = MOIS_FR.index(mois_nom) + 1
    annee_selection = st.number_input("Année", value=date_jour.year)
    df_mois = df[(df["Mois"] == mois_selection) & (df["Annee"] == annee_selection)]
    st.markdown("---"); 
    if st.button("Actualiser", use_container_width=True): clear_cache(); st.rerun()

# --- MAIN ---
tabs = st.tabs(["Transactions", "Synthèse", "Analyse & Budget", "Prévisionnel", "Équilibre", "Patrimoine", "Configuration"])

# 1. SYNTHESE
with tabs[1]:
    page_header("Synthèse du mois")
    rev = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Revenu")]["Montant"].sum()
    dep = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Dépense") & (df_mois["Imputation"] == "Perso")]["Montant"].sum()
    epg = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Épargne")]["Montant"].sum()
    com = df_mois[df_mois["Imputation"] == "Commun (50/50)"]["Montant"].sum() / 2
    
    # Reste à vivre
    charges_fixes = 0.0
    if not df_abonnements.empty:
        abos_user = df_abonnements[(df_abonnements["Proprietaire"] == user_actuel) | (df_abonnements["Imputation"].str.contains("Commun", na=False))]
        for _, row in abos_user.iterrows(): charges_fixes += float(row["Montant"]) / (2 if "Commun" in str(row["Imputation"]) else 1)
    
    rav = rev - charges_fixes - dep - com
    rav_gradient = "linear-gradient(135deg, #10B981 0%, #059669 100%)" if rav > 0 else "linear-gradient(135deg, #EF4444 0%, #DC2626 100%)"
    
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Revenus", f"{rev:,.0f} €"); k2.metric("Charges Fixes", f"{charges_fixes:,.0f} €"); k3.metric("Dépenses Variables", f"{(dep+com):,.0f} €"); k4.metric("Épargne", f"{epg:,.0f} €")
    k5.markdown(f"""<div style="background: {rav_gradient}; border-radius: 16px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); position: relative; overflow: hidden;"><div style="position: absolute; top: 10px; right: 15px; font-size: 48px; opacity: 0.2;">{'💰' if rav > 0 else '⚠️'}</div><div style="font-size: 12px; color: rgba(255,255,255,0.9); font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Reste à Vivre</div><div style="font-size: 32px; font-weight: 800; color: white; margin-bottom: 4px;">{rav:,.0f} €</div><div style="font-size: 13px; color: rgba(255,255,255,0.8); font-weight: 500;">Pour finir le mois</div></div>""", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # --- AJOUT: 5 DERNIÈRES TRANSACTIONS ---
    st.subheader("⏱️ Activité Récente")
    recent_tx = df[df['Qui_Connecte'] == user_actuel].sort_values(by='Date', ascending=False).head(5)
    
    if not recent_tx.empty:
        for _, row in recent_tx.iterrows():
            c_icon, c_det, c_mt = st.columns([1, 6, 2])
            with c_icon: st.markdown(f"<div style='font-size:24px;'>{'💳' if row['Type']=='Dépense' else '💰'}</div>", unsafe_allow_html=True)
            with c_det: st.markdown(f"**{row['Titre']}**"); st.caption(f"{row['Date']} • {row['Categorie']}")
            with c_mt: 
                col = "#EF4444" if row['Type'] in ['Dépense', 'Virement Interne'] else "#10B981"
                sig = "-" if row['Type'] in ['Dépense', 'Virement Interne'] else "+"
                st.markdown(f"<div style='color:{col}; font-weight:bold; text-align:right;'>{sig}{row['Montant']:.2f} €</div>", unsafe_allow_html=True)
            st.markdown("<hr style='margin:5px 0; opacity:0.1;'>", unsafe_allow_html=True)
    else: st.info("Aucune activité récente.")
    
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Répartition")
        if not df_mois.empty:
            fig = px.pie(df_mois[df_mois["Type"]=="Dépense"], values="Montant", names="Categorie", hole=0.6, color_discrete_sequence=['#DA7756', '#202124', '#5F6368', '#9CA3AF', '#D1D5DB'])
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("Pas de données")
    with c2:
        st.subheader("Alertes Budget")
        objs = [o for o in objectifs_list if o["Scope"] in ["Perso", user_actuel]]
        df_f = df_mois[(df_mois["Type"]=="Dépense") & (df_mois["Imputation"]=="Perso") & (df_mois["Qui_Connecte"]==user_actuel)]
        if objs:
            for o in objs:
                r = df_f[df_f["Categorie"]==o["Categorie"]]["Montant"].sum()
                b = float(o["Montant"])
                if b > 0 and r/b > 0.75:
                    st.write(f"**{o['Categorie']}** : {r:.0f} / {b:.0f} €"); st.progress(min(r/b, 1.0))
        else: st.success("Aucune alerte")

# 2. TRANSACTIONS
with tabs[0]:
    subtabs = st.tabs(["Nouvelle Saisie", "Journal", "Abonnements"])
    with subtabs[0]:
        c1, c2, c3 = st.columns(3)
        date_op = c1.date_input("Date", datetime.today(), key="d_op")
        type_op = c2.selectbox("Type", TYPES, key="t_op")
        montant_op = c3.number_input("Montant (€)", min_value=0.0, step=0.01, key="m_op")
        c4, c5 = st.columns(2)
        titre_op = c4.text_input("Titre", placeholder="Libellé...", key="tit_op")
        
        # Mots clés
        cat_finale = "Autre"; compte_auto = None; sugg = False
        if titre_op and mots_cles_map:
            for mc, data in mots_cles_map.items():
                if mc in titre_op.lower() and data["Type"] == type_op:
                    cat_finale = data["Categorie"]; compte_auto = data["Compte"]; sugg = True; break
        if sugg: c5.success(f"✨ Suggestion : {cat_finale}")
        
        if type_op == "Virement Interne": cat_finale = "Virement"
        else:
            cats = cats_memoire.get(type_op, [])
            idx = cats.index(cat_finale) if cat_finale in cats else 0
            cat_sel = c5.selectbox("Catégorie", cats + ["Autre (nouvelle)"], index=idx, key="c_sel")
            cat_finale = c5.text_input("Nom", key="c_new") if cat_sel == "Autre (nouvelle)" else cat_sel
        
        st.write(""); c_src=""; c_tgt=""; p_epg=""; p_par=user_actuel; imput="Perso"
        
        if type_op == "Épargne":
            ce1, ce2, ce3 = st.columns(3)
            c_src = ce1.selectbox("Source", comptes_disponibles, key="src_e")
            c_tgt = ce2.selectbox("Cible", [c for c in comptes_disponibles if comptes_types_map.get(c) == "Épargne"] or comptes_disponibles, key="tgt_e")
            p_sel = ce3.selectbox("Projet", list(projets_config.keys())+["Nouveau","Aucun"], key="prj_e")
            p_epg = st.text_input("Nouveau Projet", key="np_e") if p_sel == "Nouveau" else ("" if p_sel=="Aucun" else p_sel)
        elif type_op == "Virement Interne":
            cv1, cv2 = st.columns(2)
            c_src = cv1.selectbox("Débit", comptes_disponibles, key="src_v")
            c_tgt = cv2.selectbox("Crédit", comptes_disponibles, key="tgt_v")
            p_par = "Virement"; imput = "Neutre"
        else:
            cc1, cc2, cc3 = st.columns(3)
            idx_c = comptes_disponibles.index(compte_auto) if compte_auto in comptes_disponibles else 0
            c_src = cc1.selectbox("Compte", comptes_disponibles, index=idx_c, key="src_d")
            p_par = cc2.selectbox("Payé par", ["Pierre", "Elie", "Commun"], key="par_d")
            imput = cc3.radio("Imputation", IMPUTATIONS, key="imp_d")
            if imput == "Commun (Autre %)": pc = st.slider("% Pierre", 0, 100, 50, key="sl_d"); imput = f"Commun ({pc}/{100-pc})"
            
        st.write(""); desc = st.text_area("Note", height=60, key="dsc")
        if st.button("Enregistrer Transaction", type="primary", use_container_width=True, key="save_btn"):
            if not cat_finale: st.error("Catégorie requise")
            elif not c_src and type_op != "Revenu": st.error("Compte source requis")
            else:
                if not titre_op: titre_op = cat_finale
                if type_op != "Virement Interne" and cat_finale not in cats_memoire.get(type_op, []):
                    if type_op not in cats_memoire: cats_memoire[type_op] = []
                    cats_memoire[type_op].append(cat_finale); save_config_cats(cats_memoire)
                if type_op == "Épargne" and p_epg and p_epg not in projets_config:
                    projets_config[p_epg] = {"Cible": 0.0, "Date_Fin": ""}; save_projets_targets(projets_config)
                
                new = {"Date": date_op, "Mois": date_op.month, "Annee": date_op.year, "Qui_Connecte": user_actuel, "Type": type_op, "Categorie": cat_finale, "Titre": titre_op, "Description": desc, "Montant": montant_op, "Paye_Par": p_par, "Imputation": imput, "Compte_Cible": c_tgt, "Projet_Epargne": p_epg, "Compte_Source": c_src}
                df = pd.concat([df, pd.DataFrame([new])], ignore_index=True); save_data_to_sheet(TAB_DATA, df); st.success("Enregistré !"); time.sleep(1); st.rerun()

    with subtabs[1]:
        c_s, c_e = st.columns([3,1])
        search = c_s.text_input("Rechercher...", key="search_j")
        if not df.empty:
            df_e = df.copy().sort_values(by="Date", ascending=False)
            if search: df_e = df_e[df_e.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
            c_e.download_button("Export", to_excel_download(df_e), f"journal_{mois_selection}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl", use_container_width=True)
            df_e.insert(0, "Suppr", False)
            ed = st.data_editor(df_e, use_container_width=True, hide_index=True, column_config={"Suppr": st.column_config.CheckboxColumn("Suppr", width="small")}, key="ed_j")
            if st.button("Supprimer sélection", type="primary", key="del_j"): save_data_to_sheet(TAB_DATA, ed[ed["Suppr"]==False].drop(columns=["Suppr"])); st.rerun()

    with subtabs[2]:
        st.markdown("### 💳 Abonnements")
        with st.expander("➕ Nouveau", expanded=False):
            with st.form("new_abo"):
                c1, c2, c3, c4 = st.columns(4)
                n = c1.text_input("Nom"); m = c2.number_input("Montant"); j = c3.number_input("Jour", 1, 31); f = c4.selectbox("Freq", FREQUENCES)
                c5, c6, c7 = st.columns(3)
                ca = c5.selectbox("Cat", cats_memoire.get("Dépense", [])); cp = c6.selectbox("Cpt", comptes_disponibles); imp = c7.selectbox("Imp", IMPUTATIONS)
                if st.form_submit_button("Ajouter"):
                    df_abonnements = pd.concat([df_abonnements, pd.DataFrame([{"Nom": n, "Montant": m, "Jour": j, "Categorie": ca, "Compte_Source": cp, "Proprietaire": user_actuel, "Imputation": imp, "Frequence": f}])], ignore_index=True); save_abonnements(df_abonnements); st.success("Ajouté !"); st.rerun()
        
        if not df_abonnements.empty:
            my_abos = df_abonnements[(df_abonnements["Proprietaire"]==user_actuel)|(df_abonnements["Imputation"].str.contains("Commun", na=False))].copy()
            abo_list = []
            to_gen = []
            for idx, r in my_abos.iterrows():
                paid = not df_mois[(df_mois["Titre"]==r["Nom"])&(df_mois["Montant"]==float(r["Montant"]))].empty
                abo_list.append({"idx": idx, "nom": r["Nom"], "montant": r["Montant"], "jour": r["Jour"], "cat": r["Categorie"], "statut": paid, "row": r})
                if not paid: to_gen.append(r)
            
            if to_gen and st.button(f"🔄 Générer {len(to_gen)} manquants", type="primary"):
                new_t = []
                for r in to_gen:
                    try: d = datetime(annee_selection, mois_selection, int(r["Jour"])).date()
                    except: d = datetime(annee_selection, mois_selection, 28).date()
                    paye = "Commun" if "Commun" in str(r["Imputation"]) else r["Proprietaire"]
                    new_t.append({"Date": d, "Mois": mois_selection, "Annee": annee_selection, "Qui_Connecte": r["Proprietaire"], "Type": "Dépense", "Categorie": r["Categorie"], "Titre": r["Nom"], "Description": "Abo Auto", "Montant": float(r["Montant"]), "Paye_Par": paye, "Imputation": r["Imputation"], "Compte_Cible": "", "Projet_Epargne": "", "Compte_Source": r["Compte_Source"]})
                df = pd.concat([df, pd.DataFrame(new_t)], ignore_index=True); save_data_to_sheet(TAB_DATA, df); st.rerun()
            
            st.write("")
            for i in range(0, len(abo_list), 3):
                cols = st.columns(3)
                for j, col in enumerate(cols):
                    if i+j < len(abo_list):
                        a = abo_list[i+j]
                        grad = "linear-gradient(135deg, #10B981, #059669)" if a["statut"] else "linear-gradient(135deg, #F59E0B, #D97706)"
                        badge = "✅ Payé" if a["statut"] else "⏳ En attente"
                        with col:
                            st.markdown(f"""<div style="background:{grad}; border-radius:16px; padding:15px; margin-bottom:10px; box-shadow:0 4px 10px rgba(0,0,0,0.1); color:white;">
                            <div style="font-size:12px; font-weight:700; text-transform:uppercase; background:rgba(255,255,255,0.2); padding:2px 8px; border-radius:10px; display:inline-block; margin-bottom:5px;">{badge}</div>
                            <div style="font-size:18px; font-weight:800;">{a['nom']}</div><div style="font-size:24px; font-weight:900;">{a['montant']:.0f} €</div>
                            <div style="font-size:12px; opacity:0.9;">📅 Jour {a['jour']} • {a['cat']}</div></div>""", unsafe_allow_html=True)
                            if st.button("Suppr", key=f"del_abo_{a['idx']}", use_container_width=True):
                                df_abonnements = df_abonnements.drop(a['idx']); save_abonnements(df_abonnements); st.rerun()

# 3. ANALYSE
with tabs[2]:
    page_header("Analyse")
    dt_curr = datetime(annee_selection, mois_selection, 1); dt_prev = dt_curr - relativedelta(months=1)
    df_prev = df[(df["Mois"]==dt_prev.month)&(df["Annee"]==dt_prev.year)]
    
    d_curr = df_mois[(df_mois["Qui_Connecte"]==user_actuel)&(df_mois["Type"]=="Dépense")]["Montant"].sum()
    d_prev = df_prev[(df_prev["Qui_Connecte"]==user_actuel)&(df_prev["Type"]=="Dépense")]["Montant"].sum()
    var = ((d_curr-d_prev)/d_prev*100) if d_prev>0 else 0
    
    c1,c2,c3 = st.columns(3)
    c1.metric("Dépenses", f"{d_curr:.0f} €", f"{var:+.1f}%", delta_color="inverse")
    
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

    with st.expander("Budget"):
        with st.form("add_bud"):
            c1,c2,c3,c4 = st.columns([2,2,2,1])
            s = c1.selectbox("Scope", ["Commun", "Pierre", "Elie"], key="sb"); ca = c2.selectbox("Cat", cats_memoire.get("Dépense", []), key="cb"); mo = c3.number_input("Max", key="mb")
            if c4.form_submit_button("Add"): objectifs_list.append({"Scope":s,"Categorie":ca,"Montant":mo}); save_objectifs_from_df(pd.DataFrame(objectifs_list)); st.rerun()
        
        b_data = []
        for r in objectifs_list:
            msk = (df_mois["Type"]=="Dépense")&(df_mois["Categorie"]==r["Categorie"])
            if r["Scope"]=="Commun": msk = msk&(df_mois["Imputation"]=="Commun (50/50)")
            else: msk = msk&(df_mois["Imputation"]=="Perso")&(df_mois["Qui_Connecte"]==(r["Scope"] if r["Scope"] in USERS else user_actuel))
            rl = df_mois[msk]["Montant"].sum()
            b_data.append({"Cat":r["Categorie"], "Scope":r["Scope"], "Bud":r["Montant"], "Real":rl, "Prg": min(rl/float(r["Montant"]) if float(r["Montant"])>0 else 0, 1.0)})
        st.dataframe(pd.DataFrame(b_data), column_config={"Prg": st.column_config.ProgressColumn("Etat", min_value=0, max_value=1)}, use_container_width=True, hide_index=True)

# 4. PREVISIONNEL
with tabs[3]:
    page_header("Prévisionnel")
    solde_dep = sum([SOLDES_ACTUELS.get(c,0) for c in comptes_disponibles if comptes_types_map.get(c)=="Courant"])
    abos_r = 0
    if not df_abonnements.empty:
        au = df_abonnements[(df_abonnements["Proprietaire"]==user_actuel)|(df_abonnements["Imputation"].str.contains("Commun", na=False))]
        for _,r in au.iterrows():
            if int(r["Jour"]) > datetime.now().day: abos_r += float(r["Montant"])/(2 if "Commun" in str(r["Imputation"]) else 1)
    
    dmoy = dep / max(1, datetime.now().day); jrest = 30 - datetime.now().day
    proj = solde_dep - abos_r - (dmoy * jrest)
    
    c1,c2,c3 = st.columns(3)
    c1.metric("Solde Actuel", f"{solde_dep:,.0f} €"); c2.metric("Abos Restants", f"-{abos_r:,.0f} €"); c3.metric("Fin de mois", f"{proj:,.0f} €", delta_color="normal" if proj>0 else "inverse")

# 5. EQUILIBRE
with tabs[4]:
    page_header("Couple")
    df_c = df_mois[df_mois["Imputation"].str.contains("Commun", na=False)]
    pp = df_c[df_c["Paye_Par"]=="Pierre"]["Montant"].sum(); ep = df_c[df_c["Paye_Par"]=="Elie"]["Montant"].sum()
    dif = (pp - ep)/2
    c1,c2,c3 = st.columns(3)
    c1.metric("Pierre", f"{pp:.0f} €"); c2.metric("Elie", f"{ep:.0f} €")
    if dif > 0: c3.info(f"Elie doit {abs(dif):.0f} € à Pierre")
    elif dif < 0: c3.info(f"Pierre doit {abs(dif):.0f} € à Elie")
    else: c3.success("Equilibré")

# 6. PATRIMOINE
with tabs[5]:
    page_header("Patrimoine")
    tot_ep = sum([SOLDES_ACTUELS.get(c,0) for c in comptes_disponibles if comptes_types_map.get(c)=="Épargne"])
    rev_m = df[(df["Qui_Connecte"]==user_actuel)&(df["Type"]=="Revenu")].groupby(["Mois","Annee"])["Montant"].sum().mean()
    if pd.isna(rev_m): rev_m = 0
    
    ep_prec = min(tot_ep, rev_m*3); ep_proj = max(0, tot_ep - ep_prec)
    
    c1,c2 = st.columns(2)
    with c1: 
        st.metric("Précaution (Obj: 3 mois)", f"{ep_prec:,.0f} €")
        st.progress(min(ep_prec/(rev_m*3) if rev_m>0 else 0, 1.0))
    with c2:
        st.metric("Dispo Projets", f"{ep_proj:,.0f} €")
    
    st.markdown("---")
    st.subheader("Projets")
    with st.expander("Nouveau"):
        n = st.text_input("Nom", key="np"); t = st.number_input("Cible", key="tp")
        if st.button("Créer", key="cp"): projets_config[n] = {"Cible": t, "Date_Fin": ""}; save_projets_targets(projets_config); st.rerun()
    
    if projets_config:
        for p, d in projets_config.items():
            s = df[(df["Projet_Epargne"]==p)&(df["Type"]=="Épargne")]["Montant"].sum()
            t = float(d["Cible"])
            st.write(f"**{p}** : {s:.0f} / {t:.0f} €"); st.progress(min(s/t if t>0 else 0, 1.0))

# 7. CONFIG
with tabs[6]:
    page_header("Config")
    t1,t2,t3 = st.tabs(["Comptes", "Cat", "Mots-Clés"])
    with t1:
        with st.form("ac"):
            n = st.text_input("Nom"); p = st.selectbox("Proprio", ["Pierre","Elie","Commun"]); ty = st.selectbox("Type", TYPES_COMPTE)
            if st.form_submit_button("Ajouter"):
                if p not in comptes_structure: comptes_structure[p]=[]
                comptes_structure[p].append(n); comptes_types_map[n]=ty; save_comptes_struct(comptes_structure, comptes_types_map); st.rerun()
    with t2:
        ty = st.selectbox("Type", TYPES, key="st"); nc = st.text_input("Cat")
        if st.button("Add"): cats_memoire.setdefault(ty, []).append(nc); save_config_cats(cats_memoire); st.rerun()
    with t3:
        with st.form("amc"):
            m = st.text_input("Mot"); c = st.selectbox("Cat", [x for l in cats_memoire.values() for x in l]); ty = st.selectbox("Type", TYPES, key="tmc"); co = st.selectbox("Cpt", comptes_disponibles)
            if st.form_submit_button("Lier"): mots_cles_map[m.lower()] = {"Categorie":c,"Type":ty,"Compte":co}; save_mots_cles(mots_cles_map); st.rerun()
