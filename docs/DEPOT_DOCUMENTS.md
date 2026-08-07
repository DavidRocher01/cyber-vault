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

### ~~Le type MIME vient du client~~ — fait le 2026-08-03

`validate_upload` comparait `content_type` et l'extension à deux listes
blanches. Les deux valeurs venant du client, cela ne contraignait rien : un
`.pdf` contenant `<!DOCTYPE html><script>` et annoncé `application/pdf` passait
les deux contrôles, était stocké, et le consultant le téléchargeait ensuite.

La signature de début de fichier est désormais vérifiée contre l'extension
déclarée. `validate_upload` prend les **octets** et non une taille annoncée — la
taille s'en déduit, ce qui supprime au passage tout écart entre ce que
l'appelant déclare et ce qui est stocké.

Ce que ce contrôle **ne fait pas** : pour les formats à base d'archive (docx,
xlsx, odt, ods), il établit qu'il s'agit d'un ZIP, pas que le ZIP contienne un
document. Descendre plus bas signifierait ouvrir l'archive — donc parser une
entrée fournie par l'utilisateur, exactement la surface d'attaque que la
règle « lu, pas traité » écarte. C'est l'antivirus qui couvre le contenu.

Un garde-fou vérifie que toute extension de la liste blanche possède une
signature : en ajouter une sans signature la ferait refuser systématiquement —
panne silencieuse côté utilisateur, contrôle absent côté sécurité.

### Rétention — trois régimes, pas un seul

La question posée au départ — « la durée se rattache-t-elle au document ou à la
relation contractuelle ? » — était mal formulée. Le job de purge existant avait
déjà tranché ce type de question pour le Dark Web : **c'est la finalité qui
commande, pas une horloge.** Un dossier surveillé est conservé tant que la
surveillance tourne ; un dossier ponctuel est purgé.

Appliqué aux documents, cela donne **trois régimes juridiquement distincts**, et
l'axe qui les sépare est le champ `origine` prévu à l'étape 3.

| Cas | Régime | Traitement |
|---|---|---|
| **Orphelin** — déposé, jamais rattaché | aucune finalité | **7 jours. Fait le 2026-08-04.** |
| Déposé par le **client** | sous-traitance, art. 28-3-g | **90 jours après la clôture. Fait le 2026-08-05.** |
| Produit par le **consultant** | responsabilité professionnelle | **jamais purgé automatiquement. Fait le 2026-08-05.** |

**Ce que la loi impose vraiment.** Aucun texte ne fixe de durée : l'article
5-1-e demande une durée *justifiée par la finalité*. En revanche l'article
**28-3-g** s'applique directement aux documents déposés par le client — à la fin
de la prestation, le sous-traitant efface **ou restitue**, **au choix du
responsable de traitement**. Le choix n'appartient donc pas à la plateforme, et
une purge unilatérale ne suffit pas : il faut que la restitution ait été
possible.

**Ce qui tire en sens inverse.** Les livrables produits par le consultant sont
sa preuve en cas de litige sur la qualité de la prestation. La prescription de
droit commun est de **5 ans** (art. 2224 du Code civil) : les effacer peu après
la fin de mission reviendrait à détruire sa propre défense. À faire confirmer
par un conseil, au même titre que la RC Pro.

**Un manque à corriger avant d'ouvrir le dépôt.** La politique de
confidentialité publiée énumère les durées (compte, scans, journaux,
facturation) mais **ne dit rien des documents déposés**. L'article 13 impose
d'informer sur les durées de conservation : la ligne devra y être ajoutée en
même temps que l'étape 3.

**Les trois régimes sont implémentés depuis le 2026-08-05.**

Le délai de 90 jours **est** la restitution exigée par l'article 28-3-g. Le
portail reste accessible après la clôture de la mission — vérifié :
`get_current_rssi_client` ne filtre pas sur le statut — donc le client peut
récupérer ses documents pendant toute la période. Effacer sans ce délai
reviendrait à supprimer sans avoir laissé le choix.

