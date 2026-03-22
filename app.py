"""
💰 BUDGET COUPLE V2 - Application de gestion financière
======================================================
Refonte complète avec :
- Design moderne et responsive
- Calculs temps réel des soldes
- Assistant intelligent (notifications)
- Export PDF/Excel
- Détection des anomalies
- Gestion % personnalisés pour dépenses communes
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import time
from io import BytesIO
import json

# ==============================================================================
# 1. CONFIGURATION & CONSTANTES
# ==============================================================================
APP_NAME = "Budget Couple V2"
APP_VERSION = "2.0.0"

USERS = ["Pierre", "Elie"]
TYPES = ["Dépense", "Revenu", "Virement Interne", "Épargne", "Investissement"]
IMPUTATIONS = ["Perso", "Commun (50/50)", "Commun (Autre %)", "Avance/Cadeau"]
TYPES_COMPTE = ["Courant", "Épargne"]
MOIS_FR = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
]

# Seuils pour les alertes
SEUIL_DOUBLON_JOURS = 3
SEUIL_DEPENSE_ANORMALE = 1.5  # 150% de la moyenne

# Couleurs du thème
COLORS = {
    "primary": "#6366F1",      # Indigo
    "success": "#10B981",      # Emerald
    "danger": "#EF4444",       # Red
    "warning": "#F59E0B",      # Amber
    "info": "#3B82F6",         # Blue
    "dark": "#1F2937",         # Gray 800
    "light": "#F9FAFB",        # Gray 50
    "muted": "#6B7280",        # Gray 500
}

# ==============================================================================
# 2. CSS MODERNE
# ==============================================================================
def apply_modern_style():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* === BASE === */
        .stApp {
            background: linear-gradient(135deg, #F8FAFC 0%, #EEF2FF 100%);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        .block-container {
            padding: 1.5rem 2rem !important;
            max-width: 1600px;
        }
        
        /* === TYPOGRAPHY === */
        h1, h2, h3, h4, h5, h6 {
            font-weight: 600 !important;
            color: #1F2937 !important;
        }
        
        /* === CARDS === */
        .card {
            background: white;
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06);
            border: 1px solid #E5E7EB;
            transition: all 0.2s ease;
        }
        
        .card:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }
        
        .card-header {
            font-size: 14px;
            font-weight: 500;
            color: #6B7280;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .card-value {
            font-size: 28px;
            font-weight: 700;
            color: #1F2937;
        }
        
        .card-value.positive { color: #10B981; }
        .card-value.negative { color: #EF4444; }
        .card-value.neutral { color: #6366F1; }
        
        /* === METRICS GRID === */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        
        /* === NOTIFICATION CARDS === */
        .notif {
            padding: 12px 16px;
            border-radius: 12px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .notif-warning {
            background: linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%);
            border-left: 4px solid #F59E0B;
        }
        
        .notif-danger {
            background: linear-gradient(135deg, #FEE2E2 0%, #FECACA 100%);
            border-left: 4px solid #EF4444;
        }
        
        .notif-info {
            background: linear-gradient(135deg, #DBEAFE 0%, #BFDBFE 100%);
            border-left: 4px solid #3B82F6;
        }
        
        .notif-success {
            background: linear-gradient(135deg, #D1FAE5 0%, #A7F3D0 100%);
            border-left: 4px solid #10B981;
        }
        
        /* === SIDEBAR === */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1F2937 0%, #111827 100%);
        }
        
        section[data-testid="stSidebar"] .stSelectbox label,
        section[data-testid="stSidebar"] .stNumberInput label,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span {
            color: #E5E7EB !important;
        }
        
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: white !important;
        }
        
        /* === BUTTONS === */
        .stButton > button {
            border-radius: 10px;
            font-weight: 600;
            padding: 8px 20px;
            transition: all 0.2s ease;
        }
        
        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        }
        
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%);
        }
        
        /* === TABS === */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background: white;
            padding: 8px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            font-weight: 500;
            padding: 10px 20px;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%) !important;
            color: white !important;
        }
        
        /* === DATA ELEMENTS === */
        div[data-testid="stMetric"] {
            background: white;
            padding: 16px 20px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }
        
        div[data-testid="stExpander"] {
            background: white;
            border-radius: 12px;
            border: 1px solid #E5E7EB;
        }
        
        /* === FORMS === */
        .stTextInput > div > div,
        .stNumberInput > div > div,
        .stSelectbox > div > div,
        .stDateInput > div > div {
            border-radius: 10px !important;
        }
        
        /* === PROGRESS BARS === */
        .stProgress > div > div > div {
            border-radius: 10px;
            background: linear-gradient(90deg, #6366F1, #8B5CF6);
        }
        
        /* === TRANSACTION LIST === */
        .transaction-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 14px 16px;
            background: white;
            border-radius: 12px;
            margin-bottom: 8px;
            border: 1px solid #E5E7EB;
            transition: all 0.2s ease;
        }
        
        .transaction-item:hover {
            border-color: #6366F1;
            box-shadow: 0 2px 8px rgba(99, 102, 241, 0.15);
        }
        
        .transaction-left {
            display: flex;
            align-items: center;
            gap: 14px;
        }
        
        .transaction-icon {
            width: 42px;
            height: 42px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }
        
        .transaction-icon.expense { background: #FEE2E2; }
        .transaction-icon.income { background: #D1FAE5; }
        .transaction-icon.saving { background: #DBEAFE; }
        .transaction-icon.transfer { background: #F3E8FF; }
        
        .transaction-title {
            font-weight: 600;
            color: #1F2937;
        }
        
        .transaction-category {
            font-size: 13px;
            color: #6B7280;
        }
        
        .transaction-amount {
            font-weight: 700;
            font-size: 16px;
        }
        
        .transaction-amount.negative { color: #EF4444; }
        .transaction-amount.positive { color: #10B981; }
        
        /* === ACCOUNT CARDS (Sidebar) === */
        .account-card {
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 12px 14px;
            margin-bottom: 8px;
            border-left: 3px solid;
        }
        
        .account-card.current { border-left-color: #10B981; }
        .account-card.savings { border-left-color: #6366F1; }
        .account-card.negative { border-left-color: #EF4444; }
        
        .account-name {
            font-size: 13px;
            color: #D1D5DB;
            margin-bottom: 4px;
        }
        
        .account-balance {
            font-size: 18px;
            font-weight: 600;
            color: white;
        }
        
        /* === BADGES === */
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .badge-success { background: #D1FAE5; color: #065F46; }
        .badge-danger { background: #FEE2E2; color: #991B1B; }
        .badge-warning { background: #FEF3C7; color: #92400E; }
        .badge-info { background: #DBEAFE; color: #1E40AF; }
        .badge-purple { background: #F3E8FF; color: #6B21A8; }
        
        /* === HIDE STREAMLIT BRANDING === */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)


# ==============================================================================
# 3. BACKEND SUPABASE
# ==============================================================================
@st.cache_resource
def get_db() -> Client:
    """Connexion Supabase (singleton)"""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"❌ Erreur connexion Supabase: {e}")
        return None


def clean_amount(val) -> float:
    """Convertit n'importe quel format de montant en float"""
    if pd.isna(val) or str(val).strip() == "":
        return 0.0
    s = str(val).replace(" ", "").replace("€", "").replace("\xa0", "").replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0


@st.cache_data(ttl=60, show_spinner=False)
def load_table(table_name: str) -> pd.DataFrame:
    """Charge une table Supabase avec nettoyage automatique"""
    supabase = get_db()
    if not supabase:
        return pd.DataFrame()
    
    try:
        response = supabase.table(table_name).select("*").execute()
        df = pd.DataFrame(response.data)
        
        if df.empty:
            return df
        
        # Nettoyage des types
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors='coerce').dt.date
        
        # Colonnes montants
        money_cols = ["Montant", "Cible", "Montant_Initial", "Montant_Restant", 
                      "Mensualite", "Budget", "Part_Perso"]
        for col in money_cols:
            if col in df.columns:
                df[col] = df[col].apply(clean_amount)
        
        # Colonnes numériques
        int_cols = ["Mois", "Annee", "Jour", "Pourcentage_Perso"]
        for col in int_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        return df
    except Exception as e:
        return pd.DataFrame()


