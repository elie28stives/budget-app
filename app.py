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

# --- DEFINITION DES COLONNES (Le fix est ici) ---
COLS_DATA = ["Date", "Mois", "Annee", "Qui_Connecte", "Type", "Categorie", "Titre", "Description", "Montant", "Paye_Par", "Imputation", "Compte_Cible", "Projet_Epargne", "Compte_Source"]
COLS_PAT = ["Date", "Mois", "Annee", "Compte", "Montant", "Proprietaire"]

# --- STYLE CSS (FULL WIDTH & MODERN) ---
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
        
        /* FULL WIDTH OPTIMIZATION */
        .main .block-container {
            padding-top: 1.5rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 100% !important;
        }
        
        #MainMenu, footer, header {visibility: hidden;}

        /* TABS STYLISÉS */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background: transparent;
            padding: 0px;
            border-bottom: 2px solid var(--border);
            margin-bottom: 20px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 45px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-bottom: none;
            color: var(--text-secondary);
            font-weight: 600;
            font-size: 14px;
            border-radius: 8px 8px 0 0;
            padding: 0 20px;
            transition: all 0.2s;
        }
        .stTabs [data-baseweb="tab"]:hover {
            color: var(--primary);
            background: #FFFBF9;
        }
        .stTabs [aria-selected="true"] {
            background: var(--primary) !important;
            color: white !important;
            border: none !important;
        }

        /* CARTES & MÉTRIQUES */
        div[data-testid="stMetric"], div.stDataFrame, div.stForm {
            background: var(--bg-card);
            padding: 20px;
            border-radius: 16px;
            border: 1px solid var(--border) !important;
            box-shadow: var(--shadow);
        }
        
        div[data-testid="stMetric"] label {
            font-size: 13px !important;
            font-weight: 600 !important;
            color: var(--text-secondary) !important;
            text-transform: uppercase;
        }
        
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            font-size: 28px !important;
            font-weight: 700 !important;
            color: var(--text-primary) !important;
        }

        /* SIDEBAR */
        section[data-testid="stSidebar"] {
            background: var(--bg-card);
            border-right: 1px solid var(--border);
        }

        /* INPUTS */
        .stTextInput input, .stNumberInput input, .stSelectbox > div > div {
            border-radius: 10px !important;
        }
        
        /* BOUTONS */
        div.stButton > button {
            background: var(--primary) !important;
            color: white !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            border: none !important;
            box-shadow: 0 2px 5px rgba(255, 107, 53, 0.3) !important;
        }
        div.stButton > button:hover {
            background: var(--primary-dark) !important;
            transform: translateY(-1px);
        }
        
        h1, h2, h3 { color: var(--text-primary) !important; font-family: 'Inter', sans-serif !important; }
    </style>
    """, unsafe_allow_html=True)

def page_header(title, subtitle=None):
    if subtitle:
        st.markdown(f"""<div style="margin-bottom: 20px;"><h2 style='font-size:28px; font-weight:800; color:#0A1929; margin-bottom:5px;'>{title}</h2><p style='font-size:15px; color:#6B7280;'>{subtitle}</p></div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"<h2 style='font-size:28px; font-weight:800; color:#0A1929; margin-bottom:20px;'>{title}</h2>", unsafe_allow_html=True)

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
st.set_page_config(page_title="Ma Banque V59", layout="wide", page_icon="🏦", initial_sidebar_state="expanded")
apply_custom_style()

