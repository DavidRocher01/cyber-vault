# Déclarer un incident NIS2 : les 3 délais à connaître

> **En cas de cyberattaque, NIS2 impose de notifier les autorités dans des délais stricts. Un retard peut coûter jusqu'à 10 millions d'euros d'amende.** (Directive NIS2, Art. 23)

## 🎯 Ce que vous apprendrez
- Les 3 délais de notification NIS2 et leur contenu
- Qui doit déclarer, à qui et comment
- Ce que vous devez faire dès les premières minutes d'un incident

---

## Scénario réel

*Vendredi 17h30. Amandine, responsable administrative d'une ETI du secteur santé, remarque que ses collègues ne peuvent plus accéder aux dossiers patients. L'écran affiche un message de rançon. Elle appelle immédiatement son DSI — qui est en déplacement. Personne ne sait exactement quoi faire ni quand prévenir qui. 72 heures plus tard, l'ANSSI est enfin contactée. Résultat : une amende pour déclaration tardive, en plus du ransomware.*

Ce scénario se répète dans des centaines d'organisations. La panique du moment fait oublier les obligations légales. Ce module vous donne les clés pour réagir correctement.

---

## Qu'est-ce qu'un incident NIS2 ?

Selon la directive, un **incident significatif** est un événement qui :
- Cause une interruption de service significative
- Provoque des pertes financières importantes
- Affecte d'autres organisations ou personnes
- Implique un accès non autorisé à des systèmes

Exemples concrets :
- Ransomware chiffrant vos serveurs
- Exfiltration de données clients ou RH
- Attaque DDoS paralysant votre site e-commerce
- Intrusion non autorisée dans votre infrastructure

---

## Les 3 délais de notification NIS2

### ⏱️ Délai 1 — Alerte précoce : 24 heures

Dès que vous suspectez un incident significatif, votre organisation doit transmettre une **alerte précoce** à l'autorité compétente (en France : l'ANSSI ou le CERT-FR).

**Ce que vous déclarez à 24h :**
- La nature présumée de l'incident (ransomware, intrusion, DDoS…)
- L'heure et la date de détection
- Si l'incident est en cours ou contenu
- Si une cyberattaque est suspectée (oui/non)

> ❗ Vous n'avez pas besoin d'avoir toutes les réponses. L'alerte précoce est une notification, pas un rapport complet.

### 📋 Délai 2 — Notification détaillée : 72 heures

Dans les 72 heures suivant la détection, vous devez transmettre une **notification complète** incluant :
- Description détaillée de l'incident
- Systèmes et données affectés
- Nombre d'utilisateurs/organisations impactés
- Mesures de remédiation mises en place
- Impact opérationnel estimé

### 📄 Délai 3 — Rapport final : 1 mois

Dans le mois suivant la résolution, vous devez soumettre un **rapport final** couvrant :
- Analyse de la cause racine
- Chronologie complète de l'incident
- Mesures correctives implémentées
- Plan pour éviter la récurrence

---

## Qui déclare ?

La responsabilité de la déclaration incombe à **l'entité NIS2**, c'est-à-dire votre organisation en tant que telle — représentée par sa direction ou son RSSI. Mais en pratique :

| Rôle | Responsabilité |
|------|----------------|
| **Vous** | Détecter et signaler immédiatement à votre responsable / IT |
| **Responsable IT / RSSI** | Évaluer la criticité et déclencher la procédure |
| **Direction** | Valider la déclaration aux autorités |
| **ANSSI / CERT-FR** | Reçoit et traite la déclaration |

**Règle d'or :** en cas de doute, signalez toujours — mieux vaut une déclaration inutile qu'une déclaration manquée.

---

## À qui déclarer en France ?

- **ANSSI** (Agence Nationale de la Sécurité des Systèmes d'Information) : [anssi.fr](https://www.anssi.fr)
- **CERT-FR** : via la plateforme dédiée ou par email sécurisé
- **CNIL** : si des données personnelles sont compromises (délai RGPD : 72h également)
- **Assureur cyber** : vérifiez votre contrat, certains exigent une notification immédiate

---

## Vos premiers réflexes en cas d'incident

### La minute zéro — ce que vous devez faire immédiatement

1. **Ne pas paniquer** — ne faites rien qui pourrait aggraver la situation ou effacer des preuves
2. **Ne pas éteindre les machines** (sauf instruction contraire) — les logs sont sur les machines en cours
3. **Déconnecter du réseau** si l'IT vous le demande — débrancher le câble Ethernet, désactiver le Wi-Fi
4. **Signaler immédiatement** à votre responsable direct et à l'IT
5. **Documenter ce que vous avez vu** — heure, message d'erreur, comportement anormal, screenshot si possible
6. **Ne pas communiquer sur les réseaux sociaux** — pas de tweet, pas de post LinkedIn

### Ce que vous ne devez surtout pas faire
❌ Payer une rançon sans l'accord de la direction et des autorités
❌ Tenter de "réparer" vous-même sans l'accord de l'IT
❌ Éteindre les serveurs en panique
❌ Informer des partenaires extérieurs avant d'en avoir reçu l'instruction

---

## Les sanctions NIS2

Pour les **entités essentielles** (énergie, santé, eau, transports…) :
- Jusqu'à **10 millions d'euros** ou 2 % du chiffre d'affaires mondial

Pour les **entités importantes** (services numériques, PME critiques…) :
- Jusqu'à **7 millions d'euros** ou 1,4 % du CA mondial

Ces amendes s'appliquent notamment en cas de **déclaration tardive ou incomplète**.

---

## Résumé — Les 3 délais à retenir

| Délai | Contenu | Destinataire |
|-------|---------|-------------|
| **24h** | Alerte précoce (nature + heure) | ANSSI / CERT-FR |
| **72h** | Notification détaillée | ANSSI + CNIL si données perso |
| **1 mois** | Rapport final avec analyse | ANSSI |

**Votre rôle :** détecter vite, signaler immédiatement en interne, ne pas effacer les preuves. Le reste, c'est l'affaire de votre direction et de votre RSSI.
