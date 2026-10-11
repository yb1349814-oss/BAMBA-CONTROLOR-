# BAMBA-CONTROLOR-
Contrôleur de WIFI
import androidhelper
import webbrowser
import os

# Vos lignes de code corrigées :
line62 = """<div class="flex items-center space-x-1">"""
line63 = """<h1 class="text-2xl font-bold text-slate-800">Vue d'ensemble</h1>"""

# Le reste de votre code HTML (que je ne vois pas) doit être assemblé ici
html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>BAMBA CONTROLOR</title>
</head>
<body>
    {line62}
    {line63}
    <!-- Ajoutez le reste de votre code HTML ici -->
</body>
</html>
"""

# Créer un fichier HTML temporaire sur le téléphone
with open("bamba_controlor.html", "w") as f:
    f.write(html_content)

# Ouvrir le fichier HTML dans le navigateur
# Cette commande fonctionne sur la plupart des Android via Pydroid
try:
    # Essayer la méthode standard Python
    webbrowser.open("file://" + os.path.realpath("bamba_controlor.html"))
except:
    # Si ça échoue, essayer via le module Android helper (nécessite l'installation dans Pip)
    # Dans Pip de Pydroid 3, cherchez 'android' ou 'sl4a'
    try:
        droid = androidhelper.Android()
        droid.webViewShow("file://" + os.path.realpath("bamba_controlor.html"))
    except:
        print("Impossible d'ouvrir le navigateur automatiquement. Le fichier est créé sous 'bamba_controlor.html'.")
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BAMBA CONTROLOR - Tableau de Bord Wi-Fi</title>
    <!-- Tailwind CSS pour un design rapide et moderne -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- FontAwesome pour les icônes -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body class="bg-gray-100 font-sans">

    <div class="flex h-screen overflow-hidden">

        <!-- SIDEBAR (Menu Latéral) -->
        <aside class="w-64 bg-slate-900 text-white hidden md:flex flex-col justify-between">
            <div>
                <!-- Logo / Nom du Logiciel -->
                <div class="px-6 py-5 border-b border-slate-800 flex items-center space-x-3">
                    <i class="fa-solid fa-wifi text-emerald-400 text-2xl"></i>
                    <span class="text-xl font-bold tracking-wider">BAMBA <span class="text-emerald-400">CONTROLOR</span></span>
                </div>
                <!-- Navigation -->
                <nav class="mt-6 px-4 space-y-2">
                    <a href="#" class="flex items-center space-x-3 px-4 py-2.5 rounded-lg bg-emerald-600 text-white font-medium">
                        <i class="fa-solid fa-chart-pie"></i>
                        <span>Tableau de bord</span>
                    </a>
                    <a href="#" class="flex items-center space-x-3 px-4 py-2.5 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white transition">
                        <i class="fa-solid fa-tower-broadcast"></i>
                        <span>Mes Sites Wi-Fi</span>
                    </a>
                    <a href="#" class="flex items-center space-x-3 px-4 py-2.5 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white transition">
                        <i class="fa-solid fa-ticket"></i>
                        <span>Vendeurs & Tickets</span>
                    </a>
                    <a href="#" class="flex items-center space-x-3 px-4 py-2.5 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white transition">
                        <i class="fa-solid fa-wallet"></i>
                        <span>Finances & Recettes</span>
                    </a>
                    <a href="#" class="flex items-center space-x-3 px-4 py-2.5 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white transition">
                        <i class="fa-solid fa-gear"></i>
                        <span>Paramètres</span>
                    </a>
                </nav>
            </div>
            <!-- Déconnexion -->
            <div class="p-4 border-t border-slate-800">
                <a href="#" class="flex items-center space-x-3 px-4 py-2 rounded-lg text-red-400 hover:bg-slate-800 transition">
                    <i class="fa-solid fa-right-from-bracket"></i>
                    <span>Déconnexion</span>
                </a>
            </div>
        </aside>

        <!-- CONTENU PRINCIPAL -->
        <div class="flex-1 flex flex-col overflow-y-auto">

            <!-- Top Header -->
            <header class="bg-white shadow-sm px-8 py-4 flex justify-between items-center">
            
            # Ligne 62 corrigée : une chaîne de caractères complète pour la div
(
    """<div class="flex items-center space-x-1">"""
)

# Ligne 63 corrigée : une chaîne de caractères complète pour le h1
(
    """<h1 class="text-2xl font-bold text-slate-800">Vue d'ensemble</h1>"""
)

                
                <div class="flex items-center spa-4">
                    <span class="bg-emerald-100 text-emerald-800 text-xs font-semibold px-2.5 py-1 rounded-full">Système en ligne</span>
                    <div class="flex items-center space-x-2">
                        <div class="w-10 h-10 rounded-full bg-slate-800 text-white flex items-center justify-center font-bold">BC</div>
                        <span class="text-sm font-medium text-slate-700">Admin Bamba</span>
                    </div>
                </div>
            </header>

            <!-- Dashboard Content -->
            <main class="p-8 space-y-8">

                <!-- 1. STATISTIQUES GLOBALES (Cartes) -->
                <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <!-- Carte 1 -->
                    <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-100 flex items-center justify-between">
                        <div>
                            <p class="text-sm text-slate-500 font-medium">Sites Wi-Fi Actifs</p>
                            <h3 class="text-2xl font-bold text-slate-800 mt-1">12 / 15</h3>
                        </div>
                        <div class="w-12 h-12 bg-blue-50 text-blue-600 rounded-lg flex items-center justify-center text-xl">
                            <i class="fa-solid fa-network-wired"></i>
                        </div>
                    </div>
                    <!-- Carte 2 -->
                    <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-100 flex items-center justify-between">
                        <div>
                            <p class="text-sm text-slate-500 font-medium">Vendeurs Actifs</p>
                            <h3 class="text-2xl font-bold text-slate-800 mt-1">28</h3>
                        </div>
                        <div class="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-lg flex items-center justify-center text-xl">
                            <i class="fa-solid fa-users"></i>
                        </div>
                    </div>
                    <!-- Carte 3 -->
                    <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-100 flex items-center justify-between">
                        <div>
                            <p class="text-sm text-slate-500 font-medium">Tickets Vendus (Jour)</p>
                            <h3 class="text-2xl font-bold text-slate-800 mt-1">450</h3>
                        </div>
                        <div class="w-12 h-12 bg-amber-50 text-amber-600 rounded-lg flex items-center justify-center text-xl">
                            <i class="fa-solid fa-ticket"></i>
                        </div>
                    </div>
                    <!-- Carte 4 -->
                    <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-100 flex items-center justify-between">
                        <div>
                            <p class="text-sm text-slate-500 font-medium">Recette du Jour</p>
                            <h3 class="text-2xl font-bold text-emerald-600 mt-1">125 000 XOF</h3>
                        </div>
                        <div class="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-lg flex items-center justify-center text-xl">
                            <i class="fa-solid fa-money-bill-wave"></i>
                        </div>
                    </div>
                </div>

                <!-- 2. SECTION CONTRÔLE DES SITES WI-FI -->
                <div class="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
                    <div class="flex justify-between items-center mb-6">
                        <h2 class="text-lg font-bold text-slate-800">État des Sites Wi-Fi Zone</h2>
                        <button class="bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition">
                            <i class="fa-solid fa-plus mr-2"></i> Ajouter un site
                        </button>
                    </div>
                    <div class="overflow-x-auto">
                        <table class="w-full text-left border-collapse">
                            <thead>
                                <tr class="border-b border-slate-200 text-slate-400 text-sm">
                                    <th class="py-3 px-4 font-semibold">Nom du Site</th>
                                    <th class="py-3 px-4 font-semibold">Emplacement</th>
                                    <th class="py-3 px-4 font-semibold">Statut Routeur</th>
                                    <th class="py-3 px-4 font-semibold">Connectés Actuels</th>
                                    <th class="py-3 px-4 font-semibold">Actions</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-100 text-sm text-slate-700">
                                <tr>
                                    <td class="py-3 px-4 font-medium">Bamba Zone - Quartier Commerce</td>
                                    <td class="py-3 px-4 text-slate-500">Centre-Ville</td>
                                    <td class="py-3 px-4"><span class="bg-emerald-100 text-emerald-700 px-2.5 py-1 rounded-full text-xs font-semibold">En Ligne</span></td>
                                    <td class="py-3 px-4">42 utilisateurs</td>
                                    <td class="py-3 px-4 space-x-2">
                                        <button class="text-blue-600 hover:text-blue-800 font-medium">Gérer</button>
                                        <button class="text-red-600 hover:text-red-800 font-medium">Redémarrer</button>
                                    </td>
                                </tr>
                                <tr>
                                    <td class="py-3 px-4 font-medium">Bamba Zone - Lycée Municipal</td>
                                    <td class="py-3 px-4 text-slate-500">Secteur Nord</td>
                                    <td class="py-3 px-4"><span class="bg-emerald-100 text-emerald-700 px-2.5 py-1 rounded-full text-xs font-semibold">En Ligne</span></td>
                                    <td class="py-3 px-4">85 utilisateurs</td>
                                    <td class="py-3 px-4 space-x-2">
                                        <button class="text-blue-600 hover:text-blue-800 font-medium">Gérer</button>
                                        <button class="text-red-600 hover:text-red-800 font-medium">Redémarrer</button>
                                    </td>
                                </tr>
                                <tr>
                                    <td class="py-3 px-4 font-medium">Bamba Zone - Gare Routière</td>
                                    <td class="py-3 px-4 text-slate-500">Sud</td>
                                    <td class="py-3 px-4"><span class="bg-red-100 text-red-700 px-2.5 py-1 rounded-full text-xs font-semibold">Hors Ligne</span></td>
                                    <td class="py-3 px-4">0 utilisateur</td>
                                    <td class="py-3 px-4 space-x-2">
                                        <button class="text-blue-600 hover:text-blue-800 font-medium">Gérer</button>
                                        <button class="text-emerald-600 hover:text-emerald-800 font-medium">Relancer</button>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- 3. SECTION CONTRÔLE DES VENDEURS DE TICKETS -->
                <div class="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
                    <div class="flex justify-between items-center mb-6">
                        <h2 class="text-lg font-bold text-slate-800">Suivi des Vendeurs de Tickets</h2>
                        <button class="bg-slate-800 hover:bg-slate-900 text-white text-sm font-medium px-4 py-2 rounded-lg transition">
                            Attribuer des stocks
                        </button>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <!-- Vendeur 1 -->
                        <div class="border border-slate-200 rounded-lg p-4 flex flex-col justify-between">
                            <div>
                                <div class="flex justify-between items-start mb-2">
                                    <h3 class="font-bold text-slate-800">Kouassi Jean</h3>
                                    <span class="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded font-medium">Actif</span>
                                </div>
                                <p class="text-xs text-slate-500 mb-4">Site : Quartier Commerce</p>
                                <div class="space-y-2 text-sm">
                                    <div class="flex justify-between">
                                        <span class="text-slate-500">Tickets confiés :</span>
                                        <span class="font-semibold text-slate-700">100</span>
                                    </div>
                                    <div class="flex justify-between">
                                        <span class="text-slate-500">Vendus :</span>
                                        <span class="font-semibold text-emerald-600">85</span>
                                    </div>
                                    <div class="flex justify-between">
                                        <span class="text-slate-500">Restants :</span>
                                        <span class="font-semibold text-amber-600">15</span>
                                    </div>
                                </div>
                            </div>
                            <div class="mt-4 pt-3 border-t border-slate-100 flex justify-between items-center">
                                <span class="text-xs font-bold text-slate-800">À Verser : 42 500 XOF</span>
                                <button class="text-xs bg-emerald-50 text-emerald-600 hover:bg-emerald-100 font-semibold px-3 py-1.5 rounded transition">Encaisser</button>
                            </div>
                        </div>

                        <!-- Vendeur 2 -->
                        <div class="border border-slate-200 rounded-lg p-4 flex flex-col justify-between">
                            <div>
                                <div class="flex justify-between items-start mb-2">
                                    <h3 class="font-bold text-slate-800">Aicha Traoré</h3>
                                    <span class="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded font-medium">Actif</span>
                                </div>
                                <p class="text-xs text-slate-500 mb-4">Site : Lycée Municipal</p>
                                <div class="space-y-2 text-sm">
                                    <div class="flex justify-between">
                                        <span class="text-slate-500">Tickets confiés :</span>
                                        <span class="font-semibold text-slate-700">200</span>
                                    </div>
                                    <div class="flex justify-between">
                                        <span class="text-slate-500">Vendus :</span>
                                        <span class="font-semibold text-emerald-600">180</span>
                                    </div>
                                    <div class="flex justify-between">
                                        <span class="text-slate-500">Restants :</span>
                                        <span class="font-semibold text-amber-600">20</span>
                                    </div>
                                </div>
                            </div>
                            <div class="mt-4 pt-3 border-t border-slate-100 flex justify-between items-center">
                                <span class="text-xs font-bold text-slate-800">À Verser : 90 000 XOF</span>
                                <button class="text-xs bg-emerald-50 text-emerald-600 hover:bg-emerald-100 font-semibold px-3 py-1.5 rounded transition">Encaisser</button>
                            </div>
                        </div>

                        <!-- Vendeur 3 -->
                        <div class="border border-slate-200 rounded-lg p-4 flex flex-col justify-between">
                            <div>
                                <div class="flex justify-between items-start mb-2">
                                    <h3 class="font-bold text-slate-800">Bakary Koné</h3>
                                    <span class="text-xs bg-amber-50 text-amber-600 px-2 py-0.5 rounded font-medium">Stock épuisé</span>
                                </div>
                                <p class="text-xs text-slate-500 mb-4">Site : Gare Routière</p>
                                <div class="space-y-2 text-sm">
                                    <div class="flex justify-between">
                                        <span class="text-slate-500">Tickets confiés :</span>
                                        <span class="font-semibold text-slate-700">150</span>
                                    </div>
                                    <div class="flex justify-between">
                                        <span class="text-slate-500">Vendus :</span>
                                        <span class="font-semibold text-emerald-600">150</span>
                                    </div>
                                    <div class="flex justify-between">
                                        <span class="text-slate-500">Restants :</span>
                                        <span class="font-semibold text-red-600">0</span>
                                    </div>
                                </div>
                            </div>
                            <div class="mt-4 pt-3 border-t border-slate-100 flex justify-between items-center">
                                <span class="text-xs font-bold text-slate-800">À Verser : 75 000 XOF</span>
                                <button class="text-xs bg-blue-50 text-blue-600 hover:bg-blue-100 font-semibold px-3 py-1.5 rounded transition">Réapprovisionner</button>
                            </div>
                        </div>
                    </div>
                </div>

            </main>
        </div>
    </div>