**Une colonne dédiée `cloture_le`, et pas `updated_at`.** Ce dernier bouge à
chaque modification : une simple correction d'adresse aurait repoussé l'échéance
de 90 jours, indéfiniment. La date est posée au passage en `inactive` /
`churned`, effacée au retour en `active` — un client repris ne doit pas voir ses
documents purgés sur la foi d'une interruption passée.

**Une mission close sans date n'est jamais purgée.** Aucune date n'est inventée
rétroactivement : on ne détruit pas de données sur la foi d'un repère fabriqué.
Sans conséquence, le dépôt client n'existant que depuis le 2026-08-05.

Les livrables du **consultant** ne sont jamais touchés. Un test le vérifie sur
une mission close depuis plus de huit ans, et il tombe si le filtre d'origine
disparaît de la requête.

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

### Ce que l'étape 5c a tranché

**« Référencé » ne veut plus dire « désigné par un `RssiDeliverable` ».** Un
fichier rattaché à un critère est référencé, quel que soit le parcours. Sans ce
changement, la pièce d'un abonné direct était orpheline dès le dépôt et la purge
nocturne l'effaçait au bout de sept jours.

**Les deux purges utilisent un `exists()` corrélé, pas un `not_in`.** Ce n'est
pas une préférence de style : avec un `file_url` à NULL, un `not_in` rend NULL —
ni vrai ni faux — et le livrable sans fichier aurait été épargné par accident.
Un test fixe ce cas.

**Le périmètre du quota est explicite à l'appel, jamais deviné.** La signature
n'acceptait qu'un `client_id` : un abonné hors RSSI ne pouvait pas être compté du
tout, donc disposait d'un stockage illimité. `verifier_quota` exige désormais
exactement un périmètre — `client_id` **ou** `user_id` — et lève si on lui en
donne deux ou aucun. Le stockage des clients ne pèse pas sur le quota personnel
du consultant, sinon leur activité bloquerait son propre dépôt.

**La suppression de compte efface les objets S3 explicitement.** La cascade de la
base ne sait rien de S3, et les deux clés étrangères sont en `SET NULL` : la
ligne survivait avec ses deux clés nulles et l'objet n'était ramassé que sept
jours plus tard, par effet de bord. L'appel se fait **avant** `db.delete(user)`,
sans quoi les fiches clients — en CASCADE — auraient déjà disparu et plus rien ne
relierait leurs fichiers au compte.

**L'exemption a une limite, et c'est le point le plus important.** Elle protège
les preuves des purges liées au **temps**, pas du droit à l'effacement. Si elle
valait aussi contre une demande de suppression de compte, rattacher une pièce
deviendrait un moyen de retenir des données malgré l'exercice d'un droit. Un test
le vérifie.

**`item_id` n'a pas de clé étrangère** — le catalogue est du code, pas une table.
C'est la couche service qui le valide contre `ALL_ITEM_IDS`. Sans ce contrôle,
une pièce rattachée à un identifiant erroné serait acceptée, stockée, comptée au
quota, n'apparaîtrait nulle part, et échapperait à la purge puisqu'elle sert
formellement de preuve : un fichier invisible et impérissable.

**La politique de confidentialité couvre maintenant les deux cas** que 5c fait
apparaître : l'abonné sans mission, dont les documents vivent avec son compte, et
la pièce rattachée qui échappe aux 90 jours. Cette exemption est annoncée, pas
tacite — avec la mention explicite qu'elle ne retire aucun droit.

### Ce que l'étape 5e a tranché

**Trois routes, et deux d'entre elles ne sont volontairement pas gardées.**
Déposer coûte du stockage : plans payants, décision du 2026-08-07. **Retirer et
télécharger ne le sont pas.** Un abonné qui repasse au Gratuit doit pouvoir
récupérer et effacer ses propres documents ; les mettre derrière un péage les
retiendrait en otage, ce qui n'est pas défendable sur un produit qui vend de la
conformité. Un test parcourt exactement ce scénario : dépôt en payant,
rétrogradation, puis dépôt refusé mais téléchargement et retrait toujours
possibles.

