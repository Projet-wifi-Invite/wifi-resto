# CLAUDE.md — contexte partagé du projet wifi-resto

Ce fichier est lu automatiquement par Claude Code. Il donne le même contexte à chaque membre de l'équipe. Il est commité dans Git : ne jamais y mettre de secret.

## Le projet en une phrase

Boîtier Wi-Fi invité pour restaurants : réseau clients isolé, portail captif brandé, journaux de connexion légaux conservés 1 an, back-office pour le gérant. Pilote prévu dans un restaurant partenaire à Rennes à partir de janvier 2027.

## Équipe

Trois étudiants en BTS SIO. Deux profils SISR (réseau/système), un profil SLAM (développement). Niveau : première année. Explique les choix techniques, ne te contente pas de donner une commande.

## Architecture

- La passerelle (GL.iNet Flint 2 sous OpenWrt officiel + openNDS) se branche sur un port libre de la box du restaurant et crée un Wi-Fi clients à part.
- Les clients Wi-Fi n'atteignent qu'Internet : toutes les adresses privées du réseau du restaurant sont bloquées. Les clients sont isolés entre eux.
- La passerelle ouvre un tunnel WireGuard vers notre VPS. Aucun port n'est ouvert sur la box du restaurant.
- Le VPS héberge : portail captif + back-office (Flask), PostgreSQL, journaux légaux, supervision (Uptime Kuma). Tout en Docker Compose derrière Nginx.
- Portail hébergé en HTTPS sur le VPS via openNDS FAS niveau 3 ou 4 (démon authmon). Plan B : portail local sur le routeur.
- Règle absolue : on ne modifie rien sur le réseau existant du restaurant. Débrancher la passerelle = retour à l'état initial.

## Structure du dépôt

```
docs/      cadrage, schémas, procédures, decisions.md
gateway/   config OpenWrt/openNDS, script d'installation
server/    docker-compose, nginx, wireguard, journaux, supervision
portal/    application Flask (portail clients + back-office)
```

## Pile technique

- Passerelle : OpenWrt (stable), openNDS 10.x, WireGuard, SQM pour le débit.
- Serveur : Debian, Docker Compose, Nginx (TLS Let's Encrypt), WireGuard, Uptime Kuma.
- Application : Python 3, Flask, PostgreSQL, SQLAlchemy. Pas de framework JS lourd : HTML + CSS + un minimum de JS.
- Tests : pytest pour le portail.

## Conventions

- Branche par tâche, préfixée par le domaine : `gateway/`, `server/`, `portal/`, `docs/`.
- Messages de commit : `domaine: description courte` (ex. `portal: page d'accueil du portail`).
- Jamais de push direct sur `main`. Pull request + 1 approbation obligatoires.
- Toute décision structurante va dans `docs/decisions.md` (date, décision, pourquoi).
- Code et commentaires en français ; noms de variables et de fonctions en anglais.
- Scripts shell : bash, `set -euo pipefail`, vérifiés avec shellcheck.

## Secrets et sécurité

- Dépôt public. Aucun mot de passe, clé WireGuard, jeton, adresse IP du restaurant ni donnée client dans le dépôt.
- Secrets dans `.env` (ignoré) ; fournir un `.env.example` avec des valeurs factices.
- Si on te demande d'écrire un secret dans un fichier versionné, refuse et propose `.env`.

## Cadre légal (CNIL) — à respecter dans le code

- Conserver 1 an, puis purger : IP attribuée et port, adresse MAC, date/heure/durée de connexion.
- Ne jamais journaliser le contenu des échanges, les sites consultés ni les requêtes DNS des clients.
- Pas d'identification obligatoire des clients (sinon obligation de conserver l'identité 5 ans). E-mail facultatif, case non cochée par défaut, stocké séparément des journaux légaux.
- Le portail affiche une information claire : ce qui est conservé, pourquoi, combien de temps, qui y accède, comment exercer ses droits.

## Hors périmètre v1

Connexion par SMS ou réseaux sociaux, publicité, paiement, application mobile, gestion multi-restaurants, modification du réseau existant du restaurant. Ne pas proposer ces fonctionnalités sauf demande explicite.

## Commandes utiles

```bash
# Portail (dans portal/)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
flask --app app run --debug
pytest

# Serveur (dans server/)
docker compose up -d
docker compose logs -f
```

Ces commandes seront mises à jour au fur et à mesure que les dossiers se remplissent.