df = load_data_from_sheet(TAB_DATA, COLS_DATA)
df_patrimoine = load_data_from_sheet(TAB_PATRIMOINE, COLS_PAT)
cats_memoire, comptes_structure, objectifs_list, df_abonnements, projets_config, comptes_types_map, mots_cles_map = process_configs()
def get_comptes_autorises(user): return comptes_structure.get(user, []) + comptes_structure.get("Commun", []) + ["Autre / Externe"]
all_my_accounts = get_comptes_autorises("Pierre") + get_comptes_autorises("Elie")
SOLDES_ACTUELS = calculer_soldes_reels(df, df_patrimoine, list(set(all_my_accounts)))

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### Menu")
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
        color = "#0066FF" if is_saving else ("#10B981" if val >= 0 else "#EF4444")
        icon = "💎" if is_saving else "💳"
        st.markdown(f"""<div style="border-left: 4px solid {color}; background: #FFFFFF; padding: 12px; border-radius: 8px; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);"><div style="font-size: 11px; color: #6B7280; font-weight: 600; text-transform: uppercase;">{icon} {name}</div><div style="font-size: 18px; font-weight: 700; color: #1F2937;">{val:,.2f} €</div></div>""", unsafe_allow_html=True)

    st.markdown(f"**COURANTS ({total_courant:,.0f}€)**"); 
    for n,v in list_courant: draw_account_card(n,v,False)
    st.write(""); st.markdown(f"**ÉPARGNE ({total_epargne:,.0f}€)**")
    for n,v in list_epargne: draw_account_card(n,v,True)

    st.markdown("---")
    date_jour = datetime.now()
    mois_nom = st.selectbox("Mois", MOIS_FR, index=date_jour.month-1)
    mois_selection = MOIS_FR.index(mois_nom) + 1
    annee_selection = st.number_input("Année", value=date_jour.year)
    df_mois = df[(df["Mois"] == mois_selection) & (df["Annee"] == annee_selection)]
    
    st.markdown("---")
    if st.button("🔄 Actualiser"): clear_cache(); st.rerun()

# --- MAIN TABS REORGANISÉS ---
tabs = st.tabs(["🏠 Accueil", "💸 Opérations", "📊 Analyses", "💰 Patrimoine", "⚙️ Réglages"])

# 1. ACCUEIL
with tabs[0]:
    page_header(f"Synthèse de {mois_nom}", f"Situation financière pour {user_actuel}")
    
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
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Revenus", f"{rev:,.0f} €")
    k2.metric("Dépenses", f"{(dep+com):,.0f} €")
    k3.metric("Épargne", f"{epg:,.0f} €")
    k4.markdown(f"""<div style="background:{rav_col}; padding:15px; border-radius:12px; color:white; text-align:center;"><div style="font-size:12px; font-weight:600;">RESTE À VIVRE</div><div style="font-size:24px; font-weight:800;">{rav:,.0f} €</div></div>""", unsafe_allow_html=True)
    
    st.markdown("---")
    
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("⏱️ 5 Dernières Transactions")
        recent = df[df['Qui_Connecte'] == user_actuel].sort_values(by='Date', ascending=False).head(5)
        if not recent.empty:
            for _, r in recent.iterrows():
                cc1, cc2 = st.columns([3, 1])
                cc1.write(f"**{r['Titre']}** ({r['Categorie']})"); cc1.caption(f"{r['Date']}")
                col_mt = "red" if r['Type'] == "Dépense" else "green"
                sig = "-" if r['Type'] == "Dépense" else "+"
                cc2.markdown(f"<div style='color:{col_mt}; font-weight:bold; text-align:right;'>{sig}{r['Montant']:.2f}€</div>", unsafe_allow_html=True)
                st.divider()
        else: st.info("Aucune activité récente.")
        
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
        else: st.success("Tout est sous contrôle !")

