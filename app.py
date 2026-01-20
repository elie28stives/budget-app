# ============================================================================
# APPLICATION BUDGET - VERSION SUPABASE
# Performance : 10x plus rapide que Google Sheets
# ============================================================================

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client
import plotly.graph_objects as go
import io

# ============================================================================
# 1. CONFIGURATION
# ============================================================================

st.set_page_config(page_title="Ma Banque", layout="wide", page_icon="🏦")

USERS = ["Pierre", "Elie"]
TYPES = ["Dépense", "Revenu", "Épargne", "Virement Interne", "Investissement"]
TYPES_COMPTE = ["Courant", "Épargne"]
MOIS_FR = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

# ============================================================================
# 2. CONNEXION SUPABASE
# ============================================================================

@st.cache_resource
def get_supabase_client() -> Client:
    """Connexion à Supabase avec cache"""
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"❌ Erreur connexion Supabase: {e}")
        st.info("💡 Vérifiez vos secrets Streamlit (Settings → Secrets)")
        st.stop()

supabase = get_supabase_client()

# ============================================================================
# 3. FONCTIONS BASE DE DONNÉES
# ============================================================================

@st.cache_data(ttl=60, show_spinner=False)
def load_transactions() -> pd.DataFrame:
    """Charge toutes les transactions - ULTRA RAPIDE"""
    try:
        response = supabase.table('transactions').select('*').order('date', desc=True).execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date']).dt.date
            df['montant'] = pd.to_numeric(df['montant'], errors='coerce').fillna(0)
        return df
    except Exception as e:
        return pd.DataFrame(columns=['date', 'mois', 'annee', 'type', 'categorie', 'titre', 'montant', 'compte_source', 'compte_cible', 'imputation', 'qui_connecte'])

