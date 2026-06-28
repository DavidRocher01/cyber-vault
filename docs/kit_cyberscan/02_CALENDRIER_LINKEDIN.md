# Calendrier éditorial LinkedIn — 18 posts sur 6 semaines

> **Cible :** Dirigeants TPE/PME, DSI, RSSI en Auvergne-Rhône-Alpes
> **Objectif :** Générer des leads audit cybersécurité + asseoir autorité technique
> **Cadence :** 3 posts/semaine (lundi 8h, mercredi 12h, jeudi 18h — créneaux à tester)
> **Mix éditorial :** 40% pédagogique, 30% coulisses, 20% opinion, 10% conversion

---

## Conseils transverses

### Format des posts
- **Hook puissant** sur la première ligne (avant le "voir plus")
- **Texte aéré** : phrases courtes, sauts de ligne fréquents
- **600-1200 caractères** = sweet spot LinkedIn 2026
- **1 CTA par post** (commenter / réserver / partager)
- **Pas plus de 3 hashtags** : LinkedIn privilégie le contenu naturel

### Hashtags à utiliser (varier)
`#cybersécurité` `#TPE` `#PME` `#RGPD` `#Lyon` `#AuvergneRhôneAlpes`
`#DevSecOps` `#audit` `#sécurité` `#FastAPI` `#Angular` `#dirigeant`

### Règle d'or
**Commenter 5 posts d'autres / 1 post publié.** L'engagement sur des posts de dirigeants locaux génère 80% de la visibilité quand on démarre sans audience.

---

## SEMAINE 1 — Annonce et amorçage

### Post #1 — LUNDI — Annonce + offre amorçage (CONVERSION)

```
J'ai un truc un peu fou à vous proposer.

Je lance mon activité d'audit cybersécurité pour TPE/PME.

Et pour mes 3 premiers clients, l'offre Flash (490€ HT) est OFFERTE.

En échange :
→ Vous me laissez auditer votre site (4h de boulot de mon côté)
→ Vous repartez avec un score de sécurité, la liste des failles trouvées,
   et un plan d'action concret
→ Je vous demande juste un retour d'expérience écrit à la fin

Pas de carte bleue. Pas d'engagement. Pas d'embrouille.

Mon profil : développeur full-stack ET auditeur cyber (rare combo).
Donc je trouve aussi des failles que les auditeurs "papier" ratent.

Première personne qui me MP, c'est pour elle.

#cybersécurité #TPE #PME
```

### Post #2 — MERCREDI — Pédagogique (autorité technique)

```
Les 5 failles que je trouve à 90% sur les sites de TPE/PME :

1️⃣ Pas de header CSP (Content Security Policy)
→ Conséquence : votre site peut servir à phisher vos propres clients

2️⃣ Versions logicielles exposées dans les headers HTTP
→ Conséquence : un attaquant sait exactement quelles failles exploiter

3️⃣ Mots de passe admin en clair dans la base
→ Conséquence : une fuite = compromission immédiate

4️⃣ Pas de rate limiting sur les endpoints sensibles
→ Conséquence : brute force triviale en quelques heures

5️⃣ Sauvegardes accessibles publiquement
→ "/backup.zip" trouvé en 10 secondes via dirbuster

Aucune de ces failles ne nécessite un hacker russe.
Un stagiaire avec un peu de curiosité fait l'affaire.

Si vous voulez vérifier ces 5 points sur votre site :
commentez "AUDIT" et je vous fais un check gratuit en 24h.

#cybersécurité #PME #RGPD
```

### Post #3 — JEUDI — Coulisses / personal branding

```
Petite confession.

Il y a 2 ans, je pensais qu'auditer la cybersécurité d'une PME,
c'était "lancer un scanner et lire le rapport".

Aujourd'hui, je sais que c'est exactement ce qui ne marche PAS.

Les scanners automatiques (Acunetix, Nessus, Burp...) trouvent :
✅ Les failles connues
✅ Les configs par défaut
✅ Le bruit de fond

Mais ils ratent à coup sûr :
❌ Les logiques métier vulnérables ("/api/user/123" → essayer 124)
❌ Les failles de privilèges ("admin" caché dans un cookie)
❌ Les fuites de données via les messages d'erreur

Pour ça, il faut quelqu'un qui CODE.
Qui sait comment un dev pense, où il bâcle, ce qu'il oublie.

C'est pour ça que je n'ai pas fait l'erreur de devenir "auditeur papier".
Je code la semaine, j'audite le week-end.
Et ça change tout.

#DevSecOps #cybersécurité
```