</body>
</html>
CREATE DATABASE IF NOT EXISTS bamba_controlor;
USE bamba_controlor;

-- Table des vendeurs
CREATE TABLE vendeurs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    telephone VARCHAR(20),
    site_wifi VARCHAR(100),
    statut ENUM('actif', 'suspendu') DEFAULT 'actif'
);

-- Table des tickets Wi-Fi
CREATE TABLE tickets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    forfait VARCHAR(50) NOT NULL, -- Ex: 1 Heure, 24 Heures, 1 Semaine
    prix DECIMAL(10,2) NOT NULL,
    vendeur_id INT,
    vendu TINYINT(1) DEFAULT 0,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_vente DATETIME NULL,
    FOREIGN KEY (vendeur_id) REFERENCES vendeurs(id)
);
<?php
// Connexion à la base de données
$host = 'localhost';
$db   = 'bamba_controlor';
$user = 'root';
$pass = '';

try {
    $pdo = new PDO("mysql:host=$host;dbname=$db;charset=utf8mb4", $user, $pass);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch (\PDOException $e) {
    die("Erreur de connexion : " . $e->getMessage());
}

// 1. Logique pour générer des tickets (si le formulaire est soumis)
$message = "";
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['generer'])) {
    $quantite = intval($_POST['quantite']);
    $forfait = $_POST['forfait'];
    $prix = floatval($_POST['prix']);
    $vendeur_id = intval($_POST['vendeur_id']);

    for ($i = 0; $i < $quantite; $i++) {
        // Génération d'un code unique (ex: BAMBA-7X9F2)
        $code = "BAMBA-" . strtoupper(substr(md5(uniqid(mt_rand(), true)), 0, 6));
        
        $stmt = $pdo->prepare("INSERT INTO tickets (code, forfait, prix, vendeur_id) VALUES (?, ?, ?, ?)");
        $stmt->execute([$code, $forfait, $prix, $vendeur_id]);
    }
    $message = "$quantite tickets générés avec succès pour le forfait $forfait !";
}