@st.cache_data(ttl=60, show_spinner=False)
def load_patrimoine() -> pd.DataFrame:
    """Charge le patrimoine"""
    try:
        response = supabase.table('patrimoine').select('*').order('date', desc=True).execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date']).dt.date
            df['montant'] = pd.to_numeric(df['montant'], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame(columns=['date', 'mois', 'annee', 'compte', 'montant', 'proprietaire'])

@st.cache_data(ttl=300, show_spinner=False)
def load_comptes() -> pd.DataFrame:
    """Charge les comptes"""
    try:
        response = supabase.table('comptes').select('*').execute()
        return pd.DataFrame(response.data)
    except:
        return pd.DataFrame(columns=['proprietaire', 'compte', 'type'])

@st.cache_data(ttl=300, show_spinner=False)
def load_categories() -> pd.DataFrame:
    """Charge les catégories"""
    try:
        response = supabase.table('categories').select('*').execute()
        return pd.DataFrame(response.data)
    except:
        return pd.DataFrame(columns=['type', 'categorie'])

@st.cache_data(ttl=300, show_spinner=False)
def load_projets() -> pd.DataFrame:
    """Charge les projets"""
    try:
        response = supabase.table('projets').select('*').execute()
        return pd.DataFrame(response.data)
    except:
        return pd.DataFrame(columns=['projet', 'cible', 'date_fin', 'proprietaire'])

def save_transaction(data: dict):
    """Sauvegarde une transaction"""
    try:
        if 'date' in data:
            data['date'] = str(data['date'])
        supabase.table('transactions').insert(data).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erreur: {e}")
        return False

def save_patrimoine(data: dict):
    """Sauvegarde patrimoine"""
    try:
        if 'date' in data:
            data['date'] = str(data['date'])
        supabase.table('patrimoine').insert(data).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erreur: {e}")
        return False

def save_compte(data: dict):
    """Sauvegarde un compte"""
    try:
        supabase.table('comptes').insert(data).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erreur: {e}")
        return False

def save_projet(data: dict):
    """Sauvegarde un projet"""
    try:
        if 'date_fin' in data and data['date_fin']:
            data['date_fin'] = str(data['date_fin'])
        supabase.table('projets').insert(data).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erreur: {e}")
        return False

def delete_transaction(transaction_id: int):
    """Supprime une transaction"""
    try:
        supabase.table('transactions').delete().eq('id', transaction_id).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erreur: {e}")
        return False

def delete_compte(compte_id: int):
    """Supprime un compte"""
    try:
        supabase.table('comptes').delete().eq('id', compte_id).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erreur: {e}")
        return False

def delete_projet(projet_id: int):
    """Supprime un projet"""
    try:
        supabase.table('projets').delete().eq('id', projet_id).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erreur: {e}")
        return False

# ============================================================================
# 4. FONCTIONS MÉTIER
# ============================================================================

def calc_soldes(df_transactions, df_patrimoine, comptes):
    """Calcule les soldes de tous les comptes - OPTIMISÉ"""
    soldes = {}
    for compte in comptes:
        # Dernier ajustement
        df_c = df_patrimoine[df_patrimoine['compte'] == compte]
        if not df_c.empty:
            last_adj = df_c.sort_values('date', ascending=False).iloc[0]
            solde_base = float(last_adj['montant'])
            date_base = last_adj['date']
        else:
            solde_base = 0.0
            date_base = pd.to_datetime('2000-01-01').date()
        
        # Transactions après
        df_after = df_transactions[df_transactions['date'] > date_base]
        
        # Débits
        debits = df_after[
            (df_after['compte_source'] == compte) & 
            (df_after['type'].isin(['Dépense', 'Investissement', 'Virement Interne', 'Épargne']))
        ]['montant'].sum()
        
        # Crédits  
        credits_revenu = df_after[(df_after['compte_source'] == compte) & (df_after['type'] == 'Revenu')]['montant'].sum()
        credits_virement = df_after[(df_after['compte_cible'] == compte) & (df_after['type'].isin(['Virement Interne', 'Épargne']))]['montant'].sum()
        
        soldes[compte] = solde_base + credits_revenu + credits_virement - debits
    
    return soldes

def fmt(montant, decimales=0):
    """Formate un montant en français"""
    if montant is None or pd.isna(montant):
        return "0"
    try:
        m = float(montant)
        if decimales == 0:
            formatted = f"{m:,.0f}"
        else:
            formatted = f"{m:,.{decimales}f}"
        formatted = formatted.replace(',', 'TEMP').replace('.', ',').replace('TEMP', ' ')
        return formatted
    except:
        return "0"

def page_header(titre, soustitre=""):
    """Header de page stylé"""
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 12px; margin-bottom: 2rem; color: white;">
        <h1 style="margin: 0; font-size: 32px; font-weight: 700;">{titre}</h1>
        {f'<p style="margin: 0.5rem 0 0 0; opacity: 0.9; font-size: 16px;">{soustitre}</p>' if soustitre else ''}
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# 5. CHARGEMENT DONNÉES
# ============================================================================

# Init session state
if 'needs_refresh' not in st.session_state:
    st.session_state.needs_refresh = True

# Charger les données
if st.session_state.needs_refresh:
    with st.spinner('⚡ Chargement ultra-rapide...'):
        df = load_transactions()
        df_patrimoine = load_patrimoine()
        df_comptes = load_comptes()
        df_categories = load_categories()
        df_projets = load_projets()
        
        st.session_state.df = df
        st.session_state.df_patrimoine = df_patrimoine
        st.session_state.df_comptes = df_comptes
        st.session_state.df_categories = df_categories
        st.session_state.df_projets = df_projets
        st.session_state.needs_refresh = False
else:
    df = st.session_state.df
    df_patrimoine = st.session_state.df_patrimoine
    df_comptes = st.session_state.df_comptes
    df_categories = st.session_state.df_categories
    df_projets = st.session_state.df_projets

# Préparer structures
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

# Catégories par défaut si vide
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

# ============================================================================
# 6. SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown("# 👤 Utilisateur")
    user_actuel = st.selectbox("", USERS, label_visibility="collapsed")
    
    st.markdown("---")
    
    # Sélection mois/année
    st.markdown("### 📅 Période")
    mois_actuel = datetime.now().month
    annee_actuelle = datetime.now().year
    
    m_nom = st.selectbox("Mois", MOIS_FR, index=mois_actuel-1, label_visibility="collapsed")
    m_sel = MOIS_FR.index(m_nom) + 1
    a_sel = st.number_input("Année", value=annee_actuelle, label_visibility="collapsed")
    
    # Filtrer données du mois
    df_mois = df[(df['mois'] == m_sel) & (df['annee'] == a_sel)]
    df_mois_user = df_mois[df_mois['qui_connecte'] == user_actuel]
    
    st.markdown("---")
    
    # Comptes
    tous_comptes = comptes_structure.get(user_actuel, [])
    soldes = calc_soldes(df, df_patrimoine, tous_comptes)
    
    # Séparer courants et épargne
    comptes_courants = [c for c in tous_comptes if comptes_types.get(c) == 'Courant']
    comptes_epargne = [c for c in tous_comptes if comptes_types.get(c) == 'Épargne']
    
    total_courant = sum(soldes.get(c, 0) for c in comptes_courants)
    total_epargne = sum(soldes.get(c, 0) for c in comptes_epargne)
    
    st.markdown(f"""
    <div style='background: white; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;'>
        <div style='color: #6B7280; font-size: 11px; font-weight: 600; text-transform: uppercase;'>💳 Comptes Courants</div>
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
        <div style='color: #6B7280; font-size: 11px; font-weight: 600; text-transform: uppercase;'>💰 Épargne</div>
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
# 7. TABS PRINCIPALES
# ============================================================================

tabs = st.tabs(["🏠 Accueil", "💰 Opérations", "📊 Analyses", "💎 Patrimoine", "⚙️ Réglages"])

# ============================================================================
# TAB 1 : ACCUEIL
# ============================================================================

with tabs[0]:
    page_header(f"Synthèse - {m_nom} {a_sel}", f"Compte de {user_actuel}")
    
    # Métriques du mois
    rev = df_mois_user[df_mois_user['type'] == 'Revenu']['montant'].sum()
    dep = df_mois_user[(df_mois_user['type'] == 'Dépense') & (df_mois_user['imputation'] == 'Perso')]['montant'].sum()
    epg = df_mois_user[df_mois_user['type'] == 'Épargne']['montant'].sum()
    com = df_mois[df_mois['imputation'] == 'Commun (50/50)']['montant'].sum() / 2
    
    fixe = 0  # TODO: abonnements
    rav = rev - fixe - dep - com
    
    # Affichage métriques
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div style='background: white; padding: 1.5rem; border-radius: 12px; text-align: center;'>
            <div style='color: #6B7280; font-size: 12px; font-weight: 600;'>Revenus</div>
            <div style='color: #10B981; font-size: 28px; font-weight: 700;'>{fmt(rev)} €</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style='background: white; padding: 1.5rem; border-radius: 12px; text-align: center;'>
            <div style='color: #6B7280; font-size: 12px; font-weight: 600;'>Fixe</div>
            <div style='color: #F59E0B; font-size: 28px; font-weight: 700;'>{fmt(fixe)} €</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style='background: white; padding: 1.5rem; border-radius: 12px; text-align: center;'>
            <div style='color: #6B7280; font-size: 12px; font-weight: 600;'>Dépenses</div>
            <div style='color: #EF4444; font-size: 28px; font-weight: 700;'>{fmt(dep+com)} €</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        pct_epargne = (epg / rev * 100) if rev > 0 else 0
        st.markdown(f"""
        <div style='background: white; padding: 1.5rem; border-radius: 12px; text-align: center;'>
            <div style='color: #6B7280; font-size: 12px; font-weight: 600;'>Épargne</div>
            <div style='color: #4F46E5; font-size: 28px; font-weight: 700;'>{fmt(epg)} €</div>
            <div style='color: #9CA3AF; font-size: 11px;'>{pct_epargne:.1f}% du revenu</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        color_rav = "#10B981" if rav >= 0 else "#EF4444"
        icon_rav = "✓" if rav >= 0 else "⚠"
        st.markdown(f"""
        <div style='background: white; padding: 1.5rem; border-radius: 12px; text-align: center;'>
            <div style='color: #6B7280; font-size: 12px; font-weight: 600;'>{icon_rav} Reste à Vivre</div>
            <div style='color: {color_rav}; font-size: 28px; font-weight: 700;'>{fmt(rav)} €</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Graphique dépenses
    if not df_mois_user.empty:
        df_dep = df_mois_user[df_mois_user['type'] == 'Dépense']
        if not df_dep.empty:
            dep_par_cat = df_dep.groupby('categorie')['montant'].sum().sort_values(ascending=False)
            
            fig = go.Figure(data=[go.Bar(
                x=dep_par_cat.values,
                y=dep_par_cat.index,
                orientation='h',
                marker_color='#667eea'
            )])
            fig.update_layout(
                title="Dépenses par catégorie",
                xaxis_title="Montant (€)",
                height=400,
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# TAB 2 : OPÉRATIONS
# ============================================================================

with tabs[1]:
    page_header("Opérations", "Gérez vos transactions")
    
    # Formulaire nouvelle transaction
    with st.expander("➕ Nouvelle transaction", expanded=False):
        with st.form("new_trans"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                date_trans = st.date_input("Date", datetime.today())
                type_trans = st.selectbox("Type", TYPES)
            
            with col2:
                categorie_trans = st.selectbox("Catégorie", categories.get(type_trans, []))
                montant_trans = st.number_input("Montant (€)", min_value=0.01, step=0.01)
            
            with col3:
                titre_trans = st.text_input("Titre")
                compte_source = st.selectbox("Compte", tous_comptes)
            
            imputation = st.selectbox("Imputation", ["Perso", "Commun (50/50)"])
            
            if st.form_submit_button("💾 Enregistrer", use_container_width=True):
                transaction = {
                    'date': str(date_trans),
                    'mois': date_trans.month,
                    'annee': date_trans.year,
                    'type': type_trans,
                    'categorie': categorie_trans,
                    'titre': titre_trans,
                    'montant': float(montant_trans),
                    'compte_source': compte_source,
                    'compte_cible': None,
                    'imputation': imputation,
                    'qui_connecte': user_actuel
                }
                
                if save_transaction(transaction):
                    st.toast("✅ Transaction enregistrée", icon="✅")
                    st.rerun()
    
    # Liste des transactions
    st.markdown("### 📋 Dernières transactions")
    
    if not df_mois.empty:
        df_affichage = df_mois.sort_values('date', ascending=False).head(20)
        
        for _, row in df_affichage.iterrows():
            col1, col2, col3, col4 = st.columns([2, 3, 2, 1])
            
            with col1:
                st.markdown(f"**{row['date']}**")
            
            with col2:
                st.markdown(f"{row['titre']} • {row['categorie']}")
            
            with col3:
                color = "#EF4444" if row['type'] == 'Dépense' else "#10B981"
                st.markdown(f"<span style='color: {color}; font-weight: 600;'>{fmt(row['montant'], 2)} €</span>", unsafe_allow_html=True)
            
            with col4:
                if st.button("🗑️", key=f"del_{row['id']}"):
                    if delete_transaction(row['id']):
                        st.rerun()
            
            st.markdown("---")
    else:
        st.info("Aucune transaction ce mois-ci")

# ============================================================================
# TAB 3 : ANALYSES
# ============================================================================

with tabs[2]:
    page_header("Analyses", "Visualisez vos finances")
    
    st.info("📊 Graphiques et analyses à venir...")

# ============================================================================
# TAB 4 : PATRIMOINE
# ============================================================================

with tabs[3]:
    page_header("Patrimoine", "Gérez vos comptes et projets")
    
    # Sélection compte
    compte_selectionne = st.selectbox("💳 Sélectionner un compte", tous_comptes)
    
    if compte_selectionne:
        solde = soldes.get(compte_selectionne, 0)
        
        st.markdown(f"""
        <div style='background: #F0FDF4; border: 2px solid #10B981; border-radius: 12px; padding: 2rem; text-align: center; margin: 2rem 0;'>
            <div style='color: #6B7280; font-size: 14px; font-weight: 600;'>Solde actuel</div>
            <div style='color: #1F2937; font-size: 12px; margin-top: 0.25rem;'>{compte_selectionne}</div>
            <div style='color: #10B981; font-size: 48px; font-weight: 700; margin-top: 1rem;'>{fmt(solde, 2)} €</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Ajustement de solde
        with st.expander("⚙️ Ajuster le solde", expanded=False):
            with st.form("adj_solde"):
                col1, col2 = st.columns(2)
                with col1:
                    date_adj = st.date_input("Date", datetime.today())
                with col2:
                    montant_adj_text = st.text_input("Solde réel (€)", placeholder="Ex: 7500,45")
                
                if st.form_submit_button("💾 Enregistrer"):
                    try:
                        # Nettoyer le montant
                        montant_clean = montant_adj_text.replace(' ', '').replace(',', '.')
                        montant_adj = float(montant_clean)
                        
                        data = {
                            'date': str(date_adj),
                            'mois': date_adj.month,
                            'annee': date_adj.year,
                            'compte': compte_selectionne,
                            'montant': montant_adj,
                            'proprietaire': user_actuel
                        }
                        
                        if save_patrimoine(data):
                            st.toast("✅ Solde ajusté", icon="✅")
                            st.rerun()
                    except ValueError:
                        st.error("Format invalide. Utilisez: 7500,45 ou 7500.45")

# ============================================================================
# TAB 5 : RÉGLAGES
# ============================================================================

with tabs[4]:
    page_header("Réglages", "Configuration de l'application")
    
    sub_tabs = st.tabs(["💳 Comptes", "🎯 Projets"])
    
    # Gestion comptes
    with sub_tabs[0]:
        st.markdown("### Gérer les comptes")
        
        with st.expander("➕ Créer un compte", expanded=False):
            with st.form("new_compte"):
                nom_compte = st.text_input("Nom du compte")
                type_compte = st.selectbox("Type", TYPES_COMPTE)
                proprio = st.selectbox("Propriétaire", USERS)
                
                if st.form_submit_button("Créer"):
                    data = {
                        'proprietaire': proprio,
                        'compte': nom_compte,
                        'type': type_compte
                    }
                    if save_compte(data):
                        st.toast("✅ Compte créé", icon="✅")
                        st.rerun()
        
        # Liste des comptes
        if not df_comptes.empty:
            for _, compte in df_comptes.iterrows():
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"**{compte['compte']}**")
                with col2:
                    st.markdown(f"{compte['type']} • {compte['proprietaire']}")
                with col3:
                    if st.button("🗑️", key=f"del_c_{compte['id']}"):
                        if delete_compte(compte['id']):
                            st.rerun()
                st.markdown("---")
    
    # Gestion projets
    with sub_tabs[1]:
        st.markdown("### Projets d'épargne")
        
        with st.expander("➕ Créer un projet", expanded=False):
            with st.form("new_projet"):
                nom_projet = st.text_input("Nom du projet")
                cible_projet = st.number_input("Cible (€)", min_value=1.0, step=100.0)
                date_fin_projet = st.date_input("Date fin (optionnel)")
                proprio_projet = st.selectbox("Pour", ["Commun"] + USERS)
                
                if st.form_submit_button("Créer"):
                    data = {
                        'projet': nom_projet,
                        'cible': float(cible_projet),
                        'date_fin': str(date_fin_projet) if date_fin_projet else None,
                        'proprietaire': proprio_projet
                    }
                    if save_projet(data):
                        st.toast("✅ Projet créé", icon="✅")
                        st.rerun()
        
        # Liste des projets
        if not df_projets.empty:
            for _, projet in df_projets.iterrows():
                # Calculer progression
                df_epargne_projet = df[df['categorie'] == projet['projet']]
                montant_actuel = df_epargne_projet['montant'].sum()
                cible = float(projet['cible'])
                progression = (montant_actuel / cible * 100) if cible > 0 else 0
                
                st.markdown(f"""
                <div style='background: white; padding: 1.5rem; border-radius: 12px; margin-bottom: 1rem;'>
                    <div style='font-size: 18px; font-weight: 700; margin-bottom: 0.5rem;'>{projet['projet']}</div>
                    <div style='background: #E5E7EB; border-radius: 8px; height: 20px; margin-bottom: 0.5rem;'>
                        <div style='background: linear-gradient(90deg, #667eea, #764ba2); border-radius: 8px; height: 20px; width: {min(progression, 100)}%;'></div>
                    </div>
                    <div style='font-size: 14px; color: #6B7280;'>{fmt(montant_actuel)} € / {fmt(cible)} € ({progression:.0f}%)</div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("🗑️", key=f"del_p_{projet['id']}"):
                    if delete_projet(projet['id']):
                        st.rerun()

# ============================================================================
# FIN
# ============================================================================
