# DORA : la résilience numérique pour le secteur financier

> **Le règlement DORA (Digital Operational Resilience Act) est en vigueur depuis le 17 janvier 2025. Il s'applique à plus de 22 000 entités financières en Europe.** (Commission Européenne)

## 🎯 Ce que vous apprendrez
- Pourquoi DORA a été créé et qui est concerné (y compris le régime simplifié)
- Les 5 piliers de la résilience numérique et les seuils concrets
- Le Registre ICT tiers et les superviseurs français
- Comment DORA s'articule avec ISO 27001, PCI-DSS et SWIFT CSP
- Un scénario réel de réponse à incident sous DORA
- Votre rôle dans la conformité

---

## Pourquoi DORA ?

Le secteur financier est l'un des plus ciblés par les cyberattaques. En 2023, les institutions financières ont subi en moyenne 3 fois plus d'attaques que les autres secteurs. La crise financière de 2008 a montré que l'interconnexion du secteur peut transformer une défaillance locale en crise systémique mondiale.

DORA est né de ce constat : **la résilience numérique du secteur financier est une question de stabilité économique**, pas seulement de sécurité informatique.

---

## Qui est concerné par DORA ?

### Entités financières directement concernées
- Banques et établissements de crédit
- Compagnies d'assurance et réassurance
- Entreprises d'investissement
- Gestionnaires de fonds
- Établissements de paiement et monnaie électronique
- Plateformes de crypto-actifs (CASPs)
- Contreparties centrales (CCP) et dépositaires

### Prestataires critiques indirectement concernés
- Fournisseurs de services cloud (AWS, Azure, Google Cloud)
- Éditeurs de logiciels financiers critiques
- Prestataires de services IT critiques pour le secteur financier

Si votre organisation fournit des services IT à des entités financières, DORA vous concerne indirectement.

### Le régime simplifié — toutes les entités ne sont pas égales

DORA applique un **principe de proportionnalité**. Les petites entités bénéficient d'exigences allégées :

**Entités exemptées ou allégées :**
- Micro-entreprises d'investissement (moins de 10 salariés, moins de 2 M€ de bilan)
- Petites mutuelles d'assurance (primes brutes < 5 M€)
- Petits fonds de retraite professionnelle