// 2. Récupérer la liste des vendeurs pour le formulaire
$vendeurs = $pdo->query("SELECT * FROM vendeurs")->fetchAll(PDO::FETCH_ASSOC);

// 3. Récupérer les derniers tickets générés
$tickets = $pdo->query("SELECT t.*, v.nom as vendeur_nom FROM tickets t LEFT JOIN vendeurs v ON t.vendeur_id = v.id ORDER BY t.id DESC LIMIT 20")->fetchAll(PDO::FETCH_ASSOC);
?>

<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BAMBA CONTROLOR - Gestion des Tickets</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 p-8 font-sans">
    <div class="max-w-6xl mx-auto space-y-8">
        
        <!-- En-tête -->
        <div class="flex justify-between items-center bg-white p-6 rounded-xl shadow-sm">
            <div>
                <h1 class="text-2xl font-bold text-slate-800">BAMBA CONTROLOR</h1>
                <p class="text-sm text-slate-500">Module de Génération et Contrôle des Tickets</p>
            </div>
            <a href="index.html" class="bg-slate-800 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-900">Retour Dashboard</a>
        </div>

        <?php if (!empty($message)): ?>
            <div class="bg-emerald-100 border border-emerald-400 text-emerald-700 px-4 py-3 rounded relative">
                <?= htmlspecialchars($message) ?>
            </div>
        <?php endif; ?>

        <!-- Formulaire de Génération -->
        <div class="bg-white p-6 rounded-xl shadow-sm">
            <h2 class="text-lg font-bold text-slate-800 mb-4">Générer de nouveaux codes de tickets</h2>
            <form action="tickets.php" method="POST" class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                    <label class="block text-sm font-medium text-slate-700 mb-1">Forfait / Durée</label>
                    <input type="text" name="forfait" placeholder="Ex: 24 Heures" required class="w-full border border-slate-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-emerald-500">
                </div>
                <div>
                    <label class="block text-sm font-medium text-slate-700 mb-1">Prix (XOF)</label>
                    <input type="number" name="prix" placeholder="Ex: 500" required class="w-full border border-slate-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-emerald-500">
                </div>
                <div>
                    <label class="block text-sm font-medium text-slate-700 mb-1">Quantité à générer</label>
                    <input type="number" name="quantite" value="50" required class="w-full border border-slate-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-emerald-500">
                </div>
                <div>
                    <label class="block text-sm font-medium text-slate-700 mb-1">Attribuer au Vendeur</label>
                    <select name="vendeur_id" required class="w-full border border-slate-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-emerald-500">
                        <option value="">Sélectionner un vendeur</option>
                        <?php foreach ($vendeurs as $v): ?>
                            <option value="<?= $v['id'] ?>"><?= htmlspecialchars($v['nom']) ?> (<?= htmlspecialchars($v['site_wifi']) ?>)</option>
                        <?php endforeach; ?>
                    </select>
                </div>
                <div class="md:col-span-4">
                    <button type="submit" name="generer" class="bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-6 py-2.5 rounded-lg text-sm transition">
                        Générer les codes
                    </button>
                </div>
            </form>
        </div>

        <!-- Liste des derniers tickets générés -->
        <div class="bg-white p-6 rounded-xl shadow-sm">
            <h2 class="text-lg font-bold text-slate-800 mb-4">Derniers tickets générés et suivis</h2>
            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse text-sm">
                    <thead>
                        <tr class="border-b border-slate-200 text-slate-400">
                            <th class="py-3 px-4">Code du Ticket</th>
                            <th class="py-3 px-4">Forfait</th>
                            <th class="py-3 px-4">Prix</th>
                            <th class="py-3 px-4">Vendeur assigné</th>
                            <th class="py-3 px-4">Statut Vente</th>
                            <th class="py-3 px-4">Date de Création</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100 text-slate-700">
                        <?php foreach ($tickets as $t): ?>
                        <tr>
                            <td class="py-3 px-4 font-mono font-bold text-emerald-600"><?= htmlspecialchars($t['code']) ?></td>
                            <td class="py-3 px-4"><?= htmlspecialchars($t['forfait']) ?></td>
                            <td class="py-3 px-4"><?= number_format($t['prix'], 0, ',', ' ') ?> XOF</td>
                            <td class="py-3 px-4"><?= htmlspecialchars($t['vendeur_nom'] ?? 'Non assigné') ?></td>
                            <td class="py-3 px-4">
                                <?php if ($t['vendu']): ?>
                                    <span class="bg-emerald-100 text-emerald-700 px-2.5 py-1 rounded-full text-xs font-semibold">Vendu</span>
                                <?php else: ?>
                                    <span class="bg-amber-100 text-amber-700 px-2.5 py-1 rounded-full text-xs font-semibold">En stock</span>
                                <?php endif; ?>
                            </td>
                            <td class="py-3 px-4 text-slate-500"><?= $t['date_creation'] ?></td>
                        </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        </div>

    </div>