---

## SEMAINE 2 — Construction de l'autorité

### Post #4 — LUNDI — Pédagogique chiffré

```
Une cyberattaque coûte combien à une PME ?

J'ai croisé 3 sources fiables (ANSSI, Hiscox, Sphinx) sur 2023-2024.

Moyenne d'une attaque réussie sur une TPE/PME française :
💸 Coût direct : 24 000€ à 90 000€
💸 Perte d'exploitation : +35% du coût direct
💸 Impact RGPD (CNIL) : amende moyenne 40 000€ si négligence prouvée
💸 Perte de confiance clients : 22% des PME perdent des clients après une attaque

Total moyen : entre 60 000€ et 200 000€.

Un audit Flash coûte 490€ HT.
Un audit complet : 1 450€ HT.
Une surveillance mensuelle : 350€ HT.

Je laisse faire le calcul.

#cybersécurité #PME #RGPD
```

### Post #5 — MERCREDI — Coulisses / témoignage 1er audit

```
Premier audit terminé hier. Résultat surprenant.

E-commerce local, ~80 commandes/jour, 4 ans d'existence.
Site refait il y a 18 mois par une agence sérieuse.

Findings :
🔴 1 critique : injection SQL sur le formulaire de recherche
🔴 1 critique : compte admin avec mdp "admin2022"
🟠 3 modérées : CSP absent, versions exposées, cookies sans flag Secure
🟡 6 mineures : améliorations UX sécurité

Temps pour trouver la 1ère faille critique : 7 minutes.

Le client (que je remercie pour son courage de témoigner) :
"On pensait être à jour. On a passé 4h avec David. Maintenant on sait
exactement quoi corriger et dans quel ordre."

Plan d'action remis. Re-test dans 30 jours.

PS : leur agence web n'est pas en cause. Un audit, c'est un métier différent.

#cybersécurité #ecommerce #TPE
```

### Post #6 — JEUDI — Opinion (positionnement fort)

```
Pourquoi un rapport d'audit de 50 pages ne sert à rien.

J'ai lu une dizaine de rapports de gros cabinets pour des PME.
Verdict : illisibles, intimidants, jamais appliqués.

Le pire que j'ai vu :
📄 47 pages de rapport
📊 Tableau Excel de 312 lignes "à corriger"
🎯 0 priorisation
💼 0 plan d'action concret
📅 0 suivi 6 mois plus tard

Coût pour la PME : 6 800€ HT.
Impact réel sur la sécurité : zéro.

Mon approche :
1️⃣ Top 10 priorisé (P0, P1, P2)
2️⃣ Pour chaque finding : la commande exacte ou le code à modifier
3️⃣ Un appel de 30 min pour expliquer
4️⃣ Un re-test 30 jours après pour vérifier que c'est corrigé

Un audit doit produire des correctifs.
Pas du papier.

#cybersécurité #PME
```

---

## SEMAINE 3 — Crédibilité + push outils

### Post #7 — LUNDI — Pédagogique RGPD

```
RGPD et cybersécurité : ce que votre prestataire web ne fait pas pour vous.

Idée reçue : "Mon prestataire web s'occupe de tout."
Réalité : votre prestataire fait son boulot (le site marche). Pas le vôtre (la conformité).

Ce qui RESTE à votre charge en tant que dirigeant :
☑️ Registre des traitements (art. 30 RGPD)
☑️ Politique de confidentialité à jour
☑️ Bandeau cookies conforme (pas un dark pattern)
☑️ Procédure de notification de fuite sous 72h
☑️ Sécurisation des accès (MFA, principe du moindre privilège)
☑️ Sauvegardes chiffrées et testées
☑️ Audit annuel (recommandé par la CNIL)

Si vous ne pouvez pas cocher 7/7, vous êtes en risque.
Pas juridique uniquement. Opérationnel.

Vous voulez le check-up complet ?
Commentez "RGPD" et je vous envoie ma checklist gratuite (12 points).

#RGPD #PME #cybersécurité
```

### Post #8 — MERCREDI — Show off technique (Cyber-Vault)

