# Sécurité de la chaîne d'approvisionnement

> **62 % des violations de données impliquent un tiers fournisseur ou sous-traitant.** (Verizon DBIR 2024)

## 🎯 Ce que vous apprendrez
- Pourquoi vos prestataires représentent un risque pour votre organisation
- Comment les attaquants exploitent la chaîne d'approvisionnement
- Les réflexes simples pour réduire ce risque au quotidien

---

## Scénario réel

*Thomas est responsable informatique dans une PME industrielle. Un soir, il reçoit une alerte : des données clients ont été exfiltrées. L'enquête révèle que l'intrusion n'est pas venue de l'intérieur — elle est passée par le système de facturation d'un sous-traitant comptable qui avait accès à distance à leur réseau.*

Ce type d'attaque s'appelle une **attaque par la chaîne d'approvisionnement** (supply chain attack). L'attaquant cible le maillon le plus faible — souvent un prestataire — pour atteindre la vraie cible.

---

## Pourquoi vos fournisseurs sont une surface d'attaque

Votre organisation travaille avec des dizaines de tiers : logiciels SaaS, prestataires de maintenance, cabinets comptables, agences de communication, transporteurs. Chacun peut avoir accès à vos données ou systèmes.

**Le problème :** vous maîtrisez votre sécurité interne, mais pas celle de vos partenaires.

Exemples d'accès tiers fréquents :
- **Accès VPN distant** pour la maintenance informatique
- **Partage de fichiers** via des plateformes cloud communes
- **Intégrations API** entre vos logiciels métier et ceux du prestataire
- **Boîtes email partagées** ou accès à votre messagerie

Si le prestataire est compromis, l'attaquant hérite de tous ces accès.

---

## L'attaque SolarWinds : l'exemple qui a tout changé

En 2020, des hackers ont compromis les mises à jour d'un logiciel de monitoring réseau très répandu (SolarWinds). En installant la mise à jour — une action normale et recommandée — **18 000 organisations** ont involontairement installé un backdoor, dont des agences gouvernementales américaines.

**La leçon :** même un logiciel légitime, installé correctement, peut être le vecteur d'une attaque si le fournisseur est compromis.

---

## Les 4 types d'attaque supply chain

### 1. Compromission du logiciel tiers
Un attaquant infiltre l'éditeur d'un logiciel que vous utilisez et injecte du code malveillant dans une mise à jour. Vous installez la mise à jour, vous installez le malware.

### 2. Identifiants volés chez le prestataire
Un technicien de votre prestataire informatique se fait phisher. L'attaquant utilise ses identifiants — qui incluent l'accès à votre infrastructure — pour s'introduire chez vous.

### 3. Infection par document partagé
Votre comptable externe vous envoie un fichier Excel infecté. En l'ouvrant, vous exécutez une macro malveillante.

### 4. Matériel compromis
Un équipement réseau (routeur, switch) livré avec un firmware modifié. Rare mais documenté, notamment dans certaines régions géographiques.

---

## Ce que NIS2 exige sur ce sujet

L'article 21 de la directive NIS2 impose explicitement de gérer la sécurité des **fournisseurs et sous-traitants**. Cela signifie :

✅ Évaluer le niveau de sécurité de vos prestataires critiques
✅ Intégrer des clauses de sécurité dans vos contrats
✅ Limiter les accès tiers au strict nécessaire
✅ Révoquer immédiatement les accès à la fin d'un contrat

---

## Vos réflexes au quotidien

Vous n'êtes pas responsable de la sécurité de vos fournisseurs, mais vous pouvez agir :

**Avant de donner un accès à un prestataire :**
- Vérifiez qu'il a vraiment besoin de cet accès (principe du moindre privilège)
- Demandez à votre responsable IT de créer un accès temporaire et limité
- Ne partagez jamais vos propres identifiants avec un prestataire

**En cas de fin de contrat :**
- Signalez immédiatement à l'IT que le prestataire n'a plus besoin d'accès
- Vérifiez que les documents partagés ont bien été révoqués

**Quand vous recevez un fichier d'un prestataire :**
- Méfiez-vous des macros dans les fichiers Office
- En cas de doute sur l'authenticité d'un email prestataire, appelez-le directement

**Questions à poser à vos fournisseurs critiques :**
> "Avez-vous une politique de sécurité documentée ?"
> "Faites-vous des audits de sécurité réguliers ?"
> "Comment gérez-vous les accès de vos propres employés à nos données ?"

---

## Le principe du moindre privilège appliqué aux tiers

Un prestataire comptable n'a pas besoin d'accéder à votre liste de clients. Un technicien de maintenance réseau n'a pas besoin de lire vos emails.

**Règle d'or :** donnez à chaque tiers l'accès minimum strictement nécessaire à sa mission, pour la durée strictement nécessaire.

---

## Résumé

La chaîne d'approvisionnement est l'un des vecteurs d'attaque les plus exploités. Vous ne pouvez pas imposer votre sécurité à vos prestataires, mais vous pouvez :

- Limiter et tracer tous leurs accès
- Révoquer immédiatement les accès obsolètes
- Rester vigilant sur les fichiers et liens qu'ils vous envoient
- Remonter à votre responsable IT toute situation anormale

Chaque accès tiers non contrôlé est une porte potentiellement ouverte sur votre organisation.