</body>
</html>
<?php
// Inclure l'autoloader de Composer si vous utilisez la librairie RouterOS API
// composer require evilfreelancer/routeros-api-php
require_once 'vendor/autoload.php';

use RouterOS\Client;
use RouterOS\Query;

// Connexion Base de données Locale (BAMBA CONTROLOR)
$host = 'localhost';
$db   = 'bamba_controlor';
$user = 'root';
$pass = '';

try {
    $pdo = new PDO("mysql:host=$host;dbname=$db;charset=utf8mb4", $user, $pass);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch (\PDOException $e) {
    die("Erreur de connexion BD : " . $e->getMessage());
}

$message = "";

// Gestion de la génération des tickets et injection sur le MikroTik
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['generer'])) {
    $quantite   = intval($_POST['quantite']);
    $forfait    = $_POST['forfait'];       // Ex: 24h
    $prix       = floatval($_POST['prix']);
    $vendeur_id = intval($_POST['vendeur_id']);
    $site_ip    = $_POST['site_ip'];       // IP du routeur MikroTik du site concerné
    $profile    = $_POST['profile'];       // Profil Hotspot configuré sur le MikroTik (ex: "1H", "24H")

    try {
        // Connexion au routeur MikroTik du site distant via l'API
        $client = new Client([
            'host' => $site_ip,
            'user' => 'bamba_api',
            'pass' => 'VOTRE_MOT_DE_PASSE_API',
            'port' => 8728
        ]);

        $succesRouter = 0;

        for ($i = 0; $i < $quantite; $i++) {
            // Génération d'un code unique pour le ticket
            $code = "BAMBA-" . strtoupper(substr(md5(uniqid(mt_rand(), true)), 0, 6));
            
            // 1. Enregistrement dans la base de données locale Bamba Controlor
            $stmt = $pdo->prepare("INSERT INTO tickets (code, forfait, prix, vendeur_id) VALUES (?, ?, ?, ?)");
            $stmt->execute([$code, $forfait, $prix, $vendeur_id]);

            // 2. Création instantanée de l'utilisateur Hotspot dans le routeur MikroTik
            $query = (new Query('/ip/hotspot/user/add'))
                ->equal('name', $code)       // Le code du ticket devient le Login
                ->equal('password', $code)   // Le code sert aussi de Mot de passe (ou laissez vide si authentification par code unique)
                ->equal('profile', $profile); // Le profil applique la vitesse et la limite de temps

            $client->query($query);
            $succesRouter++;
        }

        $message = "Succès ! $succesRouter tickets générés localement et injectés sur le routeur du site ($site_ip).";

    } catch (Exception $e) {
        $message = "Erreur de communication avec le routeur Wi-Fi : " . $e->getMessage();
    }
}