```
J'ai codé mon propre gestionnaire de mots de passe.

Pas parce que Bitwarden est mauvais (il est excellent).
Mais parce que c'est LE projet qui force à maîtriser :
🔐 La crypto applicative (AES-256-GCM, PBKDF2, Web Crypto API)
🔐 Le zero-knowledge (le serveur ne voit JAMAIS le mot de passe)
🔐 La gestion sécurisée des sessions (JWT + refresh révocables)
🔐 La défense en profondeur (rate limit, lockout, CSP, headers...)

Stack : FastAPI + PostgreSQL + Angular 17 + chiffrement côté client.
CI/CD complet : Bandit, pip-audit, Pytest, Playwright.
Open source bientôt.

Pourquoi je vous raconte ça ?

Parce que quand je vous propose d'auditer votre app,
je le fais avec les mains d'un dev qui s'est lui-même cassé les dents
sur les mêmes problèmes que vous.

Pas un consultant qui lit des cases à cocher.

#DevSecOps #FastAPI #Angular
```

### Post #9 — JEUDI — Coulisses + appel à témoignage

```
Petit teaser de ce que vous recevez après un audit Flash.

📄 Rapport synthétique (8-12 pages, lisible par un non-tech)
🎯 Top 10 priorisé (rouge / orange / jaune)
💻 Pour chaque finding : capture d'écran + correctif technique
📞 Appel de 30 min pour parcourir le rapport ensemble
📅 Re-test à 30 jours inclus

Le tout pour 490€ HT.

(Pour comparaison : un rapport "gros cabinet" : 5-8k€,
et vous le lirez jamais.)

Si vous êtes dirigeant TPE/PME et que vous voulez tester :
- Soit le scan gratuit sur [URL]
- Soit on prend 15 min en visio pour voir si ça matche votre besoin

Pas de pitch commercial. Juste une discussion.

#cybersécurité #PME #audit
```

---

## SEMAINE 4 — Activation LinkedIn Ads (booster ce qui marche)

> 💡 À partir de cette semaine, **identifier le post le plus engageant des 9 premiers**
> et le booster en LinkedIn Ads (200€ sur 20 jours).

### Post #10 — LUNDI — Anti-FUD positif

```
Stop au FUD cybersécurité.

(FUD = Fear, Uncertainty, Doubt — la peur comme argument de vente.)

Je vois des posts du type :
🚨 "82% des PME attaquées font faillite dans les 18 mois !"
🚨 "Un ransomware peut détruire votre entreprise !"
🚨 "Vos données valent de l'or sur le dark web !"

C'est marketing.
Ce n'est pas faux mais ce n'est pas utile.

Ce qui est utile :
✅ Comprendre VOTRE surface d'attaque (votre site, vos comptes, votre Cloud)
✅ Identifier les 3-5 failles concrètes qui VOUS concernent
✅ Les corriger une par une, sans paniquer

La cybersécurité, ce n'est pas un sujet de cauchemar.
C'est un sujet de gestion, comme la compta ou les RH.

Et comme la compta, ça commence par un audit clair.

#cybersécurité #PME
```

### Post #11 — MERCREDI — Pédagogique pratique

```
5 vérifs gratuites à faire MAINTENANT sur votre site.

(5 minutes max, aucun outil payant, accessible à tous.)

1️⃣ Tapez votre URL sur https://www.ssllabs.com/ssltest/
→ Vous devez avoir au moins une note A. Si "B" ou moins : alerte.

2️⃣ Tapez votre URL sur https://securityheaders.com
→ Idem, viser A. La plupart des sites PME sont à F.

3️⃣ Tapez https://haveibeenpwned.com/ avec votre email pro
→ Si présent dans une fuite : changez immédiatement + activez MFA.

4️⃣ Sur Google : "site:VOTRE-DOMAINE.fr filetype:pdf OR filetype:xlsx"
→ Si vous voyez des fichiers internes, ils sont publics. Indexation à corriger.

5️⃣ Sur Google : "VOTRE-DOMAINE.fr password OR mot de passe"
→ Idem, parfois on trouve des mots de passe dans des forums oubliés.

Si vous trouvez un truc inquiétant : MP, je vous aide à corriger.

#cybersécurité #PME #TPE
```

### Post #12 — JEUDI — Témoignage / preuve sociale

```
"On a refusé pendant 2 ans. On a eu tort."

C'est ce que m'a dit [Prénom], dirigeant d'un cabinet d'experts-comptables
de 11 personnes, en début de mission la semaine dernière.

Le déclic : un confrère lyonnais s'est fait ransomwarer en novembre.
2 semaines d'arrêt. 35 000€ de rançon (non payée). 12 clients perdus.

Findings de leur audit (cabinet de 11 personnes) :
🔴 2 critiques (j'avais sous-estimé)
🟠 4 modérées
🟡 8 mineures

Le plus dur ? Ils PENSAIENT être bien protégés.
Antivirus pro, sauvegardes, mots de passe "compliqués"...
Mais aucun audit indépendant en 6 ans.

Ce qu'on a fait en 4h :
✅ Identifié les 2 critiques (compromission Office 365 possible)
✅ Plan d'action 30 jours
✅ Devis pour un suivi mensuel (Sentinelle, 350€/mois)

Pour 490€ HT, ils ont éliminé un risque chiffré à >100k€.

#cybersécurité #PME #expertcomptable
```

