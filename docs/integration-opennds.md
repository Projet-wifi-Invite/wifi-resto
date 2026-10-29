# Intégration openNDS ↔ portail : le contrat entre la passerelle et le serveur

Ce document décrit exactement ce que la passerelle (openNDS sur OpenWrt, dossier `gateway/`) envoie au portail (Flask, dossier `portal/`) et ce que le portail doit renvoyer. Il est tiré du code source d'openNDS **10.3.1** (`forward_authentication_service/fas-hid/fas-hid-https.php`, `libs/authmon.sh`, `libs/post-request.php`, `src/http_microhttpd.c`, `src/client_list.c`) et de la [documentation FAS](https://opennds.readthedocs.io/en/stable/fas.html).

Côté passerelle : Gabriel. Côté portail : Kilian. Le secret partagé (`faskey`) : Rudy le génère et le distribue par le gestionnaire de mots de passe, jamais par Discord ni dans Git.

## 1. Le choix : FAS niveau 4

openNDS propose 5 niveaux (`fas_secure_enabled` 0 à 4). On retient le **niveau 4** :

| Niveau | Protocole | Données envoyées | Retour vers openNDS | Pré-requis routeur |
| --- | --- | --- | --- | --- |
| 3 | HTTPS | chiffrées AES-256-CBC | démon authmon | `php-cli` + `php-openssl` sur le routeur |
| **4** | **HTTPS** | **encodées base64** | **démon authmon** | **aucun (pas de PHP)** |

Pourquoi le 4 et pas le 3 : le résultat est le même (HTTPS, traversée du NAT par authmon), sans installer PHP sur le routeur. Les données du niveau 4 ne sont pas chiffrées, mais elles transitent en HTTPS, et elles ne contiennent rien de secret : le jeton client réel (`tok`) n'est jamais envoyé, seulement son empreinte `hid`. La sécurité repose sur `faskey`, qui ne circule jamais.

## 2. Vue d'ensemble

```
Client Wi-Fi                 Passerelle (openNDS)                 Portail (Flask, VPS)
     │                              │                                      │
     │ 1. ouvre une page web        │                                      │
     │─────────────────────────────►│                                      │
     │ 2. redirection 302 vers      │                                      │
     │    https://portail/…?fas=b64 │                                      │
     │◄─────────────────────────────│                                      │
     │ 3. GET /…?fas=b64 (via Internet, le portail est dans le walled garden)│
     │─────────────────────────────────────────────────────────────────────►│
     │ 4. page « J'accepte »                                                │
     │◄─────────────────────────────────────────────────────────────────────│
     │ 5. POST acceptation                                                  │
     │─────────────────────────────────────────────────────────────────────►│
     │                              │   le portail calcule rhid et le met  │
     │                              │   dans la file d'attente de la       │
     │                              │   passerelle                         │
     │                              │ 6. authmon : POST auth_get=view      │
     │                              │    toutes les 5 s                    │
     │                              │─────────────────────────────────────►│
     │                              │ 7. réponse : "* rhid 0 0 0 0 0 custom"│
     │                              │◄─────────────────────────────────────│
     │                              │ 8. ndsctl auth rhid … → client ouvert │
     │                              │ 9. authmon : POST auth_get=view      │
     │                              │    payload = acklist "* rhid"        │
     │                              │─────────────────────────────────────►│
     │                              │ 10. réponse "ack", file vidée        │
     │ 11. Internet ouvert          │                                      │
```

Délai entre le clic du client et l'ouverture d'Internet : au plus `nat_traversal_poll_interval` (5 s par défaut). La page « merci » du portail doit donc patienter quelques secondes avant d'annoncer la connexion.

## 3. Étape 3 : ce que le portail reçoit (requête du client)

```
GET https://<fasremotefqdn>/<faspath>?fas=<base64>
```

Une fois décodé, `fas` est une chaîne de paires `clé=valeur` séparées par **une virgule et un espace** (`", "`), dans cet ordre (source : `http_microhttpd.c`, niveau 1/4) :

| Clé | Contenu | Exemple | Usage portail |
| --- | --- | --- | --- |
| `hid` | empreinte sha256 du jeton client, générée par openNDS | `3f2a…` (64 hex) | **indispensable** : sert à calculer `rhid` |
| `clientip` | IP attribuée au client sur le Wi-Fi invité | `10.20.0.42` | journal légal |
| `clientmac` | adresse MAC du client | `aa:bb:cc:dd:ee:ff` | journal légal |
| `client_type` | type détecté | `cpd_can` | stats (facultatif) |
| `cpi_query` | infos Captive Portal API | | ignoré |
| `gatewayname` | nom de la passerelle, **URL-encodé** | `Coeur%20de%20Beurre` | identifie le restaurant |
| `gatewayurl` | URL de la page statut openNDS | `http://10.20.0.1:2050/` | lien « statut » (facultatif) |
| `version` | version openNDS | `10.3.1` | log |
| `gatewayaddress` | IP:port de la passerelle | `10.20.0.1:2050` | |
| `gatewaymac` | MAC de la passerelle | | identifiant robuste de la passerelle |
| `originurl` | URL que le client voulait ouvrir, URL-encodée | | redirection finale (facultatif) |
| `clientif` | interface du client | `wlan0` ou `wlan0 <mac mesh> <if>` | zone (salle / terrasse si 2 SSID) |
| `themespec` | chemin themespec | | ignoré |
| custom | paramètres définis dans `fas_custom_parameters_list` | `resto=coeur-de-beurre` | **slug du restaurant** |

