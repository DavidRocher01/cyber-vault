# Brief stratégique — Promotion & repositionnement Rocher Cybersécurité

> **Document à destination de Claude Code (ou de toute personne reprenant le projet).**
> Ce brief synthétise l'analyse du repo `cyber-vault` (https://github.com/DavidRocher01/cyber-vault) et du site en prod `https://cyberscanapp.com/cyberscan`, ainsi que la stratégie de campagne d'acquisition à mettre en œuvre.
> Date : avril 2026 — Budget total : < 500€ — Statut : site en ligne, 0 client.

---

## 1. Contexte produit

### 1.1 Ce qui est construit

**Projet dual** sous une même marque Rocher Cybersécurité :

- **Cyber-Vault** — Gestionnaire de mots de passe zero-knowledge
  - Chiffrement client AES-256-GCM (Web Crypto API), PBKDF2 100k itérations
  - Backend FastAPI + SQLAlchemy async + PostgreSQL 17
  - Frontend Angular 17 standalone + NgRx ComponentStore
  - Auth JWT + refresh tokens révocables, verrouillage compte (5 tentatives, 15min), rate limiting
  - CI/CD GitHub Actions : Bandit, pip-audit, Pytest, Vitest, Playwright
  - Stack solide, niveau pro

- **Cyber-Scanner** — Outil interne de scan de vulnérabilités
  - Module annexe au repo, pensé comme produit d'appel
  - Sert de **lead magnet** pour l'activité d'audit

### 1.2 Modèle économique cible

**Activité prioritaire : audit cybersécurité B2B (TPE/PME)**

| Offre ponctuelle | Durée | Prix HT | Cible |
|---|---|---|---|
| Flash | 0,5 j | 490€ | Indépendants, sites vitrines, blogs pro |
| App-Check | 1,5 j | 1 450€ | Startups SaaS, applis métiers |
| Pentest léger | 4 j | 3 800€ | E-commerce, données sensibles |

| Abonnement | Fréquence | Prix HT/mois | Valeur perçue |
|---|---|---|---|
| Vigie | Hebdo | ~120€ | "Je dors tranquille" |
| Sentinelle | Quotidien | ~350€ | "Mon application est saine" |
| Blindage 360 | Continu + humain | ~950€ | "Je suis inattaquable" |

**Activité secondaire : Cyber-Vault SaaS B2C** — sert principalement de **preuve technique** pour vendre l'audit (un dev qui a codé son propre password manager zero-knowledge inspire confiance).

### 1.3 Différenciateur clé

**SecDev hybride** : développeur full-stack (FastAPI/Angular) ET auditeur cybersécurité.
Positionnement rare, plus profond que les "auditeurs théoriques" qui ne codent pas.

---

## 2. Diagnostic du site actuel

### 2.1 Constats critiques

**🚨 Problème n°1 — SEO inexistant**
- Le site est une SPA Angular **sans SSR ni prérendu**
- Google ne récupère que le `<title>`, aucun contenu indexé
- Recherche `site:cyberscanapp.com` → 0 résultat
- Conséquence : tout budget pub envoie du trafic sur une page non indexée, aucune découverte organique possible

**🚨 Problème n°2 — Nom de marque non défendable**
Concurrents existants sur "Rocher Cybersécurité" :
- `cyberscan.io` (Allemagne) — exactement le même métier, antériorité forte
- `cyberscan.com` (USA, IoT)
- App iOS Rocher Cybersécurité
- Github medbenali/Rocher Cybersécurité
- Cyberscope.io/cyberscan

Implications :
- Nom descriptif → non protégeable INPI (refus probable classe 9/42)
- Confusion en SERP : prospects qui googlent "Rocher Cybersécurité" tombent sur les concurrents
- Marque interchangeable, pas d'ancrage mémoriel

**🚨 Problème n°3 — Pas de landing page d'acquisition dédiée**
- Pas de page distincte pour l'offre audit
- Pas de scan gratuit en lead magnet activé sur la home
- Pas de CTA clair vers les offres tarifées

