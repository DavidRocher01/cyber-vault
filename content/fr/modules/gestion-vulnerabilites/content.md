# Mises à jour et correctifs : pourquoi c'est non négociable

> **80 % des cyberattaques réussies exploitent des vulnérabilités connues pour lesquelles un correctif existait déjà.** (Gartner 2023)

## 🎯 Ce que vous apprendrez
- Pourquoi une vulnérabilité non corrigée est une porte ouverte pour les attaquants
- Ce que font les hackers avec une vulnérabilité connue
- Vos responsabilités dans la gestion des mises à jour

---

## Scénario réel

*En mai 2017, le ransomware WannaCry a paralysé 200 000 ordinateurs dans 150 pays en 72 heures — dont des hôpitaux britanniques qui ont dû refuser des patients. La faille exploitée (EternalBlue) avait été corrigée par Microsoft deux mois plus tôt. Les organisations touchées n'avaient simplement pas installé la mise à jour. Coût estimé : 4 milliards de dollars.*

Ce n'est pas une histoire ancienne. En 2021, l'attaque Colonial Pipeline — qui a privé des millions d'Américains d'essence — a également exploité un système non mis à jour.

---

## Une vulnérabilité, c'est quoi concrètement ?

Un logiciel (Windows, votre navigateur, une application métier, un équipement réseau) est écrit par des humains. Il contient donc des erreurs. Certaines de ces erreurs sont des **vulnérabilités de sécurité** : des failles que des attaquants peuvent exploiter pour :

- Prendre le contrôle de votre machine
- Lire vos fichiers sans votre permission
- Installer un malware invisible
- Utiliser votre ordinateur pour attaquer d'autres systèmes

Quand un éditeur découvre une faille, il publie un **correctif** (patch) pour la corriger. Le problème : entre le moment où la faille est découverte et le moment où vous installez le correctif, votre machine est vulnérable.

---

## La course contre la montre

Voici ce qui se passe quand une vulnérabilité est rendue publique :

**Jour 0 — Publication de la vulnérabilité**
L'éditeur publie un bulletin de sécurité et met à disposition le correctif.

**Jour 1-3 — Analyse par les attaquants**
Des milliers de hackers analysent immédiatement la vulnérabilité pour créer des outils d'exploitation automatisés.

**Jour 7 — Exploitation massive**
Des outils permettant d'exploiter la faille automatiquement circulent sur des forums cybercriminels.

**Semaines 2-8 — Vague d'attaques**
Des organisations qui n'ont pas encore patché sont massivement ciblées.

**Conclusion :** Chaque jour sans mise à jour est une opportunité supplémentaire pour les attaquants.

---

## Les "zero-day" : la menace invisible

Une vulnérabilité **zero-day** est une faille dont l'éditeur n'a pas encore connaissance — et pour laquelle il n'existe donc aucun correctif.

Ces vulnérabilités sont extrêmement précieuses sur le marché noir (parfois plusieurs millions de dollars). Elles sont utilisées par :
- Des groupes de cybercriminels sophistiqués
- Des services de renseignement étatiques

**La bonne nouvelle :** pour la grande majorité des attaques (>80%), ce ne sont pas des zero-days qui sont exploités — mais des vulnérabilités connues et corrigées depuis des semaines ou des mois. L'ennemi est la **procrastination**, pas la sophistication.

---

## Ce que NIS2 impose

L'article 21 de NIS2 exige la **gestion des vulnérabilités** comme mesure de sécurité obligatoire. Concrètement, votre organisation doit :

✅ Maintenir un inventaire des actifs logiciels et matériels
✅ Appliquer les correctifs critiques dans un délai défini
✅ Effectuer des analyses de vulnérabilités régulières
✅ Prioriser les correctifs selon le niveau de risque

---

## Votre rôle dans les mises à jour

Vous n'êtes pas administrateur système, mais vous avez un rôle crucial.

### Ne retardez pas les mises à jour

Quand Windows, votre navigateur Chrome ou Firefox, ou votre application métier vous propose une mise à jour :
- **Ne cliquez pas sur "Me rappeler plus tard"** si ce n'est pas urgent pour votre travail en cours
- **Appliquez les mises à jour en fin de journée** ou pendant votre pause déjeuner
- **Ne débranchez pas votre ordinateur** pendant une mise à jour en cours

### Signalez les logiciels non maintenus

Si vous utilisez un logiciel dont vous n'avez plus de mise à jour depuis longtemps, ou dont l'éditeur a arrêté le support, signalez-le à votre IT. Exemple : Windows 7, Internet Explorer, Flash Player sont des logiciels que vous ne devriez plus utiliser sur un poste professionnel.

### Faites confiance aux demandes de votre IT

Si votre équipe IT vous demande d'appliquer une mise à jour en urgence — même en dehors des plages habituelles — c'est probablement pour une raison sérieuse. Coopérez sans délai.

---

## Comment sont classées les vulnérabilités ?

Le système **CVSS** (Common Vulnerability Scoring System) classe les vulnérabilités de 0 à 10 :

| Score | Niveau | Délai recommandé pour le patch |
|-------|--------|-------------------------------|
| 9.0-10.0 | 🔴 Critique | 24-48 heures |
| 7.0-8.9 | 🟠 Élevé | 7 jours |
| 4.0-6.9 | 🟡 Moyen | 30 jours |
| 0-3.9 | 🟢 Faible | Planification normale |

Votre IT priorise les correctifs selon ces niveaux. Quand une mise à jour critique est demandée, il y a une raison.

---

## Les équipements oubliés

Les mises à jour ne concernent pas que votre ordinateur. Vos équipements personnels et professionnels sont aussi concernés :

- **Téléphone professionnel** : mettez à jour iOS ou Android régulièrement
- **Routeur Wi-Fi** : les routeurs ont aussi des firmwares à mettre à jour (votre IT s'en charge en entreprise)
- **Applications mobiles** : vérifiez que vos apps professionnelles sont à jour

---

## Résumé

Les mises à jour ne sont pas une contrainte administrative — elles sont votre protection contre des attaques réelles et documentées.

**Vos 3 engagements :**
1. Appliquer les mises à jour proposées par votre système et vos logiciels sans délai inutile
2. Ne jamais bloquer ou contourner les politiques de mise à jour imposées par votre IT
3. Signaler tout logiciel ou équipement qui ne reçoit plus de mises à jour

Un ordinateur non à jour dans votre réseau est une porte entrouverte sur toute votre organisation.
