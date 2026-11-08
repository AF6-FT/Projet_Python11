Analyse de logs SSH

Petit projet fait dans le cadre d'un TP. Le programme lit des fichiers de logs SSH (auth.log) et montre qui a essayé de se connecter à la machine, et d'où.

Ce que ça fait
Lit tous les fichiers auth.log.* du dossier data/ (même ceux compressés en .gz)
Repère les connexions réussies, les mots de passe ratés et les utilisateurs qui n'existent pas
Trouve le pays de chaque adresse IP grâce à ipinfo.io
Enregistre tout dans une base SQLite
Affiche trois graphiques :
les échecs de connexion par pays
les connexions réussies par utilisateur
les noms d'utilisateurs invalides les plus essayés

Le résultat est aussi sauvegardé en image dans output/ssh_dashboard.png.

Lancer le projet
cd log_analysis
uv sync
uv run python main.py

Il faut une connexion internet pour trouver les pays. Si elle ne marche pas, les pays restent "Unknown".

Organisation des dossiers
data/ : les fichiers de logs à analyser
pipeline/ : lecture et traitement des logs
storage/ : la base de données
serving/ : les graphiques
logs/ : les logs du programme lui-même
main.py : le fichier à lancer
Remarques
Les logs syslog ne contiennent pas l'année, donc le programme prend l'année en cours.
Les adresses IP privées sont classées en "Unknown".
Les fichiers fournis par le prof dans ingestion/ et processing/ n'ont pas été modifiés, j'ai écrit mes propres versions dans pipeline/ parce que les originaux avaient des bugs.