// Récupération des données pour l'affichage
$vendeurs = $pdo->query("SELECT * FROM vendeurs")->fetchAll(PDO::FETCH_ASSOC);
$tickets = $pdo->query("SELECT t.*, v.nom as vendeur_nom FROM tickets t LEFT JOIN vendeurs v ON t.vendeur_id = v.id ORDER BY t.id DESC LIMIT 20")->fetchAll(PDO::FETCH_ASSOC);
?>

<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>BAMBA CONTROLOR - Génération & Routeur</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 p-8 font-sans">
    <div class="max-w-6xl mx-auto space-y-8">
        
        <div class="flex justify-between items-center bg-white p-6 rounded-xl shadow-sm">
            <div>
                <h1 class="text-2xl font-bold text-slate-800">BAMBA CONTROLOR</h1>
                <p class="text-sm text-slate-500">Passerelle de Contrôle Routeurs Wi-Fi Zone</p>
            </div>
            <a href="index.html" class="bg-slate-800 text-white px-4 py-2 rounded-lg text-sm font-medium">Dashboard</a>
        </div>

        <?php if (!empty($message)): ?>
            <div class="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded relative">
                <?= htmlspecialchars($message) ?>
            </div>
        <?php endif; ?>

        <!-- Formulaire de Génération Multisite -->
        <div class="bg-white p-6 rounded-xl shadow-sm">
            <h2 class="text-lg font-bold text-slate-800 mb-4">Générer et synchroniser des tickets sur un Site</h2>
            <form action="tickets.php" method="POST" class="grid grid-cols-1 md:grid-cols-3 gap-4">
                
                <div>
                    <label class="block text-sm font-medium text-slate-700 mb-1">IP du Routeur du Site</label>
                    <input type="text" name="site_ip" placeholder="Ex: 196.200.x.x (IP Routeur)" required class="w-full border border-slate-300 rounded-lg p-2.5 text-sm">
                </div>

                <div>
                    <label class="block text-sm font-medium text-slate-700 mb-1">Profil Hotspot MikroTik</label>
                    <input type="text" name="profile" placeholder="Ex: 24H_Pass" required class="w-full border border-slate-300 rounded-lg p-2.5 text-sm">
                </div>

                <div>
                    <label class="block text-sm font-medium text-slate-700 mb-1">Libellé Forfait (Interne)</label>
                    <input type="text" name="forfait" placeholder="Ex: 24 Heures Illimité" required class="w-full border border-slate-300 rounded-lg p-2.5 text-sm">
                </div>

                <div>
                    <label class="block text-sm font-medium text-slate-700 mb-1">Prix (XOF)</label>
                    <input type="number" name="prix" placeholder="500" required class="w-full border border-slate-300 rounded-lg p-2.5 text-sm">
                </div>

                <div>
                    <label class="block text-sm font-medium text-slate-700 mb-1">Quantité</label>
                    <input type="number" name="quantite" value="20" required class="w-full border border-slate-300 rounded-lg p-2.5 text-sm">
                </div>

                <div>
                    <label class="block text-sm font-medium text-slate-700 mb-1">Vendeur assigné</label>
                    <select name="vendeur_id" required class="w-full border border-slate-300 rounded-lg p-2.5 text-sm">
                        <option value="">Choisir un vendeur</option>
                        <?php foreach ($vendeurs as $v): ?>
                            <option value="<?= $v['id'] ?>"><?= htmlspecialchars($v['nom']) ?></option>
                        <?php endforeach; ?>
                    </select>
                </div>

                <div class="md:col-span-3">
                    <button type="submit" name="generer" class="bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-6 py-2.5 rounded-lg text-sm transition">
                        Générer & Envoyer sur le Routeur à distance
                    </button>
                </div>
            </form>
        </div>

    </div>
