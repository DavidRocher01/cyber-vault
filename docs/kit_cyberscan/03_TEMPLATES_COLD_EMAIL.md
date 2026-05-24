# Templates Cold Email B2B — Audit cybersécurité

> **Cible :** Dirigeants/DAF de TPE-PME (10-50 salariés) en Auvergne-Rhône-Alpes
> **Volume :** 100 emails sur 6 semaines, lots de 25
> **Objectif :** 5-10% de taux de réponse → 1-3 audits Flash vendus
> **Outil recommandé :** Hunter.io (recherche email) + Lemlist gratuit ou envoi manuel via Gmail/Brevo

---

## Règles d'or du cold email B2B en France

✅ **Valeur d'abord, vente ensuite** : toujours apporter un mini-finding gratuit avant de pitcher
✅ **Court** : 4-6 phrases max, lisible sur mobile en 15 secondes
✅ **Personnalisé** : prénom + nom de l'entreprise + un détail spécifique observé
✅ **Une seule question** : facile à répondre par oui/non
✅ **Pas de pièce jointe** au 1er email (filtres anti-spam)
✅ **Signature légère** : prénom + URL site, pas de logo HTML pesant
✅ **Conforme RGPD** : intérêt légitime B2B OK, mais lien de désinscription obligatoire

❌ Pas de "J'espère que ce mail vous trouve bien"
❌ Pas de "Je me permets de..."
❌ Pas de paragraphe sur QUI on est (personne ne s'en soucie au 1er contact)
❌ Pas d'urgence artificielle ("Plus que 3 places !")

---

## Template A — "Mini-finding offert" (le plus efficace)

> **Quand l'utiliser :** Première prise de contact froide. Le plus performant en taux de réponse (8-12%).

```
Objet : Une faille trouvée sur [nomdomaine.fr]

Bonjour [Prénom],

J'ai jeté un œil rapide à [nomdomaine.fr] dans le cadre de mes
recherches sur la cybersécurité des PME en [région].

J'ai noté 2 points d'amélioration immédiats :
→ [Finding 1 spécifique observé, ex: header CSP manquant]
→ [Finding 2 spécifique observé, ex: version PHP 7.4 exposée]

Rien de catastrophique, mais sur un audit complet (490€ HT),
je trouve en moyenne 8-12 failles dont 1-2 critiques.

Si ça vous intéresse, je peux vous envoyer un mini-rapport
gratuit (3 pages, sous 24h) — sans engagement.

Bien cordialement,
David Rocher
[URL site]

PS : ce message vous a été adressé en vertu de l'intérêt légitime B2B
(art. 6.1.f RGPD). Pour ne plus en recevoir, répondez "STOP".
```

### Comment préparer le mini-finding (5 min par prospect)

1. Ouvrir https://securityheaders.com/?q=[domaine] → noter la note + le 1er header manquant
2. Ouvrir https://www.ssllabs.com/ssltest/?d=[domaine] → noter la note SSL
3. Ouvrir les outils dev Chrome (F12) → onglet Network → noter version serveur exposée
4. Choisir les 2 findings les plus visuels / faciles à comprendre

### Variantes A/B à tester

**Objet A1** : "Une faille trouvée sur [nomdomaine.fr]" (curiosité forte)
**Objet A2** : "Petite vérif rapide sur [nomdomaine.fr]" (plus doux)
**Objet A3** : "[Prénom], 2 points sur la sécu de [nomdomaine.fr]" (perso + valeur)

---

## Template B — "Réseau / mise en relation"

> **Quand l'utiliser :** Si vous avez une vague connexion (LinkedIn 2nd degré, ancien collègue commun, CCI, BNI).

```
Objet : Mise en relation via [Prénom du contact commun] / sécurité [nomEntreprise]

Bonjour [Prénom],

[Prénom du contact commun] m'a glissé que vous aviez peut-être un
sujet cybersécurité à creuser sur [nomEntreprise].

Mon angle (pour gagner du temps) :
→ Je suis développeur full-stack ET auditeur cyber
→ Je travaille essentiellement avec des TPE/PME 10-50 personnes
→ Mon offre d'entrée : audit Flash 490€ HT, livrable en 5 jours

Je peux vous appeler 15 min cette semaine pour voir si ça matche ?
(Sans engagement bien sûr.)

Bonne journée,
David Rocher
[URL site]
[Numéro de téléphone]
```

---

## Template C — Cabinet d'experts-comptables / avocats

> **Quand l'utiliser :** Cible spécifique avec angle RGPD + données sensibles.

```
Objet : RGPD et données clients — un retour rapide après [événement local / actualité]

Bonjour Maître [Nom] / [Prénom],

Après [un cabinet local victime d'une attaque / un article récent sur
les obligations RGPD des professions réglementées], je me permets
de vous joindre.

Les cabinets de professions réglementées (experts-comptables, avocats,
notaires, médicaux) sont devenus la cible n°1 des attaques en 2024 :
→ Données clients à forte valeur (revente)
→ Sauvegardes souvent insuffisantes
→ Obligation RGPD renforcée (sanctions CNIL en augmentation)

Mon approche pour ces cabinets :
🔍 Audit Flash de votre site + outils internes (490€ HT)
🔍 Diagnostic RGPD (registre, sous-traitants, sauvegardes)
🔍 Plan d'action 30/60/90 jours

15 min d'appel pour voir si c'est pertinent ?

Bien cordialement,
David Rocher
[URL site]
```

---

## Template D — Relance #1 (J+5 si pas de réponse)

> **Règle :** Une relance maximum, pas plus. Sinon ça devient du harcèlement.

```
Objet : RE: Une faille trouvée sur [nomdomaine.fr]

Bonjour [Prénom],

Je me permets une relance courte au cas où mon premier message
serait passé sous les radars.

Le mini-rapport gratuit que je propose : 3 pages, sous 24h,
sans engagement, sans CB demandée.

Si le sujet ne vous concerne pas du tout, un simple "non merci"
m'aide à ne pas vous re-déranger.

Merci pour votre temps,
David
[URL site]
```

---

## Template E — Closing / proposition de RDV

> **Quand l'utiliser :** Après que le prospect a répondu favorablement au mini-finding.

```
Objet : [Prénom], voici votre mini-rapport + créneau pour en parler

Bonjour [Prénom],

Merci pour votre intérêt. Voici en pièce jointe le mini-rapport
de votre site (3 pages, gratuit, aucune obligation).

3 findings principaux à votre rythme :
🔴 [Finding critique]
🟠 [Finding modéré]
🟡 [Finding mineur]

Pour les corriger sans erreur, deux options :
1. Vous les confiez à votre prestataire web (je peux briefer directement)
2. On lance un audit Flash complet (490€ HT, livrable en 5 jours,
   re-test à 30 jours inclus)

Vous préférez qu'on en parle 15 min cette semaine ?
Voici mon Calendly : [URL Calendly]

Bien cordialement,
David Rocher
[URL site]
[Téléphone]
```

---

## Liste de scoring prospect (à remplir avant chaque envoi)

Pour chaque prospect, vérifier avant d'envoyer :

| Critère | Score |
|---------|-------|
| Site avec faille technique visible | +3 |
| Secteur sensible (e-commerce, cabinet pro, santé) | +2 |
| Localisation Auvergne-Rhône-Alpes | +2 |
| Taille 10-50 salariés | +2 |
| Site en ligne depuis 2+ ans | +1 |
| Présence d'un blog ou actualité récente sur la croissance | +1 |
| Pas de prestataire cybersécurité identifié sur LinkedIn | +1 |

**Envoyer uniquement aux prospects ≥ 8/12.**

---

## Tracking des envois (template Google Sheets)

| Date | Nom | Entreprise | URL site | Finding #1 | Finding #2 | Template | Objet utilisé | Statut | Réponse reçue | Lead qualifié | Audit signé |
|------|-----|------------|----------|------------|------------|----------|---------------|--------|----------------|----------------|-------------|

**Statuts possibles :**
- ENVOYE
- RELANCE_J5
- REPONSE_POSITIVE
- REPONSE_NEGATIVE
- RDV_PRIS
- AUDIT_SIGNE
- INJOIGNABLE
- STOP_DEMANDE

---

## KPI cible sur 100 envois

| Métrique | Cible | Excellent |
|----------|-------|-----------|
| Taux d'ouverture | 40-60% | >70% |
| Taux de réponse | 5-10% | >12% |
| Réponses positives | 2-5% | >7% |
| RDV pris | 1-3 | >5 |
| Audits Flash vendus | 1-2 | >3 |
| Revenu généré | 490-980€ | >1500€ |

**ROI cible :** 100 envois × ~50€ outils = 50€ investis → 1500€+ de CA = ROI ×30

---

## Notes de conformité RGPD

✅ Le démarchage B2B est autorisé en France au titre de l'intérêt légitime (art. 6.1.f RGPD).
✅ L'email doit concerner la fonction professionnelle du destinataire (DG, DSI...).
✅ Le destinataire doit pouvoir s'opposer facilement (mention "STOP" ou lien désabo).
✅ Pas besoin d'opt-in préalable pour les emails B2B "à fonction" (info@, contact@ → interdit).
✅ Conservation des données : 3 ans après dernier contact.

❌ Email type info@ / contact@ : INTERDIT par défaut (consentement requis).
❌ Pas de scraping de bases de données vendues sans audit RGPD du fournisseur.

---

## Outils recommandés

- **Hunter.io** (~50€/mois) : recherche emails pros + vérification délivrabilité
- **Dropcontact** (alternative française, ~50€/mois)
- **Brevo** (ex-Sendinblue) : envoi avec lien désabo automatique, gratuit jusqu'à 300/jour
- **Lemlist** : séquences automatisées (premier mois gratuit avec essai)
- **Google Sheets** : tracking, gratuit

*Fin des templates cold email.*