### 2.2 Recommandation naming

**Option A — Pivoter sur un nom propre / cabinet (recommandé)**
- "Rocher Cybersécurité" / "Cabinet Rocher" / "DR Audit"
- ✅ Zéro risque INPI, ancrage local fort, crédibilité de cabinet (cf. avocats/experts-comptables)
- ✅ Permet de garder "Rocher Cybersécurité" comme nom du produit/scanner interne
- ❌ Moins "scalable" si ambition SaaS internationale

**Option B — Marque inventée à valider INPI/EUIPO**

Pistes à vérifier (présentées par famille) :

*Inventé tech moderne :* Sekorel, Vaultek, Trustek, Klyra, Veylan, Norven, Maelstra

*Évocation latine/française :* Sentinex, Vigilare, Solidae, Faxis, Custodia, Bastia

*Métaphore protection :* Aegide / Egide, Rampar, Phalanx, Vigia, Kerion

**⚠️ Critique : la disponibilité INPI/EUIPO/domaine n'a PAS été vérifiée.** À faire impérativement sur :
1. base-marques.inpi.fr (classes 9, 35, 42, 45)
2. euipo.europa.eu/eSearch
3. Whois / Gandi / OVH (.fr, .com, .io)
4. Google "[nom] cybersécurité"
5. LinkedIn search "[nom]"

**Recommandation pragmatique :** garder Rocher Cybersécurité comme nom produit, **vendre les services sous nom propre** ("David Rocher — Audit cybersécurité") pour démarrer sans bloquer la promo, puis investir dans une marque solide après les premiers clients.

---

## 3. Plan d'action technique (à implémenter par Claude Code)

### Phase 0 — Fondations SEO et conversion (priorité absolue, ~6h)

**Objectif :** rendre le site indexable, mesurable, et capable de convertir.

#### Tâches

