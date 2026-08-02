# Mesure d'audience et de conversion — conception

> **Statut : conception, non développée.** Écrite le 2026-08-02. Elle remplace
> la ligne « Analytics maison — design validé, pas développé » de
> `ETAT_DES_LIEUX.md`, dont le raisonnement s'était perdu : la décision était
> tracée, pas son contenu.

## La question à laquelle ce système doit répondre

**Quelle source d'acquisition produit des clients payants, et où les autres
décrochent ?**

Tout le reste — pages vues, durée de session, taux de rebond — n'a d'intérêt que
s'il éclaire celle-là. C'est ce qui distingue cette conception d'un simple
compteur de visites.

Le tunnel réel, tel qu'il existe dans le code :

```
vitrine (67 routes)
   └─> scan gratuit anonyme          POST /public-scans
         └─> porte e-mail            POST /public-scans/{token}/unlock
               └─> inscription       POST /auth/register
                     └─> checkout    POST /subscriptions/checkout/{plan_id}
                           └─> abonnement actif   (webhook Stripe)
```

Points de fuite secondaires, déjà instrumentables : newsletter, formulaire de
contact, liste d'attente API.

---

## Le point dur : relier les deux moitiés

Mesurer l'acquisition est facile. Mesurer l'usage produit est facile. **Les
relier est le seul travail réel** — et c'est aussi le seul endroit où le RGPD
mord.

Deux approches, très inégales en coût comme en risque.

### A. Attribution au moment de la conversion — sans identifiant persistant

Au moment où quelqu'un convertit (scan gratuit, inscription), on enregistre
**avec lui** d'où il vient : `utm_source`, `utm_medium`, `utm_campaign`, domaine
référent. Rien avant, rien après. Aucun identifiant de visiteur, aucune lecture
d'un stockage navigateur.

- Répond à : « LinkedIn m'amène-t-il des clients, ou seulement du trafic ? »
- Ne répond pas à : « sur quelle page décrochent ceux qui ne convertissent pas ? »
- **Empreinte RGPD quasi nulle** : pas de traceur, donc pas de bandeau. La donnée
  est collectée avec un formulaire que la personne remplit volontairement.
- Coût : très faible. Quelques colonnes, un champ caché, rien de plus.

### B. Parcours complet — avec identifiant de visiteur persistant

Un identifiant pseudonyme posé au premier passage, rattaché au compte à
l'inscription. Permet de reconstituer le chemin entier, page par page.

- Répond à tout, y compris au décrochage.
- **Empreinte RGPD réelle.** L'exemption CNIL de consentement pour la mesure
  d'audience suppose que les données ne soient **pas recoupées avec un autre
  traitement**. Or rattacher les visites au compte client, c'est précisément un
  recoupement. Cette approche sort donc vraisemblablement de l'exemption et
  appelle un **bandeau de consentement** — avec le taux de refus qui va avec, qui
  biaise la mesure qu'on cherchait à obtenir.
- Coût : semaine de développement, plus une décision juridique.

### Décision : approche A, et B est écartée

**Tranché par David.** Le principe est plus large que ce chantier : *respecter le
RGPD à tout prix, pour ne pas être en contradiction avec ce que nous vendons.*

La nuance mérite d'être posée, car elle n'est pas juridique. **B serait légale**
avec un bandeau de consentement en règle. Ce qui est écarté, ce n'est pas
l'illégalité, c'est l'**incohérence commerciale** : une entreprise qui vend de la
conformité NIS2 et des audits de sécurité ne peut pas demander à ses propres
visiteurs l'autorisation de les pister. La position la plus solide n'est pas
« nous respectons le RGPD », c'est **« nous n'avons pas besoin de bandeau, parce
que nous ne vous pistons pas »**.

Conséquences concrètes, à traiter comme des contraintes et non des préférences :

- **aucun identifiant de visiteur persistant** — ni cookie, ni `localStorage`,
  ni empreinte de navigateur ;
- **aucun recoupement** entre navigation anonyme et compte client ;
- **aucun tiers** ne reçoit de donnée de navigation sans que ce soit un choix
  explicite et documenté ;
- le renoncement assumé : **on ne saura pas où décrochent ceux qui ne
  convertissent pas.** C'est le prix de la cohérence, et il est accepté.

