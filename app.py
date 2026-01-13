<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ma Banque Moderne V2 🏦</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --gradient-success: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            --gradient-info: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            --gradient-warning: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
            --gradient-danger: linear-gradient(135deg, #ff6a00 0%, #ee0979 100%);
            --gradient-dark: linear-gradient(135deg, #2d3436 0%, #000000 100%);
            --gradient-light: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
            --gradient-purple: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
            --gradient-ocean: linear-gradient(135deg, #13547a 0%, #80d0c7 100%);
            --gradient-sunset: linear-gradient(135deg, #f83600 0%, #f9d423 100%);
            --text-dark: #1a1a2e;
            --text-light: #ffffff;
            --bg-dark: #0f0f1e;
            --bg-card: rgba(255, 255, 255, 0.95);
            --shadow-sm: 0 2px 8px rgba(0,0,0,0.08);
            --shadow-md: 0 4px 16px rgba(0,0,0,0.12);
            --shadow-lg: 0 8px 32px rgba(0,0,0,0.16);
            --shadow-xl: 0 16px 48px rgba(0,0,0,0.24);
        }

        body {
            font-family: 'Outfit', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
            background-attachment: fixed;
            color: var(--text-dark);
            line-height: 1.6;
            min-height: 100vh;
            overflow-x: hidden;
        }

        /* Animated background particles */
        .bg-particles {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 0;
            opacity: 0.3;
        }

        .particle {
            position: absolute;
            background: rgba(255, 255, 255, 0.6);
            border-radius: 50%;
            animation: float 20s infinite ease-in-out;
        }

        .particle:nth-child(1) { width: 80px; height: 80px; top: 10%; left: 10%; animation-delay: 0s; }
        .particle:nth-child(2) { width: 60px; height: 60px; top: 60%; left: 80%; animation-delay: 3s; }
        .particle:nth-child(3) { width: 100px; height: 100px; top: 80%; left: 20%; animation-delay: 6s; }
        .particle:nth-child(4) { width: 40px; height: 40px; top: 30%; left: 70%; animation-delay: 9s; }

        @keyframes float {
            0%, 100% { transform: translate(0, 0) scale(1); }
            25% { transform: translate(20px, -30px) scale(1.1); }
            50% { transform: translate(-15px, 20px) scale(0.9); }
            75% { transform: translate(25px, 15px) scale(1.05); }
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            position: relative;
            z-index: 1;
        }

        /* Header */
        header {
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 24px 32px;
            margin-bottom: 32px;
            box-shadow: var(--shadow-lg);
            border: 1px solid rgba(255, 255, 255, 0.3);
            display: flex;
            justify-content: space-between;
            align-items: center;
            animation: slideDown 0.6s ease-out;
        }

        @keyframes slideDown {
            from { transform: translateY(-30px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .logo h1 {
            font-size: 32px;
            font-weight: 800;
            background: linear-gradient(135deg, #fff 0%, #ffecd2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }

        .logo-icon {
            font-size: 48px;
            animation: bounce 2s infinite;
        }

        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }

        .user-section {
            display: flex;
            gap: 16px;
            align-items: center;
        }

        .user-select {
            padding: 12px 24px;
            border-radius: 16px;
            border: 2px solid rgba(255, 255, 255, 0.4);
            background: rgba(255, 255, 255, 0.2);
            color: white;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            font-family: 'Outfit', sans-serif;
        }

        .user-select:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
        }

        .refresh-btn {
            padding: 12px 24px;
            border-radius: 16px;
            border: none;
            background: var(--gradient-info);
            color: white;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: var(--shadow-md);
            font-family: 'Outfit', sans-serif;
        }

        .refresh-btn:hover {
            transform: translateY(-3px) scale(1.05);
            box-shadow: var(--shadow-lg);
        }

        /* Dashboard Cards */
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px;
            margin-bottom: 32px;
            animation: fadeIn 0.8s ease-out;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .stat-card {
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 28px;
            box-shadow: var(--shadow-xl);
            border: 1px solid rgba(255, 255, 255, 0.5);
            position: relative;
            overflow: hidden;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            animation: slideUp 0.6s ease-out backwards;
        }

        .stat-card:nth-child(1) { animation-delay: 0.1s; }
        .stat-card:nth-child(2) { animation-delay: 0.2s; }
        .stat-card:nth-child(3) { animation-delay: 0.3s; }
        .stat-card:nth-child(4) { animation-delay: 0.4s; }

        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: var(--gradient-primary);
            transition: height 0.3s ease;
        }

        .stat-card:hover {
            transform: translateY(-8px) scale(1.02);
            box-shadow: var(--shadow-xl), 0 0 40px rgba(102, 126, 234, 0.3);
        }

        .stat-card:hover::before {
            height: 100%;
            opacity: 0.1;
        }

        .stat-card.revenue::before { background: var(--gradient-success); }
        .stat-card.expense::before { background: var(--gradient-danger); }
        .stat-card.saving::before { background: var(--gradient-info); }
        .stat-card.common::before { background: var(--gradient-warning); }

        .stat-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }

        .stat-label {
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #666;
        }

        .stat-icon {
            font-size: 32px;
            opacity: 0.8;
        }

        .stat-value {
            font-size: 42px;
            font-weight: 800;
            font-family: 'Space Mono', monospace;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }

        .stat-card.revenue .stat-value { background: var(--gradient-success); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .stat-card.expense .stat-value { background: var(--gradient-danger); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .stat-card.saving .stat-value { background: var(--gradient-info); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .stat-card.common .stat-value { background: var(--gradient-warning); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }

        .stat-change {
            font-size: 14px;
            font-weight: 600;
            color: #10b981;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        /* Tabs */
        .tabs-container {
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 12px;
            margin-bottom: 32px;
            display: flex;
            gap: 8px;
            overflow-x: auto;
            box-shadow: var(--shadow-lg);
            border: 1px solid rgba(255, 255, 255, 0.3);
            animation: fadeIn 1s ease-out;
        }

        .tab {
            padding: 14px 28px;
            border-radius: 16px;
            border: none;
            background: transparent;
            color: rgba(255, 255, 255, 0.7);
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            white-space: nowrap;
            font-family: 'Outfit', sans-serif;
        }

        .tab:hover {
            background: rgba(255, 255, 255, 0.1);
            color: white;
        }

        .tab.active {
            background: white;
            color: var(--text-dark);
            box-shadow: var(--shadow-md);
            transform: translateY(-2px);
        }

        /* Content Cards */
        .content-card {
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 32px;
            box-shadow: var(--shadow-xl);
            border: 1px solid rgba(255, 255, 255, 0.5);
            margin-bottom: 24px;
            animation: fadeIn 0.6s ease-out;
        }

        .content-card h2 {
            font-size: 28px;
            font-weight: 800;
            margin-bottom: 24px;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        /* Form Inputs */
        .form-group {
            margin-bottom: 24px;
        }

        .form-label {
            display: block;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 8px;
            color: #333;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .form-input,
        .form-select,
        .form-textarea {
            width: 100%;
            padding: 16px 20px;
            border-radius: 16px;
            border: 2px solid #e0e0e0;
            background: white;
            font-size: 16px;
            font-family: 'Outfit', sans-serif;
            transition: all 0.3s ease;
            color: var(--text-dark);
        }

        .form-input:focus,
        .form-select:focus,
        .form-textarea:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
            transform: translateY(-2px);
        }

        .form-textarea {
            resize: vertical;
            min-height: 100px;
        }

        .form-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 24px;
        }

        /* Buttons */
        .btn {
            padding: 16px 32px;
            border-radius: 16px;
            border: none;
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            box-shadow: var(--shadow-md);
            font-family: 'Outfit', sans-serif;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .btn-primary {
            background: var(--gradient-primary);
            color: white;
        }

        .btn-success {
            background: var(--gradient-success);
            color: white;
        }

        .btn-info {
            background: var(--gradient-info);
            color: white;
        }

        .btn-warning {
            background: var(--gradient-warning);
            color: white;
        }

        .btn:hover {
            transform: translateY(-4px) scale(1.05);
            box-shadow: var(--shadow-xl);
        }

        .btn:active {
            transform: translateY(-2px) scale(1.02);
        }

        .btn-full {
            width: 100%;
            margin-top: 16px;
        }

        /* Account Cards */
        .accounts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 24px;
        }

        .account-card {
            background: white;
            border-radius: 24px;
            padding: 28px;
            box-shadow: var(--shadow-lg);
            position: relative;
            overflow: hidden;
            transition: all 0.3s ease;
            border: 2px solid transparent;
        }

        .account-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: var(--gradient-primary);
            opacity: 0.05;
            transition: opacity 0.3s ease;
        }

        .account-card:hover {
            transform: translateY(-6px);
            border-color: #667eea;
            box-shadow: var(--shadow-xl), 0 0 40px rgba(102, 126, 234, 0.2);
        }

        .account-card:hover::before {
            opacity: 0.1;
        }

        .account-name {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 16px;
            color: #333;
        }

        .account-balance {
            font-size: 36px;
            font-weight: 800;
            font-family: 'Space Mono', monospace;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .account-balance.positive { background: var(--gradient-success); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .account-balance.negative { background: var(--gradient-danger); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }

        /* Charts */
        .chart-container {
            background: white;
            border-radius: 24px;
            padding: 28px;
            box-shadow: var(--shadow-lg);
            margin-bottom: 24px;
            height: 400px;
            position: relative;
        }

        /* Table */
        .data-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0 12px;
        }

        .data-table thead th {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 16px;
            text-align: left;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 13px;
        }

        .data-table thead th:first-child {
            border-radius: 12px 0 0 12px;
        }

        .data-table thead th:last-child {
            border-radius: 0 12px 12px 0;
        }

        .data-table tbody tr {
            background: white;
            box-shadow: var(--shadow-sm);
            transition: all 0.3s ease;
        }

        .data-table tbody tr:hover {
            transform: translateX(8px);
            box-shadow: var(--shadow-md);
        }

        .data-table tbody td {
            padding: 18px 16px;
            border-top: 1px solid #f0f0f0;
            border-bottom: 1px solid #f0f0f0;
        }

        .data-table tbody td:first-child {
            border-left: 1px solid #f0f0f0;
            border-radius: 12px 0 0 12px;
        }

        .data-table tbody td:last-child {
            border-right: 1px solid #f0f0f0;
            border-radius: 0 12px 12px 0;
        }

        /* Progress Bar */
        .progress-bar {
            height: 12px;
            background: #e0e0e0;
            border-radius: 12px;
            overflow: hidden;
            margin: 12px 0;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
        }

        .progress-fill {
            height: 100%;
            background: var(--gradient-success);
            border-radius: 12px;
            transition: width 1s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
        }

        /* Badge */
        .badge {
            display: inline-block;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .badge-success {
            background: var(--gradient-success);
            color: white;
        }

        .badge-danger {
            background: var(--gradient-danger);
            color: white;
        }

        .badge-info {
            background: var(--gradient-info);
            color: white;
        }

        .badge-warning {
            background: var(--gradient-warning);
            color: white;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .container {
                padding: 12px;
            }

            header {
                flex-direction: column;
                gap: 16px;
                padding: 20px;
            }

            .dashboard-grid {
                grid-template-columns: 1fr;
            }

            .stat-value {
                font-size: 32px;
            }

            .tabs-container {
                flex-wrap: nowrap;
                overflow-x: scroll;
            }

            .form-grid {
                grid-template-columns: 1fr;
            }
        }

        /* Hide inactive tabs */
        .tab-content {
            display: none;
            animation: fadeIn 0.4s ease-out;
        }

        .tab-content.active {
            display: block;
        }

        /* Info Alert */
        .alert {
            padding: 20px 24px;
            border-radius: 16px;
            margin-bottom: 24px;
            border-left: 4px solid;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 12px;
            animation: slideInLeft 0.5s ease-out;
        }

        @keyframes slideInLeft {
            from { opacity: 0; transform: translateX(-30px); }
            to { opacity: 1; transform: translateX(0); }
        }

        .alert-info {
            background: linear-gradient(135deg, rgba(79, 172, 254, 0.1) 0%, rgba(0, 242, 254, 0.1) 100%);
            border-left-color: #4facfe;
            color: #0369a1;
        }

        .alert-success {
            background: linear-gradient(135deg, rgba(240, 147, 251, 0.1) 0%, rgba(245, 87, 108, 0.1) 100%);
            border-left-color: #f093fb;
            color: #be185d;
        }

        /* Loading animation */
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 1s ease-in-out infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Floating action button */
        .fab {
            position: fixed;
            bottom: 32px;
            right: 32px;
            width: 64px;
            height: 64px;
            border-radius: 50%;
            background: var(--gradient-primary);
            color: white;
            border: none;
            font-size: 28px;
            cursor: pointer;
            box-shadow: var(--shadow-xl);
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            z-index: 1000;
        }

        .fab:hover {
            transform: scale(1.15) rotate(90deg);
            box-shadow: 0 8px 32px rgba(102, 126, 234, 0.5);
        }

        /* Month selector */
        .month-selector {
            display: flex;
            gap: 12px;
            align-items: center;
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(20px);
            border-radius: 20px;
            padding: 8px 16px;
            margin-bottom: 24px;
            border: 1px solid rgba(255, 255, 255, 0.3);
        }

        .month-btn {
            background: rgba(255, 255, 255, 0.2);
            border: none;
            color: white;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 18px;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .month-btn:hover {
            background: rgba(255, 255, 255, 0.4);
            transform: scale(1.1);
        }

        .month-display {
            font-size: 18px;
            font-weight: 700;
            color: white;
            min-width: 150px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="bg-particles">
        <div class="particle"></div>
        <div class="particle"></div>
        <div class="particle"></div>
        <div class="particle"></div>
    </div>

    <div class="container">
        <header>
            <div class="logo">
                <span class="logo-icon">🏦</span>
                <h1>Ma Banque Moderne</h1>
            </div>
            <div class="user-section">
                <select class="user-select" id="userSelect">
                    <option value="Pierre">Pierre</option>
                    <option value="Elie">Elie</option>
                </select>
                <button class="refresh-btn" onclick="refreshData()">🔄 Actualiser</button>
            </div>
        </header>

        <!-- Month Selector -->
        <div class="month-selector">
            <button class="month-btn" onclick="changeMonth(-1)">←</button>
            <span class="month-display" id="monthDisplay">Janvier 2025</span>
            <button class="month-btn" onclick="changeMonth(1)">→</button>
        </div>

        <!-- Dashboard Cards -->
        <div class="dashboard-grid">
            <div class="stat-card revenue">
                <div class="stat-header">
                    <span class="stat-label">Revenus</span>
                    <span class="stat-icon">💰</span>
                </div>
                <div class="stat-value" id="revenueValue">3 245 €</div>
                <div class="stat-change">↗ +12% vs mois dernier</div>
            </div>

            <div class="stat-card expense">
                <div class="stat-header">
                    <span class="stat-label">Dépenses Perso</span>
                    <span class="stat-icon">💸</span>
                </div>
                <div class="stat-value" id="expenseValue">1 856 €</div>
                <div class="stat-change" style="color: #ef4444;">↗ +5% vs mois dernier</div>
            </div>

            <div class="stat-card common">
                <div class="stat-header">
                    <span class="stat-label">Part Commun</span>
                    <span class="stat-icon">🏠</span>
                </div>
                <div class="stat-value" id="commonValue">782 €</div>
                <div class="stat-change">↘ -3% vs mois dernier</div>
            </div>

            <div class="stat-card saving">
                <div class="stat-header">
                    <span class="stat-label">Épargne</span>
                    <span class="stat-icon">📈</span>
                </div>
                <div class="stat-value" id="savingValue">450 €</div>
                <div class="stat-change">↗ +25% vs mois dernier</div>
            </div>
        </div>

        <!-- Tabs -->
        <div class="tabs-container">
            <button class="tab active" onclick="switchTab('dashboard')">📊 Tableau de Bord</button>
            <button class="tab" onclick="switchTab('add')">➕ Saisir</button>
            <button class="tab" onclick="switchTab('accounts')">💳 Mes Comptes</button>
            <button class="tab" onclick="switchTab('analysis')">📈 Analyse</button>
            <button class="tab" onclick="switchTab('budget')">🎯 Budget</button>
            <button class="tab" onclick="switchTab('subscriptions')">🔄 Abonnements</button>
            <button class="tab" onclick="switchTab('history')">📜 Historique</button>
            <button class="tab" onclick="switchTab('projects')">🎁 Projets</button>
            <button class="tab" onclick="switchTab('settings')">⚙️ Paramètres</button>
        </div>

        <!-- Dashboard Tab -->
        <div id="dashboard" class="tab-content active">
            <div class="content-card">
                <h2>📊 Vue d'Ensemble</h2>
                <div class="chart-container">
                    <canvas id="overviewChart"></canvas>
                </div>
            </div>

            <div class="content-card">
                <h2>🔥 Top Dépenses du Mois</h2>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Catégorie</th>
                            <th>Montant</th>
                            <th>% Budget</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>🍔 Alimentation</td>
                            <td><strong>456 €</strong></td>
                            <td>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: 76%;"></div>
                                </div>
                            </td>
                            <td><span class="badge badge-success">OK</span></td>
                        </tr>
                        <tr>
                            <td>🏠 Loyer</td>
                            <td><strong>850 €</strong></td>
                            <td>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: 100%;"></div>
                                </div>
                            </td>
                            <td><span class="badge badge-info">Fixe</span></td>
                        </tr>
                        <tr>
                            <td>🎬 Loisirs</td>
                            <td><strong>234 €</strong></td>
                            <td>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: 117%; background: var(--gradient-danger);"></div>
                                </div>
                            </td>
                            <td><span class="badge badge-danger">Dépassé</span></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Add Transaction Tab -->
        <div id="add" class="tab-content">
            <div class="content-card">
                <h2>➕ Nouvelle Opération</h2>
                <div class="alert alert-info">
                    💡 Remplissez les informations ci-dessous pour enregistrer une nouvelle transaction
                </div>

                <form id="transactionForm">
                    <div class="form-grid">
                        <div class="form-group">
                            <label class="form-label">📅 Date</label>
                            <input type="date" class="form-input" id="dateInput" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">🏷️ Type</label>
                            <select class="form-select" id="typeSelect" required>
                                <option value="">Sélectionner...</option>
                                <option value="Dépense">💸 Dépense</option>
                                <option value="Revenu">💰 Revenu</option>
                                <option value="Virement Interne">🔄 Virement Interne</option>
                                <option value="Épargne">📈 Épargne</option>
                                <option value="Investissement">📊 Investissement</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">💶 Montant</label>
                            <input type="number" class="form-input" id="amountInput" step="0.01" min="0" placeholder="0.00 €" required>
                        </div>
                    </div>

                    <div class="form-grid">
                        <div class="form-group">
                            <label class="form-label">✏️ Titre</label>
                            <input type="text" class="form-input" id="titleInput" placeholder="Ex: Courses Leclerc" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">📂 Catégorie</label>
                            <select class="form-select" id="categorySelect" required>
                                <option value="">Sélectionner...</option>
                                <option value="Alimentation">🍔 Alimentation</option>
                                <option value="Loyer">🏠 Loyer</option>
                                <option value="Transport">🚗 Transport</option>
                                <option value="Santé">⚕️ Santé</option>
                                <option value="Loisirs">🎬 Loisirs</option>
                                <option value="Autre">📦 Autre</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">💳 Compte</label>
                            <select class="form-select" id="accountSelect" required>
                                <option value="">Sélectionner...</option>
                                <option value="Compte Courant Pierre">💳 Compte Courant Pierre</option>
                                <option value="Compte Courant Elie">💳 Compte Courant Elie</option>
                                <option value="Compte Joint">🏦 Compte Joint</option>
                            </select>
                        </div>
                    </div>

                    <div class="form-group">
                        <label class="form-label">📝 Description</label>
                        <textarea class="form-textarea" id="descriptionInput" placeholder="Ajoutez des détails optionnels..."></textarea>
                    </div>

                    <button type="submit" class="btn btn-primary btn-full">✅ Enregistrer l'opération</button>
                </form>
            </div>
        </div>

        <!-- Accounts Tab -->
        <div id="accounts" class="tab-content">
            <div class="content-card">
                <h2>💳 Mes Comptes</h2>
                <div class="accounts-grid">
                    <div class="account-card">
                        <div class="account-name">💳 Compte Courant Pierre</div>
                        <div class="account-balance positive">2 456,78 €</div>
                        <div class="progress-bar" style="margin-top: 16px;">
                            <div class="progress-fill" style="width: 85%;"></div>
                        </div>
                        <p style="margin-top: 8px; font-size: 14px; color: #666;">Solde confortable</p>
                    </div>

                    <div class="account-card">
                        <div class="account-name">💳 Compte Courant Elie</div>
                        <div class="account-balance positive">1 823,45 €</div>
                        <div class="progress-bar" style="margin-top: 16px;">
                            <div class="progress-fill" style="width: 65%;"></div>
                        </div>
                        <p style="margin-top: 8px; font-size: 14px; color: #666;">Bon état</p>
                    </div>

                    <div class="account-card">
                        <div class="account-name">🏦 Compte Joint</div>
                        <div class="account-balance positive">4 567,90 €</div>
                        <div class="progress-bar" style="margin-top: 16px;">
                            <div class="progress-fill" style="width: 92%;"></div>
                        </div>
                        <p style="margin-top: 8px; font-size: 14px; color: #666;">Excellent</p>
                    </div>

                    <div class="account-card">
                        <div class="account-name">📈 Livret A</div>
                        <div class="account-balance positive">12 345,67 €</div>
                        <div class="progress-bar" style="margin-top: 16px;">
                            <div class="progress-fill" style="width: 100%; background: var(--gradient-info);"></div>
                        </div>
                        <p style="margin-top: 8px; font-size: 14px; color: #666;">Épargne de sécurité</p>
                    </div>
                </div>
            </div>

            <div class="content-card">
                <h2>📝 Faire un Relevé Bancaire</h2>
                <div class="alert alert-info">
                    💡 Utilisez cette fonctionnalité pour recaler vos soldes avec la réalité de votre banque
                </div>
                <form class="form-grid">
                    <div class="form-group">
                        <label class="form-label">📅 Date</label>
                        <input type="date" class="form-input">
                    </div>
                    <div class="form-group">
                        <label class="form-label">💳 Compte</label>
                        <select class="form-select">
                            <option>Compte Courant Pierre</option>
                            <option>Compte Courant Elie</option>
                            <option>Compte Joint</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">💶 Solde Réel</label>
                        <input type="number" class="form-input" step="0.01" placeholder="0.00 €">
                    </div>
                    <div class="form-group" style="display: flex; align-items: flex-end;">
                        <button type="submit" class="btn btn-success" style="width: 100%;">✅ Valider le Relevé</button>
                    </div>
                </form>
            </div>
        </div>

        <!-- Analysis Tab -->
        <div id="analysis" class="tab-content">
            <div class="content-card">
                <h2>📈 Analyse des Flux</h2>
                <div class="chart-container" style="height: 500px;">
                    <canvas id="flowChart"></canvas>
                </div>
            </div>

            <div class="content-card">
                <h2>📊 Répartition par Catégorie</h2>
                <div class="chart-container">
                    <canvas id="categoryChart"></canvas>
                </div>
            </div>
        </div>

        <!-- Budget Tab -->
        <div id="budget" class="tab-content">
            <div class="content-card">
                <h2>🎯 Budget Mensuel</h2>
                
                <h3 style="margin-top: 32px; margin-bottom: 16px; color: #667eea;">🏠 Dépenses Communes</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Catégorie</th>
                            <th>Budget</th>
                            <th>Réel</th>
                            <th>Reste</th>
                            <th>Progression</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>🏠 Loyer</td>
                            <td>850 €</td>
                            <td>850 €</td>
                            <td style="color: #10b981;">0 €</td>
                            <td>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: 100%;"></div>
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td>⚡ Énergie</td>
                            <td>150 €</td>
                            <td>132 €</td>
                            <td style="color: #10b981;">18 €</td>
                            <td>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: 88%;"></div>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>

                <h3 style="margin-top: 32px; margin-bottom: 16px; color: #f093fb;">👤 Dépenses Personnelles</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Catégorie</th>
                            <th>Budget</th>
                            <th>Réel</th>
                            <th>Reste</th>
                            <th>Progression</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>🍔 Alimentation</td>
                            <td>400 €</td>
                            <td>456 €</td>
                            <td style="color: #ef4444;">-56 €</td>
                            <td>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: 114%; background: var(--gradient-danger);"></div>
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td>🚗 Transport</td>
                            <td>200 €</td>
                            <td>145 €</td>
                            <td style="color: #10b981;">55 €</td>
                            <td>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: 73%;"></div>
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td>🎬 Loisirs</td>
                            <td>200 €</td>
                            <td>234 €</td>
                            <td style="color: #ef4444;">-34 €</td>
                            <td>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: 117%; background: var(--gradient-danger);"></div>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Subscriptions Tab -->
        <div id="subscriptions" class="tab-content">
            <div class="content-card">
                <h2>🔄 Mes Abonnements</h2>
                <div class="alert alert-success">
                    💡 Total mensuel : <strong>89,97 €</strong>
                </div>

                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Service</th>
                            <th>Montant</th>
                            <th>Prochaine</th>
                            <th>Compte</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>🎵 Spotify Premium</td>
                            <td><strong>9,99 €</strong></td>
                            <td>15 Jan 2025</td>
                            <td>Compte Pierre</td>
                            <td><button class="btn btn-info" style="padding: 8px 16px; font-size: 13px;">Modifier</button></td>
                        </tr>
                        <tr>
                            <td>🎬 Netflix</td>
                            <td><strong>15,99 €</strong></td>
                            <td>20 Jan 2025</td>
                            <td>Compte Joint</td>
                            <td><button class="btn btn-info" style="padding: 8px 16px; font-size: 13px;">Modifier</button></td>
                        </tr>
                        <tr>
                            <td>☁️ iCloud</td>
                            <td><strong>2,99 €</strong></td>
                            <td>08 Jan 2025</td>
                            <td>Compte Pierre</td>
                            <td><button class="btn btn-info" style="padding: 8px 16px; font-size: 13px;">Modifier</button></td>
                        </tr>
                    </tbody>
                </table>

                <button class="btn btn-primary btn-full" style="margin-top: 24px;">➕ Ajouter un Abonnement</button>
            </div>
        </div>

        <!-- History Tab -->
        <div id="history" class="tab-content">
            <div class="content-card">
                <h2>📜 Historique des Transactions</h2>
                <div style="margin-bottom: 24px; display: flex; gap: 16px;">
                    <input type="text" class="form-input" placeholder="🔍 Rechercher..." style="flex: 1;">
                    <select class="form-select" style="max-width: 200px;">
                        <option>Tous les types</option>
                        <option>Dépenses</option>
                        <option>Revenus</option>
                        <option>Épargne</option>
                    </select>
                </div>

                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Titre</th>
                            <th>Catégorie</th>
                            <th>Montant</th>
                            <th>Type</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>12/01/2025</td>
                            <td>Courses Leclerc</td>
                            <td>🍔 Alimentation</td>
                            <td><strong style="color: #ef4444;">-78,50 €</strong></td>
                            <td><span class="badge badge-danger">Dépense</span></td>
                        </tr>
                        <tr>
                            <td>10/01/2025</td>
                            <td>Salaire</td>
                            <td>💰 Salaire</td>
                            <td><strong style="color: #10b981;">+2 800,00 €</strong></td>
                            <td><span class="badge badge-success">Revenu</span></td>
                        </tr>
                        <tr>
                            <td>08/01/2025</td>
                            <td>Plein d'essence</td>
                            <td>🚗 Transport</td>
                            <td><strong style="color: #ef4444;">-65,00 €</strong></td>
                            <td><span class="badge badge-danger">Dépense</span></td>
                        </tr>
                        <tr>
                            <td>05/01/2025</td>
                            <td>Virement Livret A</td>
                            <td>📈 Épargne</td>
                            <td><strong style="color: #3b82f6;">450,00 €</strong></td>
                            <td><span class="badge badge-info">Épargne</span></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Projects Tab -->
        <div id="projects" class="tab-content">
            <div class="content-card">
                <h2>🎁 Mes Projets d'Épargne</h2>
                
                <div class="accounts-grid">
                    <div class="account-card">
                        <div class="account-name">🏖️ Vacances 2025</div>
                        <div class="account-balance positive">1 245 €</div>
                        <div style="margin-top: 16px; font-size: 14px; color: #666;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                                <span>Objectif: 3 000 €</span>
                                <span>42%</span>
                            </div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: 42%;"></div>
                            </div>
                        </div>
                    </div>

                    <div class="account-card">
                        <div class="account-name">🚗 Nouvelle Voiture</div>
                        <div class="account-balance positive">5 678 €</div>
                        <div style="margin-top: 16px; font-size: 14px; color: #666;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                                <span>Objectif: 15 000 €</span>
                                <span>38%</span>
                            </div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: 38%;"></div>
                            </div>
                        </div>
                    </div>

                    <div class="account-card">
                        <div class="account-name">🎓 Formation</div>
                        <div class="account-balance positive">890 €</div>
                        <div style="margin-top: 16px; font-size: 14px; color: #666;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                                <span>Objectif: 1 200 €</span>
                                <span>74%</span>
                            </div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: 74%;"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <button class="btn btn-primary btn-full" style="margin-top: 24px;">➕ Créer un Nouveau Projet</button>
            </div>
        </div>

        <!-- Settings Tab -->
        <div id="settings" class="tab-content">
            <div class="content-card">
                <h2>⚙️ Paramètres</h2>
                
                <h3 style="margin-bottom: 16px;">📂 Catégories</h3>
                <div class="form-grid">
                    <div class="form-group">
                        <label class="form-label">Type</label>
                        <select class="form-select">
                            <option>Dépense</option>
                            <option>Revenu</option>
                            <option>Épargne</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Nouvelle Catégorie</label>
                        <input type="text" class="form-input" placeholder="Ex: Cadeaux">
                    </div>
                    <div class="form-group" style="display: flex; align-items: flex-end;">
                        <button class="btn btn-primary" style="width: 100%;">➕ Ajouter</button>
                    </div>
                </div>

                <h3 style="margin-top: 32px; margin-bottom: 16px;">💳 Comptes</h3>
                <div class="form-grid">
                    <div class="form-group">
                        <label class="form-label">Propriétaire</label>
                        <select class="form-select">
                            <option>Pierre</option>
                            <option>Elie</option>
                            <option>Commun</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Nom du Compte</label>
                        <input type="text" class="form-input" placeholder="Ex: Livret Jeune">
                    </div>
                    <div class="form-group" style="display: flex; align-items: flex-end;">
                        <button class="btn btn-primary" style="width: 100%;">➕ Ajouter</button>
                    </div>
                </div>

                <h3 style="margin-top: 32px; margin-bottom: 16px;">🎯 Objectifs Budget</h3>
                <div class="form-grid">
                    <div class="form-group">
                        <label class="form-label">Scope</label>
                        <select class="form-select">
                            <option>Perso</option>
                            <option>Commun</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Catégorie</label>
                        <select class="form-select">
                            <option>Alimentation</option>
                            <option>Transport</option>
                            <option>Loisirs</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Montant</label>
                        <input type="number" class="form-input" placeholder="0.00 €">
                    </div>
                    <div class="form-group" style="display: flex; align-items: flex-end;">
                        <button class="btn btn-primary" style="width: 100%;">💾 Enregistrer</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Floating Action Button -->
    <button class="fab" onclick="switchTab('add')" title="Nouvelle transaction">+</button>

    <script>
        // Initialize date input with today's date
        document.getElementById('dateInput').valueAsDate = new Date();

        // Tab switching
        function switchTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Remove active class from all tab buttons
            document.querySelectorAll('.tab').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(tabName).classList.add('active');
            
            // Add active class to clicked button
            event.target.classList.add('active');
        }

        // Month navigation
        let currentMonth = 0; // January
        let currentYear = 2025;
        const months = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'];

        function changeMonth(delta) {
            currentMonth += delta;
            if (currentMonth > 11) {
                currentMonth = 0;
                currentYear++;
            } else if (currentMonth < 0) {
                currentMonth = 11;
                currentYear--;
            }
            document.getElementById('monthDisplay').textContent = `${months[currentMonth]} ${currentYear}`;
        }

        // Refresh data
        function refreshData() {
            const btn = event.target;
            btn.innerHTML = '<span class="loading"></span>';
            setTimeout(() => {
                btn.innerHTML = '🔄 Actualiser';
                alert('Données actualisées !');
            }, 1000);
        }

        // Form submission
        document.getElementById('transactionForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Get form values
            const date = document.getElementById('dateInput').value;
            const type = document.getElementById('typeSelect').value;
            const amount = document.getElementById('amountInput').value;
            const title = document.getElementById('titleInput').value;
            const category = document.getElementById('categorySelect').value;
            const account = document.getElementById('accountSelect').value;
            
            // Show success message
            alert(`✅ Transaction enregistrée avec succès!\n\nDate: ${date}\nType: ${type}\nMontant: ${amount}€\nTitre: ${title}`);
            
            // Reset form
            this.reset();
            document.getElementById('dateInput').valueAsDate = new Date();
            
            // Switch to dashboard
            switchTab('dashboard');
        });

        // Initialize Charts
        window.onload = function() {
            // Overview Chart (Bar)
            const overviewCtx = document.getElementById('overviewChart').getContext('2d');
            new Chart(overviewCtx, {
                type: 'bar',
                data: {
                    labels: ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin'],
                    datasets: [{
                        label: 'Revenus',
                        data: [3200, 3245, 3180, 3300, 3245, 3200],
                        backgroundColor: 'rgba(102, 126, 234, 0.8)',
                        borderRadius: 8
                    }, {
                        label: 'Dépenses',
                        data: [2800, 2650, 2900, 2750, 2856, 2800],
                        backgroundColor: 'rgba(245, 87, 108, 0.8)',
                        borderRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: {
                                font: { size: 14, weight: '600' },
                                padding: 20
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(0,0,0,0.05)' }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            });

            // Category Chart (Doughnut)
            const categoryCtx = document.getElementById('categoryChart').getContext('2d');
            new Chart(categoryCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Alimentation', 'Loyer', 'Transport', 'Loisirs', 'Santé', 'Autre'],
                    datasets: [{
                        data: [456, 850, 145, 234, 89, 123],
                        backgroundColor: [
                            'rgba(102, 126, 234, 0.8)',
                            'rgba(118, 75, 162, 0.8)',
                            'rgba(240, 147, 251, 0.8)',
                            'rgba(245, 87, 108, 0.8)',
                            'rgba(79, 172, 254, 0.8)',
                            'rgba(254, 215, 226, 0.8)'
                        ],
                        borderWidth: 4,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'right',
                            labels: {
                                font: { size: 14, weight: '600' },
                                padding: 16
                            }
                        }
                    }
                }
            });

            // Flow Chart (Line)
            const flowCtx = document.getElementById('flowChart').getContext('2d');
            new Chart(flowCtx, {
                type: 'line',
                data: {
                    labels: ['Sem 1', 'Sem 2', 'Sem 3', 'Sem 4'],
                    datasets: [{
                        label: 'Entrées',
                        data: [800, 2400, 200, 845],
                        borderColor: 'rgba(102, 126, 234, 1)',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.4,
                        fill: true,
                        borderWidth: 3
                    }, {
                        label: 'Sorties',
                        data: [650, 780, 920, 506],
                        borderColor: 'rgba(245, 87, 108, 1)',
                        backgroundColor: 'rgba(245, 87, 108, 0.1)',
                        tension: 0.4,
                        fill: true,
                        borderWidth: 3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: {
                                font: { size: 14, weight: '600' },
                                padding: 20
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(0,0,0,0.05)' }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            });
        };
    </script>
</body>
</html>