---

## SEMAINE 5 — Push offres récurrentes

### Post #13 — LUNDI — Pédagogique surveillance

```
"Un audit, c'est une photo. La sécurité, c'est un film."

Cette phrase, je la dis à chaque client en fin d'audit.

Pourquoi ?

Un audit ponctuel vous dit où vous en êtes AUJOURD'HUI.
Dans 30 jours, vous avez :
→ Mis à jour 4 plugins
→ Embauché 2 personnes (donc 2 comptes en plus)
→ Changé d'hébergeur sur un sous-domaine
→ Reçu 3 emails de phishing dans la nuit

Et personne ne le surveille.

C'est pour ça que mes 3 abonnements existent :
🟢 Vigie (120€/mois) : scan hebdo + alerte si nouveau risque
🟢 Sentinelle (350€/mois) : scan quotidien + rapport mensuel
🟢 Blindage 360 (950€/mois) : surveillance continue + 2h de conseil/mois

C'est nettement moins cher qu'un RSSI à plein temps.
Et nettement mieux qu'un antivirus pro tout seul.

À méditer.

#cybersécurité #PME #RSSI
```

### Post #14 — MERCREDI — Coulisses outil

```
Petite démo de mon scanner de prod.

[Joindre une capture d'écran floutée du scanner en action]

Quand un client signe pour un audit Flash, voici ce qui tourne en arrière-plan :

🔍 Phase 1 (5 min) : reconnaissance
- DNS, sous-domaines, technos détectées, certificats SSL
- Versions exposées dans les headers
- Configuration TLS

🔍 Phase 2 (15 min) : surface d'attaque
- Endpoints API découverts
- Formulaires, uploads, redirections
- Cookies, sessions, gestion d'auth

🔍 Phase 3 (1-2h) : tests manuels
- C'est là que ça devient intéressant
- Logique métier, contournement d'auth, escalade de privilèges
- C'est ce que les scanners ratent

🔍 Phase 4 (30 min) : rapport
- Priorisation P0/P1/P2
- Captures + correctifs
- Estimation de remédiation

Total : 4h. Coût : 490€ HT. ROI moyen : x100 (cf. coût moyen d'une attaque).

#cybersécurité #pentest #DevSecOps
```

### Post #15 — JEUDI — Question ouverte (engagement)

```
Question sincère aux dirigeants TPE/PME qui me lisent.

Qu'est-ce qui vous freine pour faire un audit cybersécurité ?

J'ai mes hypothèses :
🤔 "Trop cher" (alors qu'un Flash est à 490€...)
🤔 "Pas le temps" (4h de mobilisation, pas plus)
🤔 "On est trop petits, ça intéresse personne" (FAUX, les PME sont les CIBLES n°1)
🤔 "Je ne saurai pas quoi faire avec les résultats" (c'est le job de l'auditeur)
🤔 "On verra plus tard" (THE big one)

Mais je veux votre vraie réponse.

Commentez en toute honnêteté. Pas de jugement. Je veux comprendre.

(Et si ça peut faire avancer le sujet pour vous : je réponds personnellement
à chaque commentaire.)

#cybersécurité #PME #dirigeant
```

---

## SEMAINE 6 — Closing et appel à l'action

### Post #16 — LUNDI — Bilan / preuve sociale cumulée

```
6 semaines depuis le lancement de mon activité d'audit. Bilan.

📊 Audits réalisés : [X] (à compléter)
🎯 Failles critiques trouvées : [X]
💼 Clients sous abonnement Sentinelle : [X]
🔄 Re-test à 30 jours : [X]% des findings critiques corrigés

Et surtout : 0 client déçu (à date).

Ce qui marche dans mon approche :
✅ Pas de baratin commercial — je code, j'audite, je remets le rapport
✅ Prix lisible, pas de "consulting day" à 1500€
✅ Suivi inclus (re-test 30j) au lieu de "merci au revoir"

Ce qui me reste à améliorer :
🔄 Réactivité sur les demandes urgentes (j'ajoute un créneau d'urgence à 750€)
🔄 Industrialisation du livrable (template en cours)
🔄 Communication régulière auprès des clients abonnés

Si vous avez tergiversé jusqu'ici : c'est le moment.
Mes 3 prochaines semaines se remplissent vite.

#cybersécurité #PME #bilan
```

