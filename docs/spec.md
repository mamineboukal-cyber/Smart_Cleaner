# TP — Développement d'une application Web de Data Preprocessing & Cleaning

**Objectif :** Développer une application Web générique permettant d'analyser, nettoyer et transformer automatiquement un dataset pour le Machine Learning.

**Technologies :** React.js (Frontend), Python/FastAPI (Backend), Pandas et Scikit-learn.

## Fonctionnalités attendues

### 1. Importation et configuration

- Importer un dataset CSV ou Excel.
- Choisir le type d'apprentissage : supervisé ou non supervisé.
- Définir la variable cible (target) en cas d'apprentissage supervisé.

### 2. Onglet — Analyse exploratoire (EDA)

- Visualiser toutes les features, leurs types et leurs statistiques.
- Afficher les distributions, valeurs manquantes, doublons, outliers et corrélations.
- Proposer des visualisations graphiques interactives.

### 3. Onglet — Preprocessing & Cleaning

- Afficher, pour chaque feature, les anomalies détectées et les transformations recommandées avec justification statistique.
- Proposer les traitements possibles : imputation, encodage, scaling, suppression, traitement des outliers, etc.
- Permettre d'accepter la recommandation, de choisir une autre transformation ou de ne rien appliquer.
- Visualiser le résultat avant/après transformation.

### 4. Exécution et export

- Appliquer les transformations sélectionnées en respectant les bonnes pratiques ML (notamment la prévention du data leakage).
- Télécharger le dataset transformé.
- Générer un rapport Excel par feature contenant les statistiques, anomalies, recommandations et transformations réellement appliquées.

## Livrables

- Application fonctionnelle React + Python.
- Code source documenté.
- Démonstration sur le dataset de fraude bancaire.
- Validation sur un deuxième dataset pour vérifier la généricité.
- Dataset transformé et rapport Excel.

**Résultat attendu :** Une application Web interactive et générique d'analyse, de nettoyage et de préparation des données pour le Machine Learning.