def save_row(table_name: str, data: dict) -> bool:
    """Insère une nouvelle ligne"""
    supabase = get_db()
    if not supabase:
        return False
    
    try:
        clean_data = {}
        for k, v in data.items():
            if isinstance(v, (date, datetime)):
                clean_data[k] = str(v)
            elif isinstance(v, float):
                clean_data[k] = str(v)
            else:
                clean_data[k] = v
        
        supabase.table(table_name).insert(clean_data).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erreur sauvegarde: {e}")
        return False


def update_row(table_name: str, row_id: int, changes: dict) -> bool:
    """Met à jour une ligne existante"""
    supabase = get_db()
    if not supabase:
        return False
    
    try:
        clean_changes = {}
        for k, v in changes.items():
            if isinstance(v, (date, datetime)):
                clean_changes[k] = str(v)
            elif isinstance(v, float):
                clean_changes[k] = str(v)
            else:
                clean_changes[k] = v
        
        supabase.table(table_name).update(clean_changes).eq("id", row_id).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erreur modification: {e}")
        return False


def delete_row(table_name: str, row_id: int) -> bool:
    """Supprime une ligne"""
    supabase = get_db()
    if not supabase:
        return False
    
    try:
        supabase.table(table_name).delete().eq("id", row_id).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erreur suppression: {e}")
        return False


# ==============================================================================
# 4. CHARGEMENT DES DONNÉES
# ==============================================================================
class DataStore:
    """Classe centralisant toutes les données"""
    
    def __init__(self):
        self.transactions = load_table("Data")
        self.patrimoine = load_table("Patrimoine")
        self.config = load_table("Config")
        self.comptes = load_table("Comptes")
        self.objectifs = load_table("Objectifs")
        self.abonnements = load_table("Abonnements")
        self.projets = load_table("Projets_Config")
        self.mots_cles = load_table("Mots_Cles")
        self.remboursements = load_table("Remboursements")
        self.credits = load_table("Credits")
        
        # Pré-calculs
        self._build_categories()
        self._build_comptes()
    
    def _build_categories(self):
        """Construit le dictionnaire des catégories par type"""
        self.categories = {t: [] for t in TYPES}
        
        if not self.config.empty:
            for _, r in self.config.iterrows():
                t = r.get("Type")
                c = r.get("Categorie")
                if t in self.categories and c and c not in self.categories[t]:
                    self.categories[t].append(c)
        
        # Catégories par défaut
        if not self.categories["Dépense"]:
            self.categories["Dépense"] = ["Alimentation", "Transport", "Logement", "Loisirs", "Autre"]
        if not self.categories["Revenu"]:
            self.categories["Revenu"] = ["Salaire", "Prime", "Autre"]
    
    def _build_comptes(self):
        """Construit les listes de comptes"""
        self.comptes_par_proprio = {}  # {Proprio: [comptes]}
        self.type_compte = {}  # {compte: type}
        
        if not self.comptes.empty:
            for _, r in self.comptes.iterrows():
                proprio = r.get("Proprietaire", "Commun")
                compte = r.get("Compte")
                type_c = r.get("Type", "Courant")
                
                if proprio not in self.comptes_par_proprio:
                    self.comptes_par_proprio[proprio] = []
                if compte not in self.comptes_par_proprio[proprio]:
                    self.comptes_par_proprio[proprio].append(compte)
                
                self.type_compte[compte] = type_c
    
    def get_comptes_visibles(self, user: str) -> list:
        """Retourne les comptes accessibles par un utilisateur"""
        comptes = []
        comptes.extend(self.comptes_par_proprio.get(user, []))
        comptes.extend(self.comptes_par_proprio.get("Commun", []))
        return comptes if comptes else ["Principal"]
    
    def get_transactions_mois(self, mois: int, annee: int) -> pd.DataFrame:
        """Filtre les transactions pour un mois donné"""
        if self.transactions.empty:
            return pd.DataFrame()
        return self.transactions[
            (self.transactions["Mois"] == mois) & 
            (self.transactions["Annee"] == annee)
        ]


# ==============================================================================
# 5. CALCULS FINANCIERS
# ==============================================================================
class FinanceEngine:
    """Moteur de calculs financiers"""
    
    def __init__(self, data: DataStore, user: str):
        self.data = data
        self.user = user
    
    def calculer_solde_compte(self, compte: str) -> float:
        """
        Calcule le solde temps réel d'un compte :
        Dernier solde patrimoine + tous les mouvements depuis
        """
        solde = 0.0
        date_ref = date(2000, 1, 1)
        
        # 1. Trouver le dernier relevé patrimoine
        if not self.data.patrimoine.empty:
            releves = self.data.patrimoine[self.data.patrimoine["Compte"] == compte]
            if not releves.empty:
                releves = releves.sort_values("Date", ascending=False)
                dernier = releves.iloc[0]
                solde = dernier["Montant"]
                date_ref = dernier["Date"]
        
        # 2. Ajouter tous les mouvements depuis cette date
        if not self.data.transactions.empty:
            df = self.data.transactions[self.data.transactions["Date"] > date_ref]
            
            # Entrées sur ce compte
            entrees = df[
                (df["Compte_Cible"] == compte) | 
                ((df["Compte_Source"] == compte) & (df["Type"] == "Revenu"))
            ]
            
            # Sorties de ce compte
            sorties = df[
                (df["Compte_Source"] == compte) & 
                (df["Type"].isin(["Dépense", "Investissement", "Épargne", "Virement Interne"]))
            ]
            
            # Virements entrants
            virements_in = df[
                (df["Compte_Cible"] == compte) & 
                (df["Type"].isin(["Virement Interne", "Épargne"]))
            ]
            
            solde += entrees["Montant"].sum()
            solde -= sorties["Montant"].sum()
            solde += virements_in["Montant"].sum()
        
        return solde
    
    def calculer_reste_a_vivre(self, mois: int, annee: int) -> dict:
        """
        Calcule le reste à vivre pour un mois :
        RAV = Revenus - Dépenses Perso - Part Commune - Épargne
        """
        df = self.data.get_transactions_mois(mois, annee)
        user_df = df[df["Qui_Connecte"] == self.user]
        
        # Revenus
        revenus = user_df[user_df["Type"] == "Revenu"]["Montant"].sum()
        
        # Dépenses personnelles
        depenses_perso = user_df[
            (user_df["Type"] == "Dépense") & 
            (user_df["Imputation"] == "Perso")
        ]["Montant"].sum()
        
        # Part des dépenses communes
        part_commune = self._calculer_part_commune(df, mois, annee)
        
        # Épargne
        epargne = user_df[user_df["Type"] == "Épargne"]["Montant"].sum()
        
        # Investissements
        investissements = user_df[user_df["Type"] == "Investissement"]["Montant"].sum()
        
        rav = revenus - depenses_perso - part_commune - epargne - investissements
        
        return {
            "revenus": revenus,
            "depenses_perso": depenses_perso,
            "part_commune": part_commune,
            "epargne": epargne,
            "investissements": investissements,
            "reste_a_vivre": rav
        }
    
    def _calculer_part_commune(self, df: pd.DataFrame, mois: int, annee: int) -> float:
        """Calcule la part des dépenses communes pour l'utilisateur"""
        part = 0.0
        
        # 50/50
        communes_5050 = df[df["Imputation"] == "Commun (50/50)"]
        part += communes_5050["Montant"].sum() / 2
        
        # Pourcentages personnalisés
        communes_perso = df[df["Imputation"] == "Commun (Autre %)"]
        for _, r in communes_perso.iterrows():
            pct = r.get("Pourcentage_Perso", 50)
            if r.get("Paye_Par") == self.user:
                # J'ai payé, ma part est mon %
                part += r["Montant"] * pct / 100
            else:
                # L'autre a payé, ma part est (100 - son %)
                part += r["Montant"] * (100 - pct) / 100
        
        return part
    
    def calculer_budget_restant(self, categorie: str, mois: int, annee: int) -> dict:
        """Compare les dépenses réelles au budget défini"""
        df = self.data.get_transactions_mois(mois, annee)
        
        # Dépenses de la catégorie
        depenses = df[
            (df["Categorie"] == categorie) & 
            (df["Type"] == "Dépense")
        ]["Montant"].sum()
        
        # Budget défini
        budget = 0.0
        if not self.data.objectifs.empty:
            obj = self.data.objectifs[
                (self.data.objectifs["Categorie"] == categorie) &
                ((self.data.objectifs["Scope"] == "Perso") | 
                 (self.data.objectifs["Scope"] == self.user))
            ]
            if not obj.empty:
                budget = obj.iloc[0].get("Montant", 0)
        
        return {
            "budget": budget,
            "depense": depenses,
            "restant": budget - depenses,
            "pourcentage": (depenses / budget * 100) if budget > 0 else 0
        }


