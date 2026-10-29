# Journal de bord — Kilian (portail, coordination)

Une entrée par session de travail : ce que j'ai fait, ce que j'ai appris, ce qui a bloqué, la suite. Matière pour la soutenance E5 et pour le bilan du pilote.

---

## 2026-10-29 — Lancement du projet

**Durée** : environ 6 h.

**Fait**
- Choix du projet avec l'équipe : Wi-Fi invité clé en main pour restaurants, pilote chez Cœur de Beurre (crêperie, Rennes, 60 couverts + étage + terrasse 50 couverts).
- Document de cadrage : architecture (passerelle OpenWrt + openNDS, tunnel WireGuard, VPS avec portail Flask), choix techniques argumentés, cadre légal CNIL, planning en 3 sprints, budget, risques.
- Répartition : Gabriel sur `gateway/`, Rudy sur `server/`, moi sur `portal/` et la coordination. Visite technique le 17 novembre.
- Organisation GitHub `Projet-wifi-Invite`, dépôt public `wifi-resto`, branche `main` protégée (PR + 1 approbation), structure `docs/ gateway/ server/ portal/`, journal des décisions.
- Portail Flask : fabrique `create_app()`, blueprint, `/health`, PostgreSQL 17 en Docker Compose, modèle de données limité aux champs autorisés par la CNIL (`Restaurant`, `ConnectionSession`, `LegalLog` avec `purge_after` à +1 an, `NewsletterConsent` stocké à part), page « J'accepte les conditions » avec mention d'information, e-mail newsletter enregistré seulement si la case est cochée, page de remerciement avec avis Google et Instagram, couleurs et logo du restaurant. 10 tests pytest sur SQLite en mémoire.
- Contrat d'intégration openNDS ↔ portail (`docs/integration-opennds.md`), tiré du code source openNDS 10.3.1 : FAS niveau 4, format du paramètre `fas`, `rhid = sha256(hid + faskey)`, protocole du démon authmon.
- 7 pull requests ouvertes, en attente de relecture par Rudy et Gabriel.

**Appris**
- Cadre légal du Wi-Fi public (CNIL) : conserver 1 an les données techniques (IP, MAC, date, heure, durée), jamais le contenu ni les sites visités ; pas d'identification obligatoire des clients, sinon conservation 5 ans de l'identité.
- Fonctionnement d'un portail captif avec openNDS : redirection vers un FAS distant, hachage du jeton client, traversée du NAT par un démon qui interroge le serveur toutes les 5 s.
- Git en équipe : branche par tâche, PR, protection de branche, relecture obligatoire. Une PR suit sa branche : un commit poussé après coup s'y ajoute tout seul.
- Flask : fabrique d'application pour isoler les tests, blueprints, commandes CLI (`init-db`, `seed`), SQLAlchemy.
- Accessibilité : les couleurs du logo (`#ffd87b`, `#93b9d8`) sont trop claires pour du texte ; un bleu foncé dérivé (`#3b6f9c`) garde l'identité et reste lisible en plein soleil.
- Contrainte matérielle découverte : l'offloading matériel du MT7986 (Flint 2) court-circuite SQM et la limitation de débit ; à désactiver dès l'installation.

**Bloqué, et comment c'est sorti**
- Commandes bash collées dans PowerShell : erreur de syntaxe immédiate. Solution : équivalents PowerShell, puis passage à VS Code pour écrire les fichiers.
- `Set-Content -Encoding utf8` ajoute un BOM (`﻿`) en tête de fichier sous Windows PowerShell 5 ; envoyé au navigateur avant le `<!doctype>`, c'est un risque de mode de compatibilité. Nettoyage de tout `portal/`, et plus jamais de `Set-Content` pour du code.
- `[System.IO.File]` ignore le dossier courant de PowerShell : toujours un chemin absolu.
- Relancer `pytest` / `docker compose` depuis la racine au lieu de `portal/` : trois erreurs pour une seule cause. Règle : `git` à la racine, tout le reste dans `portal/`.
- Un `git status` montrait `deleted: README.md` que je n'avais pas demandé : le relire avant `git add` a évité de pousser une suppression.
- Colonne ajoutée au modèle sans migration : recréation de la base en dev (`docker compose down -v`). Dette notée : Alembic avant la production.

**Décisions prises aujourd'hui** (reportées dans `docs/decisions.md`)
- Dépôt public, `main` protégée, aucun secret dans Git.
- FAS niveau 4 plutôt que 3 (même sécurité, pas de PHP sur le routeur).
- Débits par client décidés par le portail (ligne d'autorisation), pas par le routeur.
- Pas de migrations pendant le labo, Alembic avant la production.
- Couleur principale du portail `#3b6f9c`, textes « chez Cœur de Beurre ».

**Suite**
- Route `/fas` : décodage, `rhid`, file `pending_auths`, dialogue authmon, simulateur de passerelle.
- Flask-Migrate.
- Convention de pilote d'une page.
- Visite personnelle du restaurant avec la checklist terrain (mesures de signal salle / étage / terrasse).
