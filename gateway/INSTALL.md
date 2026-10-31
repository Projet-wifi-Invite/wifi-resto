# gateway/ — installation et configuration de la passerelle

Ce document journalise la mise en place d'OpenWrt + openNDS, validée en laboratoire (VM VirtualBox, pas encore sur le Flint 2 réel). Les fichiers de config prêts à coller sont dans [`configs/`](configs/).

**État : validation de la mécanique openNDS/DHCP/pare-feu en VM. Pas encore testé sur le Flint 2 (GL-MT6000), pas encore de vrai Wi-Fi, FAS pas encore branché au portail (faskey/VPS manquants).** Voir § 7 pour ce qui reste à faire avant un vrai déploiement.

## 1. Image et VM de lab

- OpenWrt 25.12.6 x86-64 (`openwrt-25.12.6-x86-64-generic-ext4-combined.img`, sha256 vérifié), converti en `.vdi`, démarré dans VirtualBox avec deux cartes réseau : NAT (simule le WAN/la box du resto) et Host-only (simule le Wi-Fi clients).
- **Cette image n'est pas celle du Flint 2.** Le Flint 2 (GL-MT6000) a un SoC MediaTek MT7986 : il faudra l'image OpenWrt officielle pour cette cible matérielle, pas celle-ci. La config logicielle (openNDS, pare-feu, DHCP) devrait se transposer directement ; le mapping des interfaces réseau (noms de ports, radios Wi-Fi) non.
- Piège : l'image mono-NIC bridge `br-lan` sur la première interface par défaut. Avec deux cartes, il faut corriger explicitement quelle interface est le LAN (voir `configs/network`).

## 2. Paquets

Cette version d'OpenWrt utilise `apk`, pas `opkg` (changement récent dans la branche 25.x — à vérifier si le Flint 2 tourne sur la même branche).

```sh
apk update
apk add opennds dnsmasq-full
apk del dnsmasq   # dnsmasq de base : pas de support nftset/walled-garden, openNDS ne devient jamais autoritaire sur le DHCP sans ça
/etc/init.d/odhcpd stop
/etc/init.d/odhcpd disable   # laisser dnsmasq seul gérer le DHCPv4, évite un second répondeur concurrent
```

## 3. Réseau — `configs/network`

Voir le fichier complet. Résumé du principe : le pont `br-lan` (destiné à devenir `br-guest` en vrai déploiement, cf. `docs/integration-opennds.md`) doit être sur l'interface physique du **Wi-Fi clients**, pas sur celle de la box. Une interface `wan` séparée (DHCP) pointe vers la box du restaurant.

## 4. Pare-feu — `configs/firewall-additions.txt`

Trois protections ajoutées au pare-feu par défaut d'OpenWrt (toutes vérifiées par compteurs nftables, pas seulement par la config) :

1. **Isolation des clients** : `forward='REJECT'` sur la zone `lan` — bloque le trafic routé entre deux clients tout en gardant `lan → wan` ouvert.
   **Limite importante** : ça ne protège que le trafic *routé*. Sur un AP Wi-Fi réel, l'isolation clients doit AUSSI être activée côté radio (`option isolate '1'` par SSID dans `/etc/config/wireless`) — la règle pare-feu seule ne suffit pas, c'est une protection en profondeur, pas le mécanisme principal. Non vérifiable en VM (un seul segment L2 partagé, pas de vrais ports radio séparés).
