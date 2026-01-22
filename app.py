# ============================================================================
# APPLICATION BUDGET - VERSION SUPABASE COMPLÈTE
# Toutes les fonctionnalités de la version Google Sheets
# ============================================================================

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from supabase import create_client, Client
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO

# ============================================================================
# 1. CONFIGURATION
# ============================================================================

st.set_page_config(page_title="Ma Banque", layout="wide", page_icon="🏦")

USERS = ["Pierre", "Elie"]
TYPES = ["Dépense", "Revenu", "Épargne", "Virement Interne", "Investissement"]
TYPES_COMPTE = ["Courant", "Épargne"]
IMPUTATIONS = ["Perso", "Commun (50/50)", "Commun (Autre %)", "Avance/Cadeau"]
FREQUENCES_ABO = ["Mensuel", "Trimestriel", "Semestriel", "Annuel"]
MOIS_FR = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

# ============================================================================
# 2. CSS
# ============================================================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background: #FAFAFA; }
    section[data-testid="stSidebar"] { background: white !important; }
    .stButton > button { 
        background: #4F46E5 !important; 
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
    }
    .stButton > button:hover { background: #4338CA !important; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# 3. CONNEXION SUPABASE
# ============================================================================

@st.cache_resource
def get_supabase_client() -> Client:
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"❌ Erreur Supabase: {e}")
        st.stop()

supabase = get_supabase_client()

# ============================================================================
# 4. CHARGEMENT DONNÉES
# ============================================================================

