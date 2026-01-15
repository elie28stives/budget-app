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

# ==========================================
# 1. CONFIGURATION
# ==========================================
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
COLS_DATA = ["Date", "Mois", "Annee", "Qui_Connecte", "Type", "Categorie", "Titre", "Description", "Montant", "Paye_Par", "Imputation", "Compte_Cible", "Projet_Epargne", "Compte_Source"]
COLS_PAT = ["Date", "Mois", "Annee", "Compte", "Montant", "Proprietaire"]

# ==========================================
# 2. CSS & UI
# ==========================================
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
    </style>
    """, unsafe_allow_html=True)

def page_header(title, subtitle=None):
    st.markdown(f"<h2 style='font-size:26px; font-weight:700; color:#2C3E50; margin-bottom:5px;'>{title}</h2>", unsafe_allow_html=True)
    if subtitle: st.markdown(f"<p style='font-size:14px; color:#6B7280; margin-bottom:20px;'>{subtitle}</p>", unsafe_allow_html=True)

# ==========================================
# 3. BACKEND (GSPREAD)
# ==========================================
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
    # Retry logic simple
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

# ==========================================
# 4. LOGIQUE
# ==========================================
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

# ==========================================
# 5. APP MAIN
# ==========================================
st.set_page_config(page_title="Ma Banque V75", layout="wide", page_icon=None)
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

# TAB 2: OPÉRATIONS
with tabs[1]:
    op1, op2, op3 = st.tabs(["Saisie", "Journal", "Abonnements"])
    with op1:
        st.subheader("Nouvelle Transaction")
        c1, c2, c3 = st.columns(3)
        d_op = c1.date_input("Date", datetime.today()); t_op = c2.selectbox("Type", TYPES); m_op = c3.number_input("Montant", min_value=0.0, step=0.01)
        
        c4, c5 = st.columns(2)
        tit = c4.text_input("Titre"); cat_f = "Autre"; cpt_a = None
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

    with op3:
        st.subheader("Mes Abonnements")
        with st.expander("Nouveau"):
            with st.form("na"):
                a1,a2,a3 = st.columns(3); n=a1.text_input("Nom"); m=a2.number_input("Montant"); j=a3.number_input("Jour", 1, 31)
                a4,a5 = st.columns(2); c=a4.selectbox("Cat", cats_mem.get("Dépense", [])); cp=a5.selectbox("Cpt", cpt_visibles)
                im = st.selectbox("Imp", IMPUTATIONS)
                if st.form_submit_button("Ajouter"):
                    df_abos = pd.concat([df_abos, pd.DataFrame([{"Nom": n, "Montant": m, "Jour": j, "Categorie": c, "Compte_Source": cp, "Proprietaire": user_now, "Imputation": im, "Frequence": "Mensuel"}])], ignore_index=True); save_data(TAB_ABONNEMENTS, df_abos); st.rerun()
        
        if not df_abos.empty:
            ma = df_abos[df_abos["Proprietaire"]==user_now]
            tg = []
            for ix, r in ma.iterrows():
                paid = not df_m[(df_m["Titre"]==r["Nom"])&(df_m["Montant"]==float(r["Montant"]))].empty
                if not paid: tg.append(r)
            if tg and st.button(f"Générer {len(tg)} manquants"):
                nt = []
                for r in tg:
                    try: d = datetime(a_sel, m_sel, int(r["Jour"])).date()
                    except: d = datetime(a_sel, m_sel, 28).date()
                    nt.append({"Date": d, "Mois": m_sel, "Annee": a_sel, "Qui_Connecte": r["Proprietaire"], "Type": "Dépense", "Categorie": r["Categorie"], "Titre": r["Nom"], "Description": "Auto", "Montant": float(r["Montant"]), "Paye_Par": r["Proprietaire"], "Imputation": r["Imputation"], "Compte_Cible": "", "Projet_Epargne": "", "Compte_Source": r["Compte_Source"]})
                df = pd.concat([df, pd.DataFrame(nt)], ignore_index=True); save_data(TAB_DATA, df); st.rerun()

            for ix, r in ma.iterrows():
                with st.container():
                    c1,c2,c3,c4 = st.columns([2,2,1,1])
                    if not st.session_state.get(f"ed_{ix}", False):
                        c1.write(f"**{r['Nom']}**"); c2.write(f"{r['Montant']}€ (J{r['Jour']})")
                        if c3.button("📝", key=f"e_{ix}"): st.session_state[f"ed_{ix}"]=True; st.rerun()
                        if c4.button("❌", key=f"d_{ix}"): df_abos=df_abos.drop(ix); save_data(TAB_ABONNEMENTS, df_abos); st.rerun()
                    else:
                        with st.form(f"fe_{ix}"):
                            nn=st.text_input("N", value=r['Nom']); nm=st.number_input("M", value=float(r['Montant'])); nj=st.number_input("J", value=int(r['Jour']))
                            if st.form_submit_button("Ok"):
                                df_abos.at[ix,'Nom']=nn; df_abos.at[ix,'Montant']=nm; df_abos.at[ix,'Jour']=nj; save_data(TAB_ABONNEMENTS, df_abos); st.session_state[f"ed_{ix}"]=False; st.rerun()
                    st.markdown("---")

# TAB 3: ANALYSES
with tabs[2]:
    a1, a2 = st.tabs(["Vue Globale", "Budgets"])
    with a1:
        if not df_m.empty:
            fig = px.pie(df_m[df_m["Type"]=="Dépense"], values="Montant", names="Categorie", hole=0.5)
            st.plotly_chart(fig, use_container_width=True)
    with a2:
        st.markdown("### Mes Budgets")
        with st.expander("Créer un budget"):
            with st.form("nob"):
                c1,c2,c3 = st.columns(3); sc=c1.selectbox("Qui", ["Perso", "Commun"]); ca=c2.selectbox("Cat", cats_mem.get("Dépense", [])); mt=c3.number_input("Max")
                if st.form_submit_button("Ajouter"): 
                    objs_list.append({"Scope": sc, "Categorie": ca, "Montant": mt}); save_data(TAB_OBJECTIFS, pd.DataFrame(objs_list)); st.rerun()
        
        if objs_list:
            for i in range(0, len(objs_list), 2):
                cs = st.columns(2)
                for j, col in enumerate(cs):
                    if i+j < len(objs_list):
                        idx = i+j; o = objs_list[idx]
                        if o['Scope']=="Perso" and user_now not in USERS: continue
                        msk = (df_m["Type"]=="Dépense") & (df_m["Categorie"]==o["Categorie"])
                        if o["Scope"]=="Perso": msk = msk & (df_m["Imputation"]=="Perso") & (df_m["Qui_Connecte"]==user_now)
                        else: msk = msk & (df_m["Imputation"].str.contains("Commun"))
                        real = df_m[msk]["Montant"].sum(); targ = float(o["Montant"]); rat = real/targ if targ>0 else 0
                        bc = "#EF4444" if rat>=1 else ("#F59E0B" if rat>=0.8 else "#10B981")
                        with col:
                            st.markdown(f"""<div class="proj-card"><div style="display:flex; justify-content:space-between;"><b>{o['Categorie']}</b><span style="color:#888">{o['Scope']}</span></div><div style="font-weight:bold; color:{bc};">{real:.0f} / {targ:.0f} €</div><div style="background:#eee;height:6px;border-radius:3px;margin-top:5px;"><div style="width:{min(rat*100,100)}%;background:{bc};height:100%;border-radius:3px;"></div></div></div>""", unsafe_allow_html=True)
                            if st.button("Suppr", key=f"do_{idx}"): objs_list.pop(idx); save_data(TAB_OBJECTIFS, pd.DataFrame(objs_list)); st.rerun()

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
        st.subheader("🎯 Objectifs d'Épargne")
        c_titre, c_new = st.columns([2, 1])
        with c_new:
            if st.button("➕ Nouveau Projet", use_container_width=True):
                st.session_state['show_new_proj'] = not st.session_state.get('show_new_proj', False)

        if st.session_state.get('show_new_proj', False):
            with st.container():
                with st.form("create_proj_form"):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    n_p = c1.text_input("Nom du projet (ex: Voyage Japon)")
                    t_p = c2.number_input("Cible (€)", min_value=1.0, step=50.0)
                    o_p = c3.selectbox("Pour qui ?", ["Commun", user_now])
                    if st.form_submit_button("Valider la création", type="primary"):
                        if n_p and n_p not in proj_conf:
                            proj_conf[n_p] = {"Cible": t_p, "Date_Fin": "", "Proprietaire": o_p}
                            rows = []
                            for k, v in proj_conf.items(): 
                                rows.append({"Projet": k, "Cible": v["Cible"], "Date_Fin": v["Date_Fin"], "Proprietaire": v.get("Proprietaire", "Commun")})
                            save_data(TAB_PROJETS, pd.DataFrame(rows))
                            st.session_state['show_new_proj'] = False
                            st.success(f"Projet {n_p} créé !")
                            time.sleep(0.5)
                            st.rerun()
                        else: st.error("Nom invalide ou déjà existant")

        filter_owner = st.radio("Afficher :", ["Tout", "Commun", "Perso"], horizontal=True, label_visibility="collapsed")
        st.write("")

        if not proj_conf:
            st.info("Aucun projet d'épargne en cours.")
        else:
            for p_name, p_data in proj_conf.items():
                proprio = p_data.get("Proprietaire", "Commun")
                if filter_owner == "Commun" and proprio != "Commun": continue
                if filter_owner == "Perso" and proprio == "Commun": continue
                
                saved = df[(df["Projet_Epargne"] == p_name) & (df["Type"] == "Épargne")]["Montant"].sum()
                target = float(p_data["Cible"])
                reste = max(0, target - saved)
                progress = min(saved / target if target > 0 else 0, 1.0)
                pct = progress * 100
                bar_color = "#10B981" if progress >= 1.0 else "#3B82F6"
                bg_badge = "#EFF6FF" if proprio == "Commun" else "#FFF7ED"
                txt_badge = "#1E40AF" if proprio == "Commun" else "#9A3412"

                if st.session_state.get(f"edit_mode_{p_name}", False):
                    with st.container():
                        st.markdown(f"""<div style="border:2px solid #3B82F6; border-radius:12px; padding:15px; margin-bottom:15px; background:white;"><div style="font-weight:bold; color:#3B82F6; margin-bottom:10px;">Modification : {p_name}</div>""", unsafe_allow_html=True)
                        c_edit1, c_edit2 = st.columns(2)
                        new_target = c_edit1.number_input("Nouvelle Cible (€)", value=target, key=f"nt_{p_name}")
                        new_prop = c_edit2.selectbox("Propriétaire", ["Commun", user_now], index=0 if proprio=="Commun" else 1, key=f"np_{p_name}")
                        col_save, col_cancel = st.columns([1, 1])
                        if col_save.button("💾 Sauvegarder", key=f"save_{p_name}", use_container_width=True):
                            proj_conf[p_name]["Cible"] = new_target
                            proj_conf[p_name]["Proprietaire"] = new_prop
                            rows = []
                            for k, v in proj_conf.items(): rows.append({"Projet": k, "Cible": v["Cible"], "Date_Fin": v["Date_Fin"], "Proprietaire": v.get("Proprietaire", "Commun")})
                            save_data(TAB_PROJETS, pd.DataFrame(rows))
                            st.session_state[f"edit_mode_{p_name}"] = False
                            st.rerun()
                        if col_cancel.button("Annuler", key=f"cancel_{p_name}", use_container_width=True):
                            st.session_state[f"edit_mode_{p_name}"] = False
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="background-color: white; border: 1px solid #E5E7EB; border-radius: 12px; padding: 16px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                            <div><div style="font-size: 16px; font-weight: 700; color: #1F2937;">{p_name}</div><span style="font-size: 10px; font-weight: 600; text-transform: uppercase; background-color: {bg_badge}; color: {txt_badge}; padding: 2px 8px; border-radius: 10px;">{proprio}</span></div>
                            <div style="text-align: right;"><div style="font-size: 18px; font-weight: 800; color: {bar_color};">{saved:,.0f} €</div><div style="font-size: 11px; color: #6B7280;">sur {target:,.0f} €</div></div>
                        </div>
                        <div style="width: 100%; background-color: #F3F4F6; border-radius: 4px; height: 8px; margin-bottom: 8px; overflow:hidden;"><div style="width: {pct}%; background-color: {bar_color}; height: 100%; border-radius: 4px; transition: width 0.5s;"></div></div>
                        <div style="display: flex; justify-content: space-between; font-size: 12px; color: #6B7280;"><div>{pct:.0f}% financé</div><div>Reste : <b>{reste:,.0f} €</b></div></div>
                    </div>
                    """, unsafe_allow_html=True)
                    c_act1, c_act2, c_void = st.columns([1, 1, 4])
                    if c_act1.button("✏️", key=f"btn_mod_{p_name}", help="Modifier le projet"):
                        st.session_state[f"edit_mode_{p_name}"] = True
                        st.rerun()
                    if c_act2.button("🗑️", key=f"btn_del_{p_name}", help="Supprimer définitivement"):
                        del proj_conf[p_name]
                        rows = []
                        for k, v in proj_conf.items(): rows.append({"Projet": k, "Cible": v["Cible"], "Date_Fin": v["Date_Fin"], "Proprietaire": v.get("Proprietaire", "Commun")})
                        save_data(TAB_PROJETS, pd.DataFrame(rows))
                        st.success("Supprimé")
                        time.sleep(0.5)
                        st.rerun()
    
    with s2:
        with st.form("adj"):
            d=st.date_input("Date"); m=st.number_input("Solde Réel")
            if st.form_submit_button("Enregistrer"):
                df_pat = pd.concat([df_pat, pd.DataFrame([{"Date":d,"Mois":d.month,"Annee":d.year,"Compte":ac,"Montant":m,"Proprietaire":user_now}])], ignore_index=True); save_data(TAB_PATRIMOINE, df_pat); st.rerun()