### Post #17 — MERCREDI — Offre limitée / urgence saine

```
Pour les dirigeants TPE/PME qui me suivent depuis quelques semaines.

J'ouvre 3 créneaux d'audit Flash pour [mois prochain].
(Au prix normal : 490€ HT.)

Pas de promo bidon. Pas de "Black Friday cyber".
Juste 3 créneaux parce que je ne peux pas en faire plus en parallèle.

Pour chaque créneau, vous repartez avec :
✅ Audit complet de votre site (4h de mon temps)
✅ Rapport synthétique 8-12 pages
✅ Plan d'action priorisé P0/P1/P2
✅ Appel de 30 min pour parcourir
✅ Re-test à 30 jours inclus

Comment réserver :
1️⃣ MP avec le nom de votre site
2️⃣ Je confirme la dispo dans la journée
3️⃣ On bloque un créneau, vous recevez la facture
4️⃣ Audit lancé dans la semaine

Premier arrivé, premier servi.

#cybersécurité #PME #audit
```

### Post #18 — JEUDI — Vision / fermeture de boucle

```
Pourquoi je fais ce métier.

J'ai bossé 8 ans comme Product Owner.
J'ai vu des PME se faire avoir par défaut de sécurité.
J'ai vu des dirigeants pleurer parce qu'ils avaient perdu 6 mois de données.
J'ai vu des équipes débarquées un lundi matin parce que l'IT était bloquée.

Aucun de ces cas n'aurait coûté plus de 2000€ à éviter.
Mais personne ne leur avait dit :
→ "Faites un audit annuel."
→ "Mettez en place une surveillance."
→ "Formez vos équipes au phishing."

Donc je me suis dit : OK, je le fais.
Avec mes compétences de dev. Avec ma rigueur d'auditeur.
Avec des prix accessibles à une TPE de 5 personnes.

Rocher Cybersécurité, ce n'est pas un produit.
C'est ma manière de répondre à un truc qui m'énerve depuis 8 ans :
les PME françaises ne sont pas mal protégées par incompétence.
Elles le sont par manque de prestataires accessibles.

Je suis là pour ça.

Si vous êtes dirigeant TPE/PME et que ce post vous parle : MP ouvert.

#cybersécurité #PME #pourquoi
```

---

## Templates de commentaires à laisser sur les posts d'autres

> Objectif : 5 commentaires/jour minimum sur des posts de dirigeants TPE/PME locaux.

**Sur un post parlant de transformation numérique :**
> "Très juste sur la partie outils. Une réflexion souvent oubliée : la sécurité applicative. Avant d'industrialiser un outil, on vérifie qu'il ne fuit pas les données clients. Vous traitez ce point dans votre démarche ?"

**Sur un post parlant de RGPD :**
> "Bon point. Une question revient toujours en audit : "est-ce qu'on chiffre les sauvegardes ?". Réponse honnête de 90% des PME : "on ne sait pas". C'est pourtant le talon d'Achille principal."

**Sur un post parlant d'IA / nouveaux outils :**
> "Curieux de votre retour. Ce qui m'intéresse côté cyber : ces outils stockent quoi, où, et avec quel chiffrement ? C'est rarement clair dans les CGU, et c'est ce qui coince en audit RGPD."

**Sur un post générique de dirigeant :**
> "Sujet hyper concret. Bravo pour la transparence. (PS : je suis auditeur cybersécurité, si jamais le sujet vous concerne un jour, je suis à 30 min de Lyon.)"

⚠️ **Ne jamais spammer ces commentaires.** Adapter à chaque post, apporter de la valeur d'abord.

---

## Mesure de performance

À tracker chaque vendredi dans un Google Sheet :

| Semaine | Posts publiés | Impressions cumulées | Engagement moyen | Profile views | Connexions reçues | MP reçus | Leads qualifiés |
|---------|---------------|----------------------|------------------|---------------|-------------------|----------|------------------|

**Objectif S6 cumulé :**
- 15 000+ impressions
- 5+ leads qualifiés (MP avec intention d'achat)
- 2-3 audits vendus directement attribués à LinkedIn

---

## Prochaines étapes après ce calendrier

Une fois les 18 posts publiés :
1. Analyser quels formats ont le mieux marché
2. Doubler la cadence sur les formats gagnants
3. Recycler les meilleurs en articles de blog (SEO)
4. Tester la newsletter LinkedIn (mode pro)

*Fin du calendrier éditorial.*