@st.cache_data(ttl=60, show_spinner=False)
def load_transactions():
    try:
        response = supabase.table('transactions').select('*').order('date', desc=True).execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date']).dt.date
            df['montant'] = pd.to_numeric(df['montant'], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame(columns=['id', 'date', 'mois', 'annee', 'type', 'categorie', 'titre', 'description', 'montant', 'compte_source', 'compte_cible', 'imputation', 'qui_connecte', 'paye_par', 'projet_epargne'])

@st.cache_data(ttl=60, show_spinner=False)
def load_patrimoine():
    try:
        response = supabase.table('patrimoine').select('*').order('date', desc=True).execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date']).dt.date
            df['montant'] = pd.to_numeric(df['montant'], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame(columns=['id', 'date', 'mois', 'annee', 'compte', 'montant', 'proprietaire'])

@st.cache_data(ttl=300, show_spinner=False)
def load_comptes():
    try:
        return pd.DataFrame(supabase.table('comptes').select('*').execute().data)
    except:
        return pd.DataFrame(columns=['id', 'proprietaire', 'compte', 'type'])

@st.cache_data(ttl=300, show_spinner=False)
def load_categories():
    try:
        return pd.DataFrame(supabase.table('categories').select('*').execute().data)
    except:
        return pd.DataFrame(columns=['id', 'type', 'categorie'])

@st.cache_data(ttl=300, show_spinner=False)
def load_projets():
    try:
        return pd.DataFrame(supabase.table('projets').select('*').execute().data)
    except:
        return pd.DataFrame(columns=['id', 'projet', 'cible', 'date_fin', 'proprietaire'])

@st.cache_data(ttl=300, show_spinner=False)
def load_objectifs():
    try:
        return pd.DataFrame(supabase.table('objectifs').select('*').execute().data)
    except:
        return pd.DataFrame(columns=['id', 'scope', 'categorie', 'montant'])

@st.cache_data(ttl=300, show_spinner=False)
def load_abonnements():
    try:
        return pd.DataFrame(supabase.table('abonnements').select('*').execute().data)
    except:
        return pd.DataFrame(columns=['id', 'nom', 'montant', 'jour', 'categorie', 'compte_source', 'proprietaire', 'imputation', 'frequence', 'date_debut', 'date_fin'])

@st.cache_data(ttl=300, show_spinner=False)
def load_mots_cles():
    try:
        return pd.DataFrame(supabase.table('mots_cles').select('*').execute().data)
    except:
        return pd.DataFrame(columns=['id', 'mot_cle', 'categorie', 'type', 'compte'])

@st.cache_data(ttl=300, show_spinner=False)
def load_remboursements():
    try:
        response = supabase.table('remboursements').select('*').execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date']).dt.date
        return df
    except:
        return pd.DataFrame(columns=['id', 'date', 'de', 'a', 'montant', 'motif', 'statut'])

@st.cache_data(ttl=300, show_spinner=False)
def load_credits():
    try:
        response = supabase.table('credits').select('*').execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            df['date_debut'] = pd.to_datetime(df['date_debut']).dt.date
            df['date_fin'] = pd.to_datetime(df['date_fin']).dt.date
        return df
    except:
        return pd.DataFrame(columns=['id', 'nom', 'montant_initial', 'montant_restant', 'taux', 'mensualite', 'date_debut', 'date_fin', 'organisme'])

# ============================================================================
# 5. FONCTIONS MÉTIER
# ============================================================================

def calc_soldes(df_t, df_p, comptes):
    soldes = {}
    if not comptes:
        return soldes
    
    for c in comptes:
        solde_base = 0.0
        date_base = pd.to_datetime('2000-01-01').date()
        
        if not df_p.empty and 'compte' in df_p.columns:
            df_c = df_p[df_p['compte'] == c]
            if not df_c.empty:
                last = df_c.sort_values('date', ascending=False).iloc[0]
                solde_base = float(last['montant'])
                date_base = last['date']
        
        if not df_t.empty and 'date' in df_t.columns:
            df_after = df_t[df_t['date'] > date_base]
            
            debits = df_after[
                (df_after['compte_source'] == c) & 
                (df_after['type'].isin(['Dépense', 'Investissement', 'Virement Interne', 'Épargne']))
            ]['montant'].sum()
            
            credits_rev = df_after[(df_after['compte_source'] == c) & (df_after['type'] == 'Revenu')]['montant'].sum()
            credits_vir = df_after[(df_after['compte_cible'] == c) & (df_after['type'].isin(['Virement Interne', 'Épargne']))]['montant'].sum()
            
            soldes[c] = solde_base + credits_rev + credits_vir - debits
        else:
            soldes[c] = solde_base
    
    return soldes

def fmt(montant, decimales=0):
    if montant is None or pd.isna(montant):
        return "0"
    try:
        m = float(montant)
        formatted = f"{m:,.{decimales}f}" if decimales > 0 else f"{m:,.0f}"
        return formatted.replace(',', 'TEMP').replace('.', ',').replace('TEMP', ' ')
    except:
        return "0"

def page_header(titre, soustitre=""):
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 12px; margin-bottom: 2rem; color: white;">
        <h1 style="margin: 0; font-size: 32px; font-weight: 700;">{titre}</h1>
        {f'<p style="margin: 0.5rem 0 0 0; opacity: 0.9;">{soustitre}</p>' if soustitre else ''}
    </div>
    """, unsafe_allow_html=True)

def suggerer_categories(titre, historique_df, mots_cles_map):
    titre_lower = titre.lower()
    
    for mc, info in mots_cles_map.items():
        if mc in titre_lower:
            return info.get('categorie'), "mot-clé"
    
    if not historique_df.empty and 'titre' in historique_df.columns:
        similaires = historique_df[historique_df['titre'].str.lower().str.contains(titre_lower[:5], na=False, regex=False)]
        if not similaires.empty and 'categorie' in similaires.columns:
            cat_freq = similaires['categorie'].value_counts()
            if len(cat_freq) > 0:
                return cat_freq.index[0], f"historique ({len(similaires)} trans.)"
    
    return None, None

def should_generate_abo(abo, mois, annee):
    freq = abo.get('frequence', 'Mensuel')
    date_debut = abo.get('date_debut', '')
    date_fin = abo.get('date_fin', '')
    
    if date_debut:
        debut = pd.to_datetime(date_debut).date()
        if datetime(annee, mois, 1).date() < debut:
            return False
    
    if date_fin:
        fin = pd.to_datetime(date_fin).date()
        if datetime(annee, mois, 1).date() > fin:
            return False
    
    if freq == "Mensuel":
        return True
    elif freq == "Trimestriel":
        return mois % 3 == 0
    elif freq == "Semestriel":
        return mois % 6 == 0
    elif freq == "Annuel":
        return mois == 1
    return True

def to_excel(df):
    out = BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as writer:
        df_copy = df.copy()
        if "date" in df_copy.columns:
            df_copy["date"] = df_copy["date"].astype(str)
        df_copy.to_excel(writer, index=False, sheet_name='Data')
    return out.getvalue()

# ============================================================================
# 6. INIT SESSION STATE
# ============================================================================

if 'needs_refresh' not in st.session_state:
    st.session_state.needs_refresh = True

if st.session_state.needs_refresh:
    with st.spinner('⚡ Chargement...'):
        df = load_transactions()
        df_patrimoine = load_patrimoine()
        df_comptes = load_comptes()
        df_categories = load_categories()
        df_projets = load_projets()
        df_objectifs = load_objectifs()
        df_abonnements = load_abonnements()
        df_mots_cles = load_mots_cles()
        df_remboursements = load_remboursements()
        df_credits = load_credits()
        
        st.session_state.df = df
        st.session_state.df_patrimoine = df_patrimoine
        st.session_state.df_comptes = df_comptes
        st.session_state.df_categories = df_categories
        st.session_state.df_projets = df_projets
        st.session_state.df_objectifs = df_objectifs
        st.session_state.df_abonnements = df_abonnements
        st.session_state.df_mots_cles = df_mots_cles
        st.session_state.df_remboursements = df_remboursements
        st.session_state.df_credits = df_credits
        st.session_state.needs_refresh = False
else:
    df = st.session_state.df
    df_patrimoine = st.session_state.df_patrimoine
    df_comptes = st.session_state.df_comptes
    df_categories = st.session_state.df_categories
    df_projets = st.session_state.df_projets
    df_objectifs = st.session_state.df_objectifs
    df_abonnements = st.session_state.df_abonnements
    df_mots_cles = st.session_state.df_mots_cles
    df_remboursements = st.session_state.df_remboursements
    df_credits = st.session_state.df_credits

# Structures
comptes_structure = {}
comptes_types = {}
if not df_comptes.empty:
    for _, row in df_comptes.iterrows():
        comptes_structure.setdefault(row['proprietaire'], []).append(row['compte'])
        comptes_types[row['compte']] = row.get('type', 'Courant')

categories = {t: [] for t in TYPES}
if not df_categories.empty:
    for _, row in df_categories.iterrows():
        categories.setdefault(row['type'], []).append(row['categorie'])

if not categories.get('Dépense'):
    categories['Dépense'] = ["Alimentation", "Transport", "Logement", "Santé", "Loisirs", "Shopping", "Autre"]
if not categories.get('Revenu'):
    categories['Revenu'] = ["Salaire", "Prime", "Autre"]
if not categories.get('Épargne'):
    categories['Épargne'] = ["Épargne Mensuelle", "Autre"]

projets_config = {}
if not df_projets.empty:
    for _, row in df_projets.iterrows():
        projets_config[row['projet']] = {
            'Cible': float(row['cible']),
            'Date_Fin': row.get('date_fin'),
            'Proprietaire': row.get('proprietaire', 'Commun')
        }

objectifs_list = df_objectifs.to_dict('records') if not df_objectifs.empty else []

mots_cles_map = {}
if not df_mots_cles.empty:
    for _, row in df_mots_cles.iterrows():
        mots_cles_map[row['mot_cle'].lower()] = {
            'categorie': row.get('categorie'),
            'type': row.get('type'),
            'compte': row.get('compte')
        }

# ============================================================================
# 7. SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown("# 👤 Utilisateur")
    user_actuel = st.selectbox("", USERS, label_visibility="collapsed")
    
    st.markdown("---")
    st.markdown("### 📅 Période")
    
    m_nom = st.selectbox("Mois", MOIS_FR, index=datetime.now().month-1, label_visibility="collapsed")
    m_sel = MOIS_FR.index(m_nom) + 1
    a_sel = st.number_input("Année", value=datetime.now().year, label_visibility="collapsed")
    
    df_mois = df[(df['mois'] == m_sel) & (df['annee'] == a_sel)] if not df.empty and 'mois' in df.columns else pd.DataFrame()
    df_mois_user = df_mois[df_mois['qui_connecte'] == user_actuel] if not df_mois.empty and 'qui_connecte' in df_mois.columns else pd.DataFrame()
    
    st.markdown("---")
    
    tous_comptes = comptes_structure.get(user_actuel, [])
    soldes = calc_soldes(df, df_patrimoine, tous_comptes)
    
    comptes_courants = [c for c in tous_comptes if comptes_types.get(c) == 'Courant']
    comptes_epargne = [c for c in tous_comptes if comptes_types.get(c) == 'Épargne']
    
    total_courant = sum(soldes.get(c, 0) for c in comptes_courants)
    total_epargne = sum(soldes.get(c, 0) for c in comptes_epargne)
    
    st.markdown(f"""
    <div style='background: white; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;'>
        <div style='color: #6B7280; font-size: 11px; font-weight: 600;'>💳 COMPTES COURANTS</div>
        <div style='color: #1F2937; font-size: 24px; font-weight: 700;'>{fmt(total_courant)} €</div>
    </div>
    """, unsafe_allow_html=True)
    
    for compte in comptes_courants:
        solde = soldes.get(compte, 0)
        color = "#10B981" if solde >= 0 else "#EF4444"
        st.markdown(f"""
        <div style='background: white; padding: 0.75rem; border-radius: 6px; margin-bottom: 0.5rem; border-left: 3px solid {color};'>
            <div style='font-size: 12px; color: #6B7280;'>{compte}</div>
            <div style='font-size: 16px; font-weight: 600; color: {color};'>{fmt(solde, 2)} €</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.write("")
    
    st.markdown(f"""
    <div style='background: white; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;'>
        <div style='color: #6B7280; font-size: 11px; font-weight: 600;'>💰 ÉPARGNE</div>
        <div style='color: #1F2937; font-size: 24px; font-weight: 700;'>{fmt(total_epargne)} €</div>
    </div>
    """, unsafe_allow_html=True)
    
    for compte in comptes_epargne:
        solde = soldes.get(compte, 0)
        st.markdown(f"""
        <div style='background: white; padding: 0.75rem; border-radius: 6px; margin-bottom: 0.5rem; border-left: 3px solid #4F46E5;'>
            <div style='font-size: 12px; color: #6B7280;'>{compte}</div>
            <div style='font-size: 16px; font-weight: 600; color: #4F46E5;'>{fmt(solde, 2)} €</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    if st.button("🔄 Actualiser", use_container_width=True):
        st.cache_data.clear()
        st.session_state.needs_refresh = True
        st.rerun()

# ============================================================================
# 8. TABS PRINCIPALES
# ============================================================================

tabs = st.tabs(["🏠 Accueil", "💰 Opérations", "📊 Analyses", "💎 Patrimoine", "💸 Remboursements", "⚙️ Réglages"])

# ===== TAB 1: ACCUEIL =====
with tabs[0]:
    page_header(f"Synthèse - {m_nom} {a_sel}", f"Compte de {user_actuel}")
    
    if not df_mois_user.empty:
        rev = df_mois_user[df_mois_user['type'] == 'Revenu']['montant'].sum()
        dep = df_mois_user[(df_mois_user['type'] == 'Dépense') & (df_mois_user['imputation'] == 'Perso')]['montant'].sum()
        epg = df_mois_user[df_mois_user['type'] == 'Épargne']['montant'].sum()
    else:
        rev = dep = epg = 0
    
    com = df_mois[df_mois['imputation'] == 'Commun (50/50)']['montant'].sum() / 2 if not df_mois.empty and 'imputation' in df_mois.columns else 0
    fixe = 0
    rav = rev - fixe - dep - com
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    col1.metric("Revenus", f"{fmt(rev)} €")
    col2.metric("Fixe", f"{fmt(fixe)} €")
    col3.metric("Dépenses", f"{fmt(dep+com)} €")
    
    pct_epargne = (epg / rev * 100) if rev > 0 else 0
    col4.markdown(f"""
    <div style='background: white; padding: 1.25rem; border-radius: 12px; border: 1px solid #E5E7EB;'>
        <div style='color: #6B7280; font-size: 11px; font-weight: 600;'>ÉPARGNE</div>
        <div style='color: #4F46E5; font-size: 28px; font-weight: 700;'>{fmt(epg)} €</div>
        <div style='color: #10B981; font-size: 11px;'>{pct_epargne:.1f}% du revenu</div>
    </div>
    """, unsafe_allow_html=True)
    
    color = "#10B981" if rav >= 0 else "#EF4444"
    icon = "✓" if rav >= 0 else "⚠"
    col5.markdown(f"""
    <div style='background: {color}; padding: 1.25rem; border-radius: 12px; color: white; text-align: center;'>
        <div style='font-size: 11px; font-weight: 600;'>{icon} RESTE À VIVRE</div>
        <div style='font-size: 28px; font-weight: 700;'>{fmt(rav)} €</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    
    if not df_mois_user.empty and 'type' in df_mois_user.columns:
        df_dep = df_mois_user[df_mois_user['type'] == 'Dépense']
        if not df_dep.empty and 'categorie' in df_dep.columns:
            dep_par_cat = df_dep.groupby('categorie')['montant'].sum().sort_values(ascending=False)
            
            fig = go.Figure(data=[go.Bar(
                x=dep_par_cat.values,
                y=dep_par_cat.index,
                orientation='h',
                marker_color='#667eea'
            )])
            fig.update_layout(title="Dépenses par catégorie", xaxis_title="Montant (€)", height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

# ===== TAB 2: OPÉRATIONS =====
with tabs[1]:
    op_tabs = st.tabs(["Saisie", "Journal", "Abonnements"])
    
    with op_tabs[0]:
        page_header("Nouvelle Transaction")
        
        with st.form("new_trans_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            date_t = col1.date_input("Date", datetime.today())
            type_t = col2.selectbox("Type", TYPES)
            montant_t = col3.number_input("Montant (€)", min_value=0.01, step=0.01)
            
            col4, col5 = st.columns(2)
            titre_t = col4.text_input("Titre")
            
            cat_suggeree, source = suggerer_categories(titre_t, df[df['type']==type_t] if not df.empty and 'type' in df.columns else pd.DataFrame(), mots_cles_map)
            idx_cat = categories.get(type_t, []).index(cat_suggeree) if cat_suggeree and cat_suggeree in categories.get(type_t, []) else 0
            cat_t = col5.selectbox("Catégorie", categories.get(type_t, []), index=idx_cat)
            
            if source:
                st.caption(f"💡 Suggéré : {source}")
            
            col6, col7 = st.columns(2)
            compte_t = col6.selectbox("Compte Source", tous_comptes)
            imp_t = col7.selectbox("Imputation", IMPUTATIONS)
            
            compte_cible_t = ""
            projet_t = ""
            
            if type_t == "Épargne":
                comptes_epg = [c for c in tous_comptes if comptes_types.get(c) == 'Épargne']
                if comptes_epg:
                    compte_cible_t = st.selectbox("Vers Compte Épargne", comptes_epg)
                projets_access = [p for p, d in projets_config.items() if d.get("Proprietaire", "Commun") in ["Commun", user_actuel]]
                ps = st.selectbox("Projet (opt.)", ["Aucun"] + projets_access)
                if ps != "Aucun":
                    projet_t = ps
            
            elif type_t == "Virement Interne":
                compte_cible_t = st.selectbox("Vers Compte", [c for c in tous_comptes if c != compte_t])
            
            submitted = st.form_submit_button("💾 Valider", use_container_width=True)
            
            if submitted:
                if not titre_t:
                    st.error("Titre requis")
                elif montant_t <= 0:
                    st.error("Montant doit être > 0")
                else:
                    data = {
                        'date': str(date_t),
                        'mois': date_t.month,
                        'annee': date_t.year,
                        'type': type_t,
                        'categorie': cat_t,
                        'titre': titre_t,
                        'description': "",
                        'montant': float(montant_t),
                        'compte_source': compte_t,
                        'compte_cible': compte_cible_t,
                        'imputation': imp_t,
                        'qui_connecte': user_actuel,
                        'paye_par': user_actuel,
                        'projet_epargne': projet_t
                    }
                    
                    try:
                        supabase.table('transactions').insert(data).execute()
                        st.cache_data.clear()
                        st.session_state.needs_refresh = True
                        st.success("✅ Transaction enregistrée")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erreur: {e}")
    
    with op_tabs[1]:
        st.markdown("### 📋 Journal des transactions")
        
        search = st.text_input("🔍 Rechercher", placeholder="Titre, catégorie...")
        
        if not df.empty:
            df_filtered = df.sort_values('date', ascending=False)
            
            if search:
                df_filtered = df_filtered[
                    df_filtered.apply(lambda r: search.lower() in str(r).lower(), axis=1)
                ]
            
            st.download_button("📥 Exporter Excel", to_excel(df_filtered), "journal.xlsx", use_container_width=True)
            
            if not df_filtered.empty:
                for _, row in df_filtered.head(20).iterrows():
                    col_info, col_del = st.columns([5, 1])
                    
                    with col_info:
                        is_dep = row['type'] in ['Dépense', 'Virement Interne', 'Épargne', 'Investissement']
                        color = "#EF4444" if is_dep else "#10B981"
                        sign = "-" if is_dep else "+"
                        
                        st.markdown(f"""
                        <div style='background: white; border: 1px solid #E5E7EB; border-radius: 8px; padding: 1rem; margin-bottom: 0.5rem;'>
                            <div style='display: flex; justify-content: space-between; align-items: center;'>
                                <div>
                                    <div style='font-weight: 600; color: #1F2937;'>{row['titre']}</div>
                                    <div style='font-size: 12px; color: #6B7280;'>{row['date']} • {row.get('categorie', '')} • {row['type']}</div>
                                </div>
                                <div style='font-weight: 700; color: {color}; font-size: 18px;'>{sign}{fmt(row['montant'], 2)} €</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col_del:
                        if st.button("🗑️", key=f"del_{row['id']}", use_container_width=True):
                            try:
                                supabase.table('transactions').delete().eq('id', row['id']).execute()
                                st.cache_data.clear()
                                st.session_state.needs_refresh = True
                                st.rerun()
                            except:
                                st.error("❌ Erreur suppression")
            else:
                st.info("Aucune transaction trouvée")
        else:
            st.info("Aucune transaction")
    
    with op_tabs[2]:
        page_header("Mes Abonnements", "Gérez vos dépenses récurrentes")
        
        if st.button("➕ Nouveau", use_container_width=True, type="primary"):
            st.session_state['new_abo'] = not st.session_state.get('new_abo', False)
        
        if st.session_state.get('new_abo', False):
            st.markdown("### 📝 Créer un abonnement")
            
            with st.form("new_abo_form"):
                col1, col2, col3 = st.columns(3)
                nom_abo = col1.text_input("Nom", placeholder="Ex: Netflix, EDF...")
                montant_abo = col2.number_input("Montant (€)", min_value=0.0, step=0.01)
                freq_abo = col3.selectbox("Fréquence", FREQUENCES_ABO)
                
                col4, col5 = st.columns(2)
                jour_abo = col4.number_input("Jour du mois", min_value=1, max_value=31, value=1)
                cat_abo = col5.selectbox("Catégorie", categories.get('Dépense', []))
                
                col6, col7 = st.columns(2)
                compte_abo = col6.selectbox("Compte", tous_comptes)
                imp_abo = col7.selectbox("Imputation", IMPUTATIONS)
                
                col8, col9 = st.columns(2)
                date_deb_abo = col8.date_input("Date début", datetime.today())
                date_fin_abo = col9.date_input("Date fin (opt.)", value=None)
                
                col_btn1, col_btn2 = st.columns(2)
                
                if col_btn1.form_submit_button("✅ Créer", use_container_width=True):
                    if nom_abo and montant_abo > 0:
                        data = {
                            'nom': nom_abo,
                            'montant': float(montant_abo),
                            'jour': int(jour_abo),
                            'categorie': cat_abo,
                            'compte_source': compte_abo,
                            'proprietaire': user_actuel,
                            'imputation': imp_abo,
                            'frequence': freq_abo,
                            'date_debut': str(date_deb_abo),
                            'date_fin': str(date_fin_abo) if date_fin_abo else None
                        }
                        
                        try:
                            supabase.table('abonnements').insert(data).execute()
                            st.cache_data.clear()
                            st.session_state.needs_refresh = True
                            st.session_state['new_abo'] = False
                            st.success("✅ Abonnement créé")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erreur: {e}")
                    else:
                        st.error("Nom et montant requis")
                
                if col_btn2.form_submit_button("❌ Annuler", use_container_width=True):
                    st.session_state['new_abo'] = False
                    st.rerun()
        
        st.write("")
        
        # Génération automatique
        if not df_abonnements.empty:
            ma = df_abonnements[df_abonnements['proprietaire'] == user_actuel]
            
            to_gen = []
            for _, abo in ma.iterrows():
                if should_generate_abo(abo, m_sel, a_sel):
                    paid = not df_mois[(df_mois['titre'].str.lower() == abo['nom'].lower()) & (df_mois['montant'] == float(abo['montant']))].empty if not df_mois.empty and 'titre' in df_mois.columns else False
                    if not paid:
                        to_gen.append(abo)
            
            if to_gen:
                if st.button(f"⚡ Générer {len(to_gen)} transaction(s) pour {m_nom}", type="primary", use_container_width=True):
                    for abo in to_gen:
                        try:
                            d = datetime(a_sel, m_sel, int(abo['jour'])).date()
                        except:
                            d = datetime(a_sel, m_sel, 28).date()
                        
                        data = {
                            'date': str(d),
                            'mois': m_sel,
                            'annee': a_sel,
                            'type': 'Dépense',
                            'categorie': abo['categorie'],
                            'titre': abo['nom'],
                            'description': f"Auto - {abo['frequence']}",
                            'montant': float(abo['montant']),
                            'compte_source': abo['compte_source'],
                            'compte_cible': "",
                            'imputation': abo['imputation'],
                            'qui_connecte': abo['proprietaire'],
                            'paye_par': abo['proprietaire'],
                            'projet_epargne': ""
                        }
                        
                        try:
                            supabase.table('transactions').insert(data).execute()
                        except:
                            pass
                    
                    st.cache_data.clear()
                    st.session_state.needs_refresh = True
                    st.success(f"✅ {len(to_gen)} transaction(s) générée(s)")
                    st.rerun()
            
            st.write("")
            
            # Affichage
            for idx, abo in ma.iterrows():
                if should_generate_abo(abo, m_sel, a_sel):
                    paid = not df_mois[(df_mois['titre'].str.lower() == abo['nom'].lower()) & (df_mois['montant'] == float(abo['montant']))].empty if not df_mois.empty and 'titre' in df_mois.columns else False
                    statut = "PAYÉ" if paid else "EN ATTENTE"
                    color = "#10B981" if paid else "#F59E0B"
                else:
                    statut = "NON PRÉVU"
                    color = "#6B7280"
                
                st.markdown(f"""
                <div style='background: white; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem;'>
                    <div style='display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;'>
                        <div>
                            <div style='font-weight: 700; font-size: 18px; color: #1F2937;'>{abo['nom']}</div>
                            <div style='font-size: 13px; color: #6B7280; margin-top: 0.25rem;'>Jour {abo['jour']} • {abo['frequence']}</div>
                        </div>
                        <div style='background: {color}; color: white; padding: 0.25rem 0.75rem; border-radius: 6px; font-size: 12px; font-weight: 700;'>{statut}</div>
                    </div>
                    <div style='font-size: 24px; font-weight: 700; color: {color};'>{fmt(abo['montant'], 2)} €</div>
                </div>
                """, unsafe_allow_html=True)
                
                col_edit, col_del = st.columns(2)
                if col_del.button("🗑️ Supprimer", key=f"del_abo_{idx}", use_container_width=True):
                    try:
                        supabase.table('abonnements').delete().eq('id', abo['id']).execute()
                        st.cache_data.clear()
                        st.session_state.needs_refresh = True
                        st.rerun()
                    except:
                        st.error("❌ Erreur")
        else:
            st.info("Aucun abonnement")

# ===== TAB 3: ANALYSES =====
with tabs[2]:
    page_header("Analyses", "Visualisez vos finances")
    
    analysis_tabs = st.tabs(["Vue Globale", "Évolution", "Top Dépenses"])
    
    with analysis_tabs[0]:
        st.markdown("### 📊 Résumé du mois")
        
        if not df_mois.empty:
            rev_tot = df_mois[df_mois['type'] == 'Revenu']['montant'].sum() if 'type' in df_mois.columns else 0
            dep_tot = df_mois[df_mois['type'] == 'Dépense']['montant'].sum() if 'type' in df_mois.columns else 0
            epg_tot = df_mois[df_mois['type'] == 'Épargne']['montant'].sum() if 'type' in df_mois.columns else 0
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Revenus", f"{fmt(rev_tot)} €")
            col2.metric("Dépenses", f"{fmt(dep_tot)} €")
            col3.metric("Épargne", f"{fmt(epg_tot)} €")
            
            st.write("")
            
            if 'categorie' in df_mois.columns and 'type' in df_mois.columns:
                df_dep = df_mois[df_mois['type'] == 'Dépense'].groupby('categorie')['montant'].sum()
                
                if not df_dep.empty:
                    fig = go.Figure(data=[go.Pie(
                        labels=df_dep.index,
                        values=df_dep.values,
                        hole=0.5
                    )])
                    fig.update_layout(title="Répartition des dépenses", height=400)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune donnée ce mois")
    
    with analysis_tabs[1]:
        st.markdown("### 📈 Évolution sur 12 mois")
        
        date_fin = datetime(a_sel, m_sel, 1)
        dates_12m = [(date_fin - relativedelta(months=i)).replace(day=1) for i in range(11, -1, -1)]
        
        evolution_data = []
        for d in dates_12m:
            mois, annee = d.month, d.year
            df_m = df[(df['mois'] == mois) & (df['annee'] == annee) & (df['qui_connecte'] == user_actuel)] if not df.empty and 'mois' in df.columns else pd.DataFrame()
            
            rev_m = df_m[df_m['type'] == 'Revenu']['montant'].sum() if not df_m.empty and 'type' in df_m.columns else 0
            dep_m = df_m[df_m['type'] == 'Dépense']['montant'].sum() if not df_m.empty and 'type' in df_m.columns else 0
            
            evolution_data.append({
                'Mois': d.strftime("%b %y"),
                'Revenus': rev_m,
                'Dépenses': dep_m
            })
        
        df_evol = pd.DataFrame(evolution_data)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_evol['Mois'], y=df_evol['Revenus'], name='Revenus', line=dict(color='#10B981', width=3)))
        fig.add_trace(go.Scatter(x=df_evol['Mois'], y=df_evol['Dépenses'], name='Dépenses', line=dict(color='#EF4444', width=3)))
        fig.update_layout(title="Revenus vs Dépenses", height=400, hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
    
    with analysis_tabs[2]:
        st.markdown("### 💸 Top 10 des dépenses")
        
        period = st.radio("Période", ["Ce mois", "Cette année", "Tout"], horizontal=True)
        
        if period == "Ce mois":
            df_top = df_mois[(df_mois['qui_connecte'] == user_actuel) & (df_mois['type'] == 'Dépense')] if not df_mois.empty and 'type' in df_mois.columns else pd.DataFrame()
        elif period == "Cette année":
            df_top = df[(df['annee'] == a_sel) & (df['qui_connecte'] == user_actuel) & (df['type'] == 'Dépense')] if not df.empty and 'annee' in df.columns else pd.DataFrame()
        else:
            df_top = df[(df['qui_connecte'] == user_actuel) & (df['type'] == 'Dépense')] if not df.empty and 'qui_connecte' in df.columns else pd.DataFrame()
        
        if not df_top.empty and 'montant' in df_top.columns:
            top10 = df_top.nlargest(10, 'montant')
            
            for idx, (_, r) in enumerate(top10.iterrows()):
                st.markdown(f"""
                <div style='background: white; border: 1px solid #E5E7EB; border-radius: 8px; padding: 1rem; margin-bottom: 0.5rem;'>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <div>
                            <span style='background: #EF4444; color: white; padding: 0.25rem 0.5rem; border-radius: 4px; font-weight: 700; font-size: 12px; margin-right: 0.5rem;'>#{idx+1}</span>
                            <span style='font-weight: 600;'>{r['titre']}</span>
                            <span style='font-size: 12px; color: #6B7280; margin-left: 0.5rem;'>• {r['date']} • {r.get('categorie', '')}</span>
                        </div>
                        <div style='font-weight: 700; font-size: 20px; color: #EF4444;'>{fmt(r['montant'], 2)} €</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Aucune dépense")

# ===== TAB 4: PATRIMOINE =====
with tabs[3]:
    page_header("Patrimoine", "Gérez vos comptes et projets")
    
    pat_tabs = st.tabs(["💳 Comptes", "💰 Projets", "⚙️ Ajustement"])
    
    with pat_tabs[0]:
        st.markdown("### 💳 Mes comptes")
        
        compte_sel = st.selectbox("Sélectionner un compte", tous_comptes)
        
        if compte_sel:
            solde = soldes.get(compte_sel, 0)
            compte_type = comptes_types.get(compte_sel, 'Courant')
            
            color = "#10B981" if solde >= 0 else "#EF4444"
            
            st.markdown(f"""
            <div style='background: {"#F0FDF4" if solde >= 0 else "#FEF2F2"}; border: 2px solid {color}; border-radius: 12px; padding: 2rem; text-align: center; margin-bottom: 2rem;'>
                <div style='color: #6B7280; font-size: 13px; font-weight: 600;'>SOLDE ACTUEL</div>
                <div style='color: #1F2937; font-size: 12px; margin-top: 0.25rem;'>{compte_sel} • {compte_type}</div>
                <div style='color: {color}; font-size: 48px; font-weight: 700; margin-top: 1rem;'>{fmt(solde, 2)} €</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("### 📋 Dernières transactions")
            
            df_compte = df[(df['compte_source'] == compte_sel) | (df['compte_cible'] == compte_sel)] if not df.empty and 'compte_source' in df.columns else pd.DataFrame()
            
            if not df_compte.empty:
                df_compte_sorted = df_compte.sort_values('date', ascending=False).head(10)
                
                for _, r in df_compte_sorted.iterrows():
                    is_debit = r['compte_source'] == compte_sel and r['type'] in ['Dépense', 'Virement Interne', 'Épargne', 'Investissement']
                    color_t = "#EF4444" if is_debit else "#10B981"
                    sign = "-" if is_debit else "+"
                    
                    st.markdown(f"""
                    <div style='background: white; border: 1px solid #E5E7EB; border-radius: 8px; padding: 1rem; margin-bottom: 0.5rem;'>
                        <div style='display: flex; justify-content: space-between; align-items: center;'>
                            <div>
                                <div style='font-weight: 600;'>{r['titre']}</div>
                                <div style='font-size: 12px; color: #6B7280;'>{r['date']} • {r.get('type', '')}</div>
                            </div>
                            <div style='font-weight: 700; color: {color_t}; font-size: 18px;'>{sign}{fmt(r['montant'], 2)} €</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Aucune transaction")
    
    with pat_tabs[1]:
        st.markdown("### 💰 Projets d'épargne")
        
        col_btn = st.columns([3, 1])
        with col_btn[1]:
            if st.button("➕ Nouveau", use_container_width=True):
                st.session_state['new_projet'] = not st.session_state.get('new_projet', False)
        
        if st.session_state.get('new_projet', False):
            with st.form("new_projet_form"):
                col1, col2, col3 = st.columns(3)
                nom_p = col1.text_input("Nom du projet")
                cible_p = col2.number_input("Objectif (€)", min_value=0.0, step=100.0)
                prop_p = col3.selectbox("Propriétaire", ["Commun", user_actuel])
                
                col_btn1, col_btn2 = st.columns(2)
                
                if col_btn1.form_submit_button("✅ Créer", use_container_width=True):
                    if nom_p and cible_p > 0:
                        data = {
                            'projet': nom_p,
                            'cible': float(cible_p),
                            'date_fin': None,
                            'proprietaire': prop_p
                        }
                        
                        try:
                            supabase.table('projets').insert(data).execute()
                            st.cache_data.clear()
                            st.session_state.needs_refresh = True
                            st.session_state['new_projet'] = False
                            st.success("✅ Projet créé")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erreur: {e}")
                
                if col_btn2.form_submit_button("❌ Annuler", use_container_width=True):
                    st.session_state['new_projet'] = False
                    st.rerun()
        
        st.write("")
        
        if projets_config:
            for p, d in projets_config.items():
                prop = d.get('Proprietaire', 'Commun')
                
                if prop not in ['Commun', user_actuel]:
                    continue
                
                s = df[(df['projet_epargne'] == p) & (df['type'] == 'Épargne')]['montant'].sum() if not df.empty and 'projet_epargne' in df.columns else 0
                t = float(d['Cible'])
                pct = min(s/t if t > 0 else 0, 1.0) * 100
                
                color_prog = "#10B981" if pct >= 100 else "#4F46E5"
                
                st.markdown(f"""
                <div style='background: white; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem;'>
                    <div style='font-weight: 700; font-size: 18px; margin-bottom: 0.5rem;'>{p}</div>
                    <div style='font-size: 12px; color: #6B7280; margin-bottom: 1rem;'>{prop}</div>
                    <div style='display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.75rem;'>
                        <div>
                            <span style='font-weight: 700; color: {color_prog}; font-size: 24px;'>{fmt(s)} €</span>
                            <span style='color: #6B7280; font-size: 14px;'>/ {fmt(t)} €</span>
                        </div>
                        <span style='color: {color_prog}; font-weight: 700;'>{pct:.0f}%</span>
                    </div>
                    <div style='background: #E5E7EB; height: 8px; border-radius: 4px; overflow: hidden;'>
                        <div style='background: {color_prog}; height: 100%; width: {pct:.1f}%;'></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Aucun projet")
    
    with pat_tabs[2]:
        st.markdown("### ⚙️ Ajuster le solde")
        
        with st.form("ajust_solde"):
            col1, col2 = st.columns(2)
            date_adj = col1.date_input("Date", datetime.today())
            compte_adj = col2.selectbox("Compte", tous_comptes)
            
            montant_adj_text = st.text_input("Solde réel (€)", placeholder="Ex: 7500,45 ou 7500.45")
            
            if st.form_submit_button("💾 Enregistrer", use_container_width=True):
                try:
                    montant_clean = montant_adj_text.replace(' ', '').replace(',', '.')
                    montant_adj = float(montant_clean)
                    
                    data = {
                        'date': str(date_adj),
                        'mois': date_adj.month,
                        'annee': date_adj.year,
                        'compte': compte_adj,
                        'montant': montant_adj,
                        'proprietaire': user_actuel
                    }
                    
                    supabase.table('patrimoine').insert(data).execute()
                    st.cache_data.clear()
                    st.session_state.needs_refresh = True
                    st.success("✅ Solde ajusté")
                    st.rerun()
                except ValueError:
                    st.error("Format invalide")
                except Exception as e:
                    st.error(f"❌ Erreur: {e}")

# ===== TAB 5: REMBOURSEMENTS =====
with tabs[4]:
    page_header("Remboursements & Crédits")
    
    remb_tabs = st.tabs(["💰 Qui doit quoi ?", "💳 Crédits"])
    
    with remb_tabs[0]:
        st.markdown("### 💸 Équilibre Pierre / Elie")
        
        total_p_vers_e = 0
        total_e_vers_p = 0
        
        avances = df[df['imputation'] == 'Avance/Cadeau'] if not df.empty and 'imputation' in df.columns else pd.DataFrame()
        
        if not avances.empty and 'paye_par' in avances.columns:
            for _, a in avances.iterrows():
                if a['paye_par'] == 'Pierre':
                    total_p_vers_e += a['montant']
                else:
                    total_e_vers_p += a['montant']
        
        if not df_remboursements.empty and 'statut' in df_remboursements.columns:
            remb_effectues = df_remboursements[df_remboursements['statut'] == 'Payé']
            for _, r in remb_effectues.iterrows():
                if r['de'] == 'Pierre':
                    total_p_vers_e -= r['montant']
                else:
                    total_e_vers_p -= r['montant']
        
        solde_net = total_p_vers_e - total_e_vers_p
        debiteur = "Pierre" if solde_net < 0 else "Elie"
        montant_dette = abs(solde_net)
        
        col1, col2, col3 = st.columns(3)
        
        col1.markdown(f"""
        <div style='background: #EFF6FF; padding: 1.5rem; border-radius: 12px; text-align: center;'>
            <div style='color: #3B82F6; font-size: 14px; font-weight: 600;'>Pierre a avancé</div>
            <div style='font-size: 28px; font-weight: 700; color: #1E40AF;'>{fmt(total_p_vers_e)} €</div>
        </div>
        """, unsafe_allow_html=True)
        
        col2.markdown(f"""
        <div style='background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%); padding: 2rem; border-radius: 12px; text-align: center; color: white;'>
            <div style='font-size: 16px; margin-bottom: 1rem;'>{f"{debiteur} doit rembourser" if solde_net != 0 else "Équilibré !"}</div>
            <div style='font-size: 48px; font-weight: 700;'>{fmt(montant_dette)} €</div>
        </div>
        """, unsafe_allow_html=True)
        
        col3.markdown(f"""
        <div style='background: #F0FDF4; padding: 1.5rem; border-radius: 12px; text-align: center;'>
            <div style='color: #10B981; font-size: 14px; font-weight: 600;'>Elie a avancé</div>
            <div style='font-size: 28px; font-weight: 700; color: #059669;'>{fmt(total_e_vers_p)} €</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        
        if solde_net != 0:
            st.markdown("### 💸 Enregistrer un remboursement")
            
            with st.form("remb_form"):
                col_r1, col_r2, col_r3 = st.columns(3)
                montant_remb = col_r1.number_input("Montant (€)", min_value=0.0, max_value=float(montant_dette), value=float(montant_dette), step=0.01)
                date_remb = col_r2.date_input("Date", datetime.today())
                motif_remb = col_r3.text_input("Motif (opt.)")
                
                if st.form_submit_button("✅ Enregistrer", use_container_width=True):
                    data = {
                        'date': str(date_remb),
                        'de': debiteur,
                        'a': 'Elie' if debiteur == 'Pierre' else 'Pierre',
                        'montant': float(montant_remb),
                        'motif': motif_remb if motif_remb else 'Remboursement',
                        'statut': 'Payé'
                    }
                    
                    try:
                        supabase.table('remboursements').insert(data).execute()
                        st.cache_data.clear()
                        st.session_state.needs_refresh = True
                        st.success(f"✅ Remboursement de {fmt(montant_remb)} € enregistré")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erreur: {e}")
    
    with remb_tabs[1]:
        st.markdown("### 💳 Mes crédits")
        
        if st.button("➕ Nouveau crédit", use_container_width=True):
            st.session_state['new_credit'] = not st.session_state.get('new_credit', False)
        
        if st.session_state.get('new_credit', False):
            with st.form("new_credit_form"):
                col1, col2 = st.columns(2)
                nom_c = col1.text_input("Nom du crédit")
                org_c = col2.text_input("Organisme")
                
                col3, col4 = st.columns(2)
                montant_c = col3.number_input("Montant emprunté (€)", min_value=0.0, step=100.0)
                taux_c = col4.number_input("Taux (%)", min_value=0.0, step=0.1)
                
                mensualite_c = st.number_input("Mensualité (€)", min_value=0.0, step=10.0)
                
                col5, col6 = st.columns(2)
                date_deb_c = col5.date_input("Date début", datetime.today())
                duree_mois = col6.number_input("Durée (mois)", min_value=1, value=120, step=12)
                
                date_fin_c = date_deb_c + relativedelta(months=int(duree_mois))
                st.caption(f"Date fin prévue: {date_fin_c.strftime('%d/%m/%Y')}")
                
                col_btn1, col_btn2 = st.columns(2)
                
                if col_btn1.form_submit_button("✅ Créer", use_container_width=True):
                    if nom_c and montant_c > 0:
                        data = {
                            'nom': nom_c,
                            'montant_initial': float(montant_c),
                            'montant_restant': float(montant_c),
                            'taux': float(taux_c),
                            'mensualite': float(mensualite_c),
                            'date_debut': str(date_deb_c),
                            'date_fin': str(date_fin_c),
                            'organisme': org_c
                        }
                        
                        try:
                            supabase.table('credits').insert(data).execute()
                            st.cache_data.clear()
                            st.session_state.needs_refresh = True
                            st.session_state['new_credit'] = False
                            st.success("✅ Crédit créé")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erreur: {e}")
                
                if col_btn2.form_submit_button("❌ Annuler", use_container_width=True):
                    st.session_state['new_credit'] = False
                    st.rerun()
        
        st.write("")
        
        if not df_credits.empty:
            for idx, credit in df_credits.iterrows():
                montant_init = float(credit['montant_initial'])
                montant_rest = float(credit['montant_restant'])
                progression = ((montant_init - montant_rest) / montant_init * 100) if montant_init > 0 else 0
                
                st.markdown(f"""
                <div style='background: white; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem;'>
                    <div style='display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;'>
                        <div>
                            <h4 style='margin: 0; font-size: 18px;'>{credit['nom']}</h4>
                            <div style='font-size: 13px; color: #6B7280;'>{credit.get('organisme', '')} • Taux: {credit['taux']:.2f}%</div>
                        </div>
                        <div style='text-align: right;'>
                            <div style='font-size: 24px; font-weight: 700; color: #EF4444;'>{fmt(montant_rest)} €</div>
                            <div style='font-size: 12px; color: #6B7280;'>sur {fmt(montant_init)} €</div>
                        </div>
                    </div>
                    <div style='background: #F3F4F6; height: 10px; border-radius: 5px; overflow: hidden; margin-bottom: 1rem;'>
                        <div style='background: #10B981; height: 100%; width: {progression}%;'></div>
                    </div>
                    <div style='font-size: 13px;'>
                        <strong>Mensualité:</strong> {fmt(credit['mensualite'])} € • <strong>Progression:</strong> {progression:.1f}%
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                col_remb, col_del = st.columns(2)
                
                with col_remb:
                    with st.form(f"remb_credit_{idx}"):
                        montant_remb_c = st.number_input("Montant remboursé (€)", min_value=0.0, value=float(credit['mensualite']), step=10.0, key=f"remb_{idx}")
                        if st.form_submit_button("Enregistrer remboursement"):
                            try:
                                nouveau_restant = max(0, montant_rest - montant_remb_c)
                                supabase.table('credits').update({'montant_restant': nouveau_restant}).eq('id', credit['id']).execute()
                                st.cache_data.clear()
                                st.session_state.needs_refresh = True
                                st.success("✅ Remboursement enregistré")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erreur: {e}")
                
                with col_del:
                    if st.button("🗑️ Supprimer", key=f"del_credit_{idx}"):
                        try:
                            supabase.table('credits').delete().eq('id', credit['id']).execute()
                            st.cache_data.clear()
                            st.session_state.needs_refresh = True
                            st.rerun()
                        except:
                            st.error("❌ Erreur")
        else:
            st.info("Aucun crédit")

# ===== TAB 6: RÉGLAGES =====
with tabs[5]:
    page_header("Réglages", "Configuration de l'application")
    
    reg_tabs = st.tabs(["🏷️ Catégories", "💳 Comptes", "⚡ Automatisation", "📊 Budgets"])
    
    with reg_tabs[0]:
        st.markdown("### 🏷️ Gérer les catégories")
        
        with st.form("new_cat_form"):
            col1, col2, col3 = st.columns([2, 3, 1])
            type_cat = col1.selectbox("Type", TYPES)
            nom_cat = col2.text_input("Nom catégorie")
            
            if col3.form_submit_button("➕ Ajouter", use_container_width=True):
                if nom_cat:
                    try:
                        supabase.table('categories').insert({'type': type_cat, 'categorie': nom_cat}).execute()
                        st.cache_data.clear()
                        st.session_state.needs_refresh = True
                        st.success(f"✅ Catégorie '{nom_cat}' ajoutée")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erreur: {e}")
        
        st.write("")
        
        col_dep, col_rev = st.columns(2)
        
        with col_dep:
            st.markdown("**💸 Dépenses**")
            for c in categories.get('Dépense', []):
                st.markdown(f"• {c}")
        
        with col_rev:
            st.markdown("**💰 Revenus**")
            for c in categories.get('Revenu', []):
                st.markdown(f"• {c}")
    
    with reg_tabs[1]:
        st.markdown("### 💳 Gérer les comptes")
        
        with st.form("new_compte_form"):
            col1, col2, col3 = st.columns(3)
            nom_cpt = col1.text_input("Nom du compte")
            type_cpt = col2.selectbox("Type", TYPES_COMPTE)
            commun_cpt = col3.checkbox("Compte commun")
            
            if st.form_submit_button("✅ Créer", use_container_width=True):
                if nom_cpt:
                    prop = "Commun" if commun_cpt else user_actuel
                    
                    try:
                        supabase.table('comptes').insert({'proprietaire': prop, 'compte': nom_cpt, 'type': type_cpt}).execute()
                        st.cache_data.clear()
                        st.session_state.needs_refresh = True
                        st.success(f"✅ Compte '{nom_cpt}' créé")
                        st.rerun()
                    except Exception as e:
                        if '23505' in str(e) or 'duplicate' in str(e):
                            st.error("❌ Ce compte existe déjà")
                        else:
                            st.error(f"❌ Erreur: {e}")
        
        st.write("")
        
        if not df_comptes.empty:
            for _, compte in df_comptes.iterrows():
                col_info, col_del = st.columns([4, 1])
                
                with col_info:
                    icon = "💰" if compte['type'] == 'Épargne' else "💳"
                    st.markdown(f"{icon} **{compte['compte']}** • {compte['type']} • {compte['proprietaire']}")
                
                with col_del:
                    if st.button("🗑️", key=f"del_cpt_{compte['id']}", use_container_width=True):
                        try:
                            supabase.table('comptes').delete().eq('id', compte['id']).execute()
                            st.cache_data.clear()
                            st.session_state.needs_refresh = True
                            st.rerun()
                        except:
                            st.error("❌ Compte utilisé")
    
    with reg_tabs[2]:
        st.markdown("### ⚡ Règles d'automatisation")
        
        with st.form("new_rule_form"):
            col1, col2 = st.columns(2)
            mc = col1.text_input("Si le titre contient", placeholder="Ex: Uber, Netflix...")
            cat_mc = col2.selectbox("Appliquer la catégorie", [c for l in categories.values() for c in l])
            
            col3, col4 = st.columns(2)
            type_mc = col3.selectbox("Type", TYPES, key="type_mc")
            compte_mc = col4.selectbox("Compte par défaut", tous_comptes + [""])
            
            if st.form_submit_button("✅ Créer la règle", use_container_width=True):
                if mc:
                    try:
                        supabase.table('mots_cles').insert({
                            'mot_cle': mc.lower(),
                            'categorie': cat_mc,
                            'type': type_mc,
                            'compte': compte_mc
                        }).execute()
                        st.cache_data.clear()
                        st.session_state.needs_refresh = True
                        st.success(f"✅ Règle créée pour '{mc}'")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erreur: {e}")
        
        st.write("")
        
        if not df_mots_cles.empty:
            st.markdown(f"**📋 {len(df_mots_cles)} règle(s) active(s)**")
            
            for _, mc in df_mots_cles.iterrows():
                col_info, col_del = st.columns([5, 1])
                
                with col_info:
                    st.markdown(f"**\"{mc['mot_cle']}\"** → {mc['categorie']} • {mc['type']}")
                
                with col_del:
                    if st.button("🗑️", key=f"del_mc_{mc['id']}", use_container_width=True):
                        try:
                            supabase.table('mots_cles').delete().eq('id', mc['id']).execute()
                            st.cache_data.clear()
                            st.session_state.needs_refresh = True
                            st.rerun()
                        except:
                            st.error("❌ Erreur")
        else:
            st.info("Aucune règle configurée")
    
    with reg_tabs[3]:
        st.markdown("### 📊 Mes Budgets")
        
        if st.button("➕ Nouveau Budget", use_container_width=True):
            st.session_state['new_budget'] = not st.session_state.get('new_budget', False)
        
        if st.session_state.get('new_budget', False):
            with st.form("new_budget_form"):
                col1, col2, col3 = st.columns(3)
                scope_b = col1.selectbox("Scope", ["Perso", "Commun"])
                cat_b = col2.selectbox("Catégorie", categories.get('Dépense', []))
                montant_b = col3.number_input("Montant Max (€)", min_value=0.0, step=10.0)
                
                col_btn1, col_btn2 = st.columns(2)
                
                if col_btn1.form_submit_button("✅ Créer", use_container_width=True):
                    if montant_b > 0:
                        try:
                            supabase.table('objectifs').insert({
                                'scope': scope_b,
                                'categorie': cat_b,
                                'montant': float(montant_b)
                            }).execute()
                            st.cache_data.clear()
                            st.session_state.needs_refresh = True
                            st.session_state['new_budget'] = False
                            st.success("✅ Budget créé")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erreur: {e}")
                
                if col_btn2.form_submit_button("❌ Annuler", use_container_width=True):
                    st.session_state['new_budget'] = False
                    st.rerun()
        
        st.write("")
        
        if objectifs_list:
            for obj in objectifs_list:
                cat = obj.get('categorie', '')
                budget_max = float(obj.get('montant', 0))
                
                if obj.get('scope') == 'Perso':
                    dep = df_mois[(df_mois['categorie'] == cat) & (df_mois['qui_connecte'] == user_actuel) & (df_mois['imputation'] == 'Perso')]['montant'].sum() if not df_mois.empty and 'categorie' in df_mois.columns else 0
                else:
                    dep = df_mois[(df_mois['categorie'] == cat) & (df_mois['imputation'].str.contains('Commun', na=False))]['montant'].sum() if not df_mois.empty and 'categorie' in df_mois.columns else 0
                
                pct = (dep / budget_max * 100) if budget_max > 0 else 0
                restant = budget_max - dep
                
                if pct >= 100:
                    color = "#EF4444"
                elif pct >= 80:
                    color = "#F59E0B"
                else:
                    color = "#10B981"
                
                st.markdown(f"""
                <div style='background: white; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem;'>
                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;'>
                        <h4 style='margin: 0; font-size: 16px;'>{cat}</h4>
                        <div style='background: {color}; color: white; padding: 0.25rem 0.75rem; border-radius: 6px; font-size: 12px; font-weight: 700;'>{pct:.0f}%</div>
                    </div>
                    <div style='background: #F3F4F6; height: 12px; border-radius: 6px; overflow: hidden; margin-bottom: 1rem;'>
                        <div style='background: {color}; height: 100%; width: {min(pct, 100)}%;'></div>
                    </div>
                    <div style='display: flex; justify-content: space-between; font-size: 13px;'>
                        <span>Dépensé: <strong style='color: {color};'>{fmt(dep)} €</strong></span>
                        <span>Budget: <strong>{fmt(budget_max)} €</strong></span>
                    </div>
                    <div style='margin-top: 0.5rem; font-size: 12px; color: {color}; font-weight: 600;'>
                        {'Dépassé de ' + fmt(abs(restant)) + ' €' if restant < 0 else 'Reste ' + fmt(restant) + ' €'}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("🗑️ Supprimer", key=f"del_obj_{obj.get('id')}", use_container_width=True):
                    try:
                        supabase.table('objectifs').delete().eq('id', obj['id']).execute()
                        st.cache_data.clear()
                        st.session_state.needs_refresh = True
                        st.rerun()
                    except:
                        st.error("❌ Erreur")
        else:
            st.info("Aucun budget défini")