- [ ] **Activer Angular Universal (SSR)** ou prérendre les pages publiques avec **Scully** (open source) ou **Prerender.io** (gratuit jusqu'à 250 URLs)
- [ ] Créer/optimiser les pages publiques avec meta tags complets :
  - `<title>` unique par page (50-60 caractères, mot-clé en début)
  - `<meta name="description">` (150-160 caractères, CTA inclus)
  - Balises Open Graph (og:title, og:description, og:image, og:url)
  - Twitter Cards (twitter:card="summary_large_image")
  - `<link rel="canonical">` sur chaque page
- [ ] Générer un `sitemap.xml` automatique
- [ ] Créer un `robots.txt` propre autorisant l'indexation des pages publiques
- [ ] Soumettre le sitemap à **Google Search Console** + **Bing Webmaster Tools**
- [ ] Installer **Plausible** (cloud, ~9€/mois) ou **Matomo** auto-hébergé pour le tracking
- [ ] Vérifier les Core Web Vitals (LCP < 2.5s, CLS < 0.1, FID < 100ms)
- [ ] Mentions légales + politique de confidentialité RGPD complètes

#### Pages publiques à créer/refondre

```
/                          → Home avec scan gratuit en hero
/audit-cybersecurite-pme   → Landing dédiée offre audit (priorité B2B)
/tarifs                    → Grille des offres Flash / App-Check / Pentest + abonnements
/blog                      → Liste articles SEO
/blog/[slug]               → Articles individuels
/scan-gratuit              → Outil de scan en self-service (lead magnet)
/cyber-vault               → Présentation du gestionnaire de mots de passe
/contact                   → Formulaire + Calendly intégré
/mentions-legales
/politique-confidentialite
```

### Phase 1 — Landing page audit (priorité 1)

**URL : `/audit-cybersecurite-pme`**

Structure recommandée (top → bottom) :

1. **Hero** — Promesse claire + CTA scan gratuit
   - H1 : "Audit cybersécurité pour TPE/PME — Code et infra passés au crible en 4 heures"
   - Sous-titre : "Je suis développeur ET auditeur. Je trouve les failles, je les explique, et je vous remets un plan d'action concret. Pas de rapport théorique de 50 pages."
   - CTA principal : "Lancer mon scan gratuit (3 findings en 90s)"
   - CTA secondaire : "Réserver un audit Flash — 490€ HT"

2. **Bloc preuve sociale** — Logos clients (à remplir au fur et à mesure) + témoignages

3. **Bloc problème/promesse** — "Vous êtes une TPE/PME et vous craignez..." (RGPD, attaque, perte de données clients)

4. **Bloc offres** — 3 cartes Flash / App-Check / Pentest avec prix, durée, livrable, CTA

5. **Bloc différenciation** — "Pourquoi un développeur-auditeur trouve des failles que les autres ratent"

6. **Bloc abonnement Sentinelle** — Pour la rétention et le MRR

7. **FAQ** — RGPD, durée, méthodologie, confidentialité

8. **CTA final** — Calendly intégré pour prise de RDV directe

### Phase 2 — Lead magnet : Scan gratuit en self-service

**URL : `/scan-gratuit`**

Spec fonctionnelle :

```
Input : URL du site + email
↓
Backend : exécute en async
  - SSL Labs API (note A-F + détails)
  - Headers HTTP de sécurité (CSP, HSTS, X-Frame-Options...)
  - Détection technologies (Wappalyzer-like) + versions exposées
  - Top 3 trouvailles classées par criticité
↓
Output :
  - Affichage immédiat à l'écran (3-5 findings)
  - Email automatique avec mini-rapport PDF (Brevo/Sendgrid)
  - Upsell intégré : "Audit complet = 12-15 findings + plan d'action — 490€ HT"
  - CTA Calendly dans l'email
```

Stockage en base (lead) : email, URL scannée, score, date, pays via IP.

### Phase 3 — Module Blog SEO

**Objectif :** capter le trafic organique sur 5 mots-clés à intention forte, faible concurrence locale.

Articles prioritaires (1500-2000 mots, optimisés un mot-clé par article) :

1. `audit-cybersecurite-pme-prix-2026` → "Audit cybersécurité PME : combien ça coûte vraiment en 2026 ?"
2. `vulnerabilites-courantes-sites-ecommerce` → "Les 10 vulnérabilités les plus courantes sur les sites e-commerce français"
3. `rgpd-cybersecurite-checklist-tpe` → "RGPD et cybersécurité : ce que votre prestataire web ne fait pas pour vous"
4. `audit-securite-fastapi-angular` → "Audit de sécurité applicative FastAPI + Angular : méthodologie complète"
5. `comment-coder-password-manager-zero-knowledge` → Article tech sur Cyber-Vault (pour autorité dev + Hacker News/dev.to)

Stack recommandée : **Markdown + frontmatter** (ou CMS headless type Strapi/Directus si besoin d'édition no-code).
Chaque article doit avoir : meta description, image OG dédiée, table des matières, CTA Calendly + scan gratuit en bas.

### Phase 4 — Tracking et mesure

Métriques à instrumenter dès J1 :

- Visites par page (Plausible/Matomo)
- Taux de conversion `/scan-gratuit` (URL soumise / page vue)
- Email captures
- Clics CTA "Réserver un audit"
- Source du trafic par UTM (LinkedIn organique, LinkedIn Ads, cold email, Reddit, Product Hunt)
- RDV Calendly pris

Dashboards à créer (interne) : conversion par canal, coût par lead, leads → audits vendus.

---

## 4. Plan de campagne d'acquisition (8 semaines, < 500€)

### 4.1 Stratégie globale

**70% du temps : audit B2B local (Auvergne-Rhône-Alpes)**
Cible : TPE/PME 5-50 salariés — e-commerce régional, cabinets pro (experts-comptables, avocats, médicaux), startups SaaS B2B early-stage, agences web sous-traitantes.

**30% du temps : Cyber-Vault B2C tech**
Objectif : crédibilité technique et autorité, pas la monétisation directe (marché saturé : Bitwarden, 1Password, Proton Pass).

### 4.2 Budget réparti

| Poste | Montant | Priorité |
|---|---|---|
| LinkedIn Ads (post boosté, ciblage local 20j) | 200€ | 🔥 Haute |
| Cold email tools (Hunter.io 1 mois) | 50€ | 🔥 Haute |
| Outil SEO (Ubersuggest 1 mois) | 30€ | Moyenne |
| Prerender.io ou hébergement SSR | 50€ | Moyenne |
| Visuels Canva Pro 1 mois + photo pro LinkedIn | 50€ | Moyenne |
| Réserve pour amplifier ce qui fonctionne | 120€ | À garder |
| **TOTAL** | **500€** | |

### 4.3 Roadmap semaine par semaine

**S1 — Fondations (0€ marketing, dev intensif)**
- SSR/prérendu activé, Search Console + Plausible installés
- Landing `/audit-cybersecurite-pme` live
- Scan gratuit en lead magnet fonctionnel
- Google Business Profile créé ("Rocher Cybersécurité / Rocher Cybersécurité — Audit cybersécurité Trévoux/Lyon")
- Profil LinkedIn optimisé (titre, bannière, featured)
- Inscription Malt + Comet + LeHibou avec tags "Cybersécurité, Audit, FastAPI, Angular, DevSecOps"
- Post LinkedIn d'annonce avec offre 3 audits gratuits contre témoignages

**S2 — Amorçage (0€)**
- Réalisation des 3-5 premiers audits offerts
- Recueil de 2-3 témoignages écrits + autorisation citation
- 3 posts LinkedIn pédagogiques
- 1er partenariat avec une agence web locale (commission 20% sur audits apportés)
- Post r/selfhosted pour Cyber-Vault

**S3 — Visibilité (~50€)**
- Article SEO #1 publié ("Audit cybersécurité PME : combien ça coûte")
- Lancement Product Hunt (mardi/mercredi 9h heure FR)
- Show HN sur Hacker News pour Cyber-Vault
- 3 posts LinkedIn
- Démarrage cold email — lot 1 de 25 prospects

**S4 — Activation payante (~250€)**
- Démarrage LinkedIn Ads (10€/jour x 20j = 200€) sur le meilleur post organique
- Cible LinkedIn Ads : Dirigeants/DSI/RSSI, entreprises 10-50 salariés, ARA, e-commerce + services pros
- 3 posts LinkedIn
- Article SEO #2
- Cold email lot 2
- Article dev.to sur le Cyber-Vault

**S5-S6 — Optimisation (~50€)**
- Doubler le budget sur le canal qui convertit le mieux (mesure CPL par canal obligatoire)
- Articles SEO #3 et #4
- 6 posts LinkedIn
- Partenariats #2 et #3 (autres agences web, expert-comptable, CCI Lyon Métropole / CCI Ain)
- Cold email lots 3 et 4

**S7-S8 — Closing & récurrence (~150€ réserve)**
- Push final sur les leads chauds (relance, Calendly direct)
- Premiers contrats Sentinelle (350€/mois récurrent)
- Bilan campagne complet : CAC par canal, LTV estimée, ROI
- Plan de la suite (mois 3-6)

### 4.4 Objectifs réalistes 8 semaines

- 5-10 audits Flash vendus (490€ × 7 ≈ 3 400€)
- 1-2 audits App-Check (1 450€ × 1.5 ≈ 2 200€)
- 1-2 abonnements Sentinelle (350€/mois récurrent)
- **CA total prévisionnel : 5 500 - 7 000€** sur 8 semaines pour 500€ investis
- **ROI cible : x10 minimum**

### 4.5 KPIs à suivre hebdomadairement

- Visites site + taux de conversion vers scan gratuit
- Leads générés (nombre + canal d'origine)
- Coût par lead par canal (CPL)
- RDV pris / audits vendus
- Posts LinkedIn : impressions, taux d'engagement, profile views
- Coût d'acquisition client (CAC)
- MRR (revenu récurrent mensuel) cumulé

---

## 5. Canaux d'acquisition détaillés

### 5.1 LinkedIn organique (canal n°1, 0€)

**Cadence :** 3 posts/semaine pendant 6 semaines = 18 posts.

Mix éditorial :
- 40% **pédagogiques** : "Les 5 failles que je trouve à 90% sur les sites de TPE"
- 30% **coulisses** : screenshots floutés de findings, captures du scanner, story d'audit
- 20% **opinion/positionnement** : "Pourquoi un rapport d'audit de 50 pages ne sert à rien"
- 10% **conversion** : témoignages, cas d'usage, CTA direct

Hashtags : #cybersécurité #TPE #PME #RGPD #Lyon #AuvergneRhôneAlpes #DevSecOps #FastAPI

Action complémentaire : commenter activement les posts de DSI/dirigeants TPE-PME locaux (80% de l'effet LinkedIn quand on démarre).

### 5.2 SEO local (0€, long terme)

5 mots-clés cibles, intention commerciale forte, faible concurrence locale :
- "audit cybersécurité Lyon"
- "audit sécurité site web PME"
- "test intrusion Ain"
- "audit RGPD Lyon"
- "consultant cybersécurité Trévoux"

Bonus : Pages Jaunes Pro, Solocal, Yelp, annuaire CCI Lyon Métropole, annuaire Auvergne-Rhône-Alpes Entreprises. Échange de backlinks avec 3-5 sites complémentaires.

### 5.3 LinkedIn Ads (200€)

- Format : Sponsored Content (post boosté)
- Cible : Dirigeants/DSI/RSSI, 10-50 salariés, ARA, e-commerce + services pros
- 10€/jour × 20 jours
- À activer en S4 une fois 1-2 témoignages et 5-10 posts organiques publiés
- Objectif : 30-60 clics, 3-8 leads qualifiés, 1-2 audits vendus

### 5.4 Product Hunt + Reddit + Hacker News (0-50€)

- **Product Hunt** : lancement Cyber-Vault un mardi/mercredi 9h FR
- **Reddit** : r/selfhosted, r/privacy, r/PasswordManagers (lire les règles avant)
- **Hacker News** : "Show HN: Cyber-Vault — Zero-knowledge password manager built with FastAPI + Angular"
- Budget 50€ : éventuel boost Reddit Ads ou comptes premium offerts à 5 testeurs influents

### 5.5 Cold email B2B (50€ outils)

- 100 entreprises locales (TPE/PME 10-50 salariés, ARA)
- Outil : Hunter.io ou Dropcontact (1 mois)
- Approche : email court, valeur d'abord, mini-finding offert sur leur site
- Taux de réponse attendu : 5-10% → 5-10 leads → 1-2 audits

Template d'email à industrialiser :
```
Objet : Une faille trouvée sur [nomdomaine.fr]

Bonjour [Prénom],

J'ai jeté un œil rapide à [site] dans le cadre de mes recherches sur la
cybersécurité des PME locales. J'ai noté 2 points d'amélioration immédiats
(header CSP manquant + version PHP exposée).

Rien de catastrophique, mais sur un audit complet (490€ HT), je trouve en
moyenne 8-12 failles dont 1-2 critiques.

Je peux vous envoyer un mini-rapport gratuit (3 pages, sous 24h) si ça vous
intéresse — sans engagement.

Bien cordialement,
David — [URL site]
```

### 5.6 Partenariats locaux (0€, gros potentiel)

- **3-5 agences web locales** : commission 20% sur audits apportés (98€ par audit Flash)
- **Experts-comptables** : ils parlent à toutes les TPE de la région, prescripteurs naturels sur la conformité RGPD
- **CCI Lyon Métropole / CCI Ain** : formations/événements cybersécurité, intervention possible

---

## 6. Livrables à produire par Claude Code (priorisés)

### Sprint 1 — Fondations techniques (semaine 1)

1. Migration vers SSR Angular Universal OU intégration Scully/Prerender.io
2. Refonte des meta tags + génération sitemap.xml + robots.txt
3. Création des routes publiques (/audit-cybersecurite-pme, /tarifs, /blog, /scan-gratuit, /contact, /mentions-legales)
4. Intégration Plausible/Matomo + Google Search Console + Bing Webmaster Tools
5. Audit Lighthouse / Core Web Vitals + corrections

### Sprint 2 — Pages d'acquisition (semaine 1-2)

6. Landing `/audit-cybersecurite-pme` complète selon structure §3 phase 1
7. Page `/tarifs` avec 3 cartes ponctuelles + 3 cartes abonnement
8. Page `/scan-gratuit` avec backend de scan async (SSL Labs + headers HTTP + tech detection)
9. Email automatique post-scan avec mini-rapport PDF + upsell
10. Intégration Calendly sur toutes les pages de conversion

### Sprint 3 — Contenu et blog (semaine 2-3)

11. Module blog (Markdown + frontmatter ou CMS headless)
12. Rédaction et publication des 2 premiers articles SEO
13. Génération images OG par article (Open Graph dynamique)

### Sprint 4 — Tracking et CRM (semaine 3-4)

14. Dashboard interne de suivi des leads (admin)
15. Export CSV des leads vers Google Sheets ou CRM léger (Notion/Airtable)
16. Intégration UTM tracking complet par canal
17. Webhooks Calendly → notification + ajout au CRM

### Sprint 5 — Itérations (semaine 4+)

18. A/B testing CTA principal landing audit
19. Optimisation tunnel scan gratuit selon métriques
20. Articles SEO #3 à #5

---

## 7. Décisions ouvertes (à trancher avec David)

- [ ] **Naming** : garder Rocher Cybersécurité + ajouter signature "David Rocher — Audit cybersécurité" en parallèle ? Ou pivot complet vers nouveau nom ?
- [ ] **Domaine** : conserver cyberscanapp.com ou acheter un domaine secondaire dédié à l'audit (ex: `rocher-securite.fr`) qui pointe vers le même site ?
- [ ] **Modèle de scan gratuit** : limiter à 1 scan par email/24h ? Captcha pour éviter abus ?
- [ ] **CRM** : Notion / Airtable / HubSpot Free / solution custom dans Rocher Cybersécurité ?
- [ ] **Facturation** : intégrer Stripe directement (Stripe Checkout pour offre Flash) ou rester sur facturation manuelle au début ?
- [ ] **Vérification INPI** : faire avant ou après les premiers clients ? (Recommandation : avant tout dépôt de marque, lancer la promo en attendant)

---

## 8. Ressources et liens

- Repo : https://github.com/DavidRocher01/cyber-vault
- Site prod : https://cyberscanapp.com/cyberscan
- Vérification marques INPI : https://base-marques.inpi.fr
- Vérification marques EUIPO : https://euipo.europa.eu/eSearch
- Google Search Console : https://search.google.com/search-console
- Plausible : https://plausible.io
- Prerender.io : https://prerender.io
- Hunter.io : https://hunter.io
- Calendly : https://calendly.com

---

## 9. Annexe — Notes stratégiques internes du repo

Le repo contient déjà plusieurs notes textuelles utiles à exploiter pour la suite :

- `Offres audit.txt` — détail des 3 offres ponctuelles + 3 abonnements (déjà repris ci-dessus)
- `Page dédiées par client.txt` — vision MCP (Model Context Protocol) pour synchroniser les findings avec les outils des clients (Jira, Linear, GitHub Issues). Idée à creuser pour la formule Sentinelle/Blindage.
- `Newsletter cybersécurité et bonnes.txt` — projet de newsletter, peut servir de canal de nurturing
- `Recommandations UXUI.txt` — à consulter avant la refonte des pages publiques
- `Cybersécurité pour le site.txt` — checklist sécurité du site lui-même (cohérence : un site cyber doit être irréprochable côté sécurité)

**Action recommandée :** Claude Code doit lire ces fichiers en début de mission pour s'imprégner du contexte avant de coder.

---

*Fin du brief. Bonne mission !*
