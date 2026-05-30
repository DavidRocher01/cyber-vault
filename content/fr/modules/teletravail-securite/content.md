# Télétravail : sécuriser son environnement à domicile

> **Depuis 2020, les incidents de sécurité liés au télétravail ont augmenté de 238 %.** (FBI IC3) Travailler depuis chez soi expose à des risques très différents du bureau — réseau partagé, matériel personnel, absence de périmètre IT.

## 🎯 Ce que vous apprendrez

- Identifier les risques spécifiques au travail à domicile
- Sécuriser votre réseau domestique et votre espace de travail
- Appliquer les bonnes pratiques qui s'imposent hors du bureau

---

## Scénario réel

*En 2020, une PME subit une intrusion via le compte VPN d'un employé en télétravail. L'enquête révèle : routeur domestique avec firmware non mis à jour depuis 3 ans, mot de passe Wi-Fi "nomduquartier2019", partage de l'ordinateur professionnel avec les enfants. L'attaquant avait compromis le routeur via une vulnérabilité connue, intercepté le trafic, et récupéré les identifiants VPN. Coût : 80 000 € de données clients exfiltrées.*

Ce scénario est représentatif d'une majorité d'incidents télétravail — non pas de sophistication, mais de configurations négligées.

---

## Votre réseau domestique est votre périmètre

Au bureau, l'IT gère le réseau, les pare-feux, les mises à jour. Chez vous, **vous êtes votre propre IT**.

### Sécuriser votre box/routeur

- **Changez le mot de passe administrateur par défaut** — "admin/admin" est la première tentée
- **Mettez à jour le firmware** — votre opérateur envoie des mises à jour automatiques, mais vérifiez dans l'interface d'administration
- **Activez WPA3** ou au minimum WPA2 — jamais WEP (cassé depuis des années)
- **Changez le nom du réseau (SSID)** pour ne pas révéler votre opérateur ou votre adresse

### Isoler le réseau professionnel

Si votre routeur le permet, créez un **réseau Wi-Fi invité** dédié à vos appareils professionnels. Cela isole votre poste de travail des autres appareils de la maison (TV connectée, consoles, appareils IoT souvent non sécurisés).

---

## Le VPN d'entreprise : obligatoire, pas optionnel

Le VPN n'est pas une contrainte — c'est le tunnel chiffré qui relie votre domicile au réseau de l'entreprise de façon sécurisée.

**Activez-le dès que vous démarrez votre journée de travail**, pas seulement pour accéder aux ressources internes. Tout votre trafic professionnel doit passer par lui.

Si vous rencontrez des problèmes de performance, signalez-le à l'IT — mais ne le désactivez pas.

---

## Séparation vie pro / vie perso

### Le matériel

- **N'utilisez pas votre ordinateur professionnel à des fins personnelles** : réseaux sociaux, jeux, streaming
- **Ne laissez pas votre famille utiliser votre poste professionnel** — même pour "juste regarder quelque chose"
- Si vous utilisez votre ordinateur personnel pour travailler (BYOD), les règles de sécurité de l'entreprise s'appliquent intégralement

### L'espace de travail

- **Verrouillez votre écran** (Win+L ou Cmd+Ctrl+Q) dès que vous vous levez
- **Évitez les conversations professionnelles sensibles** dans des espaces partagés où vous pouvez être entendu
- **Les documents imprimés** contenant des données professionnelles ne traînent pas sur le bureau — destruction immédiate après utilisation

---

## Les risques spécifiques du domicile

### Les appareils IoT

Votre réseau domestique est probablement peuplé d'appareils connectés peu sécurisés : enceintes intelligentes, thermostats, ampoules connectées, caméras. Ces appareils peuvent être compromis et utilisés pour observer votre activité ou propager des malwares.

**Règle** : gardez-les sur un réseau séparé (Wi-Fi invité) de votre poste de travail.

### Les écoutes involontaires

Les enceintes intelligentes (Alexa, Google Home) écoutent en permanence. Lors d'appels professionnels confidentiels, désactivez-les ou éloignez-vous de leur portée.

### Le "shoulder surfing" familial

Un membre de la famille qui passe derrière vous peut voir des données confidentielles. Positionnez votre écran pour limiter la visibilité latérale, ou utilisez un filtre de confidentialité.

---

## À retenir

- **Votre routeur domestique est une porte d'entrée** — changez les mots de passe par défaut et mettez-le à jour
- **VPN activé dès le démarrage**, pas seulement pour les accès internes
- **Ordinateur pro = usage pro uniquement** — pas de partage familial
- **Verrouillez l'écran** dès que vous quittez votre poste, même 5 minutes
- Les appareils IoT domestiques sont des vecteurs de risque — isolez-les du réseau pro
