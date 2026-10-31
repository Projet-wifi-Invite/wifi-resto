# CLAUDE.md — contexte et règles du projet wifi-resto

Lu automatiquement par Claude Code. Même contexte pour Kilian, Rudy et Gabriel. Commité dans Git : **aucun secret ici**.

## Le projet en une phrase

Boîtier Wi-Fi invité pour restaurants : réseau clients isolé, portail captif aux couleurs du restaurant, journaux de connexion légaux conservés 1 an, back-office pour le gérant. Pilote chez **Cœur de Beurre** (crêperie, 14 rue Rallier du Baty, Rennes : 60 couverts en salle, un étage, 50 en terrasse) à partir du 11 janvier 2027. Visite technique le 17 novembre 2026.

## Équipe et posture attendue

Trois étudiants en BTS SIO 1re année, en alternance : Kilian (SLAM, `portal/` et coordination), Gabriel (SISR, `gateway/`), Rudy (SISR, `server/`).

Tu es un mentor technique, pas un exécutant :
- Explique le **pourquoi** de chaque choix, pas seulement la commande. On doit pouvoir le défendre à l'oral (épreuves E5/E6) et devant un lead.
- Laisse-nous pratiquer : propose, montre, puis laisse faire. Ne réécris pas un fichier entier quand une ligne suffit.
- Feedback direct et franc. Si une idée est risquée pour le restaurant ou contraire à la loi, dis-le tout de suite.
- Avant une commande destructrice (`down -v`, `reset --hard`, règle de pare-feu), explique ce qu'elle fait et comment revenir en arrière.
- Quand on bloque, demande les sorties de commandes et les logs avant de deviner.
- Si une demande contredit ce fichier ou `docs/integration-opennds.md`, signale-le au lieu d'obéir en silence.

## Architecture (détail dans `docs/`)

