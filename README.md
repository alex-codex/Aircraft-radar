# **Radar Tactique Interactif - Dashboard Temps Réel**

Ce projet est un tableau de bord de contrôle aérien en temps réel, conçu pour afficher les vols d'avions détectés autour d'une position géographique spécifique. 

L'interface est optimisée pour être utilisée comme **fond d'écran interactif** sur le bureau Windows via l'application **Lively Wallpaper**.

---

## **Fonctionnalités Visuelles & Ergonomiques**

L'application intègre des fonctionnalités visuelles et ergonomiques de haut niveau, inspirées des véritables radars de contrôle aérien (ATC) :

1.  **Esthétique Militaire & Rétroéclairée** :
    *   Thème sombre abyssal avec une grille géométrique en arrière-plan et un effet de balayage CRT discret.
    *   Panneaux d'information en verre dépoli (**glassmorphism**) avec des bordures lumineuses en cyan néon.
    *   Polices typographiques modernes et ultra-lisibles : `Outfit` pour les titres et `JetBrains Mono` pour les coordonnées et données numériques.
2.  **Animation de Sonar Actif** : Un effet de balayage radar rotatif en pur CSS tourne en continu sous les marqueurs des avions, simulant un véritable sonar.
3.  **Système Anti-Encombrement (Anti-Cluttering)** :
    *   Les étiquettes de texte (indicatifs de vols) des avions au sol ou à très basse altitude (< 1 200 m) sont masquées par défaut pour éviter que les étiquettes ne se chevauchent près des aéroports.
    *   Leurs marqueurs physiques (les blips verts) restent visibles et cliquables.
    *   Les étiquettes des vols en altitude active (> 1 200 m) s'affichent normalement.
4.  **Code Couleur d'Altitude (Liaison Visuelle)** :
    *   Les fiches de vols dans la liste de droite disposent d'une bordure gauche colorée selon leur altitude, correspondant exactement à la couleur de leur blip sur le radar :
        *    **Vert** : Basse altitude (< 3 000 m, proche du sol/aéroport).
        *    **Bleu cyan** : Moyenne altitude (3 000 - 10 000 m).
        *    **Violet** : Haute altitude (> 10 000 m).
5.  **Verrouillage de Cible (Target Lock) & Traînée Historique** :
    *   Cliquer sur un avion (sur le radar ou dans la liste) l'engage comme "cible active". Son marqueur s'illumine en jaune et grandit.
    *   Un badge clignotant jaune **`[ TARGET LOCKED ]`** apparaît dans le panneau de télémétrie.
    *   **Sa trajectoire passée** (historique des positions de l'heure précédente) est dessinée en temps réel sous forme de ligne pointillée jaune.

---

##  **Architecture Modulaire du Projet**

Conformément aux exigences de production, le code est découpé par responsabilité afin de faciliter une future migration vers un frontend **React + Tailwind** et un backend **FastAPI** :

```
radar-interactive-dashboard-ui/
├── assets/                  # Feuilles de style (Dash les charge automatiquement)
│   ├── theme.css            # Variables de couleurs, polices et animations globales
│   ├── layout.css           # Grille principale (Grid) et panneaux vitrés
│   └── components.css       # Widgets : KPIs, formulaires, dropdowns, cartes et radar
├── config/
│   ├── __init__.py
│   └── settings.py          # Constantes et variables d'environnement (.env)
├── src/                     # Logique métier (ETL)
│   ├── __init__.py
│   ├── extraction.py        # Récupération API OpenSky (100% typé)
│   ├── transformation.py    # Nettoyage, calculs de distance 3D et azimuts (100% typé)
│   └── loading.py           # Persistance SQLite via SQLAlchemy (100% typé)
├── ui/                      # Composants graphiques et callbacks Dash
│   ├── __init__.py
│   ├── components.py        # Rendu HTML des KPIs, télémétrie et cartes (100% typé)
│   ├── graphs.py            # Rendu des figures Plotly (Radar polaire 2D & Espace 3D)
│   └── callbacks.py         # Logique d'interaction et de filtrage local (100% typé)
├── tests/                   # Suite de tests unitaires
│   └── test_radar_logic.py  # Validation des calculs d'azimut et du filtrage
├── app.py                   # Point d'entrée principal (Serveur Dash)
├── requirements.txt         # Dépendances Python
├── .env.example             # Modèle de configuration des secrets
└── README.md                # Ce guide
```

---

## **Installation et Démarrage**

### 1. Installation des dépendances
Installez les bibliothèques requises à l'aide de `pip` :
```powershell
pip install -r requirements.txt
```

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

## **Honor de la Quality Gate ([40-quality-gate.mdc](file:///C:/Users/casta/.cursor/rules/40-quality-gate.mdc))**

Le code de ce projet respecte scrupuleusement les exigences suivantes :
*   **Fichiers courts** : Aucun fichier de code ou de style ne dépasse la limite de **300 lignes**.
*   **Fonctions modulaires** : Toutes les fonctions font moins de **50 lignes** (la génération des graphiques a été scindée en fonctions d'aide spécialisées pour le traitement de données et de mise en page).
*   **Typage strict** : 100 % des fonctions possèdent des signatures typées (`Type Hints`).
*   **Zéro valeur magique** : Toutes les constantes sont centralisées dans `config/settings.py`.
