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

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================
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
TYPES_COMPTE = ["Courant", "Épargne"]
MOIS_FR = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

COLS_DATA = ["Date", "Mois", "Annee", "Qui_Connecte", "Type", "Categorie", "Titre", "Description", "Montant", "Paye_Par", "Imputation", "Compte_Cible", "Projet_Epargne", "Compte_Source"]
COLS_PAT = ["Date", "Mois", "Annee", "Compte", "Montant", "Proprietaire"]

# ==============================================================================
# 2. CSS & UI
# ==============================================================================
def apply_custom_style():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        :root { --primary: #2C3E50; --bg-main: #F4F6F8; --bg-card: #FFFFFF; --text: #1F2937; --border: #E5E7EB; }
        .stApp { background-color: var(--bg-main); font-family: 'Inter', sans-serif; color: var(--text); }
        .main .block-container { padding-top: 2rem !important; max-width: 1400px; }
        #MainMenu, footer, header {visibility: hidden;}
        
        /* TABS */
        .stTabs [data-baseweb="tab-list"] { gap: 20px; background: transparent; border-bottom: 2px solid var(--border); }
        .stTabs [data-baseweb="tab"] { height: 45px; background: transparent; border: none; color: #6B7280; font-weight: 600; }
        .stTabs [aria-selected="true"] { color: var(--primary) !important; border-bottom: 3px solid var(--primary) !important; }
        
        /* CARDS */
        div[data-testid="stMetric"], div.stDataFrame, div.stForm, div[data-testid="stExpander"] {
            background: var(--bg-card); padding: 20px; border-radius: 12px; border: 1px solid var(--border) !important; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }
        section[data-testid="stSidebar"] { background: var(--bg-card); border-right: 1px solid var(--border); }
        
        /* BUTTONS & INPUTS */
        div.stButton > button { background: var(--primary) !important; color: white !important; border-radius: 8px !important; font-weight: 500 !important; border: none; }
        .stTextInput input, .stNumberInput input, .stSelectbox > div > div { border-radius: 8px !important; border-color: var(--border); }
        
        /* CUSTOM CLASSES */
        .tx-card { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #F3F4F6; }
        .proj-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 15px; margin-bottom: 10px; }
        .cat-badge { display: inline-block; padding: 4px 10px; border-radius: 15px; font-size: 12px; font-weight: 600; margin: 0 5px 5px 0; border: 1px solid transparent; }
        .cat-badge.depense { background-color: #FFF1F2; color: #991b1b; }
        .cat-badge.revenu { background-color: #ECFDF5; color: #065f46; }
        .cat-badge.epargne { background-color: #EFF6FF; color: #1e40af; }
    </style>
    """, unsafe_allow_html=True)

def page_header(title, subtitle=None):
    st.markdown(f"<h2 style='font-size:26px; font-weight:700; color:#2C3E50; margin-bottom:5px;'>{title}</h2>", unsafe_allow_html=True)
    if subtitle: st.markdown(f"<p style='font-size:14px; color:#6B7280; margin-bottom:20px;'>{subtitle}</p>", unsafe_allow_html=True)

# ==============================================================================
# 3. BACKEND (GSPREAD AVEC RETRY)
# ==============================================================================
@st.cache_resource
def get_client():
    try:
        creds = dict(st.secrets["gcp_service_account"])
        creds["private_key"] = creds["private_key"].replace("\\n", "\n")
        return gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds, ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]))
    except: return None

def get_ws(client, tab):
    try: return client.open(SHEET_NAME).worksheet(tab)
    except: return client.open(SHEET_NAME).add_worksheet(title=tab, rows="100", cols="20")

@st.cache_data(ttl=600, show_spinner=False)
def load_data(tab, cols):
    c = get_client()
    if not c: return pd.DataFrame(columns=cols)
    for i in range(3): # Retry logic
        try:
            data = get_ws(c, tab).get_all_records()
            df = pd.DataFrame(data)
            if df.empty: return pd.DataFrame(columns=cols)
            for col in cols: 
                if col not in df.columns: df[col] = ""
            if "Date" in df.columns: df["Date"] = pd.to_datetime(df["Date"], errors='coerce').dt.date
            return df
        except Exception as e:
            if "429" in str(e): time.sleep(2); continue
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_data(tab, df):
    c = get_client()
    ws = get_ws(c, tab)
    df_s = df.copy()
    if "Date" in df_s.columns: df_s["Date"] = df_s["Date"].astype(str)
    for i in range(3):
        try:
            ws.clear()
            ws.update([df_s.columns.values.tolist()] + df_s.values.tolist())
            st.cache_data.clear()
            return
        except Exception as e:
            if "429" in str(e): time.sleep(2); continue
            st.error(f"Erreur sauvegarde: {e}"); return

@st.cache_data(ttl=600, show_spinner=False)
def load_all_configs():
    return (
        load_data(TAB_CONFIG, ["Type", "Categorie"]),
        load_data(TAB_COMPTES, ["Proprietaire", "Compte", "Type"]),
        load_data(TAB_OBJECTIFS, ["Scope", "Categorie", "Montant"]),
        load_data(TAB_ABONNEMENTS, ["Nom", "Montant", "Jour", "Categorie", "Compte_Source", "Proprietaire", "Imputation", "Frequence"]),
        load_data(TAB_PROJETS, ["Projet", "Cible", "Date_Fin", "Proprietaire"]),
        load_data(TAB_MOTS_CLES, ["Mot_Cle", "Categorie", "Type", "Compte"])
    )

# ==============================================================================
# 4. LOGIQUE
# ==============================================================================
def init_state():
    if 'op_date' not in st.session_state: st.session_state.op_date = datetime.today()

def to_excel(df):
    out = BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as writer:
        df_x = df.copy()
        if "Date" in df_x.columns: df_x["Date"] = df_x["Date"].astype(str)
        df_x.to_excel(writer, index=False, sheet_name='Data')
    return out.getvalue()

def calc_soldes(df_t, df_p, comptes):
    soldes = {}
    for c in comptes:
        rel, d_rel = 0.0, pd.to_datetime("2000-01-01").date()
        if not df_p.empty:
            df_c = df_p[df_p["Compte"]==c]
            if not df_c.empty:
                last = df_c.sort_values(by="Date", ascending=False).iloc[0]
                rel, d_rel = float(last["Montant"]), last["Date"]
        mouv = 0.0
        if not df_t.empty:
            dft = df_t[df_t["Date"] > d_rel]
            deb = dft[(dft["Compte_Source"]==c) & (dft["Type"].isin(["Dépense","Investissement"]))]["Montant"].sum()
            vout = dft[(dft["Compte_Source"]==c) & (dft["Type"].isin(["Virement Interne","Épargne"]))]["Montant"].sum()
            cred = dft[(dft["Compte_Source"]==c) & (dft["Type"]=="Revenu")]["Montant"].sum()
            vin = dft[(dft["Compte_Cible"]==c) & (dft["Type"].isin(["Virement Interne","Épargne"]))]["Montant"].sum()
            mouv = cred + vin - deb - vout
        soldes[c] = rel + mouv
    return soldes

def process_data():
    raw = load_all_configs()
    
    # Catégories
    cats = {k: [] for k in TYPES}
    if not raw[0].empty:
        for _, r in raw[0].iterrows():
            if r["Type"] in cats and r["Categorie"] not in cats[r["Type"]]: 
                cats[r["Type"]].append(r["Categorie"])
    if not cats["Dépense"]: cats["Dépense"] = ["Alimentation", "Loyer"]
    
    # Comptes
    comptes, c_types = {}, {}
    if not raw[1].empty:
        for _, r in raw[1].iterrows():
            comptes.setdefault(r["Proprietaire"], []).append(r["Compte"])
            c_types[r["Compte"]] = r.get("Type", "Courant")
            
    # Projets
    projets = {}
    if not raw[4].empty:
        for _, r in raw[4].iterrows():
            projets[r["Projet"]] = {"Cible": float(r["Cible"]), "Proprietaire": r.get("Proprietaire", "Commun"), "Date_Fin": r["Date_Fin"]}
            
    # Mots clés
    mots = {r["Mot_Cle"].lower(): {"Categorie":r["Categorie"], "Type":r["Type"], "Compte":r["Compte"]} for _, r in raw[5].iterrows()} if not raw[5].empty else {}
    
    return cats, comptes, raw[2].to_dict('records'), raw[3], projets, c_types, mots

# ==============================================================================
# 5. APP MAIN
# ==============================================================================
st.set_page_config(page_title="Ma Banque V79", layout="wide", page_icon="🏦")
apply_custom_style()
init_state()

# Chargement données
df = load_data(TAB_DATA, COLS_DATA)
df_patrimoine = load_data(TAB_PATRIMOINE, COLS_PAT)
cats_memoire, comptes_structure, objectifs_list, df_abonnements, projets_config, comptes_types_map, mots_cles_map = process_data()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### Menu")
    user_actuel = st.selectbox("Utilisateur", USERS)
    st.markdown("---")
    
    cpt_visibles = comptes_structure.get(user_actuel, []) + comptes_structure.get("Commun", [])
    cpt_calc = list(set(cpt_visibles + ["Autre / Externe"]))
    soldes = calc_soldes(df, df_patrimoine, cpt_calc)
    
    lst_c, lst_e = [], []
    tot_c, tot_e = 0, 0
    for c in cpt_visibles:
        v = soldes.get(c, 0.0)
        if comptes_types_map.get(c) == "Épargne": tot_e += v; lst_e.append((c,v))
        else: tot_c += v; lst_c.append((c,v))
        
    def show_c(n, v, e):
        cl = "#0066FF" if e else ("#10B981" if v>=0 else "#EF4444")
        st.markdown(f"""<div style="background:white; border-left:4px solid {cl}; padding:10px; margin-bottom:5px; border-radius:4px; box-shadow:0 1px 2px #00000010;"><div style="font-size:11px; color:#666;">{n}</div><div style="font-weight:bold; color:#333;">{v:,.2f} €</div></div>""", unsafe_allow_html=True)

    st.markdown(f"**COURANTS ({tot_c:,.0f}€)**"); 
    for n,v in lst_c: show_c(n,v,False)
    st.write(""); st.markdown(f"**ÉPARGNE ({tot_e:,.0f}€)**")
    for n,v in lst_e: show_c(n,v,True)

    st.markdown("---")
    d_jour = datetime.now()
    m_nom = st.selectbox("Mois", MOIS_FR, index=d_jour.month-1)
    m_sel = MOIS_FR.index(m_nom) + 1
    a_sel = st.number_input("Année", value=d_jour.year)
    df_mois = df[(df["Mois"] == m_sel) & (df["Annee"] == a_sel)]
    
    st.markdown("---")
    if st.button("Actualiser", use_container_width=True): st.cache_data.clear(); st.rerun()

# --- TABS ---
tabs = st.tabs(["Accueil", "Opérations", "Analyses", "Patrimoine", "Réglages"])

# TAB 1: ACCUEIL
with tabs[0]:
    page_header(f"Synthèse - {m_nom}", f"Compte de {user_actuel}")
    
    rev = df_mois[(df_mois["Qui_Connecte"]==user_actuel) & (df_mois["Type"]=="Revenu")]["Montant"].sum()
    dep = df_mois[(df_mois["Qui_Connecte"]==user_actuel) & (df_mois["Type"]=="Dépense") & (df_mois["Imputation"]=="Perso")]["Montant"].sum()
    epg = df_mois[(df_mois["Qui_Connecte"]==user_actuel) & (df_mois["Type"]=="Épargne")]["Montant"].sum()
    com = df_mois[df_mois["Imputation"]=="Commun (50/50)"]["Montant"].sum() / 2
    
    fixe = 0
    if not df_abonnements.empty:
        au = df_abonnements[(df_abonnements["Proprietaire"]==user_actuel)|(df_abonnements["Imputation"].str.contains("Commun", na=False))]
        for _,r in au.iterrows(): fixe += float(r["Montant"])/(2 if "Commun" in str(r["Imputation"]) else 1)
    
    rav = rev - fixe - dep - com
    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric("Revenus", f"{rev:,.0f} €"); k2.metric("Fixe", f"{fixe:,.0f} €"); k3.metric("Dépenses", f"{(dep+com):,.0f} €"); k4.metric("Épargne", f"{epg:,.0f} €")
    col = "#10B981" if rav>0 else "#EF4444"
    k5.markdown(f"""<div style="background:{col}; padding:15px; border-radius:12px; color:white; text-align:center;"><div style="font-size:11px; font-weight:bold;">RESTE À VIVRE</div><div style="font-size:24px; font-weight:bold;">{rav:,.0f} €</div></div>""", unsafe_allow_html=True)
    
    st.markdown("---")
    c1, c2 = st.columns([3, 2])
    with c1:
        h1, h2 = st.columns([1,1])
        with h1: st.subheader("Activités")
        with h2: filt = st.radio("Filtre", ["Tout", "Sorties", "Entrées"], horizontal=True, label_visibility="collapsed", key="fh")
        
        dat = df[df['Qui_Connecte'] == user_actuel].sort_values(by='Date', ascending=False)
        if filt=="Sorties": dat = dat[dat['Type'].isin(["Dépense", "Virement Interne", "Épargne", "Investissement"])]
        elif filt=="Entrées": dat = dat[dat['Type']=="Revenu"]
        rec = dat.head(5)
        
        if not rec.empty:
            for _, r in rec.iterrows():
                is_d = r['Type'] in ["Dépense", "Virement Interne", "Épargne", "Investissement"]
                bg = "#FFF1F2" if is_d else "#ECFDF5"; txt = "#E11D48" if is_d else "#059669"; sig = "-" if is_d else "+"
                ic = "💸" if is_d else "💰"
                if r['Type'] == "Épargne": ic = "🐷"
                st.markdown(f"""
                <div class="tx-card">
                    <div style="display:flex; align-items:center; gap:15px;">
                        <div style="width:40px; height:40px; border-radius:10px; background:{bg}; display:flex; align-items:center; justify-content:center; font-size:18px;">{ic}</div>
                        <div><div style="font-weight:600; color:#333; font-size:14px;">{r['Titre']}</div><div style="font-size:12px; color:#888;">{r['Date'].strftime('%d/%m')} • {r['Categorie']}</div></div>
                    </div>
                    <div style="font-weight:700; font-size:15px; color:{txt};">{sig} {r['Montant']:,.2f} €</div>
                </div>
                """, unsafe_allow_html=True)
        else: st.info("Aucune activité.")
        
    with c2:
        st.subheader("Alertes")
        op = [o for o in objectifs_list if o["Scope"] in ["Perso", user_actuel]]
        dff = df_mois[(df_mois["Type"]=="Dépense") & (df_mois["Imputation"]=="Perso") & (df_mois["Qui_Connecte"]==user_actuel)]
        has_a = False
        for o in op:
            r = dff[dff["Categorie"]==o["Categorie"]]["Montant"].sum()
            b = float(o["Montant"])
            if b>0 and r/b>0.75:
                has_a = True; st.write(f"**{o['Categorie']}** : {r:.0f}/{b:.0f} €"); st.progress(min(r/b, 1.0))
        if not has_a: st.success("Budget OK")

# TAB 2: OPÉRATIONS
with tabs[1]:
    op1, op2, op3 = st.tabs(["Saisie", "Journal", "Abonnements"])
    with op1:
        st.subheader("Nouvelle Transaction")
        c1, c2, c3 = st.columns(3)
        d_op = c1.date_input("Date", datetime.today()); t_op = c2.selectbox("Type", TYPES); m_op = c3.number_input("Montant", min_value=0.0, step=0.01)
        
        c4, c5 = st.columns(2)
        tit = c4.text_input("Titre"); cat_f = "Autre"; cpt_a = None
        if tit and mots_cles_map:
            for mc, d in mots_cles_map.items():
                if mc in tit.lower() and d["Type"] == t_op: cat_f=d["Categorie"]; cpt_a=d["Compte"]; break
        
        cats = cats_memoire.get(t_op, []); idx_c = cats.index(cat_f) if cat_f in cats else 0
        cat_s = c5.selectbox("Catégorie", cats + ["Autre (nouvelle)"], index=idx_c)
        fin_c = st.text_input("Nom catégorie") if cat_s == "Autre (nouvelle)" else cat_s
        
        st.write("")
        cc1, cc2, cc3 = st.columns(3)
        idx_cp = cpt_visibles.index(cpt_a) if (cpt_a and cpt_a in cpt_visibles) else 0
        c_src = cc1.selectbox("Compte Source", cpt_visibles, index=idx_cp)
        imp = cc2.radio("Imputation", IMPUTATIONS, horizontal=True)
        
        fin_imp = imp
        if imp == "Commun (Autre %)":
            pt = cc3.slider("Part Pierre %", 0, 100, 50); fin_imp = f"Commun ({pt}/{100-pt})"
        elif t_op == "Virement Interne": fin_imp = "Neutre"
        
        c_tgt, p_epg = "", ""
        if t_op == "Épargne":
            ce1, ce2 = st.columns(2)
            c_tgt = ce1.selectbox("Vers Compte", [c for c in cpt_visibles if comptes_types_map.get(c)=="Épargne"])
            ps = ce2.selectbox("Projet", ["Aucun"]+list(projets_config.keys()))
            if ps!="Aucun": p_epg = ps
        elif t_op == "Virement Interne": c_tgt = st.selectbox("Vers Compte", cpt_visibles)
            
        if st.button("Valider Transaction", type="primary", use_container_width=True):
            if cat_s == "Autre (nouvelle)" and fin_c:
                cats_memoire.setdefault(t_op, []).append(fin_c); save_data(TAB_CONFIG, pd.DataFrame([{"Type": t, "Categorie": c} for t, l in cats_memoire.items() for c in l]))
            if t_op=="Épargne" and p_epg and p_epg not in projets_config:
                projets_config[p_epg]={"Cible":0.0, "Date_Fin":"", "Proprietaire": user_actuel}
                rows = []
                for k, v in projets_config.items(): rows.append({"Projet": k, "Cible": v["Cible"], "Date_Fin": v["Date_Fin"], "Proprietaire": v.get("Proprietaire", "Commun")})
                save_data(TAB_PROJETS, pd.DataFrame(rows))
            
            nr = {"Date": d_op, "Mois": d_op.month, "Annee": d_op.year, "Qui_Connecte": user_actuel, "Type": t_op, "Categorie": fin_c, "Titre": tit, "Description": "", "Montant": m_op, "Paye_Par": user_actuel, "Imputation": fin_imp, "Compte_Cible": c_tgt, "Projet_Epargne": p_epg, "Compte_Source": c_src}
            df = pd.concat([df, pd.DataFrame([nr])], ignore_index=True); save_data(TAB_DATA, df); st.success("Enregistré !"); time.sleep(0.5); st.rerun()

    with op2:
        sch = st.text_input("Chercher")
        if not df.empty:
            dfe = df.copy().sort_values(by="Date", ascending=False)
            if sch: dfe = dfe[dfe.apply(lambda r: str(r).lower().find(sch.lower())>-1, axis=1)]
            st.download_button("Excel", to_excel(dfe), "journal.xlsx")
            dfe.insert(0, "X", False)
            ed = st.data_editor(dfe, hide_index=True, column_config={"X": st.column_config.CheckboxColumn("Suppr", width="small")})
            if st.button("Supprimer"): save_data(TAB_DATA, ed[ed["X"]==False].drop(columns=["X"])); st.rerun()

    with op3:
        # ABONNEMENTS (NOUVEAU DESIGN)
        c_head, c_btn = st.columns([3, 1])
        with c_head: st.subheader("Mes Abonnements")
        with c_btn: 
            if st.button("➕ Nouveau", use_container_width=True): st.session_state['new_abo'] = not st.session_state.get('new_abo', False)

        if st.session_state.get('new_abo', False):
            with st.container():
                with st.form("na"):
                    a1,a2,a3 = st.columns(3); n=a1.text_input("Nom"); m=a2.number_input("Montant"); j=a3.number_input("Jour", 1, 31)
                    a4,a5 = st.columns(2); c=a4.selectbox("Cat", cats_memoire.get("Dépense", [])); cp=a5.selectbox("Cpt", cpt_visibles)
                    im = st.selectbox("Imp", IMPUTATIONS)
                    if st.form_submit_button("Ajouter"):
                        df_abonnements = pd.concat([df_abonnements, pd.DataFrame([{"Nom": n, "Montant": m, "Jour": j, "Categorie": c, "Compte_Source": cp, "Proprietaire": user_actuel, "Imputation": im, "Frequence": "Mensuel"}])], ignore_index=True); save_data(TAB_ABONNEMENTS, df_abonnements); st.session_state['new_abo']=False; st.rerun()
        
        if not df_abonnements.empty:
            ma = df_abonnements[df_abonnements["Proprietaire"]==user_actuel]
            # Generation
            to_gen = []
            for ix, r in ma.iterrows():
                paid = not df_mois[(df_mois["Titre"].str.lower()==r["Nom"].lower())&(df_mois["Montant"]==float(r["Montant"]))].empty
                if not paid: to_gen.append(r)
            if to_gen:
                if st.button(f"🚀 Générer {len(to_gen)} transactions", type="primary"):
                    nt = []
                    for r in to_gen:
                        try: d = datetime(a_sel, m_sel, int(r["Jour"])).date()
                        except: d = datetime(a_sel, m_sel, 28).date()
                        nt.append({"Date": d, "Mois": m_sel, "Annee": a_sel, "Qui_Connecte": r["Proprietaire"], "Type": "Dépense", "Categorie": r["Categorie"], "Titre": r["Nom"], "Description": "Auto", "Montant": float(r["Montant"]), "Paye_Par": r["Proprietaire"], "Imputation": r["Imputation"], "Compte_Cible": "", "Projet_Epargne": "", "Compte_Source": r["Compte_Source"]})
                    df = pd.concat([df, pd.DataFrame(nt)], ignore_index=True); save_data(TAB_DATA, df); st.rerun()

            # Cartes
            cols = st.columns(3)
            for i, (idx, r) in enumerate(ma.iterrows()):
                col = cols[i % 3]
                with col:
                    paid = not df_mois[(df_mois["Titre"].str.lower()==r["Nom"].lower())&(df_mois["Montant"]==float(r["Montant"]))].empty
                    sc = "#10B981" if paid else "#F59E0B"; sb = "#ECFDF5" if paid else "#FFFBEB"; stt = "PAYÉ" if paid else "ATTENTE"
                    
                    if not st.session_state.get(f"ed_a_{idx}", False):
                        st.markdown(f"""
                        <div style="background:white; border:1px solid #E5E7EB; border-radius:16px; padding:15px; margin-bottom:15px; box-shadow:0 2px 5px rgba(0,0,0,0.02);">
                            <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                                <div style="width:30px; height:30px; background:{sb}; color:{sc}; border-radius:50%; display:flex; justify-content:center; align-items:center; font-weight:bold;">{r['Nom'][0].upper()}</div>
                                <div style="background:{sb}; color:{sc}; font-size:10px; padding:4px 8px; border-radius:10px; font-weight:bold;">{stt}</div>
                            </div>
                            <div style="font-weight:bold; font-size:15px;">{r['Nom']}</div>
                            <div style="font-size:18px; font-weight:800; margin-bottom:8px;">{float(r['Montant']):.2f} €</div>
                            <div style="font-size:11px; color:grey; border-top:1px solid #eee; padding-top:5px;">📅 J{r['Jour']} • {r['Categorie']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        c1, c2 = st.columns(2)
                        if c1.button("✏️", key=f"e_{idx}"): st.session_state[f"ed_a_{idx}"]=True; st.rerun()
                        if c2.button("🗑️", key=f"d_{idx}"): df_abonnements=df_abonnements.drop(idx); save_data(TAB_ABONNEMENTS, df_abonnements); st.rerun()
                    else:
                        with st.form(f"fe_{idx}"):
                            nn=st.text_input("Nom", value=r['Nom']); nm=st.number_input("Montant", value=float(r['Montant'])); nj=st.number_input("Jour", value=int(r['Jour']))
                            if st.form_submit_button("💾"):
                                df_abonnements.at[idx,'Nom']=nn; df_abonnements.at[idx,'Montant']=nm; df_abonnements.at[idx,'Jour']=nj; save_data(TAB_ABONNEMENTS, df_abonnements); st.session_state[f"ed_a_{idx}"]=False; st.rerun()

# TAB 3: ANALYSES
with tabs[2]:
    a1, a2 = st.tabs(["Vue Globale", "Budgets"])
    with a1:
        if not df_mois.empty:
            fig = px.pie(df_mois[df_mois["Type"]=="Dépense"], values="Montant", names="Categorie", hole=0.5)
            st.plotly_chart(fig, use_container_width=True)
            
            dr = df_mois[df_mois["Type"]=="Revenu"]; dd = df_mois[df_mois["Type"]=="Dépense"]
            rf = dr.groupby(["Categorie", "Compte_Source"])["Montant"].sum().reset_index()
            dfd = dd.groupby(["Compte_Source", "Categorie"])["Montant"].sum().reset_index()
            lbs = list(set(rf["Categorie"].tolist()+rf["Compte_Source"].tolist()+dfd["Compte_Source"].tolist()+dfd["Categorie"].tolist()))
            lmp = {n:i for i,n in enumerate(lbs)}
            s,t,v,c = [],[],[],[]
            for _,r in rf.iterrows(): s.append(lmp[r["Categorie"]]); t.append(lmp[r["Compte_Source"]]); v.append(r["Montant"]); c.append("green")
            for _,r in dfd.iterrows(): 
                if r["Compte_Source"] in lmp: s.append(lmp[r["Compte_Source"]]); t.append(lmp[r["Categorie"]]); v.append(r["Montant"]); c.append("red")
            if v:
                fg = go.Figure(data=[go.Sankey(node=dict(pad=15, thickness=20, label=lbs, color="black"), link=dict(source=s, target=t, value=v, color=c))])
                st.plotly_chart(fg, use_container_width=True)
                
    with a2:
        st.markdown("### 🎯 Mes Budgets")
        with st.expander("Créer un budget"):
            with st.form("nob"):
                c1,c2,c3 = st.columns(3); sc=c1.selectbox("Qui", ["Perso", "Commun"]); ca=c2.selectbox("Cat", cats_memoire.get("Dépense", [])); mt=c3.number_input("Max")
                if st.form_submit_button("Ajouter"): 
                    objectifs_list.append({"Scope": sc, "Categorie": ca, "Montant": mt}); save_data(TAB_OBJECTIFS, pd.DataFrame(objectifs_list)); st.rerun()
        
        if objectifs_list:
            # Séparation Perso / Commun
            b_perso = [o for o in objectifs_list if o['Scope'] == "Perso"]
            b_commun = [o for o in objectifs_list if o['Scope'] == "Commun"]
            
            def render_budgets(liste, titre):
                if liste:
                    st.markdown(f"#### {titre}")
                    cols = st.columns(2)
                    for i, o in enumerate(liste):
                        col = cols[i % 2]
                        # Index original pour suppression
                        real_idx = objectifs_list.index(o)
                        
                        msk = (df_mois["Type"]=="Dépense") & (df_mois["Categorie"]==o["Categorie"])
                        if o["Scope"]=="Perso": msk = msk & (df_mois["Imputation"]=="Perso") & (df_mois["Qui_Connecte"]==user_actuel)
                        else: msk = msk & (df_mois["Imputation"].str.contains("Commun"))
                        
                        real = df_mois[msk]["Montant"].sum(); targ = float(o["Montant"]); rat = real/targ if targ>0 else 0
                        bc = "#EF4444" if rat>=1 else ("#F59E0B" if rat>=0.8 else "#10B981")
                        
                        with col:
                            st.markdown(f"""<div class="proj-card"><div style="display:flex; justify-content:space-between;"><b>{o['Categorie']}</b></div><div style="font-weight:bold; color:{bc};">{real:.0f} / {targ:.0f} €</div><div style="background:#eee;height:6px;border-radius:3px;margin-top:5px;"><div style="width:{min(rat*100,100)}%;background:{bc};height:100%;border-radius:3px;"></div></div></div>""", unsafe_allow_html=True)
                            if st.button("X", key=f"del_b_{real_idx}"): 
                                objectifs_list.pop(real_idx); save_data(TAB_OBJECTIFS, pd.DataFrame(objectifs_list)); st.rerun()

            render_budgets(b_perso, "👤 Mes Budgets")
            st.divider()
            render_budgets(b_commun, "🤝 Budgets Communs")

# TAB 4: PATRIMOINE
with tabs[3]:
    page_header("Patrimoine")
    ac = st.selectbox("Compte", cpt_visibles)
    if ac:
        sl = soldes.get(ac, 0.0)
        cl = "green" if sl>=0 else "red"
        st.markdown(f"## <span style='color:{cl}'>{sl:,.2f} €</span>", unsafe_allow_html=True)
        mk = (df["Compte_Source"]==ac)|(df["Compte_Cible"]==ac)
        st.dataframe(df[mk].sort_values(by="Date", ascending=False).head(10)[["Date","Titre","Montant","Type"]], use_container_width=True, hide_index=True)

    st.markdown("---")
    st1, st2 = st.tabs(["Projets", "Ajustement"])
    with st1:
        st.subheader("Mes Projets Épargne")
        f_own = st.radio("Filtre", ["Tout", "Commun", "Perso"], horizontal=True, label_visibility="collapsed")
        
        for p, d in projets_config.items():
            prop = d.get("Proprietaire", "Commun")
            if f_own == "Commun" and prop != "Commun": continue
            if f_own == "Perso" and prop == "Commun": continue
            
            with st.container():
                c1, c2 = st.columns([3, 1])
                s = df[(df["Projet_Epargne"]==p)&(df["Type"]=="Épargne")]["Montant"].sum()
                t = float(d["Cible"])
                pct = min(s/t if t>0 else 0, 1.0)*100
                bg = "#EFF6FF" if prop == "Commun" else "#FFF7ED"
                
                with c1:
                    st.markdown(f"""
                    <div class="proj-card">
                        <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                            <span style="font-weight:bold; font-size:16px;">{p}</span>
                            <span style="font-size:10px; background:{bg}; padding:2px 8px; border-radius:10px;">{prop}</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; font-size:14px; margin-bottom:5px;">
                            <span>{s:,.0f} € épargnés</span><span style="color:#6B7280;">Obj: {t:,.0f} €</span>
                        </div>
                        <div style="width:100%; background:#E5E7EB; height:8px; border-radius:4px;"><div style="width:{pct}%; background:#3B82F6; height:100%; border-radius:4px;"></div></div>
                    </div>""", unsafe_allow_html=True)
                
                with c2:
                    if st.button("✏️", key=f"e_p_{p}"): st.session_state[f"edp_{p}"]=True; st.rerun()
                    if st.button("🗑️", key=f"d_p_{p}"):
                        del projets_config[p]
                        rows = []
                        for k, v in projets_config.items(): rows.append({"Projet": k, "Cible": v["Cible"], "Date_Fin": v["Date_Fin"], "Proprietaire": v.get("Proprietaire", "Commun")})
                        save_data(TAB_PROJETS, pd.DataFrame(rows)); st.rerun()
                
                if st.session_state.get(f"edp_{p}", False):
                    with st.form(f"fep_{p}"):
                        nt = st.number_input("Nouvelle Cible", value=float(d["Cible"]))
                        np = st.selectbox("Propriétaire", ["Commun", user_actuel], index=0 if prop=="Commun" else 1)
                        if st.form_submit_button("Sauvegarder"):
                            projets_config[p]["Cible"] = nt; projets_config[p]["Proprietaire"] = np
                            rows = []
                            for k, v in projets_config.items(): rows.append({"Projet": k, "Cible": v["Cible"], "Date_Fin": v["Date_Fin"], "Proprietaire": v.get("Proprietaire", "Commun")})
                            save_data(TAB_PROJETS, pd.DataFrame(rows)); st.session_state[f"edp_{p}"]=False; st.rerun()

        with st.expander("➕ Nouveau Projet"):
            with st.form("new_proj"):
                n=st.text_input("Nom"); t=st.number_input("Cible"); prop=st.selectbox("Pour qui ?", ["Commun", user_actuel])
                if st.form_submit_button("Créer"): 
                    projets_config[n]={"Cible":t, "Date_Fin":"", "Proprietaire": prop}
                    rows = []
                    for k, v in projets_config.items(): rows.append({"Projet": k, "Cible": v["Cible"], "Date_Fin": v["Date_Fin"], "Proprietaire": v.get("Proprietaire", "Commun")})
                    save_data(TAB_PROJETS, pd.DataFrame(rows)); st.rerun()
    
    with st2:
        with st.form("adj"):
            d=st.date_input("Date"); m=st.number_input("Solde Réel")
            if st.form_submit_button("Enregistrer"):
                df_patrimoine = pd.concat([df_patrimoine, pd.DataFrame([{"Date":d,"Mois":d.month,"Annee":d.year,"Compte":ac,"Montant":m,"Proprietaire":user_actuel}])], ignore_index=True); save_data(TAB_PATRIMOINE, df_patrimoine); st.rerun()

# TAB 5: REGLAGES
with tabs[4]:
    page_header("Configuration")
    c_t1, c_t2, c_t3 = st.tabs(["🏷️ Catégories", "💳 Comptes", "⚡ Automatisation"])
    
    # 1. Catégories
    with c_t1:
        st.markdown("### Ajouter une catégorie")
        c1, c2, c3 = st.columns([2, 3, 1])
        ty = c1.selectbox("Type", TYPES, key="sc_type", label_visibility="collapsed")
        new_c = c2.text_input("Nom", key="ncat", placeholder="Nouvelle catégorie", label_visibility="collapsed")
        if c3.button("Ajouter", use_container_width=True): 
            cats_memoire.setdefault(ty, []).append(new_c); save_data(TAB_CONFIG, pd.DataFrame([{"Type": t, "Categorie": c} for t, l in cats_memoire.items() for c in l])); st.rerun()
        
        st.write("")
        col_dep, col_rev = st.columns(2)
        with col_dep:
            st.caption("Dépenses")
            for c in cats_memoire.get("Dépense", []):
                st.markdown(f'<span class="cat-badge depense">{c}</span>', unsafe_allow_html=True)
            to_del_dep = st.multiselect("Supprimer (Dépenses)", cats_memoire.get("Dépense", []))
            if to_del_dep and st.button("🗑️ Confirmer (Dépenses)"):
                for d in to_del_dep: cats_memoire["Dépense"].remove(d)
                save_data(TAB_CONFIG, pd.DataFrame([{"Type": t, "Categorie": c} for t, l in cats_memoire.items() for c in l])); st.rerun()

        with col_rev:
            st.caption("Revenus & Épargne")
            others = cats_memoire.get("Revenu", []) + cats_memoire.get("Épargne", [])
            for c in others:
                st.markdown(f'<span class="cat-badge revenu">{c}</span>', unsafe_allow_html=True)
            to_del_oth = st.multiselect("Supprimer (Autres)", others)
            if to_del_oth and st.button("🗑️ Confirmer (Autres)"):
                for d in to_del_oth:
                    for t in ["Revenu", "Épargne"]: 
                        if d in cats_memoire.get(t, []): cats_memoire[t].remove(d)
                save_data(TAB_CONFIG, pd.DataFrame([{"Type": t, "Categorie": c} for t, l in cats_memoire.items() for c in l])); st.rerun()

    # 2. Comptes
    with c_t2:
        with st.expander("Ajouter un compte", expanded=False):
            with st.form("nac"):
                n=st.text_input("Nom"); t=st.selectbox("Type", TYPES_COMPTE); c=st.checkbox("Commun")
                if st.form_submit_button("Ajouter"):
                    p = "Commun" if c else user_actuel
                    if n and n not in comptes_structure.get(p, []):
                        comptes_structure.setdefault(p, []).append(n)
                        rows = []
                        for pr, l in comptes_structure.items():
                            for ct in l: rows.append({"Proprietaire": pr, "Compte": ct, "Type": comptes_types_map.get(ct, t)})
                        save_data(TAB_COMPTES, pd.DataFrame(rows)); st.rerun()
        
        st.markdown("#### Vos comptes")
        for p in [user_actuel, "Commun"]:
            if p in comptes_structure:
                st.caption(p)
                for a in comptes_structure[p]:
                    c1,c2 = st.columns([4,1])
                    with c1: st.markdown(f"💳 **{a}** <span style='color:grey'>({comptes_types_map.get(a, 'Courant')})</span>", unsafe_allow_html=True)
                    if c2.button("Suppr", key=f"del_{a}"): 
                        comptes_structure[p].remove(a)
                        rows = []
                        for pr, l in comptes_structure.items():
                            for ct in l: rows.append({"Proprietaire": pr, "Compte": ct, "Type": comptes_types_map.get(ct, "Courant")})
                        save_data(TAB_COMPTES, pd.DataFrame(rows)); st.rerun()

    # 3. Mots-Clés
    with c_t3:
        with st.form("amc"):
            alc = [c for l in cats_memoire.values() for c in l]
            m=st.text_input("Si le titre contient...", placeholder="ex: Uber"); c=st.selectbox("Catégorie à appliquer", alc); ty=st.selectbox("Type", TYPES, key="kt"); co=st.selectbox("Compte par défaut", cpt_calc)
            if st.form_submit_button("Créer la règle"): 
                mots_cles_map[m.lower()] = {"Categorie":c,"Type":ty,"Compte":co}
                rows = []
                for mc, data in mots_cles_map.items(): rows.append({"Mot_Cle": mc, "Categorie": data["Categorie"], "Type": data["Type"], "Compte": data["Compte"]})
                save_data(TAB_MOTS_CLES, pd.DataFrame(rows)); st.rerun()
        
        if mots_cles_map:
            st.write("Règles actives :")
            data_rules = [{"Mot-Clé": k, "Catégorie": v["Categorie"], "Compte": v["Compte"]} for k,v in mots_cles_map.items()]
            edited_df = st.data_editor(pd.DataFrame(data_rules), num_rows="dynamic", use_container_width=True)
            if st.button("💾 Sauvegarder les modifications"):
                new_map = {}
                for _, row in edited_df.iterrows():
                    if row["Mot-Clé"]:
                        orig_type = mots_cles_map.get(row["Mot-Clé"], {}).get("Type", "Dépense")
                        new_map[row["Mot-Clé"].lower()] = {"Categorie": row["Catégorie"], "Type": orig_type, "Compte": row["Compte"]}
                rows = []
                for mc, data in new_map.items(): rows.append({"Mot_Cle": mc, "Categorie": data["Categorie"], "Type": data["Type"], "Compte": data["Compte"]})
                save_data(TAB_MOTS_CLES, pd.DataFrame(rows)); st.rerun()