</body>
</html>
// Lors de la création de l'utilisateur sur le MikroTik via l'API :
$query = (new Query('/ip/hotspot/user/add'))
    ->equal('name', $code)
    ->equal('password', $code)
    ->equal('profile', $profile)
    ->equal('shared-users', '1')          // 🔒 INTERDIT strict les connexions simultanées
    ->equal('mac-cookie-timeout', '0d')   // Optionnel : gère la persistance de l'appareil
    ->equal('limit-uptime', $dureeForfait); // Limite de temps exacte du forfait
<?php
// Ce fichier reçoit l'alerte du routeur MikroTik lorsqu'un code est utilisé pour la première fois
$code = $_GET['code'] ?? ''; // Le code du ticket transmis par le routeur

if (!empty($code)) {
    $pdo = new PDO("mysql:host=localhost;dbname=bamba_controlor;charset=utf8mb4", "root", "");
    
    // 1. Marquer le ticket comme vendu et enregistrer l'heure exacte
    $stmt = $pdo->prepare("UPDATE tickets SET vendu = 1, date_vente = NOW() WHERE code = ? AND vendu = 0");
    $stmt->execute([$code]);

    if ($stmt->rowCount() > 0) {
        // Le ticket vient d'être validé pour la première fois !
        // Optionnel : Vous pouvez journaliser ou envoyer une notification au vendeur
        echo "OK - Ticket comptabilisé avec succès.";
    } else {
        echo "Déjà comptabilisé ou code invalide.";
    }
}
?>
<?php
// Exemple simplifié d'intégration d'un paiement en ligne (ex: API CinetPay / MoMo)
if (isset($_POST['acheter_en_ligne'])) {
    $forfait = $_POST['forfait'];
    $prix = $_POST['prix'];
    $telephone_client = $_POST['telephone'];

    // 1. Initialiser la transaction de paiement mobile money
    // (Appel de l'API de paiement du prestataire choisi)
    $payment_url = "https://api.prestataire-paiement.com/v1/payment/initiate";
    
    // 2. Si le paiement est validé (via Webhook de retour du paiement) :
    // Le code du ticket est généré automatiquement :
    $code = "BAMBA-WEB-" . strtoupper(substr(md5(uniqid()), 0, 5));
    
    // Insertion dans la BD et injection immédiate sur le MikroTik (comme vu précédemment)
    // ...
    
    // 3. Affichage du code généré au client pour qu'il se connecte tout de suite
    echo "<div class='p-4 bg-emerald-100 text-emerald-800 rounded-lg'>Paiement réussi ! Votre code Wi-Fi est : <b>$code</b></div>";
}
?>
-- Ajouter un champ de commission (en pourcentage, ex: 15.00 pour 15%) à la table des vendeurs
ALTER TABLE vendeurs ADD COLUMN commission_pct DECIMAL(5,2) DEFAULT 15.00;

