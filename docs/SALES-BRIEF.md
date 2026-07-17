# Brief commercial — Rocher Cybersécurité (source de vérité "sales")

> **Instructions pour Claude (conversation commerciale).** Tu es mon conseiller go‑to‑market
> pour **trouver des clients en France**. Appuie‑toi **uniquement** sur les faits ci‑dessous :
> ne jamais inventer de fonctionnalité, de prix, de certification ou de garantie. Si une info
> manque, **demande‑la moi** plutôt que de la supposer.
> **Priorité commerciale : 1) RSSI externalisé · 2) Conformité GRC (NIS2 / ISO 27001) · 3) Analyse de failles & de code.**
> **Zone : France.**
>
> _Ce document est maintenu côté "Claude Code" (l'équipe produit). Quand le produit évolue,
> il est mis à jour ici — considère‑le comme la version courante._

---

## 1. L'entreprise & le produit

- **Entreprise :** Rocher Cybersécurité (cabinet de cybersécurité).
- **Produit SaaS :** plateforme de cybersécurité **tout‑en‑un pour PME** — site `rochercybersecurite.com`.
  _(Nom commercial du SaaS potentiellement "Rocsûr" — à confirmer, ne pas trop l'employer tant que ce n'est pas verrouillé.)_
- **Hébergement :** 100 % **AWS Paris (France, eu‑west‑3)**, aucune donnée hors UE.
- **Positionnement :** allier un **RSSI externalisé humain** à une **plateforme** qui outille la conformité,
  la détection de vulnérabilités et la surveillance — pensé pour des PME **sans équipe sécurité dédiée**.

**Modules disponibles (déjà en production ou prêts) :**
- **RSSI externalisé** (module consultant B2B) : gestion de clients, visites, plans d'action, livrables
  (stockés chiffrés), rapports PDF, profil consultant.
- **Conformité / GRC** : **NIS2** (34 critères), **ISO 27001:2022** (38 contrôles), **PCA** (plan de continuité) — scoring + rapports PDF.
- **Scanner de vulnérabilités externes** : SSL/TLS, en‑têtes de sécurité, DNS, e‑mail (SPF/DMARC),
  cookies, CORS, réputation IP, CMS, WAF, ports, fuites ; niveaux avancés (Threat Intel, TLS profond,
  sous‑domaines) et offensifs (JWT, clickjacking, redirections ouvertes).
- **Analyse de code (SAST/SCA)** : Bandit, Semgrep, pip‑audit — détection de failles dans le code source.
- **Scripts de remédiation** prêts à l'emploi (UFW, SSH, Nginx…).
- **Dark Web** : surveillance de fuites (e‑mails) + **Dark Web Dossier** B2B (exposition d'un domaine, scoring de risque, monitoring, PDF).
- **Coffre‑fort de mots de passe zero‑knowledge** (chiffrement AES‑GCM côté client).
- **Sensibilisation / e‑learning NIS2** (attestations) et **simulation de phishing**.

---

## 2. Les 3 offres "pointe de lance" (par priorité)

### 🥇 1. RSSI externalisé (fer de lance)
- **Quoi :** un RSSI à temps partagé (fractional CISO) + la plateforme pour piloter la mission
  (visites, plans d'action, livrables, rapports).
- **Douleur résolue :** la PME est en scope réglementaire (NIS2) ou pressée par ses clients/assureurs,
  mais **n'a ni RSSI ni budget pour un temps plein**.
- **Nature :** offre **service récurrent** (abonnement mensuel / forfait mission) — c'est le plus fort en valeur et en récurrence.

### 🥈 2. Conformité GRC (NIS2 / ISO 27001 / PCA)
- **Quoi :** auto‑évaluation guidée + scoring + rapports PDF prêts à présenter (direction, auditeur, client).
- **Douleur résolue :** "on nous demande d'être conformes NIS2/ISO, on ne sait pas par où commencer ni où on en est."
- **Angle :** souvent la **porte d'entrée** vers le RSSI externalisé (le diagnostic révèle le besoin d'accompagnement).

### 🥉 3. Analyse de failles & de code
- **Quoi :** scan externe continu + analyse de code (SAST/SCA) + scripts de remédiation.
- **Douleur résolue :** "est‑ce que mon site / mon appli a des failles exploitables ?"
- **Angle :** produit **self‑service** peu coûteux, bon pour générer des leads (offre gratuite généreuse → upsell).

---

## 3. Client idéal (ICP) — France

**Profil type :** PME / ETI françaises **50–500 salariés**, sans RSSI interne, avec un actif numérique à protéger.

**Secteurs prioritaires (pression réglementaire NIS2) :** santé, énergie, eau, transport, déchets,
agroalimentaire, prestataires numériques / MSP, collectivités & administrations, **sous‑traitants de grands
groupes** (exigences de sécurité "supply chain").

**Déclencheurs d'achat (à exploiter en prospection) :**
- Mise en conformité **NIS2** (entités essentielles/importantes nouvellement concernées).
- **Questionnaires sécurité** imposés par un grand donneur d'ordre ou un client.
- Exigences d'une **assurance cyber** (souvent conditionnée à un minimum de maturité).
- **Post‑incident** (rançongiciel, fuite) ou audit récent.

**Interlocuteurs :** dirigeant/DG (PME), DSI/RSI, responsable qualité/conformité, DPO.

---

## 4. Différenciateurs (à marmarteler)
- **Souveraineté : hébergement France / UE**, aucun transfert hors UE (argument fort face aux solutions US).
- **Tout‑en‑un** : RSSI + conformité + scan + dark web + coffre‑fort, au lieu de 5 outils.
- **Humain + logiciel** : un vrai RSSI, pas juste un dashboard.
- **Zero‑knowledge** sur le coffre‑fort (le prestataire ne peut pas lire les secrets).
- **Accessible aux PME** : offre gratuite généreuse, prix lisibles, sans jargon.

---

## 5. Grille tarifaire (HT / mois, sans engagement, Stripe)
_La différenciation se fait par les **fonctionnalités** ; sites surveillés et fréquence de scan sont **illimités/quotidiens sur tous les plans**._

| Plan | Prix | Inclus (en plus du précédent) |
|---|---|---|
| **Gratuit** | 0 € | Sites illimités · scan quotidien · sécurité de base · **NIS2 + ISO 27001** · alerte e‑mail critique · rapport PDF |
| **Starter** | 14,90 € | **Analyse de code (SAST/SCA)** · scripts de remédiation |
| **Pro** | 49 € | Analyse avancée (Threat Intel, TLS profond) · **surveillance Dark Web + Dossier** |
| **Business** | 149 € | Analyse experte (JWT, redirections, clickjacking) |
| **Sur devis** | — | API REST, webhooks, account manager dédié, rapport marque blanche, support prioritaire |

> ⚠️ Le **RSSI externalisé** est une **prestation de service** (forfait/abonnement dédié), pas un simple
> palier du SaaS — à tarifer au cas par cas (à cadrer avec moi si un prospect avance).

---

## 6. Arguments de confiance / preuves
- Hébergement **AWS Paris**, chiffrement **AES‑256 au repos**, **TLS 1.3** en transit.
- Coffre‑fort **zero‑knowledge** (chiffrement côté client).
- Démarche sécurité documentée (modèle de menaces / dossier sécurité disponible pour due diligence).

---

## 7. À NE PAS promettre (pas encore finalisé) — pour éviter de sur‑vendre
- **Assurance RC Pro + volet cyber : en cours de souscription.** ⚠️ Ne pas s'engager sur des **scans intrusifs /
  pentests** chez un client tant que la couverture n'est pas active.
- **Délivrabilité e‑mail** (boîte de contact / transactionnels) : configuration domaine en cours de finalisation.
- **Médiateur de la consommation** (obligatoire pour vendre en **B2C**) : à trancher — privilégier le **B2B** pour démarrer.
- **Nom commercial "Rocsûr"** : non verrouillé (marque + domaine à vérifier).
- Pas de certification ISO/HDS **de l'entreprise elle‑même** revendicable à ce stade (on **outille** la conformité du client, on n'est pas encore certifié).

---

## 8. Angles de prospection prioritaires (France)
1. **NIS2 comme "cheval de Troie"** : proposer un **diagnostic de conformité gratuit** → révèle l'écart → vend le RSSI externalisé.
2. **Cibler les sous‑traitants** de grands groupes/OIV soumis à des exigences sécurité en cascade.
3. **Collectivités & santé** (fort besoin, budgets fléchés cyber, sensibilité souveraineté).
4. **Partenariats** : experts‑comptables, cabinets conseil, MSP/infogérants (apporteurs d'affaires PME).
5. Offre **gratuite** du scanner comme aimant à leads (self‑service) → nurturing vers Starter/Pro puis RSSI.

---

## 9. Ce dont j'ai besoin de la conversation "sales"
- Un **profil de client idéal (ICP)** affiné + une **liste de segments/secteurs** à attaquer en premier.
- Des **messages de prospection** (cold e‑mail, LinkedIn, pitch téléphonique) déclinés par offre.
- Un **argumentaire d'objections** (prix, souveraineté, "on a déjà un prestataire IT", RGPD…).
- Une **trame de diagnostic NIS2 gratuit** à offrir en amorce.
- Des idées de **partenariats/apporteurs** et de **contenus** (webinaire, checklist NIS2).

> Pour toute question **technique/produit** (une feature existe‑t‑elle ? est‑ce faisable ?), renvoie‑la moi :
> je la traite côté produit et je mets ce brief à jour.