Exemple de chaîne décodée :

```
hid=3f2a…, clientip=10.20.0.42, clientmac=aa:bb:cc:dd:ee:ff, client_type=cpd_can, cpi_query=, gatewayname=Coeur%20de%20Beurre, gatewayurl=http%3A%2F%2F10.20.0.1%3A2050%2F, version=10.3.1, gatewayaddress=10.20.0.1:2050, gatewaymac=94:83:c4:…, originurl=http%3A%2F%2Fconnectivitycheck…, clientif=wlan0, themespec=, resto=coeur-de-beurre
```

**Décision** : le portail identifie le restaurant par le paramètre custom `resto=<slug>`, pas par `gatewayname` (qui peut contenir des accents et changer). Gabriel le déclare côté passerelle, voir § 7.

Le portail doit **garder `fas` tel quel** dans un champ caché du formulaire : la requête POST d'acceptation le renvoie, et c'est là qu'on relit `hid`.

## 4. Étape 5 : ce que fait le portail à l'acceptation

1. Décoder `fas`, relire `hid`, `clientip`, `clientmac`, `gatewaymac`, `resto`.
2. Calculer le **return hash id** :
   ```
   rhid = sha256( hid + faskey )        # concaténation simple, sans séparateur, hex minuscule
   ```
   Source : `client_list.c` ligne 381 (`"%s%s", ptr->hid, config->fas_key`) et `fas-hid-https.php` ligne 515.
3. Enregistrer la session (`ConnectionSession`) et le **journal légal** (`LegalLog` : IP, MAC, date, `purge_after` = +1 an).
4. Déposer dans la **file d'attente de la passerelle** une ligne d'autorisation :
   ```
   <rhid> <sessionlength> <uploadrate> <downloadrate> <uploadquota> <downloadquota> <custom>
   ```
   | Champ | Unité | Valeur v1 | Sens |
   | --- | --- | --- | --- |
   | `sessionlength` | minutes | `240` | déconnexion après 4 h |
   | `uploadrate` | kbit/s | `2000` | plafond montant 2 Mbit/s |
   | `downloadrate` | kbit/s | `8000` | plafond descendant 8 Mbit/s |
   | `uploadquota` | ko | `0` | pas de quota de volume |
   | `downloadquota` | ko | `0` | pas de quota de volume |
   | `custom` | base64 | `base64("resto=coeur-de-beurre")` | transmis au script BinAuth du routeur |

   `0` = illimité. Les plafonds de débit par client sont donc **décidés par le portail**, pas par le routeur : on pourra les changer sans toucher à la passerelle.
5. Afficher la page « merci », qui patiente (JS, 5 à 10 s) puis propose avis Google et Instagram.

La file d'attente est **par passerelle**, indexée par `gatewayhash` (§ 5). En base : table `pending_auths(gateway_hash, rhid, line, created_at)`, ou un simple dictionnaire en mémoire pour le labo.

## 5. Étapes 6 à 10 : le dialogue avec authmon

Le démon `authmon.sh` tourne sur le routeur et interroge le portail **toutes les 5 secondes** (`nat_traversal_poll_interval`, défaut 5, bornes 1-59). Il envoie :

```
POST https://<fasremotefqdn>/<faspath>
Content-Type: application/x-www-form-urlencoded
User-Agent: openNDS(authmon;NDS:10.3.1;)

auth_get=<action>&gatewayhash=<sha256 du gatewayname URL-encodé>&payload=<base64>
```

(Si le routeur n'a pas PHP, authmon passe par `wget` et envoie les **mêmes trois paramètres en GET**. Le portail doit accepter les deux : lire `auth_get`, `gatewayhash`, `payload` dans `request.values`.)

`gatewayhash = sha256(gatewayname URL-encodé)`, calculé par le routeur au démarrage (`main.c` ligne 743). Le portail le recalcule depuis `gatewayname` reçu à l'étape 3 pour savoir dans quelle file ranger le client.

| `auth_get` | Quand | `payload` décodé | Réponse attendue du portail |
| --- | --- | --- | --- |
| `clear` | au démarrage d'openNDS | `none` | vider la file de cette passerelle, réponse vide |
| `view` | toutes les 5 s | `none` | la file, format § 5.1, **sans la vider** |
| `view` | juste après, si des clients ont été ouverts | `* rhid1 rhid2…` (acklist) | retirer ces rhid de la file, répondre `ack` |
| `list` | variante : lister et vider d'un coup | `none` | la file, puis la vider (authmon ne l'utilise pas par défaut) |
| `deauthed` | quand un client est déconnecté (BinAuth) | infos de déconnexion | journaliser (`disconnected_at` du journal légal), répondre `ack` |
| `custom` | chaîne libre depuis BinAuth | texte | journaliser, répondre `ack` |