**`preuves` et `pieces` sont deux champs distincts**, et le nom les sépare
exprès. `preuves` porte les mesures que la plateforme détient déjà (la formation
suivie) ; `pieces` porte les documents que l'utilisateur a lui-même déposés. Les
réunir sous un seul nom laisserait croire que la plateforme a produit ce que
l'utilisateur a fourni.

**Le dépôt et le rattachement se font en un seul appel**, comme côté portail. En
deux temps, le fichier existerait un instant sans être référencé par rien — et
la purge des orphelins finirait par l'effacer.

**L'évaluation est créée si elle n'existe pas.** Exiger d'avoir enregistré son
auto-évaluation avant de joindre une pièce imposerait un ordre que rien ne
justifie. Une évaluation vide rend exactement ce que rendait son absence : items
vides, score à zéro.

**La clé de stockage ne dit plus « None ».** `upload_file` exigeait un
`client_id` entier ; un dépôt hors suivi RSSI aurait écrit le littéral `None`
dans le chemin, sous un préfixe `rssi-deliverables` qui mentait sur la nature du
fichier. Le segment est désormais explicite.

**Le gate est en fail-open, et ça n'a pas la même portée qu'ailleurs.** Sur
l'export, un plan inconnu laissait passer un PDF ; ici il laisserait passer une
écriture sur S3, donc de la facture. Deux choses le bornent : en production le
plan Gratuit est toujours semé, donc un compte sans abonnement retombe dessus et
reçoit un 403 ; et le quota s'applique de toute façon.

---

## Séquencement proposé

| Étape | Contenu | Condition |
|---|---|---|
| 0 | Plafond de corps de requête côté ALB/CloudFront | indépendant, vaut déjà |
| ~~1~~ | ~~Vérification des octets de tête dans `validate_upload`~~ | **fait le 2026-08-03** |
| 2a | Registre des fichiers, état d'analyse, règle de délivrance | **fait le 2026-08-03** |
| ~~2b~~ | ~~Activer GuardDuty Malware Protection for S3~~ | **fait le 2026-08-05** |
| ~~2c~~ | ~~Brancher le verdict~~ | **fait le 2026-08-05 — relecture de balise** |
| ~~3~~ | ~~Dépôt côté portail RSSI~~ | **backend fait le 2026-08-05 — interface à faire** |
| 4a | ~~Purge des dépôts orphelins + suppression S3~~ | **fait le 2026-08-04** |
| ~~4b~~ | ~~Rétention des documents rattachés~~ | **fait le 2026-08-05** |
| ~~5a~~ | ~~Catalogue NIS2 sorti de la couche de routage~~ | **fait le 2026-08-07** |
| ~~5b~~ | ~~`client_id` + unicité `NULLS NOT DISTINCT`~~ | **fait le 2026-08-07** |
| ~~5c~~ | ~~Table de preuves, purge générique, quota, rétention~~ | **fait le 2026-08-07** |
| 5d | Interface RSSI — rattacher une pièce au dossier client | après 5c |
| ~~5e~~ | ~~Abonné direct — dépôt sur l'auto-évaluation~~ | **fait le 2026-08-07** |
| 5f | Export PDF auditeur listant les preuves | **le livrable réel** |

**L'étape 2 n'est pas négociable avant l'étape 3.** Ouvrir le dépôt aux clients
sans analyse antivirus, c'est accepter de distribuer ce qu'on reçoit.

---

## Décidé

**Trois sujets, un seul modèle** (2026-08-07). Les évaluations NIS2 et ISO sont
aujourd'hui uniques par `user_id` — un consultant ne peut donc pas détenir un
dossier par client. La colonne `client_id` nullable règle les trois cas d'un
coup : `NULL` = mon auto-évaluation (abonné direct, comportement actuel),
renseignée = le dossier monté pour ce client.

