# wifi-resto

Wi-Fi invité clé en main pour restaurants et commerces : un boîtier qui fournit un Wi-Fi clients **isolé** du réseau de l'établissement, un **portail captif** aux couleurs du restaurant, et la **conservation légale des journaux de connexion** (1 an) gérée pour le gérant.

Projet d'équipe de 3 étudiants en BTS SIO (2 SISR, 1 SLAM), avec un pilote dans un restaurant partenaire à Rennes.

## Ce que fait le produit

- Wi-Fi clients séparé : les clients n'atteignent jamais la caisse, le TPE ni le bureau.
- Portail captif au nom du restaurant, avec lien vers ses avis Google.
- Débit plafonné par client : le Wi-Fi des clients ne ralentit pas la caisse.
- Journaux de connexion conservés 1 an puis purgés, conformément aux obligations CNIL.
- Back-office pour le gérant : fréquentation, contacts newsletter (opt-in), état du boîtier.

## Architecture

```
Box Internet (FAI)
   │
   ├── Réseau du restaurant (caisse, TPE, bureau)  ← on n'y touche pas
   │
   └── Passerelle (GL.iNet Flint 2, OpenWrt + openNDS)
         ├── Wi-Fi clients (réseau isolé, portail captif, débit plafonné)
         └── Tunnel WireGuard ──► Serveur VPS (UE)
                                    ├── Portail + back-office (Flask)
                                    ├── Base PostgreSQL
                                    ├── Journaux légaux (1 an)
                                    └── Supervision (Uptime Kuma)
```

Règle d'or : débrancher la passerelle remet le restaurant exactement dans son état d'avant.

## Structure du dépôt

```
wifi-resto/
├── docs/      cadrage, schémas réseau, procédures, journal des décisions
├── gateway/   configuration OpenWrt et openNDS, script d'installation
├── server/    Docker Compose, Nginx, WireGuard, journaux, supervision
└── portal/    application Flask : portail clients + back-office
```

## Pile technique

| Couche | Choix |
| --- | --- |
| Passerelle | GL.iNet Flint 2 (GL-MT6000), OpenWrt officiel, openNDS |
| Accès distant | WireGuard (la passerelle appelle le serveur, aucun port ouvert chez le resto) |
| Serveur | VPS OVHcloud ou Hetzner, Debian, Docker Compose |
| Application | Python / Flask, PostgreSQL, Nginx |
| Supervision | Uptime Kuma |

## Équipe et rôles

| Rôle | Domaine | Dossier |
| --- | --- | --- |
| SLAM | Coordination, portail, back-office, relation restaurant | `portal/` |
| SISR 1 | Réseau, Wi-Fi, passerelle OpenWrt/openNDS | `gateway/` |
| SISR 2 | Serveur, sécurité, WireGuard, journaux légaux, supervision | `server/` |

## Comment on travaille

- Une branche par tâche, nommée par domaine : `gateway/…`, `server/…`, `portal/…`, `docs/…`.
- Jamais de push direct sur `main` : chaque changement passe par une pull request relue par un autre membre.
- Les tâches sont dans les Issues et le tableau Projects de l'organisation.
- Chaque décision est notée dans [`docs/decisions.md`](docs/decisions.md).
- Réunion hebdo de 30 minutes, démo toutes les deux semaines.

### Cycle de travail

```bash
git switch main && git pull
git switch -c portal/ma-tache
# ... travail ...
git add . && git commit -m "portal: description courte"
git push -u origin portal/ma-tache
# puis ouvrir la pull request sur GitHub
```

## Secrets

Ce dépôt est **public**. Aucun mot de passe, aucune clé WireGuard, aucun jeton, aucune donnée du restaurant ne doit y entrer. Les secrets vivent dans des fichiers `.env` ou `secrets/`, ignorés par Git. Une clé qui fuit se régénère : la supprimer de l'historique ne suffit pas.

## Cadre légal

Un établissement qui offre un accès Internet au public doit conserver 1 an les données techniques de connexion (IP, identifiant de l'appareil, date, heure, durée), sans identifier ses clients ni conserver le contenu des échanges ou les sites consultés. Voir [CNIL — Fournir un accès internet public](https://www.cnil.fr/fr/fournir-un-acces-internet-public-quelles-obligations).

## Licence

À définir au kickoff (voir `docs/decisions.md`).