Si `gatewayhash` est absent : réponse vide, rien d'autre. Si la file est vide : réponse vide ou `*`.

### 5.1 Format de la réponse à `view` / `list`

Texte brut, **une seule ligne**, qui commence par `*`, puis chaque ligne d'autorisation **URL-encodée** (`rawurlencode`), séparées par des espaces :

```
* 9c1f…%20240%202000%208000%200%200%20cmVzdG89Y29ldXItZGUtYmV1cnJl
```

authmon décode le `%20` en espaces et lance `ndsctl auth <rhid> <sessionlength> <uploadrate> <downloadrate> <uploadquota> <downloadquota> <custom>`. Il traite **au plus 4 clients par cycle** (limite de Busybox), les autres attendent le cycle suivant.

### 5.2 Erreurs à prévoir

- Un `rhid` resté dans la file plus de 60 s sans ack : le client a fermé la page ou le routeur ne joint pas le portail. Le supprimer et le compter (métrique « échecs d'authentification »).
- authmon qui ne vient plus : le portail doit l'exposer (`last_seen` par passerelle) pour la supervision de Rudy (Uptime Kuma peut interroger `/health?gateway=<hash>`).

## 6. Sécurité

- `faskey` : 64 caractères hex (`openssl rand -hex 32`), identique dans `/etc/config/opennds` et dans le `.env` du portail (`FAS_KEY=`). **Jamais dans Git.**
- Le portail refuse toute requête `fas` dont le décodage ne donne pas un `hid` de 64 hex.
- Le portail refuse toute requête `auth_get` sans `gatewayhash` connu (liste des passerelles en base, `Restaurant.gateway_id` = gatewayhash).
- Le portail ne stocke pas `originurl` (c'est un site visité : hors journal légal).
- HTTPS obligatoire : certificat Let's Encrypt sur le VPS (Rudy). Le routeur doit avoir `ca-bundle` installé pour valider le certificat (sinon authmon log `ERROR:`).

## 7. Configuration côté passerelle (Gabriel)

Dans `/etc/config/opennds` :

```
option enabled '1'
option gatewayname 'Coeur de Beurre'
option gatewayinterface 'br-guest'           # l'interface du Wi-Fi invité
option fas_secure_enabled '4'
option fasport '443'
option fasremotefqdn 'portail.<notre-domaine>'
option fasremoteip '<IP publique du VPS>'
option faspath '/fas'
option faskey '<64 hex, fourni par Rudy>'
option fas_custom_parameters_list 'resto=coeur-de-beurre'
option nat_traversal_poll_interval '5'
option checkinterval '15'
option sessiontimeout '240'
list walledgarden_fqdn_list 'portail.<notre-domaine>'
```

Puis `service opennds restart`, et vérifier dans `logread -f` que authmon démarre et ne logue pas `ERROR:`.

## 8. Routes du portail à implémenter (Kilian)

| Route | Méthode | Rôle |
| --- | --- | --- |
| `/fas` | GET | **point d'entrée openNDS** : décode `fas`, charge le restaurant via `resto`, affiche la page d'acceptation |
| `/fas` | POST (si `auth_get` présent) | dialogue authmon (§ 5) |
| `/fas/accept` | POST | acceptation : calcule `rhid`, écrit session + journal légal, met en file, affiche « merci » |
| `/portal/<slug>` | GET | page de prévisualisation sans openNDS (déjà en place, garde `client_hid="dev-hid"`) |
| `/health` | GET | supervision |

Un **simulateur de passerelle** (`portal/tools/fake_gateway.py`) est à écrire en sprint 1 : il construit un `fas` base64 avec un `hid` aléatoire, ouvre la page, puis joue authmon (`view`, puis `view` avec acklist) et vérifie que la ligne d'autorisation reçue contient `sha256(hid+faskey)`. Ça permet de tester tout le § 5 sans routeur.

## 9. Ce qui reste à trancher

- [ ] Deux SSID (salle / terrasse) ou un seul ? Si deux, `clientif` permet des plafonds différents.
- [ ] `sessionlength` : 240 min est un choix de départ, à ajuster avec le gérant.
- [ ] Faut-il envoyer `deauthed` au portail (niveau 4 : à vérifier en labo, la doc ne le garantit que pour le niveau 3) ? Sinon, `disconnected_at` restera vide et la durée de connexion sera estimée par `sessionlength`.