Si la question du décrochage devient un jour bloquante, la réponse n'est pas de
rouvrir B : c'est de mesurer autrement — tests A/B côté serveur sur une page,
entretiens utilisateurs, ou instrumentation d'un parcours unique et borné dans le
temps.

---

## Modèle de données (approche A)

Deux tables, aucune modification des existantes.

### `sources_acquisition` — une ligne par conversion

| Colonne | Type | Note |
|---|---|---|
| `id` | PK | |
| `evenement` | str | `scan_gratuit`, `email_debloque`, `inscription`, `abonnement` |
| `utm_source` / `utm_medium` / `utm_campaign` | str, nullable | tels que reçus |
| `referent_domaine` | str, nullable | **domaine seul**, jamais l'URL complète |
| `page_atterrissage` | str, nullable | route interne, sans paramètres |
| `user_id` | FK, nullable | posé à l'inscription |
| `public_scan_id` | FK, nullable | rattache la conversion anonyme |
| `pays` | str(2), nullable | en-tête CloudFront, granularité pays |
| `cree_le` | timestamptz | |

Le lien acquisition → revenu se lit ensuite en joignant `user_id` vers
`subscriptions`. Aucune donnée nouvelle à caractère personnel n'est créée : on
qualifie une conversion qui existait déjà.

### `stats_journalieres` — agrégat

Compteurs par jour et par route, alimentés par un job nocturne. Permet de purger
le détail sans perdre les tendances, et garde les requêtes du tableau de bord
triviales.

---

## Ingestion

Un seul endpoint public, non authentifié — donc à traiter comme une surface
d'attaque, l'audit du 2026-07-27 ayant montré que c'est exactement là que le
risque se concentre :

- **liste blanche stricte** des noms d'événements : tout autre nom est rejeté,
  pas enregistré ;
- **rate-limit** par IP, via le limiteur existant ;
- **taille de charge utile bornée**, rejet en 413 au-delà ;
- **aucune écriture synchrone bloquante** : la réponse ne dépend pas de
  l'insertion ;
- **aucune donnée libre** : pas de champ texte alimenté par le client, sinon
  l'endpoint devient un stockage gratuit pour n'importe qui.

Côté Angular : tout accès à `window`/`localStorage` derrière `isPlatformBrowser`
— le site est prérendu statiquement, la règle est déjà dans `CLAUDE.md`.

---

## RGPD

- **Pas d'IP brute.** Si une IP est nécessaire (anti-abus), réutiliser la
  convention `ip_hash` salé déjà en place sur `public_scans`.
- **Rétention.** Brancher sur le job existant
  (`app/services/scheduler/retention.py`), qui purge déjà `public_scans` à 90
  jours. Proposition : détail à 13 mois, agrégats sans limite puisqu'anonymes.
- **Droits.** `sources_acquisition` porte un `user_id` : les lignes doivent
  entrer dans l'export Art. 20 et dans l'effacement, au même titre que le reste.
- **Transparence.** Mentionner la finalité dans la politique de confidentialité,
  même en approche A où aucun bandeau n'est requis.

---

## Restitution — un onglet dédié dans l'admin

**Décidé : un onglet à part, pas un bloc de plus dans « Vue d'ensemble ».**
L'acquisition répond à une question commerciale, la vue d'ensemble à une question
d'exploitation ; les mélanger rendrait les deux illisibles.

Concrètement, dans `admin-shell.component.ts` :

```ts
{ path: '/admin/acquisition', label: 'Acquisition', icon: 'trending_up', exact: false },
```

Le shell existe déjà et porte sept onglets (vue d'ensemble, contacts, blog,
utilisateurs, scans publics, factures, devis) : c'est un huitième, pas une
nouvelle interface. Côté backend, un module dédié plutôt qu'un ajout à
`admin_stats.py`, dont ce n'est pas le sujet.

Trois vues suffisent :

1. **Sources → revenu** : par `utm_source`, le nombre d'inscriptions et
   d'abonnements payants. C'est la vue qui justifie tout le reste.
2. **Tunnel** : volumes à chaque étape, du scan gratuit à l'abonnement, avec les
   taux de passage.
3. **Pages d'atterrissage** : lesquelles amènent des conversions, pas seulement
   du trafic.

> **Prérequis, déjà identifié** : il n'existe pas de vrai rôle admin aujourd'hui,
> seulement la clé `X-Admin-Key` (cf. `ETAT_DES_LIEUX.md` §4). Exposer des
> données de conversion derrière un secret partagé statique serait un recul.