L'unicité devient `UNIQUE (user_id, client_id) NULLS NOT DISTINCT`. **Ce dernier
point n'est pas un raffinement.** PostgreSQL considère par défaut deux NULL
comme distincts : sans lui, un même compte pourrait créer une infinité
d'auto-évaluations, et `upsert_assessment` — qui fait un `scalar_one_or_none()`
— se mettrait à lever une exception dès la deuxième. Disponible à partir de
PostgreSQL 15, et la plateforme est en 17. Vérifié aussi côté SQLAlchemy 2.0.49
(`postgresql_nulls_not_distinct`).

**Le dépôt de pièces est réservé aux plans payants** (2026-08-07). Par
cohérence avec l'export de conformité, déjà gardé par
`require_conformity_export` : le plan Gratuit fait l'auto-évaluation mais
n'exporte pas. Ce choix borne aussi la facture S3, que le quota par client ne
couvre pas pour un abonné hors RSSI.

**L'abonné qui veut NIS2 seul est un cas de premier rang** (2026-08-07) — ni
consultant, ni client d'un RSSI fractionné. Conséquence : la surface de dépôt
est construite **générique dès 5c**, indexée sur le sujet de l'évaluation, le
portail RSSI devenant un appelant parmi deux. La construire d'abord côté RSSI
puis la porter referait le chemin deux fois.

### Ce que l'étape 5b a fait apparaître (2026-08-07)

**Quatre requêtes reposaient sur « une seule évaluation par compte »**, toutes
avec un `scalar_one_or_none()`. Dès qu'un consultant en détient plusieurs, celles
qui ignorent le sujet lèvent. La plus grave : `export_account_data`, **l'export
de portabilité RGPD (art. 20)** — il aurait cassé précisément pour les comptes
qui se servent le plus du produit.

Elles filtrent désormais `client_id IS NULL`. Ce n'est pas qu'une parade
technique : un dossier de conformité décrit l'entité du **client**. Le verser
dans l'export d'un autre compte publierait les données d'un tiers dans un
fichier de portabilité.

**`client_id` est en CASCADE, pas en SET NULL.** Repasser la colonne à NULL
confondrait le dossier avec l'auto-évaluation personnelle du consultant — en y
versant les réponses d'un tiers — et violerait l'unicité s'il en avait déjà une.

**Le `downgrade` généré par autogenerate était faux deux fois** : il supprimait
la clé étrangère par le nom `None`, et recréait l'unicité par compte **avant**
que les dossiers clients ne disparaissent, donc en échec dès qu'un consultant en
détenait plus d'un. Vérifié en semant le cas puis en tentant la contrainte :
violation d'unicité. Le fichier a été repris à la main.

### Ce que ce cas cassait — réglé le 2026-08-07 (étape 5c)

**La purge des orphelins effacerait la preuve au bout de 7 jours.** Elle
considère comme référencé tout fichier présent dans `RssiDeliverable.file_url`.
Un abonné hors RSSI n'a par construction aucun `RssiDeliverable` : sa pièce est
orpheline dès le dépôt. La notion de « fichier référencé » est de forme RSSI et
doit devenir générique — c'est ce qui rend ce cas possible, pas un détail.

**Le quota ne peut pas être appelé.** `verifier_quota(db, client_id, ...)` exige
un client RSSI. Sans lui, un abonné direct dispose d'un stockage illimité —
exactement le risque que ce quota a été écrit pour éviter.

**La rétention n'a plus de repère.** Les 90 jours partent de `cloture_le`, et un
abonné direct n'a pas de mission qui se clôt. Sa durée devient la vie de son
compte. Or `delete_account` fait `db.delete(user)` + cascade, et
`depose_par_id` est en `SET NULL` : la ligne de registre survit avec ses deux
clés à `NULL`, et l'objet S3 n'est supprimé par aucun chemin explicite —
seulement ramassé sept jours plus tard par la purge des orphelins, par effet de
bord. Sur une demande d'effacement RGPD, ce délai doit être un choix assumé.

