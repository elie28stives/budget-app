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
# 2. CSS & UI (DESIGN COMPLET)
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
        
        /* BADGES CATEGORIES */
        .cat-badge { display: inline-block; padding: 4px 10px; border-radius: 15px; font-size: 12px; font-weight: 600; margin: 0 5px 5px 0; border: 1px solid transparent; }
        .cat-badge.depense { background-color: #FFF1F2; color: #991b1b; }
        .cat-badge.revenu { background-color: #ECFDF5; color: #065f46; }
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
    # Retry logic
    for i in range(3):
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
    cats = {k: [] for k in TYPES}
    if not raw[0].empty:
        for _, r in raw[0].iterrows():
            if r["Type"] in cats and r["Categorie"] not in cats[r["Type"]]: cats[r["Type"]].append(r["Categorie"])
    if not cats["Dépense"]: cats["Dépense"] = ["Alimentation", "Loyer"]
    
    comptes, c_types = {}, {}
    if not raw[1].empty:
        for _, r in raw[1].iterrows():
            comptes.setdefault(r["Proprietaire"], []).append(r["Compte"])
            c_types[r["Compte"]] = r.get("Type", "Courant")
            
    projets = {}
    if not raw[4].empty:
        for _, r in raw[4].iterrows():
            projets[r["Projet"]] = {"Cible": float(r["Cible"]), "Proprietaire": r.get("Proprietaire", "Commun"), "Date_Fin": r["Date_Fin"]}
            
    mots = {r["Mot_Cle"].lower(): {"Categorie":r["Categorie"], "Type":r["Type"], "Compte":r["Compte"]} for _, r in raw[5].iterrows()} if not raw[5].empty else {}
    
    return cats, comptes, raw[2].to_dict('records'), raw[3], projets, c_types, mots

# ==============================================================================
# 5. APP MAIN
# ==============================================================================
st.set_page_config(page_title="Ma Banque V76", layout="wide", page_icon=None)
apply_custom_style()
init_state()

df = load_data(TAB_DATA, COLS_DATA)
df_pat = load_data(TAB_PATRIMOINE, COLS_PAT)
cats_mem, cpt_struct, objs_list, df_abos, proj_conf, cpt_types, kw_map = process_data()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### Menu")
    user_now = st.selectbox("Utilisateur", USERS)
    st.markdown("---")
    
    cpt_visibles = cpt_struct.get(user_now, []) + cpt_struct.get("Commun", [])
    cpt_calc = list(set(cpt_visibles + ["Autre / Externe"]))
    soldes = calc_soldes(df, df_pat, cpt_calc)
    
    lst_c, lst_e = [], []
    tot_c, tot_e = 0, 0
    for c in cpt_visibles:
        v = soldes.get(c, 0.0)
        if cpt_types.get(c) == "Épargne": tot_e += v; lst_e.append((c,v))
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
    df_m = df[(df["Mois"] == m_sel) & (df["Annee"] == a_sel)]
    
    st.markdown("---")
    if st.button("Actualiser", use_container_width=True): st.cache_data.clear(); st.rerun()

# --- TABS ---
tabs = st.tabs(["Accueil", "Opérations", "Analyses", "Patrimoine", "Réglages"])

# TAB 1: ACCUEIL
with tabs[0]:
    page_header(f"Synthèse - {m_nom}", f"Compte de {user_now}")
    
    rev = df_m[(df_m["Qui_Connecte"]==user_now) & (df_m["Type"]=="Revenu")]["Montant"].sum()
    dep = df_m[(df_m["Qui_Connecte"]==user_now) & (df_m["Type"]=="Dépense") & (df_m["Imputation"]=="Perso")]["Montant"].sum()
    epg = df_m[(df_m["Qui_Connecte"]==user_now) & (df_m["Type"]=="Épargne")]["Montant"].sum()
    com = df_m[df_m["Imputation"]=="Commun (50/50)"]["Montant"].sum() / 2
    
    fixe = 0
    if not df_abos.empty:
        au = df_abos[(df_abos["Proprietaire"]==user_now)|(df_abos["Imputation"].str.contains("Commun", na=False))]
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
        
        dat = df[df['Qui_Connecte'] == user_now].sort_values(by='Date', ascending=False)
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
        op = [o for o in objs_list if o["Scope"] in ["Perso", user_now]]
        dff = df_m[(df_m["Type"]=="Dépense") & (df_m["Imputation"]=="Perso") & (df_m["Qui_Connecte"]==user_now)]
        has_a = False
        for o in op:
            r = dff[dff["Categorie"]==o["Categorie"]]["Montant"].sum()
            b = float(o["Montant"])
            if b>0 and r/b>0.75:
                has_a = True; st.write(f"**{o['Categorie']}** : {r:.0f}/{b:.0f} €"); st.progress(min(r/b, 1.0))
        if not has_a: st.success("Budget OK")

# TAB 2: OPÉRATIONS (DYNAMIQUE, SANS FORMULAIRE BLOQUANT)
with tabs[1]:
    op1, op2, op3 = st.tabs(["Saisie", "Journal", "Abonnements"])
    with op1:
        st.subheader("Nouvelle Transaction")
        
        # Saisie fluide (session state auto)
        c1, c2, c3 = st.columns(3)
        d_op = c1.date_input("Date", datetime.today()); t_op = c2.selectbox("Type", TYPES); m_op = c3.number_input("Montant", min_value=0.0, step=0.01)
        
        c4, c5 = st.columns(2)
        tit = c4.text_input("Titre"); cat_f = "Autre"; cpt_a = None
        
        # Auto-complete
        if tit and kw_map:
            for mc, d in kw_map.items():
                if mc in tit.lower() and d["Type"] == t_op: cat_f=d["Categorie"]; cpt_a=d["Compte"]; break
        
        cats = cats_mem.get(t_op, []); idx_c = cats.index(cat_f) if cat_f in cats else 0
        cat_s = c5.selectbox("Catégorie", cats + ["Autre (nouvelle)"], index=idx_c)
        fin_c = st.text_input("Nom catégorie") if cat_s == "Autre (nouvelle)" else cat_s
        
        st.write("")
        cc1, cc2, cc3 = st.columns(3)
        idx_cp = cpt_visibles.index(cpt_a) if (cpt_a and cpt_a in cpt_visibles) else 0
        c_src = cc1.selectbox("Compte Source", cpt_visibles, index=idx_cp)
        imp = cc2.radio("Imputation", IMPUTATIONS, horizontal=True)
        
        # Champs dynamiques
        fin_imp = imp
        if imp == "Commun (Autre %)":
            pt = cc3.slider("Part Pierre %", 0, 100, 50); fin_imp = f"Commun ({pt}/{100-pt})"
        elif t_op == "Virement Interne": fin_imp = "Neutre"
        
        c_tgt, p_epg = "", ""
        if t_op == "Épargne":
            ce1, ce2 = st.columns(2)
            c_tgt = ce1.selectbox("Vers Compte", [c for c in cpt_visibles if cpt_types.get(c)=="Épargne"])
            ps = ce2.selectbox("Projet", ["Aucun"]+list(proj_conf.keys()))
            if ps!="Aucun": p_epg = ps
        elif t_op == "Virement Interne": c_tgt = st.selectbox("Vers Compte", cpt_visibles)
            
        if st.button("Valider Transaction", type="primary", use_container_width=True):
            if cat_s == "Autre (nouvelle)" and fin_c:
                cats_mem.setdefault(t_op, []).append(fin_c); save_data(TAB_CONFIG, pd.DataFrame([{"Type": t, "Categorie": c} for t, l in cats_mem.items() for c in l]))
            if t_op=="Épargne" and p_epg and p_epg not in proj_conf:
                proj_conf[p_epg]={"Cible":0.0, "Date_Fin":"", "Proprietaire": user_now}
                rows = []
                for k, v in proj_conf.items(): rows.append({"Projet": k, "Cible": v["Cible"], "Date_Fin": v["Date_Fin"], "Proprietaire": v.get("Proprietaire", "Commun")})
                save_data(TAB_PROJETS, pd.DataFrame(rows))
            
            nr = {"Date": d_op, "Mois": d_op.month, "Annee": d_op.year, "Qui_Connecte": user_now, "Type": t_op, "Categorie": fin_c, "Titre": tit, "Description": "", "Montant": m_op, "Paye_Par": user_now, "Imputation": fin_imp, "Compte_Cible": c_tgt, "Projet_Epargne": p_epg, "Compte_Source": c_src}
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

   # 3. ABONNEMENTS (DESIGN REVOLUT / GRILLE)
    with op3:
        # En-tête avec bouton d'ajout
        c_head, c_btn = st.columns([3, 1])
        with c_head:
            st.markdown("### 📅 Mes Abonnements Fixes")
        with c_btn:
            if st.button("➕ Nouvel Abonnement", use_container_width=True):
                st.session_state['show_new_abo'] = not st.session_state.get('show_new_abo', False)

        # Formulaire d'ajout (caché par défaut)
        if st.session_state.get('show_new_abo', False):
            with st.container():
                st.markdown("""<div style="background:#f8fafc; padding:15px; border-radius:10px; border:1px solid #e2e8f0; margin-bottom:20px;">""", unsafe_allow_html=True)
                with st.form("new_abo_form"):
                    c1, c2, c3 = st.columns(3)
                    n = c1.text_input("Nom (ex: Netflix)")
                    m = c2.number_input("Montant (€)", min_value=0.0, step=0.01)
                    j = c3.number_input("Jour du prélèvement", 1, 31, 1)
                    
                    c4, c5, c6 = st.columns(3)
                    c = c4.selectbox("Catégorie", cats_memoire.get("Dépense", []))
                    cp = c5.selectbox("Compte débité", comptes_visibles)
                    im = c6.selectbox("Imputation", IMPUTATIONS)
                    
                    if st.form_submit_button("Valider la création", type="primary"):
                        new_abo = pd.DataFrame([{
                            "Nom": n, "Montant": m, "Jour": j, 
                            "Categorie": c, "Compte_Source": cp, 
                            "Proprietaire": user_actuel, "Imputation": im, 
                            "Frequence": "Mensuel"
                        }])
                        df_abonnements = pd.concat([df_abonnements, new_abo], ignore_index=True)
                        save_abonnements(df_abonnements)
                        st.session_state['show_new_abo'] = False
                        st.success("Abonnement ajouté !")
                        time.sleep(0.5)
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        # --- LISTE DES ABONNEMENTS ---
        if not df_abonnements.empty:
            # Filtrer pour l'utilisateur
            my_abos = df_abonnements[df_abonnements["Proprietaire"] == user_actuel]
            
            if not my_abos.empty:
                # 1. Vérification des paiements ce mois-ci
                to_generate = []
                abo_status = [] # Liste pour stocker les infos enrichies
                
                for idx, row in my_abos.iterrows():
                    # On cherche si une dépense du même nom et montant existe ce mois-ci
                    is_paid = not df_mois[
                        (df_mois["Titre"].str.lower() == row["Nom"].lower()) & 
                        (df_mois["Montant"] == float(row["Montant"]))
                    ].empty
                    
                    if not is_paid:
                        to_generate.append(row)
                    
                    abo_status.append({
                        "idx": idx,
                        "data": row,
                        "is_paid": is_paid
                    })

                # 2. Bouton Génération Globale (si manquants)
                if to_generate:
                    st.warning(f"⚠️ {len(to_generate)} abonnements n'ont pas encore été débités ce mois-ci.")
                    if st.button(f"🚀 Générer les {len(to_generate)} transactions manquantes", type="primary", use_container_width=True):
                        new_txs = []
                        for r in to_generate:
                            # Calcul de la date (si jour passé, on met la date réelle, sinon date du jour ou fin de mois)
                            try: 
                                date_prevue = datetime(annee_selection, mois_selection, int(r["Jour"])).date()
                            except: 
                                date_prevue = datetime(annee_selection, mois_selection, 28).date()
                            
                            new_txs.append({
                                "Date": date_prevue,
                                "Mois": mois_selection,
                                "Annee": annee_selection,
                                "Qui_Connecte": r["Proprietaire"],
                                "Type": "Dépense",
                                "Categorie": r["Categorie"],
                                "Titre": r["Nom"],
                                "Description": "Abonnement Automatique",
                                "Montant": float(r["Montant"]),
                                "Paye_Par": r["Proprietaire"],
                                "Imputation": r["Imputation"],
                                "Compte_Cible": "",
                                "Projet_Epargne": "",
                                "Compte_Source": r["Compte_Source"]
                            })
                        
                        df = pd.concat([df, pd.DataFrame(new_txs)], ignore_index=True)
                        save_data_to_sheet(TAB_DATA, df)
                        st.success("Transactions générées !")
                        time.sleep(1)
                        st.rerun()
                    st.divider()

                # 3. Affichage en Grille (Cards)
                cols = st.columns(3) # 3 Cartes par ligne
                
                for i, item in enumerate(abo_status):
                    col = cols[i % 3] # Distribution dans les colonnes
                    idx = item['idx']
                    r = item['data']
                    paid = item['is_paid']
                    
                    with col:
                        # Mode Édition
                        if st.session_state.get(f"edit_abo_{idx}", False):
                            with st.container():
                                st.markdown(f"""<div style="border:1px solid #3B82F6; border-radius:12px; padding:10px; background:white;">""", unsafe_allow_html=True)
                                with st.form(f"edit_abo_form_{idx}"):
                                    en = st.text_input("Nom", value=r['Nom'])
                                    em = st.number_input("Montant", value=float(r['Montant']))
                                    ej = st.number_input("Jour", value=int(r['Jour']))
                                    
                                    c_s1, c_s2 = st.columns(2)
                                    if c_s1.form_submit_button("💾"):
                                        df_abonnements.at[idx, 'Nom'] = en
                                        df_abonnements.at[idx, 'Montant'] = em
                                        df_abonnements.at[idx, 'Jour'] = ej
                                        save_abonnements(df_abonnements)
                                        st.session_state[f"edit_abo_{idx}"] = False
                                        st.rerun()
                                    if c_s2.form_submit_button("❌"):
                                        st.session_state[f"edit_abo_{idx}"] = False
                                        st.rerun()
                                st.markdown("</div>", unsafe_allow_html=True)
                        
                        # Mode Lecture (Carte Visuelle)
                        else:
                            # Style dynamique
                            status_col = "#10B981" if paid else "#F59E0B"
                            status_bg = "#ECFDF5" if paid else "#FFFBEB"
                            status_txt = "PAYÉ" if paid else "EN ATTENTE"
                            initiale = r['Nom'][0].upper() if r['Nom'] else "?"
                            
                            # HTML Carte
                            st.markdown(f"""
                            <div style="
                                background-color: white;
                                border: 1px solid #E5E7EB;
                                border-radius: 16px;
                                padding: 15px;
                                margin-bottom: 15px;
                                box-shadow: 0 2px 5px rgba(0,0,0,0.02);
                                position: relative;
                            ">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                    <div style="
                                        width: 35px; height: 35px; 
                                        background-color: {status_bg}; 
                                        color: {status_col}; 
                                        border-radius: 50%; 
                                        display: flex; align-items: center; justify-content: center; 
                                        font-weight: 800; font-size: 14px;">
                                        {initiale}
                                    </div>
                                    <div style="background-color: {status_bg}; color: {status_col}; font-size: 9px; font-weight: 700; padding: 4px 8px; border-radius: 10px;">
                                        {status_txt}
                                    </div>
                                </div>
                                
                                <div style="font-weight: 700; font-size: 15px; color: #1F2937; margin-bottom: 2px;">{r['Nom']}</div>
                                <div style="font-weight: 800; font-size: 18px; color: #1F2937; margin-bottom: 8px;">{float(r['Montant']):.2f} €</div>
                                
                                <div style="font-size: 11px; color: #6B7280; display:flex; justify-content:space-between; border-top:1px solid #F3F4F6; padding-top:8px;">
                                    <span>📅 Le {r['Jour']} du mois</span>
                                    <span>🏷️ {r['Categorie']}</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Boutons d'action (petits icônes)
                            ca1, ca2, void = st.columns([1, 1, 3])
                            if ca1.button("✏️", key=f"ed_a_{idx}", help="Modifier"):
                                st.session_state[f"edit_abo_{idx}"] = True
                                st.rerun()
                            if ca2.button("🗑️", key=f"del_a_{idx}", help="Supprimer"):
                                df_abonnements = df_abonnements.drop(idx)
                                save_abonnements(df_abonnements)
                                st.rerun()
            else:
                st.info("Aucun abonnement configuré pour vous.")
        else:
            st.info("Commencez par ajouter un abonnement ci-dessus.")

# TAB 3: ANALYSES (SEPARATION BUDGETS)
with tabs[2]:
    an1, an2 = st.tabs(["Vue Globale", "Objectifs & Budgets"])
    with an1:
        if not df_m.empty:
            fig = px.pie(df_m[df_m["Type"]=="Dépense"], values="Montant", names="Categorie", hole=0.5)
            st.plotly_chart(fig, use_container_width=True)
            
            dr = df_m[df_m["Type"]=="Revenu"]; dd = df_m[df_m["Type"]=="Dépense"]
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
                
    with an2:
        st.markdown("### 🎯 Configuration")
        with st.expander("Créer un budget", expanded=False):
            with st.form("new_obj"):
                c1,c2,c3 = st.columns(3); sc=c1.selectbox("Scope", ["Perso", "Commun"]); ca=c2.selectbox("Cat", cats_mem.get("Dépense", [])); mt=c3.number_input("Max €")
                if st.form_submit_button("Ajouter"):
                    objs_list.append({"Scope": sc, "Categorie": ca, "Montant": mt}); save_data(TAB_OBJECTIFS, pd.DataFrame(objs_list)); st.rerun()
        
        if not objs_list:
            st.info("Aucun budget.")
        else:
            # Séparation Perso / Commun
            b_perso = [o for o in objs_list if o['Scope'] == "Perso"]
            b_commun = [o for o in objs_list if o['Scope'] == "Commun"]
            
            def render_budgets(liste_budgets, titre_section):
                if liste_budgets:
                    st.markdown(f"#### {titre_section}")
                    for i in range(0, len(liste_budgets), 2):
                        cs = st.columns(2)
                        for j, col in enumerate(cs):
                            if i+j < len(liste_budgets):
                                o = liste_budgets[i+j]
                                # Retrouver index réel pour suppression
                                real_idx = objs_list.index(o)
                                
                                msk = (df_m["Type"]=="Dépense") & (df_m["Categorie"]==o["Categorie"])
                                if o["Scope"]=="Perso": msk = msk & (df_m["Imputation"]=="Perso") & (df_m["Qui_Connecte"]==user_now)
                                else: msk = msk & (df_m["Imputation"].str.contains("Commun"))
                                
                                real = df_m[msk]["Montant"].sum(); targ = float(o["Montant"]); rat = real/targ if targ>0 else 0
                                bcol = "#EF4444" if rat>=1 else ("#F59E0B" if rat>=0.8 else "#10B981")
                                
                                with col:
                                    st.markdown(f"""<div class="proj-card"><div style="display:flex; justify-content:space-between;"><b>{o['Categorie']}</b></div><div style="font-weight:bold; color:{bcol};">{real:.0f} / {targ:.0f} €</div><div style="background:#eee;height:6px;border-radius:3px;margin-top:5px;"><div style="width:{min(rat*100,100)}%;background:{bcol};height:100%;border-radius:3px;"></div></div></div>""", unsafe_allow_html=True)
                                    if st.button("X", key=f"del_b_{real_idx}"): objs_list.pop(real_idx); save_data(TAB_OBJECTIFS, pd.DataFrame(objs_list)); st.rerun()

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
        # Filtre
        f_own = st.radio("Filtre", ["Tout", "Commun", "Perso"], horizontal=True, label_visibility="collapsed")
        
        for p, d in proj_conf.items():
            proprio = d.get("Proprietaire", "Commun")
            if f_own == "Commun" and proprio != "Commun": continue
            if f_own == "Perso" and proprio == "Commun": continue
            
            with st.container():
                c1, c2 = st.columns([3, 1])
                s = df[(df["Projet_Epargne"]==p)&(df["Type"]=="Épargne")]["Montant"].sum()
                t = float(d["Cible"])
                pct = min(s/t if t>0 else 0, 1.0)*100
                bg = "#EFF6FF" if proprio == "Commun" else "#FFF7ED"
                
                with c1:
                    st.markdown(f"""
                    <div class="proj-card">
                        <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                            <span style="font-weight:bold; font-size:16px;">{p}</span>
                            <span style="font-size:10px; background:{bg}; padding:2px 8px; border-radius:10px;">{proprio}</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; font-size:14px; margin-bottom:5px;">
                            <span>{s:,.0f} € épargnés</span>
                            <span style="color:#6B7280;">Objectif: {t:,.0f} €</span>
                        </div>
                        <div style="width:100%; background:#E5E7EB; height:8px; border-radius:4px;"><div style="width:{pct}%; background:#3B82F6; height:100%; border-radius:4px;"></div></div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with c2:
                    if st.button("✏️", key=f"e_p_{p}"): st.session_state[f"edp_{p}"]=True; st.rerun()
                    if st.button("🗑️", key=f"d_p_{p}"):
                        del proj_conf[p]
                        rows = []
                        for k, v in proj_conf.items(): rows.append({"Projet": k, "Cible": v["Cible"], "Date_Fin": v["Date_Fin"], "Proprietaire": v.get("Proprietaire", "Commun")})
                        save_data(TAB_PROJETS, pd.DataFrame(rows)); st.rerun()
                
                if st.session_state.get(f"edp_{p}", False):
                    with st.form(f"fep_{p}"):
                        nt = st.number_input("Nouvelle Cible", value=float(d["Cible"]))
                        np = st.selectbox("Propriétaire", ["Commun", user_now], index=0 if d.get("Proprietaire")=="Commun" else 1)
                        if st.form_submit_button("Sauvegarder"):
                            proj_conf[p]["Cible"] = nt
                            proj_conf[p]["Proprietaire"] = np
                            rows = []
                            for k, v in proj_conf.items(): rows.append({"Projet": k, "Cible": v["Cible"], "Date_Fin": v["Date_Fin"], "Proprietaire": v.get("Proprietaire", "Commun")})
                            save_data(TAB_PROJETS, pd.DataFrame(rows))
                            st.session_state[f"edp_{p}"] = False
                            st.rerun()

        with st.expander("➕ Nouveau Projet"):
            with st.form("new_proj"):
                n=st.text_input("Nom"); t=st.number_input("Cible"); prop=st.selectbox("Pour qui ?", ["Commun", user_now])
                if st.form_submit_button("Créer"): 
                    proj_conf[n]={"Cible":t, "Date_Fin":"", "Proprietaire": prop}
                    rows = []
                    for k, v in proj_conf.items(): rows.append({"Projet": k, "Cible": v["Cible"], "Date_Fin": v["Date_Fin"], "Proprietaire": v.get("Proprietaire", "Commun")})
                    save_data(TAB_PROJETS, pd.DataFrame(rows)); st.rerun()
    
    with st2:
        with st.form("adj"):
            d=st.date_input("Date"); m=st.number_input("Solde Réel")
            if st.form_submit_button("Enregistrer"):
                df_pat = pd.concat([df_pat, pd.DataFrame([{"Date":d,"Mois":d.month,"Annee":d.year,"Compte":ac,"Montant":m,"Proprietaire":user_now}])], ignore_index=True); save_data(TAB_PATRIMOINE, df_pat); st.rerun()

# TAB 5: REGLAGES (VISUEL RESTAURÉ)
with tabs[4]:
    page_header("Configuration")
    
    c_t1, c_t2, c_t3 = st.tabs(["🏷️ Catégories", "💳 Comptes", "⚡ Automatisation"])
    
    # 1. Catégories
    with c_t1:
        with st.container():
            st.markdown("#### Ajouter une catégorie")
            c1, c2, c3 = st.columns([2, 3, 1])
            ty = c1.selectbox("Type", TYPES, key="sc_type", label_visibility="collapsed")
            new_c = c2.text_input("Nom", key="ncat", placeholder="Nouvelle catégorie", label_visibility="collapsed")
            if c3.button("Ajouter", use_container_width=True): 
                cats_mem.setdefault(ty, []).append(new_c); save_data(TAB_CONFIG, pd.DataFrame([{"Type": t, "Categorie": c} for t, l in cats_mem.items() for c in l])); st.rerun()
        
        st.write("")
        col_dep, col_rev = st.columns(2)
        with col_dep:
            st.caption("Dépenses")
            for c in cats_mem.get("Dépense", []):
                st.markdown(f'<span class="cat-badge depense">{c}</span>', unsafe_allow_html=True)
            to_del_dep = st.multiselect("Supprimer (Dépenses)", cats_mem.get("Dépense", []))
            if to_del_dep and st.button("🗑️ Confirmer (Dépenses)"):
                for d in to_del_dep: cats_mem["Dépense"].remove(d)
                save_data(TAB_CONFIG, pd.DataFrame([{"Type": t, "Categorie": c} for t, l in cats_mem.items() for c in l])); st.rerun()

        with col_rev:
            st.caption("Revenus & Épargne")
            others = cats_mem.get("Revenu", []) + cats_mem.get("Épargne", [])
            for c in others:
                st.markdown(f'<span class="cat-badge revenu">{c}</span>', unsafe_allow_html=True)
            to_del_oth = st.multiselect("Supprimer (Autres)", others)
            if to_del_oth and st.button("🗑️ Confirmer (Autres)"):
                for d in to_del_oth:
                    for t in ["Revenu", "Épargne"]: 
                        if d in cats_mem.get(t, []): cats_mem[t].remove(d)
                save_data(TAB_CONFIG, pd.DataFrame([{"Type": t, "Categorie": c} for t, l in cats_mem.items() for c in l])); st.rerun()

    # 2. Comptes
    with c_t2:
        with st.expander("Ajouter un compte", expanded=False):
            with st.form("nac"):
                n=st.text_input("Nom"); t=st.selectbox("Type", TYPES_COMPTE); c=st.checkbox("Commun")
                if st.form_submit_button("Ajouter"):
                    p = "Commun" if c else user_now
                    if n and n not in cpt_struct.get(p, []):
                        cpt_struct.setdefault(p, []).append(n)
                        rows = []
                        for pr, l in cpt_struct.items():
                            for ct in l: rows.append({"Proprietaire": pr, "Compte": ct, "Type": cpt_types.get(ct, t)})
                        save_data(TAB_COMPTES, pd.DataFrame(rows)); st.rerun()
        
        st.markdown("#### Vos comptes")
        for p in [user_now, "Commun"]:
            if p in cpt_struct:
                st.caption(p)
                for a in cpt_struct[p]:
                    c1,c2 = st.columns([4,1])
                    with c1: st.markdown(f"💳 **{a}** <span style='color:grey'>({cpt_types.get(a, 'Courant')})</span>", unsafe_allow_html=True)
                    if c2.button("Suppr", key=f"del_{a}"): 
                        cpt_struct[p].remove(a)
                        rows = []
                        for pr, l in cpt_struct.items():
                            for ct in l: rows.append({"Proprietaire": pr, "Compte": ct, "Type": cpt_types.get(ct, "Courant")})
                        save_data(TAB_COMPTES, pd.DataFrame(rows)); st.rerun()

    # 3. Mots-Clés
    with c_t3:
        with st.form("amc"):
            alc = [c for l in cats_mem.values() for c in l]
            m=st.text_input("Si le titre contient...", placeholder="ex: Uber"); c=st.selectbox("Catégorie", alc); ty=st.selectbox("Type", TYPES, key="kt"); co=st.selectbox("Compte", cpt_calc)
            if st.form_submit_button("Créer la règle"): 
                kw_map[m.lower()] = {"Categorie":c,"Type":ty,"Compte":co}
                rows = []
                for mc, data in kw_map.items(): rows.append({"Mot_Cle": mc, "Categorie": data["Categorie"], "Type": data["Type"], "Compte": data["Compte"]})
                save_data(TAB_MOTS_CLES, pd.DataFrame(rows)); st.rerun()
        
        if kw_map:
            st.write("Règles actives :")
            data_rules = [{"Mot-Clé": k, "Catégorie": v["Categorie"], "Compte": v["Compte"]} for k,v in kw_map.items()]
            edited_df = st.data_editor(pd.DataFrame(data_rules), num_rows="dynamic", use_container_width=True)
            if st.button("💾 Sauvegarder les modifications"):
                new_map = {}
                for _, row in edited_df.iterrows():
                    if row["Mot-Clé"]:
                        # Retrouver le type original ou par défaut
                        orig_type = kw_map.get(row["Mot-Clé"], {}).get("Type", "Dépense")
                        new_map[row["Mot-Clé"].lower()] = {"Categorie": row["Catégorie"], "Type": orig_type, "Compte": row["Compte"]}
                rows = []
                for mc, data in new_map.items(): rows.append({"Mot_Cle": mc, "Categorie": data["Categorie"], "Type": data["Type"], "Compte": data["Compte"]})
                save_data(TAB_MOTS_CLES, pd.DataFrame(rows)); st.rerun()