# ==============================================================================
# 6. ASSISTANT INTELLIGENT (NOTIFICATIONS)
# ==============================================================================
class SmartAssistant:
    """Détecte les anomalies et génère des alertes"""
    
    def __init__(self, data: DataStore, user: str, mois: int, annee: int):
        self.data = data
        self.user = user
        self.mois = mois
        self.annee = annee
        self.df_mois = data.get_transactions_mois(mois, annee)
        self.notifications = []
    
    def analyser(self) -> list:
        """Exécute toutes les analyses et retourne les notifications"""
        self._detecter_doublons()
        self._detecter_depenses_anormales()
        self._verifier_abonnements_manquants()
        self._verifier_depassements_budget()
        self._verifier_soldes_negatifs()
        return self.notifications
    
    def _detecter_doublons(self):
        """Détecte les transactions potentiellement en double"""
        if self.df_mois.empty:
            return
        
        df = self.df_mois[self.df_mois["Qui_Connecte"] == self.user].copy()
        if df.empty:
            return
        
        # Grouper par titre et montant
        for (titre, montant), group in df.groupby(["Titre", "Montant"]):
            if len(group) > 1:
                dates = group["Date"].tolist()
                # Vérifier si les dates sont proches
                for i, d1 in enumerate(dates):
                    for d2 in dates[i+1:]:
                        if d1 and d2:
                            delta = abs((d1 - d2).days) if isinstance(d1, date) and isinstance(d2, date) else 999
                            if delta <= SEUIL_DOUBLON_JOURS:
                                self.notifications.append({
                                    "type": "warning",
                                    "icon": "⚠️",
                                    "title": "Doublon potentiel",
                                    "message": f"\"{titre}\" ({montant:.2f}€) apparaît plusieurs fois à des dates proches"
                                })
                                return  # Une seule alerte par type de doublon
    
    def _detecter_depenses_anormales(self):
        """Détecte les dépenses anormalement élevées vs la moyenne"""
        if self.data.transactions.empty:
            return
        
        # Calculer la moyenne des 3 derniers mois par catégorie
        date_limite = date(self.annee, self.mois, 1) - relativedelta(months=3)
        
        df_historique = self.data.transactions[
            (self.data.transactions["Qui_Connecte"] == self.user) &
            (self.data.transactions["Type"] == "Dépense") &
            (self.data.transactions["Date"] >= date_limite)
        ]
        
        if df_historique.empty:
            return
        
        moyennes = df_historique.groupby("Categorie")["Montant"].mean()
        
        # Comparer avec ce mois
        df_actuel = self.df_mois[
            (self.df_mois["Qui_Connecte"] == self.user) &
            (self.df_mois["Type"] == "Dépense")
        ]
        
        for _, row in df_actuel.iterrows():
            cat = row["Categorie"]
            if cat in moyennes:
                moyenne = moyennes[cat]
                if row["Montant"] > moyenne * SEUIL_DEPENSE_ANORMALE and row["Montant"] > 50:
                    self.notifications.append({
                        "type": "info",
                        "icon": "📊",
                        "title": "Dépense inhabituelle",
                        "message": f"\"{row['Titre']}\" ({row['Montant']:.2f}€) est supérieur à votre moyenne en {cat} ({moyenne:.2f}€)"
                    })
    
    def _verifier_abonnements_manquants(self):
        """Vérifie si des abonnements n'ont pas été payés ce mois"""
        if self.data.abonnements.empty:
            return
        
        abos_user = self.data.abonnements[
            self.data.abonnements["Proprietaire"] == self.user
        ]
        
        for _, abo in abos_user.iterrows():
            nom = abo.get("Nom", "")
            montant = abo.get("Montant", 0)
            
            # Chercher si payé ce mois
            existe = not self.df_mois[
                (self.df_mois["Titre"].str.contains(nom, case=False, na=False)) |
                ((self.df_mois["Montant"] == montant) & 
                 (self.df_mois["Categorie"] == abo.get("Categorie", "")))
            ].empty
            
            if not existe:
                jour = abo.get("Jour", 1) or 1
                if datetime.now().day >= jour:
                    self.notifications.append({
                        "type": "warning",
                        "icon": "📅",
                        "title": "Abonnement non détecté",
                        "message": f"\"{nom}\" ({montant:.2f}€) n'a pas été trouvé ce mois"
                    })
    
    def _verifier_depassements_budget(self):
        """Vérifie les dépassements de budget"""
        if self.data.objectifs.empty:
            return
        
        engine = FinanceEngine(self.data, self.user)
        
        for _, obj in self.data.objectifs.iterrows():
            cat = obj.get("Categorie")
            if not cat:
                continue
            
            result = engine.calculer_budget_restant(cat, self.mois, self.annee)
            
            if result["budget"] > 0:
                if result["pourcentage"] >= 100:
                    self.notifications.append({
                        "type": "danger",
                        "icon": "🚨",
                        "title": "Budget dépassé",
                        "message": f"{cat}: {result['depense']:.0f}€ / {result['budget']:.0f}€ ({result['pourcentage']:.0f}%)"
                    })
                elif result["pourcentage"] >= 80:
                    self.notifications.append({
                        "type": "warning",
                        "icon": "⚡",
                        "title": "Budget bientôt atteint",
                        "message": f"{cat}: {result['depense']:.0f}€ / {result['budget']:.0f}€ ({result['pourcentage']:.0f}%)"
                    })
    
    def _verifier_soldes_negatifs(self):
        """Alerte si un compte est en négatif"""
        engine = FinanceEngine(self.data, self.user)
        
        for compte in self.data.get_comptes_visibles(self.user):
            solde = engine.calculer_solde_compte(compte)
            if solde < 0:
                self.notifications.append({
                    "type": "danger",
                    "icon": "💸",
                    "title": "Compte à découvert",
                    "message": f"{compte}: {solde:.2f}€"
                })


