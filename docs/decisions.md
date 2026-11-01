# Journal des décisions

| Date | Décision | Pourquoi |
|---|---|---|
| 2026-10-29 | Dépôt public sur GitHub, organisation Projet-wifi-Invite | Protection de branche gratuite, vitrine portfolio |
| 2026-10-29 | Branche main protégée : PR + 1 approbation obligatoires | Relecture systématique, personne ne pousse directement |
| 2026-10-29 | Aucun secret dans le dépôt (.env, clés, wg*.conf) | Dépôt public |
| 2026-10-29 | Portail en openNDS FAS niveau 4 (HTTPS, base64, démon authmon) | Même sécurité que le niveau 3 (HTTPS) sans installer PHP sur le routeur |
| 2026-10-29 | Débits et durée de session de chaque client fixés par le portail, dans la ligne d'autorisation | Un seul endroit à modifier, réglable par restaurant depuis le serveur |
| 2026-10-29 | Passerelle GL.iNet Flint 2 sous OpenWrt officiel, offloading matériel désactivé | Le flow offloading du MT7986 contourne SQM et les plafonds de débit |
| 2026-10-29 | Couleur principale du portail `#3b6f9c`, textes « chez Cœur de Beurre » | Les couleurs du logo (`#ffd87b`, `#93b9d8`) sont trop claires pour du texte lisible |
| 2026-10-29 | Pas de migrations pendant le labo, Flask-Migrate (Alembic) avant la production | Aller vite tant qu'il n'y a pas de données réelles ; aucune base de production recréée à la main |
| 2026-10-29 | À l'acceptation, le portail vérifie que sha256(gatewayname) = `Restaurant.gateway_hash`, sinon 403 | Détecte une passerelle mal configurée dès le premier client ; un restaurant = une passerelle en v1 |
| 2026-10-29 | Portail en français seulement en v1 ; anglais, espagnol et italien en v2 | Clientèle de vacanciers, mais priorité au pilote |
| 2026-10-30 | Identifiants du code en anglais ; commentaires, docstrings, messages et noms de tests en français | Noms standards pour le code, explications lisibles par toute l'équipe et le jury |
| 2026-10-30 | Restaurant sans `gateway_hash` configuré : `/fas/accept` répond 503 | Une erreur de configuration doit se voir, pas laisser passer n'importe quelle passerelle |
| 2026-10-30 | authmon : passerelle inconnue ou `gatewayhash` invalide → 403 | Refus visible dans `logread` côté routeur, aucune donnée renvoyée à un inconnu |
| 2026-10-30 | Autorisations non acquittées purgées après 60 s ; 4 lignes au plus par réponse authmon | Un client parti ne doit pas bloquer la file (authmon traite 4 clients par cycle) |
