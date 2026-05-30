# Réseaux sociaux et OSINT : ce que vous exposez sans le savoir

> **Un attaquant déterminé peut construire un profil complet de sa cible en moins de 2 heures, uniquement avec des sources publiques et gratuites.** Votre LinkedIn, votre Twitter, le site de votre entreprise — tout est de l'OSINT.

## 🎯 Ce que vous apprendrez

- Comprendre ce qu'est l'OSINT et comment les attaquants l'utilisent
- Identifier ce que vous exposez sur LinkedIn et les réseaux sociaux
- Réduire votre empreinte numérique professionnelle sans disparaître

---

## Scénario réel

*Avant d'attaquer une entreprise de services financiers, un groupe de hackers passe 3 jours à collecter de l'OSINT. Sur LinkedIn : organigramme, noms des responsables IT et finance, projets en cours mentionnés dans les profils. Sur le site web : noms des dirigeants et leurs photos. Sur Twitter : un développeur a publié un screenshot de son terminal avec le nom de domaine interne visible. Sur GitHub : un stagiaire a poussé du code avec des clés API en clair. En 72h, les attaquants connaissent l'organisation mieux que certains employés.*

Cette reconnaissance précède systématiquement les attaques sophistiquées.

---

## Qu'est-ce que l'OSINT ?

L'OSINT (Open Source INTelligence) désigne la collecte de renseignements à partir de sources publiques et légalement accessibles.

Les attaquants utilisent l'OSINT pour :

- Construire l'organigramme d'une entreprise cible
- Identifier les personnes clés (finance, IT, RH, direction)
- Comprendre les technologies utilisées (offres d'emploi, GitHub, profils tech)
- Trouver des contacts pour le spear phishing
- Détecter des informations sensibles publiées par inadvertance

---

## Ce que LinkedIn révèle à un attaquant

LinkedIn est la source OSINT professionnelle la plus riche. Chaque profil public expose :

**Votre poste et responsabilités** → l'attaquant sait qui peut autoriser des virements, accéder aux systèmes, traiter des données sensibles.

**Votre hiérarchie et vos collègues** → il reconstitue l'organigramme sans avoir besoin de l'annuaire interne.

**Vos projets en cours** → "Je viens de terminer la migration vers Azure" ou "Nous déployons SAP d'ici fin d'année" révèle la stack technologique et les prestataires.

**Vos connexions** → il sait qui vous connaissez, qui sont vos relations de confiance.

**L'entreprise elle-même** → taille, secteur, bureaux, technologies utilisées (souvent listées dans les descriptions de postes d'offres d'emploi).

---

## Ce que vous ne devriez pas publier

### Sur les réseaux professionnels

- Détails de projets confidentiels ou en cours ("on travaille sur X avec le client Y")
- Informations sur vos systèmes internes, technologies, prestataires
- Captures d'écran de vos outils professionnels (interfaces internes visibles)
- Frustrations professionnelles qui révèlent des tensions internes ou des failles

### Sur les réseaux personnels

- Photos depuis votre lieu de travail montrant des informations au tableau, des écrans
- Check-ins et localisations régulières qui permettent de prédire vos déplacements
- Informations sur vos absences ("je pars en vacances 2 semaines") — signal pour les attaquants

### Sur GitHub / espaces techniques

- Clés API, tokens, mots de passe dans du code (même dans un dépôt privé — les fuites existent)
- Noms de domaines internes, adresses IP, schémas d'architecture
- Fichiers de configuration contenant des informations d'environnement

---

## Les offres d'emploi comme source OSINT

Votre entreprise cherche un "Administrateur CrowdStrike + Azure AD" → l'attaquant sait que vous utilisez CrowdStrike et Azure AD, et cherche les vulnérabilités associées.

Ce n'est pas une raison de ne pas recruter — mais c'est une raison pour que le service IT soit conscient de ce qu'il expose dans les offres.

---

## Comment réduire votre exposition sans disparaître

**Contrôlez votre visibilité LinkedIn**

- Vérifiez qui peut voir votre profil complet
- Réfléchissez avant de mentionner les projets en cours et les technologies

**Réfléchissez avant de publier**

Avant chaque publication professionnelle, demandez-vous : "Si un concurrent ou un attaquant voit ça, que peut-il en déduire ?"

**Configurez vos paramètres de confidentialité**

Revoyez régulièrement les paramètres de confidentialité de vos réseaux sociaux. La plupart sont par défaut en "public".

**Signalez les expositions**

Si vous voyez un collègue publier quelque chose qui révèle des informations sensibles de l'entreprise, signalez-le discrètement. Ce n'est généralement pas intentionnel.

---

## À retenir

- **L'OSINT est gratuit et légal** — les attaquants l'utilisent systématiquement avant d'agir
- **LinkedIn est une mine d'or pour l'ingénierie sociale** — limitez l'exposition des projets et technologies internes
- **Vos offres d'emploi révèlent votre stack** — en avoir conscience est déjà une protection
- **"Réfléchissez avant de publier"** — surtout pour les screenshots, projets en cours et informations techniques
- La visibilité numérique n'est pas mauvaise en soi — c'est ce qu'elle révèle qui compte