**Ce que le régime simplifié allège :**
- Cadre de gestion des risques IT simplifié (pas besoin d'un SIEM complet)
- Tests de résilience allégés (auto-évaluation acceptée)
- Registre ICT tiers allégé

> ❗ Même en régime simplifié, les obligations de notification d'incidents et les exigences contractuelles tiers restent entières.

---

## Les 5 piliers de DORA

### Pilier 1 : Gestion des risques informatiques (ICT Risk Management)
Les entités doivent disposer d'un cadre de gestion des risques IT complet et documenté :
- Identification et cartographie des actifs critiques
- Analyse des risques IT régulière
- Politiques de sécurité documentées
- **ICT Risk Appetite** : documentation formelle du niveau de risque accepté par la direction
- Formation continue du personnel (c'est ce que vous faites maintenant)

### Pilier 2 : Gestion et reporting des incidents — les seuils précis

DORA ne vous demande pas de signaler chaque panne. Un incident est "majeur" s'il franchit au moins un de ces seuils :

| Critère | Seuil "majeur" |
|---------|----------------|
| Clients affectés | > 10 % des clients ou > 10 000 clients |
| Durée d'indisponibilité | > 24 heures pour un service critique |
| Transactions perturbées | > 25 % du volume journalier habituel |
| Impact géographique | Perturbation dans plusieurs États membres |
| Perte financière | > 1 M€ pour l'entité elle-même |

**Les délais :**
- **4 heures** : alerte précoce à l'autorité compétente
- **72 heures** : rapport intermédiaire avec évaluation des impacts
- **1 mois** : rapport final avec cause racine et plan correctif

### Pilier 3 : Tests de résilience opérationnelle numérique
- **Tests de base** (annuels minimum) : revue des politiques, tests de pénétration, analyses de vulnérabilités, tests de scénarios de reprise
- **Tests avancés TLPT** (Threat-Led Penetration Testing) tous les 3 ans pour les entités importantes : simulations d'attaques réelles menées par des équipes certifiées selon la méthodologie TIBER-EU

### Pilier 4 : Gestion des risques tiers et Registre ICT

C'est l'un des piliers les plus novateurs. Les entités financières doivent :
- Cartographier **tous** leurs prestataires IT (pas seulement les critiques)
- Évaluer leur niveau de sécurité avant tout contrat
- Inclure des clauses contractuelles spécifiques (droits d'audit, SLA de sécurité, notification d'incident)
- Surveiller en continu les prestataires critiques

La Commission Européenne peut désigner certains prestataires comme **"prestataires tiers critiques" (CTPPs)** et leur imposer une supervision directe.

### Pilier 5 : Partage d'informations
DORA encourage le partage d'informations sur les menaces entre entités financières via des plateformes dédiées (FS-ISAC en Europe). Ce partage peut être volontaire ou, pour les grandes entités, imposé par les superviseurs.

---

## Le Registre ICT tiers — une obligation concrète

DORA impose la tenue d'un **Registre des contrats ICT tiers** exhaustif. Ce n'est pas un document interne — les superviseurs peuvent le demander à tout moment.

**Ce que le registre doit contenir pour chaque fournisseur :**
- Nom, pays d'établissement, coordonnées
- Type de services fournis (cloud, SaaS, maintenance, hébergement…)
- Niveau de criticité (critique / non critique)
- Données et systèmes accessibles par ce prestataire
- Localisation des données (pays, datacenters)
- Dates de début et fin de contrat
- Clauses de sécurité et résultats des derniers audits

**Pourquoi c'est important pour vous :**
Si vous signez un contrat avec un nouveau prestataire IT ou si vous utilisez un service cloud non référencé, votre responsable doit en être informé pour mettre à jour le registre. Utiliser un outil non enregistré (Shadow IT) est une violation DORA potentielle.

---

## Les superviseurs français

Contrairement à NIS2 (supervisée par l'ANSSI), DORA est supervisée par les **autorités sectorielles** :

| Entité | Superviseur |
|--------|------------|
| Banques, établissements de crédit | **ACPR** (Autorité de Contrôle Prudentiel et de Résolution) |
| Assurances et mutuelles | **ACPR** |
| Marchés financiers, sociétés de gestion | **AMF** (Autorité des Marchés Financiers) |
| Établissements systémiques (grandes banques) | **BCE** (Banque Centrale Européenne) |
| Crypto-actifs | **AMF** + **ACPR** selon le service |

**En cas d'incident majeur, c'est votre superviseur sectoriel que vous notifiez**, pas l'ANSSI directement. L'ANSSI est informée en parallèle par le superviseur sectoriel.

---

## DORA et les autres standards : ce qui change (ou pas)

Si votre organisation est déjà certifiée selon d'autres référentiels, DORA ne remet pas tout à zéro — mais ne dispense pas non plus.

### ISO 27001
✅ **Réutilisable :** La cartographie des actifs, l'analyse de risques, les politiques de sécurité et les procédures de gestion des incidents correspondent aux piliers 1 et 2 de DORA.
⚠️ **Manque :** ISO 27001 ne couvre pas les tests TLPT, le Registre ICT tiers DORA, ni les seuils précis de notification. Une organisation certifiée ISO 27001 a environ 60 % du chemin fait.

### PCI-DSS (secteur des paiements)
✅ **Réutilisable :** Les contrôles sur les réseaux, les accès et les tests de pénétration annuels s'alignent avec DORA.
⚠️ **Manque :** PCI-DSS est centré sur la protection des données cartes. DORA est plus large (résilience opérationnelle globale, tiers non-paiement, partage d'informations).

### SWIFT CSP (Customer Security Programme)
✅ **Réutilisable :** Les contrôles d'accès, la surveillance des transactions et les audits correspondent en partie aux piliers 1 et 4.
⚠️ **Manque :** SWIFT CSP est limité à l'infrastructure SWIFT. DORA couvre l'ensemble du système d'information.

**Conclusion pratique :** Ces certifications accélèrent la mise en conformité DORA mais ne la remplacent pas. Présentez-les à vos superviseurs comme preuves de maturité, pas comme substituts à DORA.

---

## Scénario concret : une journée de réponse à incident sous DORA

*Mardi matin, 8h17. La plateforme de paiement d'une banque régionale affiche des erreurs. Les transactions sont bloquées.*

**8h17 — Détection**
L'équipe monitoring reçoit une alerte SIEM. Première évaluation : l'API de paiement est indisponible. Cause inconnue.

**8h25 — Qualification**
Le RSSI est contacté. Première question : est-ce un incident majeur DORA ? Évaluation rapide :
- Nombre de clients affectés : estimation 15 000 → seuil franchi (> 10 000)
- Durée prévisible : inconnue → à surveiller
- Conclusion : **qualification "majeur" probable** → procédure DORA activée

**8h30 — Activation de la cellule de crise**
La direction est notifiée. Le responsable de la résilience numérique prend la coordination. L'équipe juridique est alertée pour la communication réglementaire.

**10h17 — Alerte précoce (deadline : 12h17)**
La banque notifie l'ACPR via le portail dédié. Contenu minimal : nature de l'incident (indisponibilité API paiement), heure de détection, nombre estimé de clients affectés, cause probable en cours d'investigation. L'incident est toujours en cours.

**14h45 — Résolution**
La cause est identifiée : un déploiement de mise à jour défectueux. La rollback est effectuée. Le service reprend.

**Jour J+3 — Rapport intermédiaire (deadline : 72h)**
Rapport envoyé à l'ACPR : description détaillée, 18 500 clients affectés, 6h28 d'indisponibilité, cause confirmée, premières mesures correctives.

**Jour J+30 — Rapport final**
Analyse complète de la cause racine, chronologie précise, mesures correctives implémentées (nouveau processus de validation des déploiements), plan de test de résilience renforcé.

**Ce que cet exemple illustre :**
- La qualification "majeur" se fait en quelques minutes — les critères doivent être connus à l'avance
- L'alerte à 4h est faisable même sans avoir toutes les réponses
- Toute l'organisation est impliquée : IT, direction, juridique, conformité

---

## Différences DORA vs NIS2

| Aspect | NIS2 | DORA |
|--------|------|------|
| Périmètre | Tous secteurs critiques | Secteur financier uniquement |
| Délai notification | 24h (alerte) | 4h (alerte) |
| Seuils incidents | Qualitatifs | Quantitatifs et précis |
| Tests obligatoires | Recommandés | Imposés avec méthodologie TIBER-EU |
| Registre tiers | Non imposé | Obligatoire, partageable avec superviseur |
| Superviseur | ANSSI (France) | ACPR / AMF / BCE selon entité |
| Proportionnalité | Limitée | Régime simplifié pour petites entités |

---

## Les sanctions DORA

Pour les entités financières :
- Sanctions administratives jusqu'à **1 % du CA journalier moyen mondial** par jour de non-conformité
- Pour les prestataires critiques désignés : jusqu'à **5 millions d'euros** ou 10 % du CA annuel

---

## Votre rôle dans la conformité DORA

Même si vous n'êtes pas RSSI, chaque employé contribue :

- **Signaler les incidents immédiatement** — les 4 heures commencent à la détection, pas à l'escalade
- **Ne pas utiliser de services IT non référencés** — tout Shadow IT compromet le Registre ICT tiers
- **Suivre les formations** — DORA impose la formation continue comme preuve de conformité
- **Respecter les procédures** — surtout en période de test TLPT ou d'audit superviseur
- **Connaître votre superviseur** — en cas d'incident, c'est l'ACPR ou l'AMF, pas l'ANSSI

---

## Résumé

DORA est la réponse réglementaire européenne à la cyber-fragilité du secteur financier. Il va bien au-delà de NIS2 sur presque tous les aspects : seuils quantitatifs, registre tiers obligatoire, tests TLPT, supervision sectorielle directe.

La proportionnalité permet aux petites entités de respirer — mais personne n'est exempté des obligations d'incidents et de gestion tiers.

Si votre organisation est concernée, la conformité DORA n'est pas optionnelle — c'est une condition d'exercice.
