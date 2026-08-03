# Dépôt de documents par les clients — conception

> **Statut : conception, non développée.** Écrite le 2026-08-03.

## La question à laquelle ce système doit répondre

**Un client peut-il remettre un document, sans que la plateforme devienne un
risque pour lui, pour nous, ou pour les autres clients ?**

Aujourd'hui le flux est à sens unique : le consultant dépose, le client
télécharge. Les six routes du portail client (`portal.py`) sont **toutes en
lecture**.

---

## Trois acteurs différents s'appellent « client »

Les confondre mènerait à une conception fausse.

| Acteur | Dépendance | Dépose aujourd'hui |
|---|---|---|
| **Abonné self-service** | `get_current_user` | Oui — ZIP de code, CSV cibles phishing, CSV apprenants, CSV Dark Web |
| **Client RSSI** | `get_current_rssi_client` | **Non** — portail en lecture seule |
| **Apprenant e-learning** | magic link | Non, et ce n'est pas souhaitable |

Le besoin exprimé porte sur le **client RSSI** et sur l'**abonné en démarche de
conformité**. L'apprenant reste hors périmètre : lui ouvrir un dépôt
multiplierait la surface pour un usage inexistant.

---

## Où le dépôt a du sens, et où il n'en a pas

### 1. Portail RSSI — le besoin le plus net

Le client suivi doit pouvoir **rendre** : politique de sécurité relue, preuve de
mise en œuvre d'une action, inventaire demandé lors d'une visite.

Le modèle existe déjà à moitié. `RssiDeliverable` porte `client_id`, `title`,
`doc_type`, `file_url` — il suffirait d'une **origine** (`consultant` ou
`client`) plutôt que d'une table parallèle. Un livrable reste un livrable ; ce
qui change est qui l'a produit.

### 2. Preuves de conformité NIS2 / ISO 27001 — la valeur la plus forte

Les évaluations stockent 34 critères dans un `items_json` par compte. Aucune
pièce ne peut y être rattachée.

C'est le chantier qui change la nature du produit : **une conformité sans preuve
est une déclaration ; avec preuves, c'est un dossier opposable.** C'est aussi le
plus lourd — il touche le cœur fonctionnel, et `items_json` n'est pas une
structure faite pour porter des pièces jointes.

### 3. Simulation de phishing — rien à déposer

La seule pièce est le CSV de cibles, qui existe déjà et relève de celui qui lance
la campagne. Ajouter un dépôt ici serait une fonctionnalité sans usage.

---

## La question qui commande tout le reste

**Le document est-il lu par un humain, ou traité par le système ?**

- **Lu** — il est stocké, puis téléchargé par le consultant. Les contrôles
  portent sur l'innocuité et la confidentialité.
- **Traité** — parsé pour en extraire quelque chose. La surface d'attaque change
  d'ordre de grandeur : tout analyseur de PDF, de DOCX ou de tableur est un
  vecteur.

**Recommandation : commencer par « lu ».** Un dépôt qui se contente de
transporter un fichier d'un client à son consultant répond déjà au besoin
exprimé, et se sécurise avec des moyens connus.

---

## Ce qui manque côté sécurité

Le socle actuel (`storage.py`) fait déjà plusieurs choses bien : `Path().name`
contre la traversée de répertoire, préfixe UUID contre l'écrasement,
`ContentDisposition: attachment` contre le XSS stocké, URL présignée à une heure
plutôt qu'un service par l'application, et depuis le 2026-08-03 une lecture
bornée sur les quatre points de dépôt.

Trois manques subsistent, par ordre de gravité.

### L'antivirus — le point indéfendable

**Il n'y en a aucun.** Un client dépose un document infecté, le consultant le
télécharge : la plateforme a servi de vecteur. Pour une entreprise qui vend de
la cybersécurité, c'est le manque qui se défend le plus mal — le critère est
celui déjà posé ailleurs : non pas « est-ce légal » mais « défendable devant un
prospect à qui nous vendons de la conformité ».

**Décidé le 2026-08-03 : GuardDuty Malware Protection for S3.** Managé, aucun
service à maintenir, et surtout **la donnée ne sort pas d'AWS** — ce qu'un
service d'analyse tiers ne permettrait pas sans contredire le principe RGPD posé
dans `ANALYTICS.md`.

> ⚠️ **N'activer QUE Malware Protection for S3.** Ce service est disponible seul
> depuis 2024. Activer GuardDuty « en entier » enclencherait aussi l'analyse des
> journaux VPC, DNS et CloudTrail, facturée séparément et sans commune mesure
> avec les quelques centimes ci-dessous. La confusion est facile et coûteuse.

**Le coût ne se pose pas à cette échelle.** Relevé sur la page de tarification
AWS le 2026-08-03 : 0,09 $ par Go analysé et 0,215 $ par millier d'objets, avec
un **palier gratuit mensuel de 1 000 objets et 1 Go** (chiffres Virginie du
Nord ; Paris est légèrement au-dessus). Dix clients déposant dix documents de
2 Mo par mois font 100 objets et 200 Mo — entièrement dans le gratuit. Il
faudrait dépasser mille documents mensuels pour commencer à payer, et deux mille
documents pour trois gigaoctets coûteraient environ 0,40 $.