# 2. OPÉRATIONS
with tabs[1]:
    op1, op2, op3 = st.tabs(["Nouvelle Saisie", "Journal", "Abonnements"])
    with op1:
        c1, c2, c3 = st.columns(3)
        date_op = c1.date_input("Date", datetime.today())
        type_op = c2.selectbox("Type", TYPES)
        montant_op = c3.number_input("Montant (€)", min_value=0.0, step=0.01)
        c4, c5 = st.columns(2)
        titre_op = c4.text_input("Titre", placeholder="Libellé...")
        
        # Mots clés
        cat_finale = "Autre"; compte_auto = None; sugg = False
        if titre_op and mots_cles_map:
            for mc, data in mots_cles_map.items():
                if mc in titre_op.lower() and data["Type"] == type_op:
                    cat_finale = data["Categorie"]; compte_auto = data["Compte"]; sugg = True; break
        if sugg: c5.success(f"Suggestion : {cat_finale}")
        
        if type_op == "Virement Interne": cat_finale = "Virement"
        else:
            cats = cats_memoire.get(type_op, [])
            idx = cats.index(cat_finale) if cat_finale in cats else 0
            cat_sel = c5.selectbox("Catégorie", cats + ["Autre (nouvelle)"], index=idx)
            cat_finale = c5.text_input("Nom", key="cn") if cat_sel == "Autre (nouvelle)" else cat_sel
        
        c_src=""; c_tgt=""; p_epg=""; p_par=user_actuel; imput="Perso"
        if type_op == "Épargne":
            ce1, ce2, ce3 = st.columns(3)
            c_src = ce1.selectbox("Source", comptes_disponibles)
            c_tgt = ce2.selectbox("Cible", [c for c in comptes_disponibles if comptes_types_map.get(c) == "Épargne"] or comptes_disponibles)
            p_sel = ce3.selectbox("Projet", list(projets_config.keys())+["Nouveau","Aucun"])
            p_epg = st.text_input("Nouveau Projet") if p_sel == "Nouveau" else ("" if p_sel=="Aucun" else p_sel)
        elif type_op == "Virement Interne":
            cv1, cv2 = st.columns(2); c_src = cv1.selectbox("Débit", comptes_disponibles); c_tgt = cv2.selectbox("Crédit", comptes_disponibles); p_par = "Virement"; imput = "Neutre"
        else:
            cc1, cc2, cc3 = st.columns(3)
            idx_c = comptes_disponibles.index(compte_auto) if compte_auto in comptes_disponibles else 0
            c_src = cc1.selectbox("Compte", comptes_disponibles, index=idx_c)
            p_par = cc2.selectbox("Payé par", ["Pierre", "Elie", "Commun"])
            imput = cc3.radio("Imputation", IMPUTATIONS)
            if imput == "Commun (Autre %)": pc = st.slider("% Pierre", 0, 100, 50); imput = f"Commun ({pc}/{100-pc})"
            
        if st.button("Enregistrer Transaction", type="primary", use_container_width=True):
            new = {"Date": date_op, "Mois": date_op.month, "Annee": date_op.year, "Qui_Connecte": user_actuel, "Type": type_op, "Categorie": cat_finale, "Titre": titre_op, "Description": "", "Montant": montant_op, "Paye_Par": p_par, "Imputation": imput, "Compte_Cible": c_tgt, "Projet_Epargne": p_epg, "Compte_Source": c_src}
            df = pd.concat([df, pd.DataFrame([new])], ignore_index=True); save_data_to_sheet(TAB_DATA, df); st.success("Enregistré !"); time.sleep(1); st.rerun()

    with op2:
        c_s, c_e = st.columns([3,1])
        search = c_s.text_input("Rechercher...")
        if not df.empty:
            df_e = df.copy().sort_values(by="Date", ascending=False)
            if search: df_e = df_e[df_e.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
            c_e.download_button("Export Excel", to_excel_download(df_e), f"journal.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            df_e.insert(0, "Suppr", False)
            ed = st.data_editor(df_e, use_container_width=True, hide_index=True, column_config={"Suppr": st.column_config.CheckboxColumn("Suppr", width="small")})
            if st.button("Supprimer sélection"): save_data_to_sheet(TAB_DATA, ed[ed["Suppr"]==False].drop(columns=["Suppr"])); st.rerun()

    with op3:
        st.markdown("### Abonnements")
        with st.expander("Nouveau", expanded=False):
            with st.form("new_abo"):
                c1, c2, c3, c4 = st.columns(4)
                n = c1.text_input("Nom"); m = c2.number_input("Montant"); j = c3.number_input("Jour", 1, 31); f = c4.selectbox("Freq", FREQUENCES)
                c5, c6, c7 = st.columns(3)
                ca = c5.selectbox("Cat", cats_memoire.get("Dépense", [])); cp = c6.selectbox("Cpt", comptes_disponibles); imp = c7.selectbox("Imp", IMPUTATIONS)
                if st.form_submit_button("Ajouter"):
                    df_abonnements = pd.concat([df_abonnements, pd.DataFrame([{"Nom": n, "Montant": m, "Jour": j, "Categorie": ca, "Compte_Source": cp, "Proprietaire": user_actuel, "Imputation": imp, "Frequence": f}])], ignore_index=True); save_abonnements(df_abonnements); st.rerun()
        
        if not df_abonnements.empty:
            my_abos = df_abonnements[(df_abonnements["Proprietaire"]==user_actuel)|(df_abonnements["Imputation"].str.contains("Commun", na=False))].copy()
            abo_list = []
            to_gen = []
            for idx, r in my_abos.iterrows():
                paid = not df_mois[(df_mois["Titre"]==r["Nom"])&(df_mois["Montant"]==float(r["Montant"]))].empty
                abo_list.append({"idx": idx, "nom": r["Nom"], "montant": r["Montant"], "jour": r["Jour"], "statut": paid, "row": r})
                if not paid: to_gen.append(r)
            
            if to_gen and st.button(f"🔄 Générer {len(to_gen)} manquants"):
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
                        badge = "Payé" if a["statut"] else "À venir"
                        with col:
                            st.markdown(f"""<div style="background:{grad}; border-radius:12px; padding:15px; margin-bottom:10px; color:white;"><div style="font-size:12px; font-weight:700;">{badge}</div><div style="font-size:18px; font-weight:800;">{a['nom']}</div><div style="font-size:20px; font-weight:900;">{a['montant']:.0f} €</div><div style="font-size:12px; opacity:0.9;">Jour {a['jour']}</div></div>""", unsafe_allow_html=True)
                            if st.button("Suppr", key=f"del_abo_{a['idx']}", use_container_width=True):
                                df_abonnements = df_abonnements.drop(a['idx']); save_abonnements(df_abonnements); st.rerun()

# 3. ANALYSES
with tabs[2]:
    an1, an2, an3 = st.tabs(["Graphiques", "Équilibre Couple", "Prévisionnel"])
    with an1:
        st.subheader("Répartition (Pie Chart)")
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
        c1,c2,c3 = st.columns(3)
        c1.metric("Pierre", f"{pp:.0f} €"); c2.metric("Elie", f"{ep:.0f} €")
        if dif > 0: c3.info(f"Elie doit {abs(dif):.0f} € à Pierre")
        elif dif < 0: c3.info(f"Pierre doit {abs(dif):.0f} € à Elie")
        else: c3.success("Equilibré")

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
    page_header("Patrimoine")
    tot_ep = sum([SOLDES_ACTUELS.get(c,0) for c in comptes_disponibles if comptes_types_map.get(c)=="Épargne"])
    c1,c2 = st.columns(2)
    with c1: st.metric("Épargne Totale", f"{tot_ep:,.0f} €")
    
    st.subheader("Projets")
    with st.expander("Nouveau"):
        n = st.text_input("Nom", key="pn"); t = st.number_input("Cible", key="pt")
        if st.button("Créer", key="pb"): projets_config[n] = {"Cible": t, "Date_Fin": ""}; save_projets_targets(projets_config); st.rerun()
    
    if projets_config:
        for p, d in projets_config.items():
            s = df[(df["Projet_Epargne"]==p)&(df["Type"]=="Épargne")]["Montant"].sum()
            t = float(d["Cible"])
            st.write(f"**{p}** : {s:.0f} / {t:.0f} €"); st.progress(min(s/t if t>0 else 0, 1.0))
            
    st.subheader("Relevé de compte")
    with st.form("rel"):
        c1, c2 = st.columns(2); d = c1.date_input("Date"); c = c2.selectbox("Compte", comptes_disponibles); m = st.number_input("Solde Réel")
        if st.form_submit_button("Enregistrer"):
            df_patrimoine = pd.concat([df_patrimoine, pd.DataFrame([{"Date": d, "Mois": d.month, "Annee": d.year, "Compte": c, "Montant": m, "Proprietaire": user_actuel}])], ignore_index=True); save_data_to_sheet(TAB_PATRIMOINE, df_patrimoine); st.rerun()

# 5. CONFIG
with tabs[4]:
    page_header("Réglages")
    t1,t2,t3 = st.tabs(["Comptes", "Catégories", "Mots-Clés"])
    with t1:
        with st.form("ac"):
            n = st.text_input("Nom"); p = st.selectbox("Proprio", ["Pierre","Elie","Commun"]); ty = st.selectbox("Type", TYPES_COMPTE)
            if st.form_submit_button("Ajouter"):
                if p not in comptes_structure: comptes_structure[p]=[]
                comptes_structure[p].append(n); comptes_types_map[n]=ty; save_comptes_struct(comptes_structure, comptes_types_map); st.rerun()
        st.write(comptes_structure)
    with t2:
        ty = st.selectbox("Type", TYPES, key="st"); nc = st.text_input("Cat")
        if st.button("Add"): cats_memoire.setdefault(ty, []).append(nc); save_config_cats(cats_memoire); st.rerun()
    with t3:
        with st.form("amc"):
            m = st.text_input("Mot"); c = st.selectbox("Cat", [x for l in cats_memoire.values() for x in l]); ty = st.selectbox("Type", TYPES, key="tmc"); co = st.selectbox("Cpt", comptes_disponibles)
            if st.form_submit_button("Lier"): mots_cles_map[m.lower()] = {"Categorie":c,"Type":ty,"Compte":co}; save_mots_cles(mots_cles_map); st.rerun()