---

## Séquencement

| Étape | Contenu | Quand |
|---|---|---|
| 0 | Vrai rôle admin | prérequis à toute restitution |
| 1 | Approche A : sources d'acquisition + tunnel + vues admin | maintenant |
| 2 | Usage produit dans l'application | quand il y aura des clients |
| 3 | Approche B, si le décrochage devient la question bloquante | à trancher sur chiffres |

**L'étape 2 est prématurée aujourd'hui** : il n'y a aucun client, donc rien à
mesurer côté usage. La construire maintenant produirait des tableaux vides et du
code à maintenir sans retour.

---

## Conventions de taguage

Sans `?utm_source=` dans le lien publié, il n'y a **rien à mesurer** : c'est la
seule partie du système qui ne se code pas. Les liens à taguer vivent hors du
dépôt — dans LinkedIn, dans un client mail, dans une signature.

Le vocabulaire doit rester **court et stable**. La normalisation serveur fusionne
les casses (« LinkedIn » et « linkedin » comptent ensemble), mais pas les
synonymes : `linkedin` et `linkedin-post` feraient deux lignes dans le tableau et
disperseraient le revenu. Un canal, une étiquette, pour toujours.

| Canal | Lien à publier |
|-------|----------------|
| Post LinkedIn | `https://rochercybersecurite.com/scan-gratuit?utm_source=linkedin` |
| Cold e-mail | `https://rochercybersecurite.com/scan-gratuit?utm_source=cold-email` |
| Signature e-mail | `https://rochercybersecurite.com/?utm_source=signature` |
| Carte de visite, QR | `https://rochercybersecurite.com/?utm_source=qr` |
| Salon, événement | `https://rochercybersecurite.com/?utm_source=evenement` |

`utm_campaign` sert à distinguer deux opérations sur le **même** canal — par
exemple `?utm_source=linkedin&utm_campaign=serie-nis2`. Inutile tant qu'il n'y a
qu'une campagne par canal.

### Ne PAS taguer les e-mails transactionnels

Le rapport de scan, les alertes, la réinitialisation de mot de passe : ce ne sont
pas des canaux d'acquisition. Les personnes qui les reçoivent sont **déjà**
entrées par un canal, et le clic sur ces e-mails est une étape du tunnel, pas une
source.

Les taguer ferait apparaître une ligne « e-mail » qui volerait des inscriptions à
LinkedIn ou au référencement, et donnerait l'impression qu'un canal interne
recrute des clients. Le revenu, lui, resterait correctement attribué — l'abonnement
hérite de la **première** source connue du compte — mais les colonnes
intermédiaires deviendraient trompeuses.

---

## Décisions arrêtées (2026-08-02)

Rien ne reste ouvert. Ce qui suit est tranché ; le rouvrir demande une raison
nouvelle, pas une préférence.

1. **Approche A** — attribution au moment de la conversion, sans identifiant
   persistant. Voir la décision et son raisonnement plus haut.
2. **Solution maison, sans coût récurrent.** Ni Plausible (~9 €/mois) ni Matomo
   auto-hébergé, que le kit marketing recommandait
   (`kit_cyberscan/01_BRIEF_STRATEGIQUE.md`) : cette recommandation est
   **caduque**. Les deux étaient compatibles avec le principe RGPD, mais l'un
   coûte un abonnement et l'autre une instance à héberger et à maintenir — pour
   un volume de trafic qu'on ne mesure même pas encore.
   Le comptage de pages vues sera donc maison lui aussi, agrégé côté serveur, et
   ne sortira d'aucune infrastructure déjà en place.
3. **Rétention** — détail à **13 mois**, agrégats sans limite puisque anonymes.
   Branché sur `app/services/scheduler/retention.py`, qui purge déjà
   `public_scans` à 90 jours : un job de plus, pas une mécanique de plus.

### Ce que « maison et gratuit » implique vraiment

Le coût n'est pas nul, il est déplacé : pas d'abonnement, mais du code à écrire
et à maintenir. C'est tenable **parce que le périmètre est petit** — deux tables,
un endpoint, trois vues. Il le restera tant qu'on ne cherchera pas à reconstruire
un Matomo : la tentation viendra, et la réponse est non. Ce système répond à une
question, pas à toutes.