2. **Offloading désactivé** (`flow_offloading` et `flow_offloading_hw` à `0`) — contourne le bug matériel MT7986 mentionné par William dans le retour du 29 oct.
3. **Plages privées RFC1918 bloquées en sortie WAN** (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) — empêche un client Wi-Fi de pivoter vers le réseau interne du resto (caisse, TPE, bureau) si jamais il atteint une IP privée derrière la box. Complète la règle "isolation inverse" prévue pour le 13 nov (qui elle protège dans l'autre sens : la passerelle ne doit joindre que la box).

Reste à faire (pas cette semaine, cf. feuille de route) : isolation inverse (la passerelle elle-même ne doit joindre que la box, jamais le reste du réseau du resto) et débit par client (SQM + plafonds 2000/8000 kbit/s, qui doivent venir du portail d'après `docs/integration-opennds.md` §4, pas être codés en dur côté passerelle).

## 5. openNDS — `configs/opennds-fas-production` et `configs/opennds-local-fallback`

Deux fichiers :

- **`opennds-fas-production`** : la config cible, conforme au contrat défini dans `docs/integration-opennds.md` (FAS niveau 4, authmon, portail sur le VPS). **Contient des valeurs à compléter** (`faskey` fourni par Rudy le 13 nov au plus tard, `fasremotefqdn`/`fasremoteip` une fois le VPS de Rudy monté). Ne pas committer de vraies valeurs ici — dépôt public.
- **`opennds-local-fallback`** : ce qui a été réellement testé en labo (portail local, page "Click to continue" générique d'openNDS, sans FAS). Sert de filet de sécurité / plan B si la décision du 3 nov retient "portail sur le routeur" plutôt que VPS (`CLAUDE.md` indique VPS comme plan A actuel), et sert de base de test pour valider la mécanique DHCP/pare-feu sans dépendre du VPS/FAS.

Dans les deux cas : `/etc/init.d/opennds enable && /etc/init.d/opennds restart`, puis vérifier `logread -f` (pas d'erreur `ERROR:` côté authmon pour la version FAS) et `ndsctl status`.

**Piège DHCP découvert en labo**, susceptible de se reproduire sur le Flint 2 si jamais plusieurs services DHCP coexistent (ex. test avec un réseau Wi-Fi existant, ou odhcpd pas bien désactivé) : openNDS refuse tout client dont l'IP n'apparaît pas dans le fichier de leases dnsmasq (`logread` : `IP not allocated by dhcp [x.x.x.x]`), même si ce client a une IP qui fonctionne. Trois causes trouvées en pratique, à vérifier si ça se reproduit :
1. dnsmasq de base sans `dnsmasq-full` (pas de support nftset) → openNDS log `Dnsmasq reload failed!` et ne devient jamais autoritaire.
2. `/tmp/dhcp.leases` appartenant à `root` sans droit d'écriture pour l'utilisateur `dnsmasq` (le process droppe ses privilèges après démarrage) → le fichier reste vide pour toujours. `chown dnsmasq:dnsmasq /tmp/dhcp.leases`.
3. Un deuxième serveur DHCP répond avant dnsmasq (en labo : VirtualBox lui-même ; sur le terrain : surtout vérifier qu'il n'y a qu'un seul DHCP sur le segment Wi-Fi clients). Le propre self-test de dnsmasq au démarrage (`/etc/init.d/dnsmasq`, sonde `udhcpc -s /bin/true`) détecte un concurrent et se met en retrait silencieusement.

## 6. Comment on a vérifié que ça marche (méthodologie)

- VM cliente Alpine Linux séparée (pas la machine de dev) pour simuler un vrai client Wi-Fi avec un vrai bail DHCP — tester depuis la machine de l'admin (IP fixe, jamais vue comme cliente DHCP légitime) donne des faux négatifs.
- Les clients non authentifiés : openNDS intercepte TOUT le port 80/443 et sert sa page captive, quelle que soit la destination demandée. Donc un test applicatif (`curl`/`wget`) vers une IP quelconque "réussit" toujours tant que le client n'est pas authentifié — inutile pour tester d'autres règles de pare-feu (comme le blocage des plages privées). Pour tester le vrai chemin de forwarding, authentifier le client de test manuellement : `ndsctl auth <mac>` ; remettre en pré-auth ensuite avec `ndsctl deauth <mac>`.
- Préférer les compteurs nftables (`nft list chain inet fw4 forward_lan`) au résultat d'une requête applicative pour vérifier qu'une règle de pare-feu fonctionne : plus fiable, surtout en VM où le NAT VirtualBox a ses propres soucis de fiabilité réseau (timeouts intermittents indépendants du pare-feu testé).
- Rendu réel de la page captive (pas juste en texte) : navigateur Chromium headless dans la VM cliente (`chromium-browser --headless --disable-gpu --no-sandbox --screenshot=...`), capture exportée. Nécessite d'augmenter la RAM de la VM (512 Mo insuffisant pour chromium).

## 7. Ce qui reste avant un vrai déploiement

- [ ] Image OpenWrt officielle pour le Flint 2 (MT7986), pas l'image x86 de ce labo
- [ ] Décision du 3 nov : portail VPS (FAS niveau 4) ou portail local — change `configs/opennds-*` à utiliser
- [ ] `faskey` (Rudy, 13 nov) + endpoint VPS (`fasremotefqdn`/`fasremoteip`)
- [ ] Vrai Wi-Fi : SSID, canaux, pays radio FR, `option isolate '1'` (isolation clients niveau radio)
- [ ] Isolation inverse (passerelle ne joint que la box) — prévu 13 nov
- [ ] Débit par client (SQM) — valeurs côté portail selon `docs/integration-opennds.md` §4, pas câblées ici
- [ ] Mot de passe root (actuellement vide en labo — à ne JAMAIS laisser ainsi sur du matériel réel)
- [ ] Visite du 17 nov : couverture réelle, débit de la box, emplacement du boîtier → dimensionnement final
