# ✈️ Radar Tactique Interactif - Dashboard Temps Réel

Ce projet est un tableau de bord de contrôle aérien en temps réel, conçu pour afficher les vols d'avions détectés autour d'une position géographique spécifique (par défaut **Houilles, Yvelines, France**). 

L'interface est optimisée pour être utilisée comme **fond d'écran interactif** sur le bureau Windows via l'application **Lively Wallpaper**.

---

## 🎨 Nouveautés de la Version Actuelle (Refonte Premium HUD)

Par rapport à la version d'origine, l'application a subi une refonte visuelle et fonctionnelle majeure :

1.  **Esthétique Scientifique/Militaire (HUD)** :
    *   Thème sombre abyssal avec une grille géométrique en arrière-plan et un effet de balayage CRT discret.
    *   Panneaux d'information en verre dépoli (**glassmorphism**) avec des bordures lumineuses cyan néon.
    *   Polices typographiques technologiques : `Orbitron` pour les titres et `Share Tech Mono` pour les données numériques.
2.  **Animation de Sonar Actif** : Un effet de balayage radar rotatif en pur CSS tourne en continu sous les marqueurs des avions, simulant un véritable sonar militaire.
3.  **Interactivité Avancée & Télémétrie** :
    *   **Sélection de cible** : Cliquer sur un avion sur le radar ou sur sa fiche dans la liste de droite l'engage comme "cible active". Son marqueur s'illumine en jaune et sa fiche technique complète s'affiche dans le panneau de télémétrie (vitesse en km/h et nœuds, taux vertical précis, azimut, coordonnées, statut).
    *   **Indicateurs de tendance** : La liste de droite affiche des flèches de tendance verticale (↗ en montée, ↘ en descente, → en palier) calculées en temps réel.
4.  **Optimisation de l'API & Performance** :
    *   L'API OpenSky est requêtée dans un rayon fixe maximal de 100 km.
    *   Les filtres de **portée** (curseur de 5 à 100 km), d'**altitude**, et de **recherche par indicatif** filtrent le jeu de données localement dans le navigateur. Cela élimine les requêtes API répétitives et évite d'épuiser les quotas (rate limiting).
5.  **Double Vue Tactique** : Basculement instantané entre le **Radar Polaire 2D** et le **Dôme Aérien 3D** rotatif.

---

## 📂 Architecture Modulaire du Projet

Afin de garantir l'évolutivité du code et de faciliter une future migration vers un frontend **React + Tailwind** et un backend **FastAPI**, le projet a été entièrement restructuré selon les meilleures pratiques industrielles :

```
radar-interactive-dashboard-ui/
├── assets/
│   └── style.css            # Styles CSS premium et animations du HUD
├── config/
│   └── settings.py          # Configuration centralisée (GPS, API, DB) et chargement du .env
├── src/                     # Logique métier (ETL)
│   ├── extraction.py        # Extraction depuis l'API OpenSky (Entièrement typé)
│   ├── transformation.py    # Nettoyage, calculs géométriques et azimut (Entièrement typé)
│   └── loading.py           # Persistance dans la base de données SQLite (Entièrement typé)
├── ui/                      # Composants graphiques et callbacks Dash
│   ├── components.py        # Rendu des KPIs, de la télémétrie et des cartes (HTML)
│   ├── graphs.py            # Rendu des figures Plotly (Radar polaire 2D & Espace 3D)
│   └── callbacks.py         # Gestion des interactions, du filtrage et des stores
├── tests/                   # Suite de tests unitaires
│   └── test_radar_logic.py  # Validation des calculs d'azimut et des filtres
├── app.py                   # Point d'entrée principal (Serveur Dash)
├── requirements.txt         # Dépendances Python
├── .env.example             # Fichier d'exemple pour les variables d'environnement
└── README.md                # Ce guide
```

---

## ⚙️ Installation et Démarrage

### Prérequis
*   Python 3.8 ou supérieur
*   Un fichier `.env` à la racine (optionnel, voir `.env.example` pour utiliser vos identifiants OpenSky afin d'avoir des limites de requêtes plus élevées).

### 1. Installation des dépendances
Installez les bibliothèques requises à l'aide de `pip` :
```powershell
pip install -r requirements.txt
```
*Note : Si la bibliothèque `opensky-api` n'est pas installée, assurez-vous de l'installer depuis son dépôt officiel.*

### 2. Lancement des tests
Exécutez les tests unitaires pour valider la logique de calcul :
```powershell
python -m unittest discover -s tests
```

### 3. Démarrage du serveur
Lancez le tableau de bord local :
```powershell
python app.py
```
Le serveur sera disponible à l'adresse suivante : [http://localhost:8050/](http://localhost:8050/).

---

## 🖥️ Intégration dans Lively Wallpaper (Bureau Windows)

Pour définir ce radar interactif comme fond d'écran animé sous Windows :

1.  Lancez le serveur local (`python app.py`).
2.  Ouvrez **Lively Wallpaper**.
3.  Cliquez sur le bouton **Ajouter un fond d'écran** (`+` dans le panneau latéral).
4.  Dans la zone de saisie d'URL, entrez : `http://localhost:8050/` et cliquez sur la flèche pour valider.
5.  Une fois chargé, donnez-lui un nom (ex: *Radar Aérien Tactique*) et validez.
6.  *Optionnel :* Pour interagir avec le radar (cliquer sur les avions, utiliser les filtres) directement depuis votre bureau, faites un clic droit sur l'icône de Lively dans la barre des tâches, allez dans **Actif**, et vérifiez que le contrôle est activé.

---

## 🛠️ Critères de Qualité (Quality Gate)
Le code de ce projet respecte scrupuleusement les exigences suivantes :
*   **Fichiers courts** : Aucun fichier de code ne dépasse 300 lignes.
*   **Fonctions modulaires** : Toutes les fonctions font moins de 50 lignes de code, facilitant la relecture et le test.
*   **Typage strict** : 100% des fonctions possèdent des signatures typées (type hints).
*   **Aucun secret committé** : Toutes les configurations sensibles sont lues depuis le `.env`.
*   **Zéro duplication** : Les calculs et rendus sont centralisés et réutilisés.
