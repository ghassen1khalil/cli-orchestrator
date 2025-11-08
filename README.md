# Orchestrateur de commandes Java

Application de bureau PySide6 pour orchestrer l'exécution d'un jar Java sur des lots de bases SQLite. L'outil permet une exécution parallèle des commandes dans un même lot et séquentielle entre les lots.

## Fonctionnalités

- Sélection du fichier `.jar` et édition des arguments JVM (`-D`) et applicatifs.
- Gestion graphique des lots avec ordre d'exécution, sélection de dossier ou fichiers individuels et sauvegarde/chargement en YAML.
- Exécution parallèle des bases d'un même lot via `QProcess` avec capture temps réel des logs.
- Mode automatique ou manuel pour passer au lot suivant.
- Arrêt individuel d'un processus ou arrêt global de l'orchestration.
- Visualisation des commandes lancées et de leur statut dans des onglets dynamiques.

## Installation

1. Créer un environnement Python 3.10+.
2. Installer les dépendances :

```bash
pip install PySide6 pyyaml
```

## Utilisation

```bash
python app.py
```

1. Sélectionnez le jar Java et configurez les arguments.
2. Ajoutez des lots soit par dossier + pattern (`*.db` par défaut) soit en listant des fichiers spécifiques.
3. Chargez ou sauvegardez la configuration YAML via les boutons dédiés.
4. Choisissez le mode Auto (enchaînement automatique) ou Manuel (confirmation nécessaire).
5. Cliquez sur **Démarrer orchestration** pour lancer les traitements. Les logs apparaissent en temps réel dans les onglets.

### Format YAML

```yaml
Lots:
  - name: Lot1
    databases_path: "C:\\migration\\lot_1\\between_0_49\\"
    pattern: "*.db"
  - name: Lot2
    databases_path: "C:\\migration\\lot_2\\sup_50\\"
    pattern: "*.db"
```

Si des fichiers sont listés explicitement pour un lot, le pattern est ignoré.

## Notes

- La propriété `spring.datasource.url` est automatiquement renseignée avec le chemin de la base courante.
- L'application stocke la dernière configuration d'arguments et le chemin du jar via `QSettings`.