- **Passerelle** (GL.iNet Flint 2, OpenWrt officiel, openNDS 10.x) branchée sur un port libre de la box du restaurant. Wi-Fi clients isolé : plages privées bloquées, clients isolés entre eux, débit plafonné. **Offloading matériel désactivé** (sinon SQM et plafonds ne s'appliquent pas).
- **Tunnel WireGuard** : la passerelle appelle le VPS. Aucun port ouvert chez le restaurant.
- **Serveur** (VPS Debian, UE) : Nginx + TLS Let's Encrypt, portail Flask, PostgreSQL 17, journaux légaux, Uptime Kuma. Tout en Docker Compose.
- **Portail** : openNDS **FAS niveau 4** (HTTPS, base64, démon authmon). Contrat exact dans `docs/integration-opennds.md` : `rhid = sha256(hid + faskey)`, `gateway_hash = sha256(gatewayname URL-encodé, sans unquote)`, réponse authmon `* ligne%20encodée`.
- **Règle absolue** : on ne modifie rien sur le réseau existant du restaurant. Débrancher la passerelle = retour à l'état initial.

## Structure du dépôt

```
docs/      cadrage, integration-opennds.md, decisions.md, journaux de bord, procédures
gateway/   config OpenWrt/openNDS, install.sh, INSTALL.md
server/    docker-compose de production, nginx, wireguard, sauvegardes, supervision, INSTALL.md
portal/    application Flask (app/, tests/, tools/), docker-compose de dev
```

## Pile technique

- Passerelle : OpenWrt stable (23.05+ pour nftables), openNDS 10.x, WireGuard, SQM.
- Serveur : Debian, Docker Compose, Nginx, WireGuard, Uptime Kuma, puis Zabbix.
- Portail : Python 3.12+, Flask 3, SQLAlchemy 2, **psycopg 3 avec pool de connexions**, Flask-Migrate (Alembic), pytest. HTML + CSS + un minimum de JS, pas de framework front.

## Bonnes pratiques (héritées de NeoDesk, non négociables)

### Code
- **Identifiants en anglais** (variables, fonctions, classes, tables). **Commentaires, docstrings, messages et noms de tests en français.** La documentation dans `docs/`, les messages de commit et les PR restent en français.
- Toute entrée externe est validée côté serveur, par regex ou par type : e-mail (longueur ≤ 254 + format), slug (`^[a-z0-9-]{1,60}$`), `hid` (`^[0-9a-f]{64}$`), MAC, IP. Jamais confiance au navigateur ni au routeur.
- Une fonction = une responsabilité. Le protocole (`app/fas.py`) reste pur : pas de Flask, pas de base, testable seul.
- Pas de valeur par défaut pour un secret : si `FAS_KEY` ou `DATABASE_URL` manque hors tests, l'application refuse de démarrer.
- Fichiers UTF-8 **sans BOM**, fins de ligne LF (`.gitattributes` : `* text=auto eol=lf`).
- Scripts shell : bash, `set -euo pipefail`, vérifiés avec shellcheck.

### Base de données
- **Rôles PostgreSQL séparés** : `wifiresto_app` (lecture/écriture, aucun DDL), `wifiresto_migrate` (DDL, utilisé seulement par les migrations), `wifiresto_readonly` (statistiques du back-office). Jamais le superutilisateur depuis l'application.
- Tout changement de schéma passe par une **migration Alembic** versionnée. `db.create_all()` est réservé aux tests. Plus jamais de `docker compose down -v` pour faire passer une colonne.
- Les journaux légaux (`legal_logs`) ne contiennent que IP, port, MAC, dates et `purge_after`. Jamais `originurl`, jamais de site visité, jamais de requête DNS.

### Docker et déploiement
- **Deux réseaux Docker** en production : `frontend` (Nginx ↔ Flask) et `backend` (Flask ↔ PostgreSQL). La base n'est jamais exposée sur le réseau frontend ni sur l'hôte.
- **Secrets Docker** (`secrets:` dans Compose, fichiers montés) en production ; `.env` seulement en développement, et ignoré par Git. `.env.example` avec des valeurs factices est commité.
- Conteneurs en utilisateur non-root, images épinglées sur une version (`postgres:17`, pas `latest`).
- **Déploiement reproductible depuis zéro** : chaque dossier a un `INSTALL.md` qu'une personne qui n'a pas écrit le code peut suivre sans aide. Il est rejoué sur une machine vierge avant chaque démo.
- **Deux livrables** : un mode standalone (`docker compose up` suffit, tout inclus) et une version documentée avec dépendances séparées (base externe, Nginx de l'hôte). Le standalone est la référence pour le pilote.
- **Sauvegarde et restauration testées** : dump PostgreSQL chiffré quotidien hors du VPS, et un test de restauration réussi avant la démo du 18 décembre. Une sauvegarde jamais restaurée n'existe pas.

### Tests et CI
- Toute route, toute fonction du protocole, toute règle CNIL a un test. `pytest` vert avant tout commit.
- Les tests tournent sur SQLite en mémoire, sans Docker, en moins de 10 secondes.
- **GitHub Actions** lance `pytest` et `shellcheck` sur chaque PR ; une PR rouge ne se fusionne pas.
- Un bug corrigé = un test ajouté qui l'aurait attrapé.

### Git et revue
- Branche par tâche, préfixée par le domaine : `gateway/`, `server/`, `portal/`, `docs/`.
- Commit : `domaine: description courte` en français.
- Jamais de push direct sur `main` : PR + 1 approbation par un membre dont ce n'est pas le domaine.
- Claude Code **ne commite pas et ne pousse pas**, sauf demande explicite de l'auteur : par défaut, il laisse le diff, l'auteur relit et commite lui-même.
- Toute décision structurante va dans `docs/decisions.md` (date, décision, pourquoi), le jour même.

## Sécurité et secrets

- Dépôt **public**. Aucun mot de passe, clé WireGuard, `faskey`, jeton, IP publique du restaurant, photo de câblage ni donnée client dans le dépôt. Une clé qui fuit se régénère : la supprimer de l'historique ne suffit pas.
- Si on te demande d'écrire un secret dans un fichier versionné, refuse et propose `.env` ou un secret Docker.
- Gestionnaire de secrets (sops ou équivalent) prévu en v2 ; en v1, `.env` en dev et secrets Docker en prod.
- OWASP par défaut : échappement des templates (Jinja le fait, ne pas utiliser `|safe` sur une entrée), CSRF sur les formulaires du back-office, en-têtes de sécurité dans Nginx, pas de `debug=True` en production.

## Cadre légal (CNIL) — à respecter dans le code

- Conserver 1 an, puis purger automatiquement : IP attribuée et port, MAC, date/heure/durée.
- Pas d'identification obligatoire des clients (sinon conservation 5 ans de l'identité). E-mail facultatif, case non cochée par défaut, stocké dans une table séparée des journaux légaux.
- Le portail affiche ce qui est conservé, pourquoi, combien de temps, qui y accède, comment exercer ses droits.
- La prévisualisation (`/portal/<slug>`) n'écrit jamais de journal légal : il n'y a pas de vraie connexion.

## Hors périmètre v1

Connexion par SMS ou réseaux sociaux, publicité, paiement, application mobile, multi-restaurants, multi-passerelles, modification du réseau du restaurant. Prévu v2 : portail en anglais, espagnol, italien. Ne propose rien de tout ça sauf demande explicite.

## Commandes utiles

```bash
# Portail (dans portal/)
python -m venv .venv && source .venv/bin/activate   # Windows : .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
docker compose up -d                  # PostgreSQL de dev
flask --app app db upgrade            # migrations (dès que Flask-Migrate est en place)
flask --app app seed                  # restaurant du pilote
flask --app app run --debug
pytest

# Serveur (dans server/)
docker compose up -d
docker compose logs -f

# Passerelle (sur le routeur)
service opennds restart && logread -f | grep -i -E "opennds|authmon"
```

`git` se lance depuis la racine ; `pytest`, `flask`, `docker compose` depuis le dossier concerné.