# TAB 5: REGLAGES
with tabs[4]:
    page_header("Réglages")
    with st.expander("Ajouter Compte"):
        with st.form("nac"):
            n=st.text_input("Nom"); t=st.selectbox("Type", TYPES_COMPTE); c=st.checkbox("Commun")
            if st.form_submit_button("Ajouter"):
                p = "Commun" if c else user_now
                if n and n not in cpt_struct.get(p, []):
                    cpt_struct.setdefault(p, []).append(n)
                    rows = []
                    for pr, l in cpt_struct.items():
                        for ct in l: rows.append({"Proprietaire": pr, "Compte": ct, "Type": cpt_types.get(ct, t)}) # Save type
                    save_data(TAB_COMPTES, pd.DataFrame(rows)); st.rerun()
    
    st.markdown("#### Comptes Actifs")
    for p in [user_now, "Commun"]:
        if p in cpt_struct:
            st.markdown(f"**{p}**")
            for a in cpt_struct[p]:
                c1,c2 = st.columns([4,1]); c1.write(f"- {a}")
                if c2.button("X", key=f"d_{a}"): 
                    cpt_struct[p].remove(a)
                    rows = []
                    for pr, l in cpt_struct.items():
                        for ct in l: rows.append({"Proprietaire": pr, "Compte": ct, "Type": cpt_types.get(ct, "Courant")})
                    save_data(TAB_COMPTES, pd.DataFrame(rows)); st.rerun()

    st.markdown("---")
    t1, t2 = st.tabs(["Catégories", "Mots-Clés"])
    with t1:
        ty=st.selectbox("Type", TYPES, key="st"); nc=st.text_input("Nom")
        if st.button("Ajouter"): cats_mem.setdefault(ty, []).append(nc); save_data(TAB_CONFIG, pd.DataFrame([{"Type": t, "Categorie": c} for t, l in cats_mem.items() for c in l])); st.rerun()
    with t2:
        with st.form("amc"):
            alc = [c for l in cats_mem.values() for c in l]
            m=st.text_input("Mot"); c=st.selectbox("Cat", alc); ty=st.selectbox("Type", TYPES, key="kt"); co=st.selectbox("Cpt", cpt_calc)
            if st.form_submit_button("Lier"): 
                kw_map[m.lower()] = {"Categorie":c,"Type":ty,"Compte":co}
                rows = []
                for mc, data in kw_map.items(): rows.append({"Mot_Cle": mc, "Categorie": data["Categorie"], "Type": data["Type"], "Compte": data["Compte"]})
                save_data(TAB_MOTS_CLES, pd.DataFrame(rows)); st.rerun()