-- Mettre à jour la table des tickets pour enregistrer la répartition au moment de la vente
ALTER TABLE tickets 
ADD COLUMN montant_vendeur DECIMAL(10,2) DEFAULT 0.00,
ADD COLUMN montant_entreprise DECIMAL(10,2) DEFAULT 0.00;
<?php
// Script appelé lors de la première connexion (vente du ticket)
$code = $_GET['code'] ?? '';

if (!empty($code)) {
    $pdo = new PDO("mysql:host=localhost;dbname=bamba_controlor;charset=utf8mb4", "root", "");
    
    // 1. Récupérer les infos du ticket et le pourcentage du vendeur associé
    $stmt = $pdo->prepare("
        SELECT t.id, t.prix, t.vendu, v.commission_pct 
        FROM tickets t 
        LEFT JOIN vendeurs v ON t.vendeur_id = v.id 
        WHERE t.code = ?
    ");
    $stmt->execute([$code]);
    $ticket = $stmt->fetch(PDO::FETCH_ASSOC);

    if ($ticket && $ticket['vendu'] == 0) {
        $prixTotal = $ticket['prix'];
        $commissionPct = $ticket['commission_pct'] ?? 15.00; // 15% par défaut si non défini

        // Calcul de la répartition
        $partVendeur = ($prixTotal * $commissionPct) / 100;
        $partEntreprise = $prixTotal - $partVendeur;

        // 2. Mettre à jour le ticket avec la vente et les parts financières
        $update = $pdo->prepare("
            UPDATE tickets 
            SET vendu = 1, 
                date_vente = NOW(), 
                montant_vendeur = ?, 
                montant_entreprise = ? 
            WHERE id = ?
        ");
        $update->execute([$partVendeur, $partEntreprise, $ticket['id']]);

        echo "Succès : Vente enregistrée. Vendeur: $partVendeur XOF | Entreprise: $partEntreprise XOF";
    } else {
        echo "Ticket déjà vendu ou introuvable.";
    }
}
?>
<?php
// Récupérer le chiffre d'affaires global et la répartition totale
$stats = $pdo->query("
    SELECT 
        SUM(prix) as CA_Total,
        SUM(montant_vendeur) as Total_Commission_Vendeurs,
        SUM(montant_entreprise) as CA_Net_Entreprise
    FROM tickets 
    WHERE vendu = 1
")->fetch(PDO::FETCH_ASSOC);
?>

<!-- Affichage sur le Dashboard -->
<div class="grid grid-cols-1 md:grid-cols-3 gap-6 my-6">
    <!-- Chiffre d'affaires Brut -->
    <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
        <p class="text-sm text-slate-500 font-medium">Chiffre d'Affaires Global</p>
        <h3 class="text-2xl font-bold text-slate-800 mt-1"><?= number_format($stats['CA_Total'] ?? 0, 0, ',', ' ') ?> XOF</h3>
    </div>
    
    <!-- Part des Vendeurs (À verser / Commissions) -->
    <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
        <p class="text-sm text-slate-500 font-medium">Commissions Vendeurs</p>
        <h3 class="text-2xl font-bold text-amber-600 mt-1"><?= number_format($stats['Total_Commission_Vendeurs'] ?? 0, 0, ',', ' ') ?> XOF</h3>
    </div>

    <!-- Part Nette Bamba Controlor -->
    <div class="bg-white p-6 rounded-xl shadow-sm border border-emerald-100 bg-emerald-50/30">
        <p class="text-sm text-emerald-700 font-medium">Bénéfice Net (BAMBA CONTROLOR)</p>
        <h3 class="text-2xl font-bold text-emerald-600 mt-1"><?= number_format($stats['CA_Net_Entreprise'] ?? 0, 0, ',', ' ') ?> XOF</h3>
    </div>
</div>
import os

def effacer_ecran():
    # Nettoie l'écran du terminal pour plus de clarté (fonctionne sur Pydroid 3)
    os.system('cls' if os.name == 'nt' else 'clear')

def scanner_wifi():
    print("\n--- SCAN DES RÉSEAUX WI-FI ---")
    # 👉 INÉGREZ VOTRE CODE DE SCAN WI-FI ICI
    print("[Simulation] Réseau trouvé : MonWiFi_123 (Signal: Excellent)")
    input("\nAppuyez sur Entrée pour revenir au menu...")

def verifier_connexion():
    print("\n--- ÉTAT DE LA CONNEXION ---")
    # 👉 INTÉGREZ VOTRE CODE DE VÉRIFICATION ICI
    print("[Simulation] Connecté au réseau : MonWiFi_123")
    input("\nAppuyez sur Entrée pour revenir au menu...")

def menu_principal():
    while True:
        effacer_ecran()
        print("==================================")
        print("         BAMBA CONTROLLOR         ")
        print("==================================")
        print("1. Scanner les réseaux Wi-Fi")
        print("2. Vérifier l'état du Wi-Fi")
        print("3. Quitter")
        print("==================================")
        
        choix = input("Faites votre choix (1, 2 ou 3) : ")
        
        if choix == '1':
            scanner_wifi()
        elif choix == '2':
            verifier_connexion()
        elif choix == '3':
            print("\nFermeture de BAMBA CONTROLLOR. À bientôt !")
            break
        else:
            input("\nOption invalide ! Appuyez sur Entrée pour réessayer.")

if __name__ == "__main__":
    menu_principal()
    import os
import sys

# --- DÉFINITION DES ACTIONS (Vos vrais codes iront ici !) ---

def effacer_ecran():
    """Nettoie l'écran du terminal."""
    # Sur Pydroid 3 (Android), 'clear' fonctionne généralement. 'cls' est pour Windows.
    os.system('cls' if os.name == 'nt' else 'clear')

def scanner_wifi():
    """Simule un scan Wi-Fi."""
    print("\n--- DÉMARRAGE DU SCAN WI-FI ---")
    # 👉 REMPLACEZ CETTE LIGNE PAR VOTRE VRAI CODE DE SCAN (API Android/Root, subprocess, etc.)
    print("Recherche des réseaux en cours...")
    print("\n[RÉSULTAT DU SCAN]")
    print("1. Reseau_Maison (Signal: Fort)")
    print("2. Bureau_Pro (Signal: Moyen)")
    input("\nAppuyez sur Entrée pour revenir au menu...")

def verifier_connexion():
    """Simule la vérification de l'état."""
    print("\n--- ÉTAT DE LA CONNEXION ---")
    # 👉 REMPLACEZ CETTE LIGNE PAR VOTRE VRAI CODE DE STATUT (API Android, iwconfig, ip addr, etc.)
    print("Vérification en cours...")
    print("\n[RÉSULTAT DE L'ÉTAT]")
    print("Connecté à : Reseau_Maison")
    print("Force du signal : 85%")
    input("\nAppuyez sur Entrée pour revenir au menu...")

# --- MENU PRINCIPAL (Structure de votre image) ---

def menu_principal():
    while True:
        effacer_ecran()
        # Header (adapté de votre image)
        print("==================================================")
        print("         BAMBA CONTROLLOR         ")
        print("==================================================")
        print("1. Scanner les réseaux Wi-Fi")
        print("2. Vérifier l'état du Wi-Fi")
        print("3. Quitter")
        print("==================================================")
        
        # Saisie (adapté de votre image)
        choix = input("Faites votre choix (1, 2 ou 3) : ")
        
        if choix == '1':
            scanner_wifi() # CORRECTION : appel de la fonction définie ci-dessus
        elif choix == '2':
            verifier_connexion() # CORRECTION : appel de la fonction définie ci-dessus
        elif choix == '3':
            # Quitter proprement (adapté de votre image)
            print("\nFermeture de BAMBA CONTROLLOR. À bientôt !")
            # Sortie propre au lieu de break pour éviter des problèmes de boucle
            sys.exit() 
        else:
            # Gestion d'erreur (adapté de votre image)
            input("\nOption invalide ! Appuyez sur Entrée pour réessayer.")

# --- POINT D'ENTRÉE DU SCRIPT ---

if __name__ == "__main__":
    menu_principal() # CORRECTION : parenthèses manquantes dans votre image