**Une pièce rattachée ne peut plus être purgée à 90 jours.** Rattacher un
document en change la finalité : il devient une pièce du dossier, au même titre
qu'un livrable consultant. Mais la politique de confidentialité annonce
« effacés 90 jours après la fin de votre mission », et ne couvre pas non plus
l'abonné sans mission. **Les deux régimes doivent y être écrits dans le même lot
que le code** — sinon on publie un engagement que le code ne tient pas, ce qu'on
s'est déjà interdit pour les livrables consultant.


**Antivirus : GuardDuty Malware Protection for S3** (2026-08-03). Managé, la
donnée reste dans AWS, et le palier gratuit couvre largement le volume attendu.
Les alternatives sont écartées : ClamAV coûte du temps et une Lambda
surdimensionnée, les services d'analyse tiers conservent les fichiers soumis.

### État au 2026-08-03 : la moitié applicative est faite

Ce qui existe désormais dans le code :

- une table **`fichiers_deposes`** — un registre. Le dépôt renvoyait une clé sans
  que rien ne garde trace de ce qui était stocké ; un fichier téléversé puis
  abandonné n'existait donc nulle part, occupant S3 sans titulaire ni date. La
  rétention et le quota butaient tous deux là-dessus ;
- l'état `en_analyse` / `sain` / `rejete` porté par le fichier, **pas par le
  livrable** — le dépôt précède la création du livrable, et une colonne sur
  celui-ci ne verrait pas les fichiers jamais rattachés ;
- **la règle de délivrance sur les deux voies** : côté consultant et côté
  portail client. Ne la poser que côté consultant laisserait passer exactement
  ce qu'elle prétend arrêter, puisque c'est le client qu'on protège.

Deux bords assumés, l'un et l'autre destinés à ne rien casser :

**Un fichier antérieur au registre reste téléchargeable.** Les refuser rendrait
indisponibles d'un coup tous les livrables déjà déposés en production. Ces
fichiers n'ont jamais été analysés — ils ne l'auraient pas été davantage sans
registre.

**Le réglage `ANTIVIRUS_DEPOT_ACTIF` est faux par défaut**, et les dépôts sont
alors enregistrés directement sains. À vrai sans GuardDuty en service, chaque
dépôt resterait bloqué en `en_analyse` : une porte fermée dont personne ne
détient la clé, et rien pour signaler la panne.

### Activé le 2026-08-05, et vérifié

Plan `70cfe8f2f02d87c32d65`, statut `ACTIVE`, sur
`cybervault-rssi-deliverables-prod`, **tous les objets** (pas de préfixe : un
préfixe mal saisi échouerait en silence), balisage `ENABLED`, rôle
`GuardDutyS3MalwareScanRole-rssi-deliverables`.

Vérifié par deux dépôts de test réels, tous deux supprimés ensuite :

| Fichier | Verdict | Délai |
|---|---|---|
| PDF anodin | `NO_THREATS_FOUND` | < 45 s |
| **EICAR** (faux virus standard, 68 octets) | **`THREATS_FOUND`** | **20 s** |

Le second compte plus que le premier : il établit que la détection **détecte**,
et pas seulement qu'elle s'exécute. Sans lui, on aurait supposé que
`THREATS_FOUND` fonctionne.

**Aucun détecteur GuardDuty n'existe dans le compte** (`list-detectors` rend une
liste vide) : Malware Protection for S3 tourne bien seul, sans enclencher —
ni facturer — l'analyse des journaux VPC, DNS et CloudTrail. Conséquence à
connaître : sans détecteur, il n'y a pas de « findings » dans la console
GuardDuty. La balise sur l'objet est le canal de vérité.

Un objet `malware-protection-resource-validation-object` de 0 octet subsiste
dans le bucket : c'est GuardDuty qui l'a écrit à l'activation pour vérifier ses
propres droits. Ne pas le supprimer.

**CINQ statuts, pas deux.** L'écran d'activation les nomme :
`NO_THREATS_FOUND`, `THREATS_FOUND`, `UNSUPPORTED`, `ACCESS_DENIED`, `FAILED`.
Les trois derniers ne sont ni sains ni rejetés — les ranger dans l'un des deux
serait faux dans les deux sens. Ils vont en `indetermine`, un état terminal qui
n'ouvre pas le téléchargement et qui se voit. **Une valeur inconnue y va
aussi** : AWS peut ajouter un statut demain, le défaut doit rester fermé.