# ==============================================================================
# 7. EXPORT PDF & EXCEL
# ==============================================================================
class ExportManager:
    """Gère les exports de données"""
    
    def __init__(self, data: DataStore, user: str, mois: int, annee: int):
        self.data = data
        self.user = user
        self.mois = mois
        self.annee = annee
        self.df_mois = data.get_transactions_mois(mois, annee)
    
    def export_excel(self) -> BytesIO:
        """Génère un fichier Excel avec les données du mois"""
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Onglet Transactions
            if not self.df_mois.empty:
                df_export = self.df_mois.copy()
                df_export.to_excel(writer, sheet_name='Transactions', index=False)
            
            # Onglet Résumé
            engine = FinanceEngine(self.data, self.user)
            rav = engine.calculer_reste_a_vivre(self.mois, self.annee)
            
            resume = pd.DataFrame([
                {"Libellé": "Revenus", "Montant": rav["revenus"]},
                {"Libellé": "Dépenses Perso", "Montant": rav["depenses_perso"]},
                {"Libellé": "Part Commune", "Montant": rav["part_commune"]},
                {"Libellé": "Épargne", "Montant": rav["epargne"]},
                {"Libellé": "Investissements", "Montant": rav["investissements"]},
                {"Libellé": "Reste à Vivre", "Montant": rav["reste_a_vivre"]},
            ])
            resume.to_excel(writer, sheet_name='Résumé', index=False)
            
            # Onglet Par Catégorie
            if not self.df_mois.empty:
                par_cat = self.df_mois.groupby(["Type", "Categorie"])["Montant"].sum().reset_index()
                par_cat.to_excel(writer, sheet_name='Par Catégorie', index=False)
        
        output.seek(0)
        return output
    
    def generate_report_data(self) -> dict:
        """Génère les données pour le rapport PDF"""
        engine = FinanceEngine(self.data, self.user)
        rav = engine.calculer_reste_a_vivre(self.mois, self.annee)
        
        # Top dépenses
        top_depenses = []
        if not self.df_mois.empty:
            deps = self.df_mois[
                (self.df_mois["Type"] == "Dépense") &
                (self.df_mois["Qui_Connecte"] == self.user)
            ].nlargest(5, "Montant")
            top_depenses = deps[["Titre", "Categorie", "Montant"]].to_dict('records')
        
        # Répartition par catégorie
        repartition = []
        if not self.df_mois.empty:
            par_cat = self.df_mois[
                self.df_mois["Type"] == "Dépense"
            ].groupby("Categorie")["Montant"].sum().sort_values(ascending=False)
            repartition = [{"cat": k, "montant": v} for k, v in par_cat.items()]
        
        return {
            "mois": MOIS_FR[self.mois - 1],
            "annee": self.annee,
            "user": self.user,
            "rav": rav,
            "top_depenses": top_depenses,
            "repartition": repartition
        }


# ==============================================================================
# 8. COMPOSANTS UI
# ==============================================================================
def render_metric_card(label: str, value: str, color: str = "neutral", icon: str = ""):
    """Affiche une carte métrique stylée"""
    color_class = f"card-value {color}"
    st.markdown(f"""
        <div class="card">
            <div class="card-header">{icon} {label}</div>
            <div class="{color_class}">{value}</div>
        </div>
    """, unsafe_allow_html=True)


def render_notification(notif: dict):
    """Affiche une notification"""
    notif_class = f"notif notif-{notif['type']}"
    st.markdown(f"""
        <div class="{notif_class}">
            <span style="font-size:20px">{notif['icon']}</span>
            <div>
                <strong>{notif['title']}</strong><br>
                <span style="font-size:13px; opacity:0.9">{notif['message']}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_transaction_item(row: pd.Series, show_delete: bool = True) -> bool:
    """Affiche une ligne de transaction. Retourne True si supprimée."""
    type_icons = {
        "Dépense": ("💸", "expense", "negative"),
        "Revenu": ("💰", "income", "positive"),
        "Épargne": ("🏦", "saving", "neutral"),
        "Investissement": ("📈", "saving", "negative"),
        "Virement Interne": ("🔄", "transfer", "neutral"),
    }
    
    icon, icon_class, amount_class = type_icons.get(row["Type"], ("📝", "expense", "neutral"))
    
    col1, col2, col3, col4 = st.columns([0.5, 3, 2, 1])
    
    with col1:
        st.markdown(f'<div class="transaction-icon {icon_class}">{icon}</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="transaction-title">{row['Titre']}</div>
            <div class="transaction-category">{row['Categorie']} · {row['Date']}</div>
        """, unsafe_allow_html=True)
    
    with col3:
        sign = "-" if row["Type"] in ["Dépense", "Investissement"] else "+"
        st.markdown(f"""
            <div class="transaction-amount {amount_class}">{sign}{row['Montant']:,.2f} €</div>
        """, unsafe_allow_html=True)
    
    with col4:
        if show_delete:
            if st.button("🗑️", key=f"del_{row['id']}", help="Supprimer"):
                return True
    
    return False


def render_account_card(nom: str, solde: float, is_epargne: bool = False):
    """Affiche une carte compte dans la sidebar"""
    if is_epargne:
        card_class = "account-card savings"
    elif solde < 0:
        card_class = "account-card negative"
    else:
        card_class = "account-card current"
    
    st.markdown(f"""
        <div class="{card_class}">
            <div class="account-name">{nom}</div>
            <div class="account-balance">{solde:,.2f} €</div>
        </div>
    """, unsafe_allow_html=True)


