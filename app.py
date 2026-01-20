-- ============================================================================
-- SCRIPTS SQL POUR CRÉER LES TABLES MANQUANTES DANS SUPABASE
-- À exécuter dans le SQL Editor de Supabase
-- ============================================================================

-- 1. Table objectifs (pour les budgets)
CREATE TABLE IF NOT EXISTS objectifs (
    id BIGSERIAL PRIMARY KEY,
    scope TEXT NOT NULL,
    categorie TEXT NOT NULL,
    montant DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. Table abonnements
CREATE TABLE IF NOT EXISTS abonnements (
    id BIGSERIAL PRIMARY KEY,
    nom TEXT NOT NULL,
    montant DECIMAL(10,2) NOT NULL,
    jour INTEGER NOT NULL,
    categorie TEXT NOT NULL,
    compte_source TEXT NOT NULL,
    proprietaire TEXT NOT NULL,
    imputation TEXT NOT NULL,
    frequence TEXT DEFAULT 'Mensuel',
    date_debut DATE,
    date_fin DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 3. Table mots_cles (pour l'automatisation)
CREATE TABLE IF NOT EXISTS mots_cles (
    id BIGSERIAL PRIMARY KEY,
    mot_cle TEXT NOT NULL UNIQUE,
    categorie TEXT NOT NULL,
    type TEXT NOT NULL,
    compte TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 4. Table remboursements
CREATE TABLE IF NOT EXISTS remboursements (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    de TEXT NOT NULL,
    a TEXT NOT NULL,
    montant DECIMAL(10,2) NOT NULL,
    motif TEXT,
    statut TEXT DEFAULT 'Payé',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 5. Table credits
CREATE TABLE IF NOT EXISTS credits (
    id BIGSERIAL PRIMARY KEY,
    nom TEXT NOT NULL,
    montant_initial DECIMAL(12,2) NOT NULL,
    montant_restant DECIMAL(12,2) NOT NULL,
    taux DECIMAL(5,2) NOT NULL,
    mensualite DECIMAL(10,2) NOT NULL,
    date_debut DATE NOT NULL,
    date_fin DATE NOT NULL,
    organisme TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 6. Modifier la table transactions pour ajouter les colonnes manquantes
ALTER TABLE transactions 
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS paye_par TEXT,
ADD COLUMN IF NOT EXISTS projet_epargne TEXT;

-- 7. Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(qui_connecte);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
CREATE INDEX IF NOT EXISTS idx_patrimoine_compte ON patrimoine(compte);
CREATE INDEX IF NOT EXISTS idx_abonnements_proprietaire ON abonnements(proprietaire);

-- 8. Activer Row Level Security (RLS) - Optionnel mais recommandé
ALTER TABLE objectifs ENABLE ROW LEVEL SECURITY;
ALTER TABLE abonnements ENABLE ROW LEVEL SECURITY;
ALTER TABLE mots_cles ENABLE ROW LEVEL SECURITY;
ALTER TABLE remboursements ENABLE ROW LEVEL SECURITY;
ALTER TABLE credits ENABLE ROW LEVEL SECURITY;

-- 9. Politiques RLS simples (autoriser tout pour l'instant)
CREATE POLICY "Allow all for objectifs" ON objectifs FOR ALL USING (true);
CREATE POLICY "Allow all for abonnements" ON abonnements FOR ALL USING (true);
CREATE POLICY "Allow all for mots_cles" ON mots_cles FOR ALL USING (true);
CREATE POLICY "Allow all for remboursements" ON remboursements FOR ALL USING (true);
CREATE POLICY "Allow all for credits" ON credits FOR ALL USING (true);

-- 10. Vue pour faciliter les requêtes
CREATE OR REPLACE VIEW v_transactions_enrichies AS
SELECT 
    t.*,
    c.type as type_compte,
    CASE 
        WHEN t.type = 'Dépense' THEN -t.montant
        WHEN t.type = 'Revenu' THEN t.montant
        ELSE 0
    END as impact_solde
FROM transactions t
LEFT JOIN comptes c ON t.compte_source = c.compte;

-- ============================================================================
-- DONNÉES DE DÉMONSTRATION (optionnel)
-- ============================================================================

-- Catégories par défaut pour Dépense
INSERT INTO categories (type, categorie) VALUES
('Dépense', 'Alimentation'),
('Dépense', 'Transport'),
('Dépense', 'Logement'),
('Dépense', 'Santé'),
('Dépense', 'Loisirs'),
('Dépense', 'Shopping'),
('Dépense', 'Autre')
ON CONFLICT DO NOTHING;

-- Catégories par défaut pour Revenu
INSERT INTO categories (type, categorie) VALUES
('Revenu', 'Salaire'),
('Revenu', 'Prime'),
('Revenu', 'Freelance'),
('Revenu', 'Autre')
ON CONFLICT DO NOTHING;

-- Catégories par défaut pour Épargne
INSERT INTO categories (type, categorie) VALUES
('Épargne', 'Épargne Mensuelle'),
('Épargne', 'Épargne Projet'),
('Épargne', 'Autre')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- FONCTIONS UTILITAIRES
-- ============================================================================

-- Fonction pour calculer le solde d'un compte
CREATE OR REPLACE FUNCTION calcul_solde_compte(nom_compte TEXT)
RETURNS DECIMAL AS $$
DECLARE
    solde DECIMAL := 0;
    dernier_ajustement DECIMAL := 0;
    date_ajustement DATE := '2000-01-01';
BEGIN
    -- Récupérer le dernier ajustement
    SELECT montant, date INTO dernier_ajustement, date_ajustement
    FROM patrimoine
    WHERE compte = nom_compte
    ORDER BY date DESC
    LIMIT 1;
    
    -- Calculer les mouvements depuis l'ajustement
    SELECT 
        COALESCE(dernier_ajustement, 0) +
        COALESCE(SUM(CASE 
            WHEN type = 'Revenu' AND compte_source = nom_compte THEN montant
            WHEN compte_cible = nom_compte AND type IN ('Virement Interne', 'Épargne') THEN montant
            WHEN compte_source = nom_compte AND type IN ('Dépense', 'Investissement', 'Virement Interne', 'Épargne') THEN -montant
            ELSE 0
        END), 0)
    INTO solde
    FROM transactions
    WHERE (compte_source = nom_compte OR compte_cible = nom_compte)
    AND date > COALESCE(date_ajustement, '2000-01-01');
    
    RETURN solde;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGERS POUR AUTOMATISATION
-- ============================================================================

-- Trigger pour mettre à jour automatiquement mois et annee
CREATE OR REPLACE FUNCTION update_date_fields()
RETURNS TRIGGER AS $$
BEGIN
    NEW.mois := EXTRACT(MONTH FROM NEW.date);
    NEW.annee := EXTRACT(YEAR FROM NEW.date);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_transactions_date
BEFORE INSERT OR UPDATE ON transactions
FOR EACH ROW
EXECUTE FUNCTION update_date_fields();

CREATE TRIGGER trg_patrimoine_date
BEFORE INSERT OR UPDATE ON patrimoine
FOR EACH ROW
EXECUTE FUNCTION update_date_fields();