### Le verdict remonte par RELECTURE, pas par EventBridge

Décidé le 2026-08-05. EventBridge supposerait une cible, et les trois possibles
posent le même problème :

- une **Lambda** — infrastructure absente du projet, qui déploie tout en
  impératif depuis `deploy.yml` ;
- un **endpoint HTTP** — qu'il faudrait authentifier, faute de quoi n'importe
  qui pourrait annoncer qu'un fichier est sain. C'est le trou que tout ce
  chantier ferme, rouvert par la porte de service ;
- une **file SQS** — qu'il faudrait interroger, donc sonder quand même, avec
  une file en plus.

**La relecture inverse le sens de la confiance** : c'est nous qui allons lire,
avec nos propres identifiants IAM. Rien d'extérieur n'affirme quoi que ce soit,
la chaîne ne quitte jamais AWS. Pour un produit qui vend de la sécurité, cette
différence pèse plus que trente secondes de latence. Et sans détecteur
GuardDuty, la balise est de toute façon déjà le seul canal de vérité.

Tâche `depot_rafraichir_analyses`, toutes les **2 minutes** — les scans prennent
20 à 45 s. Deux garde-fous :

**Le coût est borné par construction.** La requête ne rend que les fichiers
`en_analyse` : aucun fichier en attente, aucun appel S3. Un test l'impose, et il
échoue si l'on retire le filtre — vérifié.

**Renoncement à 1 heure.** Un fichier jamais étiqueté passe en `indetermine`.
Sans ce délai il serait relu indéfiniment — la seule façon dont cette tâche
pourrait finir par coûter quelque chose — et resterait indiscernable d'un scan
en cours.

Le mode de panne est bénin : si la tâche s'arrête, les fichiers restent
`en_analyse` et rien n'est délivré.

### La permission IAM qui n'existe nulle part dans le dépôt

Découverte le 2026-08-05, par le premier dépôt réel — et par rien d'autre.

Le rôle `cybervault-ecs-task-role` porte une politique **en ligne**,
`cybervault-rssi-s3`, créée à la main dans la console. Elle n'accordait que
`PutObject`, `GetObject` et `DeleteObject`. **Lire une balise est une permission
distincte** : `lire_balise` recevait un `AccessDenied`, le code l'attrapait, et
le fichier restait en `en_analyse` jusqu'au renoncement.

Les tests ne pouvaient pas l'attraper — ils simulent `lire_balise`. **Une
permission ne se vérifie que dans l'environnement réel.**

`s3:GetObjectTagging` a été ajoutée, et l'effet vérifié par
`aws iam simulate-principal-policy` → `allowed`.

**Le vrai enseignement n'est pas la permission manquante, c'est que cette
politique ne vit que dans la console.** Si le compte est reconstruit, elle est
perdue, et personne ne le saura avant que les téléchargements cessent en
silence. Contenu à recréer à l'identique :

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:GetObjectTagging"
      ],
      "Resource": "arn:aws:s3:::cybervault-rssi-deliverables-prod/rssi-deliverables/*"
    }
  ]
}
```

`s3:PutObjectTagging` n'est **pas** nécessaire : GuardDuty écrit les balises
avec son propre rôle, pas avec celui de la tâche.

### Reste à faire — et l'ordre compte

1. Activer **Malware Protection for S3** sur le bucket (et lui seul).
2. Vérifier que les objets déposés sont bien étiquetés par GuardDuty.
3. Brancher le verdict sur `depot_service.enregistrer_verdict` — étiquette S3
   relue, ou événement EventBridge. Le second évite un sondage mais ajoute un
   chemin asynchrone à tester.
4. **Alors seulement** passer `ANTIVIRUS_DEPOT_ACTIF` à vrai.

Inverser 4 et 1 coupe les téléchargements sans qu'aucune alerte ne se déclenche.

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
