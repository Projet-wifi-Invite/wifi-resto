# Budget du pilote

Proposition de budget pour le pilote wifi-resto (restaurant partenaire à Rennes, à partir de janvier 2027), à valider au kickoff, au plus tard le 4 novembre 2026.

**En une phrase :** on prévoit d'acheter tout le matériel et l'hébergement pour **≈ 215 à 306 €**, avec un plafond de **300 €** (100 € chacun : Kilian, Gabriel, Rudy).

---

## Ordre du jour : 5 décisions

- [ ] 1. Choisir l'hébergeur du VPS
- [ ] 2. Choisir qui ouvre le compte de l'hébergeur
- [ ] 3. Choisir où stocker la sauvegarde
- [ ] 4. Choisir le nom de domaine et qui l'achète
- [ ] 5. Valider le plafond de 300 €

Chaque décision ci-dessous suit le même modèle : **proposition**, **éléments pour décider**, puis **décision** (à remplir en réunion).

---

## Décision 1 : quel hébergeur pour le VPS ?

**Proposition :** OVHcloud VPS-1.

**OVHcloud VPS-1 (recommandé)**

- Prix : **4,57 € TTC par mois**, soit **≈ 55 € sur 12 mois**
- Puissance : 2 vCores, 4 Go RAM, 40 Go NVMe
- Sauvegarde quotidienne incluse
- Données hébergées en **France**
- Support en français
- Pas de problème de disponibilité connu

**Hetzner CX23**

- Prix : ≈ 7,13 € TTC par mois, soit ≈ 86 € sur 12 mois
- Puissance : 2 vCPU, 4 Go RAM, 40 Go NVMe
- Données hébergées en Allemagne ou en Finlande
- Gamme économique indisponible à la commande : signalée en septembre 2026, toujours le cas le 30 octobre 2026

**Pourquoi OVHcloud :** environ 30 € moins cher sur l'année, données en France, pas de risque de rupture à la commande.

> Prix relevés le 30 octobre 2026 : à revérifier sur les sites officiels avant de commander. OVHcloud : 3,81 € HT, prix « à partir de », probablement avec engagement 12 mois. Hetzner : 5,49 € HT + 0,50 € pour l'adresse IPv4.

**Décision :** …

---

## Décision 2 : au nom de qui ouvrir le compte de l'hébergeur ?

**Proposition :** au nom d'un membre, avec un accès pour au moins un deuxième membre.

**Pourquoi c'est important :** le VPS contiendra les journaux légaux, conservés 1 an. Si une seule personne a accès au compte et qu'elle est indisponible, l'équipe est bloquée.

**Décision :** compte au nom de … ; accès aussi pour …

---

## Décision 3 : où stocker la sauvegarde chiffrée hors du VPS ?

Ce poste n'était pas prévu dans le cadrage initial.

Le VPS OVHcloud inclut une sauvegarde quotidienne, mais elle est stockée dans le même datacenter que le VPS : elle ne remplace pas une sauvegarde hors du VPS.

- **Option A :** PC ou Raspberry Pi d'un membre, **0 €**
- **Option B :** stockage payant, **jusqu'à 40 €**

**Décision :** …

---

## Décision 4 : quel nom de domaine, et qui l'achète ?

**Coût :** ≈ 5 à 15 € par an, selon l'extension et le registraire.

Exemple chez OVHcloud (relevé le 30 octobre 2026) :

- **.fr :** 4,99 € la première année, puis 7,79 € par an
- **.com :** 7,99 € la première année, puis 14,29 € par an

**Décision :** nom … ; acheté par …

---

## Décision 5 : valide-t-on le plafond de 300 € ?

Coûts estimés :

- Routeur GL.iNet Flint 2 (GL-MT6000) : 125 à 166 €
- VPS OVHcloud VPS-1 (12 mois) : ≈ 55 €
- Nom de domaine : ≈ 5 à 15 €
- Câbles, multiprise, étiquettes : ≈ 20 €
- QR codes de table : ≈ 10 €
- Stockage pour la sauvegarde : 0 à 40 €
- **Total : ≈ 215 à 306 €**

**À savoir :** on ne dépasse 300 € que dans le pire cas (routeur au prix fort **et** sauvegarde payante). Or le routeur est **aujourd'hui au prix fort** : 163,99 € sur Amazon.fr et 165,95 € sur la boutique officielle GL.iNet (relevé le 30 octobre 2026). Il descendrait vers 125-130 € en promo, mais aucune promo n'était en cours au relevé. Pour rester sous le plafond, il faut attendre une promo ou choisir la sauvegarde gratuite.

**Décision :** …

---

## Après le kickoff : registre des dépenses

**Règle :** toute dépense est notée ici **avant** l'achat. Après l'achat, on complète le coût réel, qui a payé et la date.

**Dépôt public :** uniquement des prénoms et des montants. Jamais de donnée bancaire, d'identifiant, de mot de passe ni de facture.

### Routeur GL.iNet Flint 2 (GL-MT6000)

- Coût estimé : 125 à 166 € (≈ 164-166 € au prix fort, 125-130 € en promo)
- Coût réel :
- Payé par :
- Date :

### VPS OVHcloud VPS-1 (12 mois)

- Coût estimé : ≈ 55 € (engagement 12 mois à confirmer à la commande)
- Coût réel :
- Payé par :
- Date :

### Nom de domaine

- Coût estimé : ≈ 5 à 15 €/an (selon l'extension et le registraire)
- Coût réel :
- Payé par :
- Date :

### Câbles, multiprise, étiquettes

- Coût estimé : ≈ 20 €
- Coût réel :
- Payé par :
- Date :

### QR codes de table

- Coût estimé : ≈ 10 €
- Coût réel :
- Payé par :
- Date :

### Stockage pour la sauvegarde chiffrée

- Coût estimé : 0 à 40 € (0 € si matériel d'un membre)
- Coût réel :
- Payé par :
- Date :

### Total

- Coût estimé : **≈ 215 à 306 €**
- Coût réel :