> AWS a réduit le prix au Go de 85 % en février 2025 (0,60 → 0,09 $). Toute
> estimation antérieure à cette date est fausse d'un facteur sept.

### Les alternatives, et leur vrai prix

**ClamAV en Lambda** — logiciel libre, mais sa base de signatures dépasse le
gigaoctet en mémoire : Lambda largement dimensionnée, mises à jour de signatures
à gérer, démarrages à froid. Gratuit en licence, pas en temps.

**ClamAV dans la tâche ECS** — écarté : la tâche a 2 Go au total, la base en
consommerait la moitié. C'est ce même dimensionnement qui rendait la lecture non
bornée dangereuse.

**VirusTotal et services équivalents** — **à écarter fermement**. Ils conservent
les fichiers soumis et les rendent accessibles à leurs abonnés. Envoyer
l'analyse de risques d'une PME cliente à un tiers serait indéfendable.

Conséquence de conception : **un document n'est téléchargeable qu'une fois
déclaré sain.** Il faut donc un état (`en_analyse` / `sain` / `rejete`) et un
écran qui l'affiche, pas un simple lien. Un fichier infecté est supprimé, jamais
mis en quarantaine consultable.

### Le type MIME vient du client

`validate_upload` compare `content_type` à une liste blanche. Cet en-tête est
envoyé par le navigateur : il se falsifie en une ligne. La liste blanche
d'extensions est du même ordre.

Il faut vérifier les **octets de tête**. Un `.pdf` qui commence par `<!DOCTYPE
html>` doit être refusé, quoi qu'annonce le client.

### Aucune rétention

Le job nocturne purge `public_scans` et les dossiers Dark Web à 90 jours. Des
documents clients — analyses de risques, inventaires, rapports d'incident — sont
plus sensibles que ce qui est déjà purgé, et n'ont aujourd'hui **ni durée de
conservation ni effacement**.

À trancher : la durée se rattache-t-elle au document ou à la relation
contractuelle ? Un livrable RSSI n'a probablement pas à survivre à la fin du
suivi.

---

## Ce qu'il ne faut pas que ça devienne

**Un service de stockage.** Le dépôt doit rester attaché à un objet — un
livrable, un critère de conformité — jamais flottant. Sans cette contrainte, un
abonné à 49 €/mois dispose d'un espace de fichiers illimité, et la facture S3
suit.

Corollaire : un **quota par client**, et un plafond par fichier aligné sur
l'existant (20 Mo, cf. `MAX_UPLOAD_BYTES`).

---

## Ce que ça n'adresse pas

La lecture bornée protège la mémoire, **pas la réception**. Starlette analyse le
corps multipart avant que le code applicatif ne s'exécute. Un plafond de taille
de requête au niveau de l'ALB ou de CloudFront reste à poser — action infra,
absente aujourd'hui, et qui vaut pour toute la plateforme et pas seulement pour
ce chantier.

---

## Séquencement proposé

| Étape | Contenu | Condition |
|---|---|---|
| 0 | Plafond de corps de requête côté ALB/CloudFront | indépendant, vaut déjà |
| 1 | Vérification des octets de tête dans `validate_upload` | code seul |
| 2 | Analyse antivirus + état du document | prérequis à toute ouverture aux clients |
| 3 | Dépôt côté portail RSSI (`origine` sur `RssiDeliverable`) | après 1 et 2 |
| 4 | Rétention et effacement des documents déposés | avec l'étape 3 |
| 5 | Preuves rattachées aux critères NIS2 / ISO | chantier distinct, à cadrer |

**L'étape 2 n'est pas négociable avant l'étape 3.** Ouvrir le dépôt aux clients
sans analyse antivirus, c'est accepter de distribuer ce qu'on reçoit.

---

## Décidé

**Antivirus : GuardDuty Malware Protection for S3** (2026-08-03). Managé, la
donnée reste dans AWS, et le palier gratuit couvre largement le volume attendu.
Les alternatives sont écartées : ClamAV coûte du temps et une Lambda
surdimensionnée, les services d'analyse tiers conservent les fichiers soumis.

### Ce que cette décision impose au produit

Le scan est **asynchrone** : l'objet est déposé, puis analysé, puis étiqueté.
Trois conséquences que la conception doit assumer.

- **Un état, pas un lien.** Un document porte `en_analyse`, `sain` ou `rejete`.
  Tant qu'il n'est pas sain, aucune URL présignée n'est délivrée — ni au
  consultant, ni au client qui vient de le déposer.
- **L'interface doit montrer l'attente.** Un fichier qui apparaît sans être
  téléchargeable ressemble à une panne si rien ne l'explique.
- **Un fichier infecté est supprimé, pas mis en quarantaine consultable.** On ne
  garde pas de dépôt malveillant « pour analyse » : ce serait s'en constituer
  un stock.

Reste à préciser au moment de la construction : lecture de l'étiquette S3 par
sondage, ou réaction à l'événement EventBridge. Le second évite un sondage
inutile mais ajoute un chemin asynchrone à tester.

---

## À trancher

1. **Rétention** : durée fixe, ou liée à la fin du suivi RSSI ?
2. **NIS2** : chantier à part ou intégré dès le début ? Il change la nature du
   produit et mérite sa propre décision.