def render_progress_bar(label: str, current: float, target: float, color: str = "#6366F1"):
    """Affiche une barre de progression personnalisée"""
    pct = min(current / target * 100, 100) if target > 0 else 0
    
    # Couleur dynamique selon le niveau
    if pct >= 100:
        bar_color = "#EF4444"  # Rouge si dépassé
    elif pct >= 80:
        bar_color = "#F59E0B"  # Orange si proche
    else:
        bar_color = color
    
    st.markdown(f"""
        <div style="margin-bottom: 16px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                <span style="font-weight:600; color:#374151;">{label}</span>
                <span style="color:#6B7280;">{current:,.0f}€ / {target:,.0f}€</span>
            </div>
            <div style="background:#E5E7EB; border-radius:10px; height:10px; overflow:hidden;">
                <div style="background:{bar_color}; width:{pct}%; height:100%; border-radius:10px; transition:width 0.3s ease;"></div>
            </div>
        </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# 9. PAGES DE L'APPLICATION
# ==============================================================================
def page_accueil(data: DataStore, user: str, mois: int, annee: int):
    """Page d'accueil / Dashboard"""
    st.markdown(f"## 👋 Bonjour {user}")
    st.markdown(f"<p style='color:#6B7280; margin-top:-10px;'>Voici votre synthèse pour {MOIS_FR[mois-1]} {annee}</p>", unsafe_allow_html=True)
    
    # Calculs
    engine = FinanceEngine(data, user)
    rav = engine.calculer_reste_a_vivre(mois, annee)
    
    # === NOTIFICATIONS ===
    assistant = SmartAssistant(data, user, mois, annee)
    notifications = assistant.analyser()
    
    if notifications:
        st.markdown("### 🔔 Alertes")
        for notif in notifications[:5]:  # Max 5 alertes
            render_notification(notif)
        st.markdown("<br>", unsafe_allow_html=True)
    
    # === MÉTRIQUES PRINCIPALES ===
    st.markdown("### 📊 Vue d'ensemble")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Revenus",
            f"{rav['revenus']:,.0f} €",
            delta=None
        )
    
    with col2:
        st.metric(
            "Dépenses",
            f"{rav['depenses_perso'] + rav['part_commune']:,.0f} €",
            delta=f"-{rav['depenses_perso'] + rav['part_commune']:,.0f}",
            delta_color="inverse"
        )
    
    with col3:
        st.metric(
            "Épargne",
            f"{rav['epargne']:,.0f} €",
            delta=f"+{rav['epargne']:,.0f}" if rav['epargne'] > 0 else None
        )
    
    with col4:
        delta_color = "normal" if rav['reste_a_vivre'] >= 0 else "inverse"
        st.metric(
            "Reste à vivre",
            f"{rav['reste_a_vivre']:,.0f} €",
            delta_color=delta_color
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # === DEUX COLONNES ===
    col_left, col_right = st.columns([3, 2])
    
    with col_left:
        st.markdown("### 📝 Dernières transactions")
        
        df_user = data.transactions[data.transactions["Qui_Connecte"] == user]
        if not df_user.empty:
            recents = df_user.sort_values("Date", ascending=False).head(8)
            
            for _, row in recents.iterrows():
                if render_transaction_item(row, show_delete=False):
                    pass  # Pas de suppression sur l'accueil
        else:
            st.info("Aucune transaction enregistrée.")
    
    with col_right:
        st.markdown("### 🎯 Budgets")
        
        if not data.objectifs.empty:
            for _, obj in data.objectifs.head(4).iterrows():
                cat = obj.get("Categorie", "")
                budget = obj.get("Montant", 0)
                
                result = engine.calculer_budget_restant(cat, mois, annee)
                render_progress_bar(cat, result["depense"], budget)
        else:
            st.info("Aucun budget défini. Configurez vos enveloppes dans Réglages.")
        
        st.markdown("---")
        
        # Projets d'épargne
        st.markdown("### 🎯 Projets")
        
        if not data.projets.empty:
            for _, proj in data.projets.head(3).iterrows():
                nom = proj.get("Projet", "")
                cible = proj.get("Cible", 0)
                
                # Calculer l'épargne affectée
                epargne_projet = 0
                if not data.transactions.empty:
                    epargne_projet = data.transactions[
                        data.transactions["Projet_Epargne"] == nom
                    ]["Montant"].sum()
                
                render_progress_bar(nom, epargne_projet, cible, color="#10B981")
        else:
            st.info("Aucun projet d'épargne.")


def page_operations(data: DataStore, user: str, mois: int, annee: int, comptes_visibles: list):
    """Page Opérations (Saisie, Journal, Abonnements)"""
    
    tabs = st.tabs(["➕ Saisie rapide", "📋 Journal", "🔄 Abonnements"])
    
    # === SAISIE ===
    with tabs[0]:
        st.markdown("### Nouvelle opération")
        
        with st.form("form_saisie", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                date_op = st.date_input("Date", datetime.now())
            with col2:
                type_op = st.selectbox("Type", TYPES)
            with col3:
                montant = st.number_input("Montant (€)", min_value=0.0, step=0.01, format="%.2f")
            
            col4, col5 = st.columns(2)
            
            with col4:
                titre = st.text_input("Titre", placeholder="Ex: Carrefour, Loyer...")
            
            # Auto-catégorisation
            cat_auto = "Autre"
            compte_auto = comptes_visibles[0] if comptes_visibles else ""
            
            if titre and not data.mots_cles.empty:
                for _, mc in data.mots_cles.iterrows():
                    if str(mc.get("Mot_Cle", "")).lower() in titre.lower():
                        cat_auto = mc.get("Categorie", cat_auto)
                        compte_auto = mc.get("Compte", compte_auto)
                        break
            
            categories = data.categories.get(type_op, ["Autre"])
            try:
                idx_cat = categories.index(cat_auto)
            except ValueError:
                idx_cat = 0
            
            with col5:
                categorie = st.selectbox("Catégorie", categories, index=idx_cat)
            
            col6, col7 = st.columns(2)
            
            with col6:
                try:
                    idx_compte = comptes_visibles.index(compte_auto)
                except ValueError:
                    idx_compte = 0
                compte_source = st.selectbox("Compte", comptes_visibles, index=idx_compte)
            
            with col7:
                imputation = st.selectbox("Imputation", IMPUTATIONS)
            
            # Champs conditionnels
            compte_cible = ""
            projet_epargne = ""
            pourcentage_perso = 50
            
            if imputation == "Commun (Autre %)":
                pourcentage_perso = st.slider(
                    f"Ma part ({user})", 
                    min_value=0, max_value=100, value=50,
                    help="Pourcentage que vous payez"
                )
            
            if type_op in ["Épargne", "Virement Interne"]:
                col_a, col_b = st.columns(2)
                with col_a:
                    if type_op == "Épargne":
                        comptes_epargne = [c for c in comptes_visibles if data.type_compte.get(c) == "Épargne"]
                        if comptes_epargne:
                            compte_cible = st.selectbox("Vers compte épargne", comptes_epargne)
                    else:
                        compte_cible = st.selectbox("Vers compte", comptes_visibles)
                
                with col_b:
                    if type_op == "Épargne" and not data.projets.empty:
                        projets_list = ["Aucun"] + data.projets["Projet"].tolist()
                        projet_epargne = st.selectbox("Affecter au projet", projets_list)
                        if projet_epargne == "Aucun":
                            projet_epargne = ""
            
            submitted = st.form_submit_button("💾 Enregistrer", type="primary", use_container_width=True)
            
            if submitted and montant > 0:
                new_row = {
                    "Date": date_op,
                    "Mois": date_op.month,
                    "Annee": date_op.year,
                    "Qui_Connecte": user,
                    "Type": type_op,
                    "Categorie": categorie,
                    "Titre": titre,
                    "Montant": montant,
                    "Paye_Par": user,
                    "Imputation": imputation,
                    "Pourcentage_Perso": pourcentage_perso,
                    "Compte_Source": compte_source,
                    "Compte_Cible": compte_cible,
                    "Projet_Epargne": projet_epargne
                }
                
                if save_row("Data", new_row):
                    st.success("✅ Transaction enregistrée !")
                    time.sleep(0.5)
                    st.rerun()
    
    # === JOURNAL ===
    with tabs[1]:
        st.markdown("### Historique des transactions")
        
        col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
        
        with col_f1:
            filtre_mois = st.checkbox("Mois en cours uniquement", value=True)
        with col_f2:
            recherche = st.text_input("🔍 Rechercher", placeholder="Titre, catégorie...")
        with col_f3:
            if st.button("📥 Export Excel"):
                export = ExportManager(data, user, mois, annee)
                excel_data = export.export_excel()
                st.download_button(
                    "Télécharger",
                    excel_data,
                    file_name=f"budget_{MOIS_FR[mois-1]}_{annee}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        
        # Filtrage
        if filtre_mois:
            df_display = data.get_transactions_mois(mois, annee)
        else:
            df_display = data.transactions.copy()
        
        if recherche:
            df_display = df_display[
                df_display["Titre"].str.contains(recherche, case=False, na=False) |
                df_display["Categorie"].str.contains(recherche, case=False, na=False)
            ]
        
        # Affichage
        if not df_display.empty:
            df_sorted = df_display.sort_values("Date", ascending=False)
            
            for _, row in df_sorted.head(50).iterrows():
                deleted = render_transaction_item(row, show_delete=True)
                if deleted:
                    delete_row("Data", row["id"])
                    st.rerun()
        else:
            st.info("Aucune transaction trouvée.")
    
    # === ABONNEMENTS ===
    with tabs[2]:
        st.markdown("### Vos abonnements récurrents")
        
        col_btn, _ = st.columns([1, 3])
        with col_btn:
            if st.button("➕ Nouvel abonnement"):
                save_row("Abonnements", {
                    "Nom": "Nouvel abonnement",
                    "Montant": 0,
                    "Proprietaire": user,
                    "Jour": 1,
                    "Categorie": "Abonnements",
                    "Imputation": "Perso"
                })
                st.rerun()
        
        if not data.abonnements.empty:
            mes_abos = data.abonnements[data.abonnements["Proprietaire"] == user]
            
            total_abos = mes_abos["Montant"].sum()
            st.metric("Total mensuel", f"{total_abos:,.2f} €")
            
            st.markdown("---")
            
            for _, abo in mes_abos.iterrows():
                with st.expander(f"📅 {abo['Nom']} - {abo['Montant']:.2f} €/mois"):
                    with st.form(f"edit_abo_{abo['id']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            nom = st.text_input("Nom", value=abo.get("Nom", ""))
                            montant_abo = st.number_input("Montant", value=float(abo.get("Montant", 0)))
                        with col2:
                            jour = st.number_input("Jour du mois", value=int(abo.get("Jour", 1) or 1), min_value=1, max_value=31)
                            cat_abo = st.selectbox(
                                "Catégorie",
                                data.categories.get("Dépense", ["Abonnements"]),
                                index=0
                            )
                        
                        col_save, col_del = st.columns(2)
                        with col_save:
                            if st.form_submit_button("💾 Sauvegarder"):
                                update_row("Abonnements", abo['id'], {
                                    "Nom": nom,
                                    "Montant": montant_abo,
                                    "Jour": jour,
                                    "Categorie": cat_abo
                                })
                                st.rerun()
                        with col_del:
                            if st.form_submit_button("🗑️ Supprimer", type="secondary"):
                                delete_row("Abonnements", abo['id'])
                                st.rerun()
            
            st.markdown("---")
            
            if st.button("🚀 Générer les transactions du mois", type="primary", use_container_width=True):
                df_mois = data.get_transactions_mois(mois, annee)
                count = 0
                
                for _, abo in mes_abos.iterrows():
                    # Vérifier si déjà payé
                    existe = not df_mois[
                        (df_mois["Titre"] == abo["Nom"]) &
                        (df_mois["Montant"] == abo["Montant"])
                    ].empty
                    
                    if not existe:
                        jour = int(abo.get("Jour", 1) or 1)
                        jour = min(jour, 28)  # Éviter les erreurs de date
                        
                        new_row = {
                            "Date": date(annee, mois, jour),
                            "Mois": mois,
                            "Annee": annee,
                            "Qui_Connecte": user,
                            "Type": "Dépense",
                            "Categorie": abo.get("Categorie", "Abonnements"),
                            "Titre": abo["Nom"],
                            "Montant": abo["Montant"],
                            "Paye_Par": user,
                            "Imputation": abo.get("Imputation", "Perso"),
                            "Compte_Source": comptes_visibles[0] if comptes_visibles else ""
                        }
                        save_row("Data", new_row)
                        count += 1
                
                if count > 0:
                    st.success(f"✅ {count} transaction(s) générée(s) !")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.info("Tous les abonnements ont déjà été comptabilisés ce mois.")
        else:
            st.info("Aucun abonnement configuré.")


def page_analyses(data: DataStore, user: str, mois: int, annee: int):
    """Page Analyses et graphiques"""
    st.markdown("## 📊 Analyses")
    
    df_mois = data.get_transactions_mois(mois, annee)
    
    if df_mois.empty:
        st.info("Aucune donnée pour ce mois.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Répartition des dépenses")
        
        df_dep = df_mois[df_mois["Type"] == "Dépense"].groupby("Categorie")["Montant"].sum().reset_index()
        
        if not df_dep.empty:
            fig = px.pie(
                df_dep,
                values="Montant",
                names="Categorie",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(
                showlegend=False,
                margin=dict(t=20, b=20, l=20, r=20)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune dépense ce mois.")
    
    with col2:
        st.markdown("### Évolution sur 6 mois")
        
        # Données des 6 derniers mois
        evolution = []
        for i in range(6):
            d = date(annee, mois, 1) - relativedelta(months=i)
            df_m = data.transactions[
                (data.transactions["Mois"] == d.month) &
                (data.transactions["Annee"] == d.year) &
                (data.transactions["Qui_Connecte"] == user)
            ]
            
            revenus = df_m[df_m["Type"] == "Revenu"]["Montant"].sum()
            depenses = df_m[df_m["Type"] == "Dépense"]["Montant"].sum()
            
            evolution.append({
                "Mois": f"{MOIS_FR[d.month-1][:3]}",
                "Revenus": revenus,
                "Dépenses": depenses
            })
        
        df_evol = pd.DataFrame(evolution[::-1])  # Inverser pour ordre chronologique
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_evol["Mois"],
            y=df_evol["Revenus"],
            name="Revenus",
            marker_color="#10B981"
        ))
        fig.add_trace(go.Bar(
            x=df_evol["Mois"],
            y=df_evol["Dépenses"],
            name="Dépenses",
            marker_color="#EF4444"
        ))
        fig.update_layout(
            barmode='group',
            margin=dict(t=20, b=20, l=20, r=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02)
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Tableau détaillé par catégorie
    st.markdown("### Détail par catégorie")
    
    df_detail = df_mois.groupby(["Type", "Categorie"]).agg({
        "Montant": ["sum", "count", "mean"]
    }).reset_index()
    df_detail.columns = ["Type", "Catégorie", "Total", "Nb", "Moyenne"]
    df_detail["Total"] = df_detail["Total"].apply(lambda x: f"{x:,.2f} €")
    df_detail["Moyenne"] = df_detail["Moyenne"].apply(lambda x: f"{x:,.2f} €")
    
    st.dataframe(df_detail, use_container_width=True, hide_index=True)
    
    # Export
    st.markdown("---")
    
    col_exp1, col_exp2, _ = st.columns([1, 1, 2])
    
    with col_exp1:
        export = ExportManager(data, user, mois, annee)
        excel_data = export.export_excel()
        st.download_button(
            "📥 Télécharger Excel",
            excel_data,
            file_name=f"analyse_{MOIS_FR[mois-1]}_{annee}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )


def page_patrimoine(data: DataStore, user: str, comptes_visibles: list):
    """Page Patrimoine et Projets"""
    st.markdown("## 💎 Patrimoine")
    
    engine = FinanceEngine(data, user)
    
    # === SOLDES DES COMPTES ===
    st.markdown("### 💳 Vos comptes")
    
    cols = st.columns(len(comptes_visibles) if comptes_visibles else 1)
    
    total_patrimoine = 0
    
    for i, compte in enumerate(comptes_visibles):
        solde = engine.calculer_solde_compte(compte)
        total_patrimoine += solde
        type_c = data.type_compte.get(compte, "Courant")
        
        with cols[i]:
            color = "#6366F1" if type_c == "Épargne" else ("#10B981" if solde >= 0 else "#EF4444")
            icon = "🏦" if type_c == "Épargne" else "💳"
            
            st.markdown(f"""
                <div class="card">
                    <div class="card-header">{icon} {compte}</div>
                    <div class="card-value" style="color:{color}">{solde:,.2f} €</div>
                    <div style="font-size:12px; color:#9CA3AF; margin-top:4px;">{type_c}</div>
                </div>
            """, unsafe_allow_html=True)
    
    st.markdown(f"""
        <div style="text-align:center; margin:20px 0; padding:16px; background:linear-gradient(135deg, #6366F1, #8B5CF6); border-radius:12px;">
            <div style="color:rgba(255,255,255,0.8); font-size:14px;">PATRIMOINE TOTAL</div>
            <div style="color:white; font-size:32px; font-weight:700;">{total_patrimoine:,.2f} €</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # === AJUSTEMENT SOLDE ===
    with st.expander("🔧 Ajuster un solde (inventaire bancaire)"):
        st.markdown("*Utilisez cette fonction pour recaler votre solde avec celui de votre banque.*")
        
        with st.form("form_ajustement"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                compte_adj = st.selectbox("Compte", comptes_visibles)
            with col2:
                montant_adj = st.number_input("Solde réel actuel", step=0.01)
            with col3:
                date_adj = st.date_input("Date", datetime.now())
            
            if st.form_submit_button("💾 Enregistrer", use_container_width=True):
                save_row("Patrimoine", {
                    "Date": date_adj,
                    "Compte": compte_adj,
                    "Montant": montant_adj,
                    "Proprietaire": user
                })
                st.success("✅ Solde mis à jour !")
                st.rerun()
    
    st.markdown("---")
    
    # === PROJETS D'ÉPARGNE ===
    st.markdown("### 🎯 Projets d'épargne")
    
    if not data.projets.empty:
        for _, proj in data.projets.iterrows():
            nom = proj.get("Projet", "")
            cible = proj.get("Cible", 0)
            
            # Calculer l'épargne
            epargne = 0
            if not data.transactions.empty:
                epargne = data.transactions[
                    data.transactions["Projet_Epargne"] == nom
                ]["Montant"].sum()
            
            col_p1, col_p2 = st.columns([4, 1])
            
            with col_p1:
                render_progress_bar(nom, epargne, cible, color="#10B981")
            
            with col_p2:
                if st.button("🗑️", key=f"del_proj_{proj['id']}"):
                    delete_row("Projets_Config", proj['id'])
                    st.rerun()
    else:
        st.info("Aucun projet d'épargne. Créez-en un ci-dessous !")
    
    # Nouveau projet
    with st.form("form_projet"):
        col1, col2 = st.columns(2)
        with col1:
            nom_proj = st.text_input("Nom du projet")
        with col2:
            cible_proj = st.number_input("Objectif (€)", min_value=0.0, step=100.0)
        
        if st.form_submit_button("➕ Créer le projet"):
            if nom_proj:
                save_row("Projets_Config", {
                    "Projet": nom_proj,
                    "Cible": cible_proj,
                    "Proprietaire": user
                })
                st.success("✅ Projet créé !")
                st.rerun()


def page_remboursements(data: DataStore):
    """Page de gestion des remboursements entre personnes"""
    st.markdown("## 🤝 Qui doit quoi ?")
    
    # Calcul des avances
    avances = {"Pierre": 0.0, "Elie": 0.0}
    
    if not data.transactions.empty:
        for user in USERS:
            avances[user] = data.transactions[
                (data.transactions["Paye_Par"] == user) &
                (data.transactions["Imputation"] == "Avance/Cadeau")
            ]["Montant"].sum()
    
    # Calcul des remboursements
    rembourses = {"Pierre": 0.0, "Elie": 0.0}
    
    if not data.remboursements.empty:
        for user in USERS:
            rembourses[user] = data.remboursements[
                data.remboursements["De"] == user
            ]["Montant"].sum()
    
    # Solde net
    # Pierre a avancé X pour Elie, Elie a remboursé Y → Elie doit encore X - Y
    # Et inversement
    pierre_net = avances["Pierre"] - rembourses["Elie"]
    elie_net = avances["Elie"] - rembourses["Pierre"]
    
    diff = pierre_net - elie_net
    
    # Affichage
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
            <div class="card">
                <div class="card-header">Pierre a avancé</div>
                <div class="card-value neutral">{avances['Pierre']:,.2f} €</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="card">
                <div class="card-header">Elie a avancé</div>
                <div class="card-value neutral">{avances['Elie']:,.2f} €</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Résultat
    if diff > 5:  # Seuil de 5€
        st.markdown(f"""
            <div style="text-align:center; padding:24px; background:linear-gradient(135deg, #FEF3C7, #FDE68A); border-radius:16px; border:2px solid #F59E0B;">
                <div style="font-size:18px; color:#92400E; margin-bottom:8px;">💰 Solde à régler</div>
                <div style="font-size:28px; font-weight:700; color:#78350F;">Elie doit {diff:,.2f} € à Pierre</div>
            </div>
        """, unsafe_allow_html=True)
    elif diff < -5:
        st.markdown(f"""
            <div style="text-align:center; padding:24px; background:linear-gradient(135deg, #FEF3C7, #FDE68A); border-radius:16px; border:2px solid #F59E0B;">
                <div style="font-size:18px; color:#92400E; margin-bottom:8px;">💰 Solde à régler</div>
                <div style="font-size:28px; font-weight:700; color:#78350F;">Pierre doit {abs(diff):,.2f} € à Elie</div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div style="text-align:center; padding:24px; background:linear-gradient(135deg, #D1FAE5, #A7F3D0); border-radius:16px; border:2px solid #10B981;">
                <div style="font-size:28px; font-weight:700; color:#065F46;">✅ Tout est équilibré !</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Historique des remboursements
    st.markdown("### 📜 Historique")
    
    if not data.remboursements.empty:
        for _, r in data.remboursements.sort_values("Date", ascending=False).iterrows():
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.write(f"**{r['De']}** → **{r['A']}**")
            with col2:
                st.write(f"{r['Montant']:,.2f} € le {r['Date']}")
            with col3:
                if st.button("🗑️", key=f"del_remb_{r['id']}"):
                    delete_row("Remboursements", r['id'])
                    st.rerun()
    
    st.markdown("---")
    
    # Nouveau remboursement
    st.markdown("### ➕ Enregistrer un remboursement")
    
    with st.form("form_remboursement"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            qui = st.selectbox("Qui rembourse ?", USERS)
        with col2:
            combien = st.number_input("Montant", min_value=0.0, step=10.0)
        with col3:
            quand = st.date_input("Date", datetime.now())
        
        if st.form_submit_button("✅ Valider", type="primary", use_container_width=True):
            dest = "Elie" if qui == "Pierre" else "Pierre"
            save_row("Remboursements", {
                "Date": quand,
                "De": qui,
                "A": dest,
                "Montant": combien
            })
            st.success("Remboursement enregistré !")
            st.rerun()


def page_credits(data: DataStore):
    """Page de suivi des crédits"""
    st.markdown("## 🏦 Crédits en cours")
    
    if not data.credits.empty:
        for _, cred in data.credits.iterrows():
            initial = cred.get("Montant_Initial", 0)
            restant = cred.get("Montant_Restant", 0)
            mensualite = cred.get("Mensualite", 0)
            
            paye = initial - restant
            pct = (paye / initial * 100) if initial > 0 else 0
            
            st.markdown(f"""
                <div class="card" style="margin-bottom:16px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                        <div>
                            <div style="font-size:18px; font-weight:600; color:#1F2937;">{cred.get('Nom', 'Crédit')}</div>
                            <div style="font-size:13px; color:#6B7280;">{cred.get('Organisme', '')}</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:24px; font-weight:700; color:#6366F1;">{restant:,.0f} €</div>
                            <div style="font-size:12px; color:#6B7280;">restant</div>
                        </div>
                    </div>
                    <div style="display:flex; gap:20px; margin-bottom:12px;">
                        <div><span style="color:#6B7280;">Initial:</span> <strong>{initial:,.0f} €</strong></div>
                        <div><span style="color:#6B7280;">Mensualité:</span> <strong>{mensualite:,.0f} €</strong></div>
                        <div><span style="color:#6B7280;">Remboursé:</span> <strong>{paye:,.0f} € ({pct:.0f}%)</strong></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Barre de progression
            render_progress_bar("", paye, initial, color="#10B981")
            
            with st.expander("🔧 Modifier"):
                with st.form(f"edit_credit_{cred['id']}"):
                    new_restant = st.number_input(
                        "Nouveau montant restant",
                        value=float(restant),
                        key=f"restant_{cred['id']}"
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("💾 Sauvegarder"):
                            update_row("Credits", cred['id'], {"Montant_Restant": new_restant})
                            st.rerun()
                    with col2:
                        if st.form_submit_button("🗑️ Supprimer"):
                            delete_row("Credits", cred['id'])
                            st.rerun()
            
            st.markdown("---")
    else:
        st.info("Aucun crédit enregistré.")
    
    # Nouveau crédit
    with st.expander("➕ Ajouter un crédit"):
        with st.form("form_credit"):
            col1, col2 = st.columns(2)
            
            with col1:
                nom = st.text_input("Nom du crédit")
                organisme = st.text_input("Organisme")
            
            with col2:
                montant_initial = st.number_input("Montant emprunté", min_value=0.0)
                montant_restant = st.number_input("Montant restant", min_value=0.0)
            
            mensualite = st.number_input("Mensualité", min_value=0.0)
            
            if st.form_submit_button("➕ Ajouter", type="primary"):
                save_row("Credits", {
                    "Nom": nom,
                    "Organisme": organisme,
                    "Montant_Initial": montant_initial,
                    "Montant_Restant": montant_restant,
                    "Mensualite": mensualite
                })
                st.success("Crédit ajouté !")
                st.rerun()


def page_reglages(data: DataStore, user: str):
    """Page de configuration"""
    st.markdown("## ⚙️ Configuration")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📁 Catégories", "💳 Comptes", "🎯 Budgets", "🔑 Mots-clés"])
    
    # === CATÉGORIES ===
    with tab1:
        st.markdown("### Gérer les catégories")
        
        with st.form("form_categorie"):
            col1, col2 = st.columns(2)
            with col1:
                new_cat = st.text_input("Nouvelle catégorie")
            with col2:
                type_cat = st.selectbox("Type", TYPES)
            
            if st.form_submit_button("➕ Ajouter"):
                if new_cat:
                    save_row("Config", {"Categorie": new_cat, "Type": type_cat})
                    st.rerun()
        
        st.markdown("---")
        
        if not data.config.empty:
            for type_t in TYPES:
                cats = data.config[data.config["Type"] == type_t]
                if not cats.empty:
                    st.markdown(f"**{type_t}**")
                    cols = st.columns(4)
                    for i, (_, cat) in enumerate(cats.iterrows()):
                        with cols[i % 4]:
                            col_a, col_b = st.columns([3, 1])
                            col_a.write(cat["Categorie"])
                            if col_b.button("×", key=f"del_cat_{cat['id']}"):
                                delete_row("Config", cat['id'])
                                st.rerun()
    
    # === COMPTES ===
    with tab2:
        st.markdown("### Gérer les comptes")
        
        with st.form("form_compte"):
            col1, col2, col3 = st.columns(3)
            with col1:
                new_compte = st.text_input("Nom du compte")
            with col2:
                proprio = st.selectbox("Propriétaire", ["Commun"] + USERS)
            with col3:
                type_compte = st.selectbox("Type", TYPES_COMPTE)
            
            if st.form_submit_button("➕ Ajouter"):
                if new_compte:
                    save_row("Comptes", {
                        "Compte": new_compte,
                        "Proprietaire": proprio,
                        "Type": type_compte
                    })
                    st.rerun()
        
        st.markdown("---")
        
        if not data.comptes.empty:
            for _, cpt in data.comptes.iterrows():
                col1, col2, col3 = st.columns([2, 2, 1])
                col1.write(f"**{cpt['Compte']}**")
                col2.write(f"{cpt['Proprietaire']} · {cpt.get('Type', 'Courant')}")
                if col3.button("🗑️", key=f"del_cpt_{cpt['id']}"):
                    delete_row("Comptes", cpt['id'])
                    st.rerun()
    
    # === BUDGETS ===
    with tab3:
        st.markdown("### Définir les enveloppes budgétaires")
        
        with st.form("form_budget"):
            col1, col2, col3 = st.columns(3)
            with col1:
                cat_budget = st.selectbox("Catégorie", data.categories.get("Dépense", ["Autre"]))
            with col2:
                montant_budget = st.number_input("Budget mensuel (€)", min_value=0.0, step=50.0)
            with col3:
                scope = st.selectbox("Portée", ["Perso", "Commun"])
            
            if st.form_submit_button("➕ Définir"):
                save_row("Objectifs", {
                    "Categorie": cat_budget,
                    "Montant": montant_budget,
                    "Scope": scope
                })
                st.rerun()
        
        st.markdown("---")
        
        if not data.objectifs.empty:
            for _, obj in data.objectifs.iterrows():
                col1, col2, col3 = st.columns([2, 2, 1])
                col1.write(f"**{obj['Categorie']}**")
                col2.write(f"{obj['Montant']:,.0f} € / mois")
                if col3.button("🗑️", key=f"del_obj_{obj['id']}"):
                    delete_row("Objectifs", obj['id'])
                    st.rerun()
    
    # === MOTS-CLÉS ===
    with tab4:
        st.markdown("### Règles d'auto-catégorisation")
        st.caption("Quand un mot-clé est détecté dans le titre, la catégorie et le compte sont automatiquement remplis.")
        
        with st.form("form_motcle"):
            col1, col2, col3 = st.columns(3)
            with col1:
                mot = st.text_input("Mot-clé")
            with col2:
                cat_mot = st.selectbox("Catégorie", data.categories.get("Dépense", ["Autre"]))
            with col3:
                compte_mot = st.selectbox("Compte", data.get_comptes_visibles(user))
            
            if st.form_submit_button("➕ Ajouter"):
                if mot:
                    save_row("Mots_Cles", {
                        "Mot_Cle": mot,
                        "Categorie": cat_mot,
                        "Compte": compte_mot
                    })
                    st.rerun()
        
        st.markdown("---")
        
        if not data.mots_cles.empty:
            for _, mc in data.mots_cles.iterrows():
                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                col1.write(f"**{mc['Mot_Cle']}**")
                col2.write(mc.get('Categorie', ''))
                col3.write(mc.get('Compte', ''))
                if col4.button("🗑️", key=f"del_mc_{mc['id']}"):
                    delete_row("Mots_Cles", mc['id'])
                    st.rerun()


# ==============================================================================
# 10. APPLICATION PRINCIPALE
# ==============================================================================
def main():
    st.set_page_config(
        page_title=APP_NAME,
        page_icon="💰",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    apply_modern_style()
    
    # Chargement des données
    data = DataStore()
    
    # === SIDEBAR ===
    with st.sidebar:
        st.markdown(f"# 💰 {APP_NAME}")
        st.caption(f"v{APP_VERSION}")
        
        st.markdown("---")
        
        # Sélecteur utilisateur
        user = st.selectbox("👤 Utilisateur", USERS)
        
        # Sélecteurs date
        d_now = datetime.now()
        mois_nom = st.selectbox("📅 Mois", MOIS_FR, index=d_now.month - 1)
        mois = MOIS_FR.index(mois_nom) + 1
        annee = st.number_input("Année", value=d_now.year, min_value=2020, max_value=2030)
        
        st.markdown("---")
        
        # Soldes des comptes
        st.markdown("### 💳 Soldes")
        
        comptes_visibles = data.get_comptes_visibles(user)
        engine = FinanceEngine(data, user)
        
        total_courant = 0
        total_epargne = 0
        
        for compte in comptes_visibles:
            solde = engine.calculer_solde_compte(compte)
            is_epargne = data.type_compte.get(compte) == "Épargne"
            
            if is_epargne:
                total_epargne += solde
            else:
                total_courant += solde
            
            render_account_card(compte, solde, is_epargne)
        
        st.markdown(f"""
            <div style="padding:12px; margin-top:12px; background:rgba(255,255,255,0.05); border-radius:8px; text-align:center;">
                <span style="color:#9CA3AF; font-size:12px;">Courant: {total_courant:,.0f}€ · Épargne: {total_epargne:,.0f}€</span>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        if st.button("🔄 Actualiser", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # === CONTENU PRINCIPAL ===
    tabs = st.tabs([
        "🏠 Accueil",
        "💳 Opérations",
        "📊 Analyses",
        "💎 Patrimoine",
        "🤝 Remboursements",
        "🏦 Crédits",
        "⚙️ Réglages"
    ])
    
    with tabs[0]:
        page_accueil(data, user, mois, annee)
    
    with tabs[1]:
        page_operations(data, user, mois, annee, comptes_visibles)
    
    with tabs[2]:
        page_analyses(data, user, mois, annee)
    
    with tabs[3]:
        page_patrimoine(data, user, comptes_visibles)
    
    with tabs[4]:
        page_remboursements(data)
    
    with tabs[5]:
        page_credits(data)
    
    with tabs[6]:
        page_reglages(data, user)


if __name__ == "__main__":
    main()
