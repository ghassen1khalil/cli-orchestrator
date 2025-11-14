# Orchestrateur de commandes Java

Application de bureau PySide6 pour orchestrer l'exécution d'un jar Java sur des lots de bases SQLite. L'outil permet une exécution parallèle des commandes dans un même lot et séquentielle entre les lots.

## Fonctionnalités

- Sélection du fichier `.jar` avec injection automatique des paramètres JVM (`-Dspring.profiles.active=fsada` et `-Dspring.datasource.url=...`) et de l'argument applicatif `--fsada`.
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

1. Sélectionnez le jar Java ; les paramètres requis (`-Dspring.profiles.active=fsada` et `--fsada`) sont ajoutés automatiquement.
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

- La commande exécutée prend la forme `java -Dspring.profiles.active=fsada -Dspring.datasource.url=jdbc:sqlite:<base> -jar <jar> --fsada`.
- La propriété `spring.datasource.url` est automatiquement renseignée avec le chemin de la base courante.
- L'application stocke uniquement le chemin du jar et le mode automatique via `QSettings`.

## Packaging Windows (.exe)

Un fichier `cli_orchestrator.spec` est fourni pour générer un exécutable Windows autonome via [PyInstaller](https://pyinstaller.org/).

1. Sur **Windows**, installez Python 3.10 ou supérieur puis créez un environnement virtuel :

   ```powershell
   py -3.10 -m venv .venv
   .\.venv\Scripts\activate
   ```

2. Installez les dépendances de l'application ainsi que PyInstaller :

   ```powershell
   pip install -r requirements.txt
   ```

3. Générez l'exécutable en utilisant la spec fournie (désactive la console car l'application est 100% graphique) :

   ```powershell
   pyinstaller --clean --noconfirm cli_orchestrator.spec
   ```

4. L'exécutable `dist/cli-orchestrator.exe` peut alors être copié et distribué. PyInstaller embarque automatiquement les dépendances Qt nécessaires.

> ℹ️ PyInstaller produit des exécutables spécifiques au système. L'exécutable Windows doit donc être construit depuis un poste Windows ; les systèmes Linux/macOS devront utiliser PyInstaller localement pour générer leur propre binaire.
