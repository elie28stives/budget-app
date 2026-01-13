import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json

# --- CONFIGURATION GOOGLE SHEETS ---
SHEET_NAME = "Budget_Couple_DB"

# Noms des Onglets dans le Google Sheet
TAB_DATA = "Data"
TAB_CONFIG = "Config"
TAB_OBJECTIFS = "Objectifs"
TAB_PATRIMOINE = "Patrimoine"
TAB_COMPTES = "Comptes"

USERS = ["Pierre", "Elie"]
TYPES = ["Dépense", "Revenu", "🔄 Virement Interne", "Épargne", "Investissement"]
IMPUTATIONS = ["Perso (Pour moi)", "Commun (50/50)", "Pour l'autre (Cadeau/Avance)"]
MOIS_FR = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

# --- STYLE CSS ---
def apply_custom_style():
    st.markdown("""
    <style>
        .block-container {padding-top: 2rem;}
        div[data-testid="stMetric"] {
            background-color: #FFFFFF;
            border: 1px solid #EAECEE;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
    </style>
    """, unsafe_allow_html=True)

# --- CONNEXION GOOGLE SHEETS (CACHE) ---
@st.cache_resource
def get_gspread_client():
    # On récupère les infos depuis .streamlit/secrets.toml
    creds_dict = dict(st.secrets["gcp_service_account"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def get_worksheet(client, sheet_name, tab_name):
    """Récupère un onglet, le crée s'il n'existe pas"""
    sh = client.open(sheet_name)
    try:
        ws = sh.worksheet(tab_name)
    except:
        ws = sh.add_worksheet(title=tab_name, rows="100", cols="20")
    return ws

# --- FONCTIONS LECTURE / ÉCRITURE ---

def load_data_from_sheet(tab_name, colonnes):
    client = get_gspread_client()
    ws = get_worksheet(client, SHEET_NAME, tab_name)
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    
    # Si le tableau est vide ou colonnes manquantes, on initialise
    if df.empty:
        return pd.DataFrame(columns=colonnes)
    
    # S'assurer que toutes les colonnes existent
    for col in colonnes:
        if col not in df.columns:
            df[col] = ""
            
    # Conversion date si nécessaire
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce').dt.date
        
    return df

def save_data_to_sheet(tab_name, df):
    client = get_gspread_client()
    ws = get_worksheet(client, SHEET_NAME, tab_name)
    
    # Conversion des dates en string pour Google Sheets
    df_save = df.copy()
    if "Date" in df_save.columns:
        df_save["Date"] = df_save["Date"].astype(str)
        
    ws.clear() # On efface tout
    # On remet les en-têtes et les données
    ws.update([df_save.columns.values.tolist()] + df_save.values.tolist())

# --- GESTION DES JSON EN TABLEAUX (ADAPTATION POUR SHEETS) ---
# Pour stocker les configs (Comptes, Catégories, Objectifs) dans Sheets, 
# on va les aplatir en tableau simple : [Type, Clé, Valeur]

def load_config_cats():
    df = load_data_from_sheet(TAB_CONFIG, ["Type", "Categorie"])
    config = {k: [] for k in TYPES} # Reset default structure
    
    # Si vide, on charge les défauts
    if df.empty:
        return {
            "Dépense": ["Alimentation/Courses", "Loyer", "Remboursement Prêt", "Électricité/Eau/Gaz", "Transport/Essence", "Santé/Médecine", "Assurances", "Abonnements", "Animaux", "Vacances", "Cadeaux", "Resto/Sorties", "Shopping", "Autre"],
            "Revenu": ["Salaire", "Primes", "Remboursement Sécu", "Ventes (Vinted)", "Aides (CAF)", "Dividendes", "Autre"],
            "Épargne": ["Virement Mensuel", "Cagnotte", "Autre"],
            "Investissement": ["Bourse (PEA)", "Assurance Vie", "Crypto", "Immobilier", "Autre"],
            "🔄 Virement Interne": ["Alimentation Compte", "Équilibrage", "Autre"]
        }
    
    # Reconstruction du dict
    config = {}
    for _, row in df.iterrows():
        t = row["Type"]
        c = row["Categorie"]
        if t not in config: config[t] = []
        if c not in config[t]: config[t].append(c)
    return config

def save_config_cats(config_dict):
    rows = []
    for t, cats in config_dict.items():
        for c in cats:
            rows.append({"Type": t, "Categorie": c})
    df = pd.DataFrame(rows)
    save_data_to_sheet(TAB_CONFIG, df)

def load_comptes_struct():
    df = load_data_from_sheet(TAB_COMPTES, ["Proprietaire", "Compte"])
    if df.empty:
        return {"Pierre": ["Compte Courant Pierre"], "Elie": ["Compte Courant Elie"], "Commun": []}
    
    struct = {}
    for _, row in df.iterrows():
        p = row["Proprietaire"]
        c = row["Compte"]
        if p not in struct: struct[p] = []
        struct[p].append(c)
    return struct

def save_comptes_struct(struct_dict):
    rows = []
    for p, comptes in struct_dict.items():
        for c in comptes:
            rows.append({"Proprietaire": p, "Compte": c})
    df = pd.DataFrame(rows)
    save_data_to_sheet(TAB_COMPTES, df)

def load_objectifs():
    df = load_data_from_sheet(TAB_OBJECTIFS, ["Scope", "Categorie", "Montant"])
    objs = {"Commun": {}, "Perso": {}}
    if df.empty: return objs
    
    for _, row in df.iterrows():
        s = row["Scope"]
        c = row["Categorie"]
        m = row["Montant"]
        if s not in objs: objs[s] = {}
        objs[s][c] = float(m) if m else 0.0
    return objs

def save_objectifs(objs_dict):
    rows = []
    for scope, cats in objs_dict.items():
        for c, m in cats.items():
            rows.append({"Scope": scope, "Categorie": c, "Montant": m})
    df = pd.DataFrame(rows)
    save_data_to_sheet(TAB_OBJECTIFS, df)


# --- INTERFACE ---
st.set_page_config(page_title="Budget Cloud V17", layout="wide", page_icon="☁️")
apply_custom_style()

# --- CHARGEMENT DONNÉES (DEPUIS CLOUD) ---
# Colonnes Data
COLS_DATA = ["Date", "Mois", "Annee", "Qui_Connecte", "Type", "Categorie", "Description", "Montant", "Paye_Par", "Imputation", "Compte_Cible", "Projet_Epargne", "Compte_Source"]
df = load_data_from_sheet(TAB_DATA, COLS_DATA)

# Colonnes Patrimoine
COLS_PAT = ["Date", "Mois", "Annee", "Compte", "Montant", "Proprietaire"]
df_patrimoine = load_data_from_sheet(TAB_PATRIMOINE, COLS_PAT)

# Configs
cats_memoire = load_config_cats()
comptes_structure = load_comptes_struct()
objectifs = load_objectifs()

# Helpers
def get_comptes_autorises(user):
    return comptes_structure.get(user, []) + comptes_structure.get("Commun", []) + ["Autre / Externe"]

# --- SIDEBAR ---
with st.sidebar:
    st.header("👤 Profil (Cloud)")
    user_actuel = st.selectbox("Qui es-tu ?", USERS)
    st.divider()
    date_jour = datetime.now()
    mois_nom = st.selectbox("Mois", MOIS_FR, index=date_jour.month-1)
    mois_selection = MOIS_FR.index(mois_nom) + 1
    annee_selection = st.number_input("Année", value=date_jour.year)
    st.success("✅ Connecté à Google Sheets")
    
    comptes_disponibles = get_comptes_autorises(user_actuel)

# Filtre Mois
df_mois = df[(df["Mois"] == mois_selection) & (df["Annee"] == annee_selection)]

# --- NAVIGATION ---
tabs = st.tabs(["📊 Tableau de Bord", "➕ Saisir", "🎯 Objectifs", "🏦 Patrimoine", "📝 Historique", "📅 Bilan Annuel", "⚙️ Config Comptes"])

# ==============================================================================
# TAB 1 : DASHBOARD
# ==============================================================================
with tabs[0]:
    st.header(f"Tableau de Bord - {mois_nom} {annee_selection}")
    
    def color_red(val): 
        return f'color: {"#E74C3C" if val < 0 else "#27AE60"}; font-weight: bold;'
    format_dict = {"Objectif (€)": "{:.0f}", "Réel (€)": "{:.0f}", "Écart (€)": "{:.0f}"}

    def tableau_prevu_reel(type_flux, scope, df_source):
        objs_scope = objectifs.get(scope, {})
        mask = (df_source["Type"] == type_flux)
        if scope == "Commun":
            mask = mask & (df_source["Imputation"] == "Commun (50/50)")
        else: # Perso
            mask = mask & (df_source["Imputation"] == "Perso (Pour moi)") & (df_source["Qui_Connecte"] == user_actuel)
        
        df_filtered = df_source[mask]
        cats_budget = set(objs_scope.keys())
        cats_reel = set(df_filtered["Categorie"].unique())
        all_cats = list(cats_budget.union(cats_reel))
        
        data_rows = []
        tot_prevu = 0; tot_reel = 0
        for cat in all_cats:
            prevu = float(objs_scope.get(cat, 0.0))
            reel = df_filtered[df_filtered["Categorie"] == cat]["Montant"].sum()
            if prevu > 0 or reel > 0:
                diff = prevu - reel if type_flux == "Dépense" else reel - prevu
                data_rows.append({"Catégorie": cat, "Objectif (€)": prevu, "Réel (€)": reel, "Écart (€)": diff})
                tot_prevu += prevu; tot_reel += reel
        return pd.DataFrame(data_rows), tot_prevu, tot_reel

    col1, col2, col3, col4 = st.columns(4)
    rev_perso = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Revenu")]["Montant"].sum()
    dep_perso = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Dépense") & (df_mois["Imputation"] == "Perso (Pour moi)")]["Montant"].sum()
    epargne_perso = df_mois[(df_mois["Qui_Connecte"] == user_actuel) & (df_mois["Type"] == "Épargne")]["Montant"].sum()
    part_commun = df_mois[df_mois["Imputation"] == "Commun (50/50)"]["Montant"].sum() / 2
    
    col1.metric("💰 Revenus", f"{rev_perso:.0f} €")
    col2.metric("🛍️ Dépenses Perso", f"{dep_perso:.0f} €")
    col3.metric("🏠 Part du Commun", f"{part_commun:.0f} €")
    col4.metric("🐷 Épargne", f"{epargne_perso:.0f} €")
    
    st.markdown("---")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏠 Budget COMMUN")
        df_tab, t_prev, t_reel = tableau_prevu_reel("Dépense", "Commun", df_mois)
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Prévu", f"{t_prev:.0f} €")
        col_m2.metric("Réel", f"{t_reel:.0f} €")
        col_m3.metric("Reste", f"{t_prev - t_reel:.0f} €", delta_color="normal")
        if not df_tab.empty:
            st.dataframe(df_tab.style.map(color_red, subset=['Écart (€)']).format(format_dict), use_container_width=True, hide_index=True)
            
    with c2:
        st.subheader(f"👤 Budget PERSO ({user_actuel})")
        df_tab_p, t_prev_p, t_reel_p = tableau_prevu_reel("Dépense", "Perso", df_mois)
        col_p1, col_p2, col_p3 = st.columns(3)
        col_p1.metric("Prévu", f"{t_prev_p:.0f} €")
        col_p2.metric("Réel", f"{t_reel_p:.0f} €")
        col_p3.metric("Reste", f"{t_prev_p - t_reel_p:.0f} €", delta_color="normal")
        if not df_tab_p.empty:
            st.dataframe(df_tab_p.style.map(color_red, subset=['Écart (€)']).format(format_dict), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("⚖️ Balance des Comptes")
    df_com = df_mois[(df_mois["Imputation"] == "Commun (50/50)") & (df_mois["Type"] == "Dépense")]
    paye_pierre = df_com[df_com["Paye_Par"] == "Pierre"]["Montant"].sum()
    paye_elie = df_com[df_com["Paye_Par"] == "Elie"]["Montant"].sum()
    total_commun = df_com["Montant"].sum()
    diff = (paye_pierre - paye_elie) / 2
    
    b1, b2 = st.columns([3, 1])
    with b1: st.info(f"Total Dépenses Communes : **{total_commun:.2f} €**.")
    with b2:
        if diff > 0: st.error(f"Elie doit **{abs(diff):.2f}€** à Pierre")
        elif diff < 0: st.error(f"Pierre doit **{abs(diff):.2f}€** à Elie")
        else: st.success("Comptes équilibrés.")

# ==============================================================================
# TAB 2 : SAISIE
# ==============================================================================
with tabs[1]:
    st.header("Nouvelle Opération")
    with st.container():
        c1, c2 = st.columns(2)
        with c1:
            date_op = st.date_input("Date", datetime.today())
            type_op = st.selectbox("Type", TYPES)
            if type_op == "🔄 Virement Interne":
                cat_finale = "Virement"; st.info("ℹ️ Virement neutre.")
            else:
                cats = cats_memoire.get(type_op, ["Autre"])
                cat_sel = st.selectbox("Catégorie", cats)
                cat_finale = st.text_input("Nouvelle catégorie :") if cat_sel == "Autre" else cat_sel
        with c2:
            montant_op = st.number_input("Montant (€)", min_value=0.0, step=1.0)
            compte_source = ""; compte_cible = ""; projet_epargne = ""; paye_par = user_actuel; imput_op = "Perso (Pour moi)"

            if type_op == "🔄 Virement Interne":
                compte_source = st.selectbox("Débit (Source)", comptes_disponibles)
                compte_cible = st.selectbox("Crédit (Cible)", comptes_disponibles)
                paye_par = "Virement"; imput_op = "Neutre"
            elif type_op == "Épargne":
                compte_source = st.selectbox("Depuis quel compte ?", comptes_disponibles)
                compte_cible = st.selectbox("Vers quel compte épargne ?", comptes_disponibles)
                projet_epargne = st.text_input("Projet ?", placeholder="Ex: Vacances")
            else:
                label_compte = "Sur quel compte ?" if type_op == "Revenu" else "Payé avec quel compte ?"
                compte_source = st.selectbox(label_compte, comptes_disponibles)
                paye_par = st.selectbox("Qui a payé ?", ["Pierre", "Elie", "Autre (Commun)"])
                imput_op = st.radio("Pour qui ?", IMPUTATIONS)

        desc_op = st.text_input("Note / Description")
        recurrence = st.checkbox("Récurrence")
        nb_mois = st.slider("Mois", 1, 12, 1) if recurrence else 1
        
        if st.button("💾 Enregistrer (Cloud)", use_container_width=True):
            if not cat_finale: cat_finale = "Autre"
            if type_op != "🔄 Virement Interne" and cat_sel == "Autre" and cat_finale not in cats_memoire.get(type_op, []):
                if type_op not in cats_memoire: cats_memoire[type_op] = []
                cats_memoire[type_op].append(cat_finale)
                save_config_cats(cats_memoire) # Save Cloud
            
            new_rows = []
            for i in range(nb_mois):
                d = date_op + relativedelta(months=i)
                new_rows.append({
                    "Date": d, "Mois": d.month, "Annee": d.year, "Qui_Connecte": user_actuel,
                    "Type": type_op, "Categorie": cat_finale, "Description": desc_op,
                    "Montant": montant_op, "Paye_Par": paye_par, "Imputation": imput_op,
                    "Compte_Cible": compte_cible, "Projet_Epargne": projet_epargne, "Compte_Source": compte_source
                })
            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
            save_data_to_sheet(TAB_DATA, df) # Save Cloud
            st.success("✅ Sauvegardé chez Google !")
            st.rerun()

# ==============================================================================
# TAB 3 : OBJECTIFS
# ==============================================================================
with tabs[2]:
    st.header("🎯 Budgets")
    c_o1, c_o2 = st.columns(2)
    with c_o1:
        with st.form("obj_com"):
            st.subheader("Commun")
            new_obj = objectifs["Commun"].copy()
            for cat in cats_memoire["Dépense"]:
                new_obj[cat] = st.number_input(f"{cat}", value=float(new_obj.get(cat, 0.0)), step=10.0, key=f"c_{cat}")
            if st.form_submit_button("Sauvegarder"):
                objectifs["Commun"] = new_obj
                save_objectifs(objectifs)
                st.rerun()
    with c_o2:
        with st.form("obj_per"):
            st.subheader("Perso")
            new_obj_p = objectifs["Perso"].copy()
            for cat in cats_memoire["Dépense"]:
                new_obj_p[cat] = st.number_input(f"{cat}", value=float(new_obj_p.get(cat, 0.0)), step=10.0, key=f"p_{cat}")
            if st.form_submit_button("Sauvegarder"):
                objectifs["Perso"] = new_obj_p
                save_objectifs(objectifs)
                st.rerun()

# ==============================================================================
# TAB 4 : PATRIMOINE
# ==============================================================================
with tabs[3]:
    st.header("🏦 Comptes")
    with st.expander("➕ Mettre à jour solde", expanded=True):
        with st.form("bq_form"):
            c1, c2 = st.columns(2)
            with c1:
                date_releve = st.date_input("Date", datetime.today())
                compte = st.selectbox("Compte", comptes_disponibles)
            with c2:
                proprio = st.selectbox("Qui ?", ["Moi ("+user_actuel+")", "L'Autre", "Commun"])
                solde = st.number_input("Solde (€)", step=100.0)
            if st.form_submit_button("Valider"):
                new_row = pd.DataFrame([{"Date": date_releve, "Mois": date_releve.month, "Annee": date_releve.year, "Compte": compte, "Montant": solde, "Proprietaire": proprio}])
                df_patrimoine = pd.concat([df_patrimoine, new_row], ignore_index=True)
                save_data_to_sheet(TAB_PATRIMOINE, df_patrimoine)
                st.rerun()
    
    if not df_patrimoine.empty:
        df_sorted = df_patrimoine.sort_values(by="Date", ascending=False).drop_duplicates(subset=["Compte", "Proprietaire"])
        st.divider()
        fig_pat = px.bar(df_sorted, x="Compte", y="Montant", color="Proprietaire", text_auto=True, title="Répartition Globale")
        st.plotly_chart(fig_pat, use_container_width=True)

# ==============================================================================
# TAB 5 : HISTORIQUE
# ==============================================================================
with tabs[4]:
    st.header("📝 Historique")
    if not df.empty:
        df_to_edit = df.copy()
        df_to_edit.insert(0, "Supprimer", False)
        # Convertir date pour éditeur
        if "Date" in df_to_edit.columns: df_to_edit["Date"] = pd.to_datetime(df_to_edit["Date"])
            
        edited_df = st.data_editor(df_to_edit, use_container_width=True, hide_index=True, num_rows="fixed",
            column_config={"Supprimer": st.column_config.CheckboxColumn("🗑️"), "Date": st.column_config.DateColumn("Date")})
        
        if st.button("💾 Valider modifications (Cloud)", type="primary"):
            df_final = edited_df[edited_df["Supprimer"] == False].drop(columns=["Supprimer"])
            save_data_to_sheet(TAB_DATA, df_final)
            st.success("Mis à jour !")
            st.rerun()

# ==============================================================================
# TAB 6 : BILAN ANNUEL
# ==============================================================================
with tabs[5]:
    st.header("📅 Bilan")
    c1, c2 = st.columns(2)
    with c1: annee_bilan = st.selectbox("Année", sorted(df["Annee"].unique(), reverse=True)) if not df.empty else datetime.now().year
    with c2: qui_bilan = st.selectbox("Vue", ["Global (Foyer)", "Pierre", "Elie"])
    
    if not df.empty:
        df_year = df[(df["Annee"] == annee_bilan) & (df["Type"] != "🔄 Virement Interne")]
        if qui_bilan == "Global (Foyer)":
            df_calc = df_year; label = "Foyer"
        else:
            label = qui_bilan
            df_p = df_year[(df_year["Qui_Connecte"] == qui_bilan) & (df_year["Imputation"] == "Perso (Pour moi)")]
            df_c = df_year[df_year["Imputation"] == "Commun (50/50)"].copy(); df_c["Montant"] /= 2
            df_calc = pd.concat([df_p, df_c])

        k1, k2, k3 = st.columns(3)
        if qui_bilan == "Global (Foyer)":
             dep = df_calc[df_calc["Type"]=="Dépense"]["Montant"].sum()
             rev = df_calc[df_calc["Type"]=="Revenu"]["Montant"].sum()
             epg = df_calc[df_calc["Type"]=="Épargne"]["Montant"].sum()
        else:
             dep = df_calc[df_calc["Type"]=="Dépense"]["Montant"].sum()
             rev = df_year[(df_year["Qui_Connecte"]==qui_bilan) & (df_year["Type"]=="Revenu")]["Montant"].sum()
             epg = df_year[(df_year["Qui_Connecte"]==qui_bilan) & (df_year["Type"]=="Épargne")]["Montant"].sum()
             
        k1.metric("Dépenses", f"{dep:,.0f} €"); k2.metric("Revenus", f"{rev:,.0f} €"); k3.metric("Épargne", f"{epg:,.0f} €")
        
        c_g1, c_g2 = st.columns(2)
        with c_g1:
            df_bar = df_calc[df_calc["Type"]=="Dépense"].groupby("Mois")["Montant"].sum().reset_index()
            if not df_bar.empty: st.plotly_chart(px.bar(df_bar, x="Mois", y="Montant", text_auto=True), use_container_width=True)
        with c_g2:
            df_pie = df_calc[df_calc["Type"]=="Dépense"]
            if not df_pie.empty: st.plotly_chart(px.pie(df_pie, values='Montant', names='Categorie', hole=0.4), use_container_width=True)

# ==============================================================================
# TAB 7 : CONFIG COMPTES
# ==============================================================================
with tabs[6]:
    st.header("⚙️ Comptes")
    c1, c2, c3 = st.columns([2,1,1])
    with c1: n = st.text_input("Nom compte")
    with c2: p = st.selectbox("Proprio", ["Pierre", "Elie", "Commun"])
    with c3: 
        st.write(""); st.write("")
        if st.button("Ajouter"):
            if n:
                if p not in comptes_structure: comptes_structure[p] = []
                if n not in comptes_structure[p]:
                    comptes_structure[p].append(n)
                    save_comptes_struct(comptes_structure)
                    st.rerun()
    
    st.divider()
    for prop, lst in comptes_structure.items():
        st.write(f"**{prop}**"); 
        for c in lst:
            cc1, cc2 = st.columns([4,1])
            with cc1: st.text(f"- {c}")
            with cc2: 
                if st.button("🗑️", key=c):
                    comptes_structure[prop].remove(c)
                    save_comptes_struct(comptes_structure)
                    st.rerun()