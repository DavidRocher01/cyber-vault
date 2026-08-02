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

### Recommandation

**Commencer par A.** Elle répond à la question économique — quelle source produit
des clients — pour une fraction du coût et sans bandeau. Elle donne aussi la
ligne de base qui manque aujourd'hui : on ne sait même pas combien de visiteurs
arrivent.

Passer à B seulement si, une fois A en place, la question « où décrochent-ils ? »
devient bloquante. À ce moment-là le trafic justifiera l'investissement, et le
bandeau se discutera sur des chiffres plutôt que sur une intuition.

Pour une entreprise qui vend de la conformité NIS2, poser un bandeau de
consentement pour son propre suivi n'est pas neutre commercialement. Ce n'est pas
un argument décisif, mais il mérite d'être posé.

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

## Restitution

Étendre le tableau de bord admin existant (`admin_stats.py`), et non construire
un outil séparé. Trois vues suffisent :

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

## Ce qui reste à trancher

1. **A ou B** — voir la recommandation ci-dessus.
2. **Faire ou acheter.** Plausible (~9 €/mois) ou Matomo auto-hébergé couvrent
   l'audience en une journée, et le kit marketing les recommande déjà
   (`kit_cyberscan/01_BRIEF_STRATEGIQUE.md`). Ils ne savent en revanche pas
   relier une visite à un abonnement payant : c'est justement la question posée
   ici. Les deux peuvent coexister — un tiers pour l'audience brute, l'approche A
   pour l'attribution économique.
3. **Rétention du détail** : 13 mois proposés, à confirmer.
