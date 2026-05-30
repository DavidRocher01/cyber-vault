# Le ransomware : comprendre pour se protéger

> **La rançon moyenne demandée aux entreprises a dépassé 1,5 million de dollars en 2023.** (Sophos State of Ransomware) Mais le vrai coût — interruption, reconstruction, réputation — est souvent 5 à 10 fois plus élevé.

## 🎯 Ce que vous apprendrez

- Comprendre comment un ransomware entre et se propage
- Reconnaître les signaux d'alerte précoces
- Connaître les bons réflexes si vous suspectez une infection

---

## Scénario réel

*En mars 2021, l'hôpital de Dax (Landes) subit une attaque ransomware. Les systèmes informatiques tombent. Les médecins reviennent au papier, les opérations sont reportées, des patients transférés vers d'autres établissements. La reconstruction prend plusieurs mois. Coût estimé : plus de 2 millions d'euros. Point d'entrée probable : un email de phishing ouvert par un employé administratif.*

Ce type d'attaque touche les hôpitaux, les mairies, les PME industrielles, les cabinets comptables — tout le monde.

---

## Comment le ransomware arrive

**Les vecteurs d'entrée les plus courants :**

1. **Email de phishing** avec pièce jointe piégée (PDF, Word avec macros, archive ZIP) ou lien vers un site malveillant
2. **Identifiants volés** donnant accès au VPN, au bureau à distance (RDP), ou aux outils cloud
3. **Vulnérabilités non corrigées** dans des logiciels ou systèmes d'exploitation non mis à jour
4. **Clé USB infectée** branchée sur un poste de travail

---

## Ce qui se passe après l'entrée

Un ransomware professionnel ne se déclenche pas immédiatement. Il suit un schéma précis :

**Semaines 1-4 :** L'attaquant explore silencieusement le réseau. Il cartographie les systèmes, identifie les sauvegardes, escalade ses privilèges.

**Semaines 2-6 :** Il exfiltre les données sensibles (double extorsion) — des copies de vos fichiers partent chez lui avant le chiffrement.

**Jour J :** Il chiffre simultanément tous les systèmes accessibles — postes, serveurs, sauvegardes connectées.

**Note de rançon :** Vous découvrez l'attaque en arrivant le matin ou après un week-end.

---

## La double extorsion

Les groupes ransomware modernes ne se contentent plus de chiffrer. Ils **volent les données d'abord**. Si vous refusez de payer, ils menacent de publier les informations confidentielles (contrats, données clients, données RH) ou de les vendre.

Cela signifie que même si vous restaurez depuis une sauvegarde, vous faites face à une fuite de données.

---

## Faut-il payer la rançon ?

**Non, pour plusieurs raisons :**

- Rien ne garantit que vous récupérerez vos données — certains groupes prennent l'argent et disparaissent
- Payer finance les attaquants et les encourage à recommencer
- Vous restez sur leur liste de cibles (payeur connu = cible rentable)
- Dans certains cas, payer des groupes sanctionnés est illégal

---

## Les signaux d'alerte précoces

Signalez immédiatement si vous observez :

- Votre ordinateur devient anormalement lent sans raison apparente
- Des fichiers disparaissent ou deviennent inaccessibles
- Des fichiers renommés avec une extension bizarre (`.encrypted`, `.locked`, `.XXX`)
- Votre antivirus se désactive tout seul
- Une activité réseau inhabituelle la nuit ou le week-end (visible dans les logs IT)

---

## Si vous suspectez un ransomware en cours

1. **Déconnectez immédiatement** du réseau — câble Ethernet et Wi-Fi
2. **N'éteignez pas** l'ordinateur — préservez les traces forensiques
3. **Alertez l'IT** depuis un autre appareil (téléphone, autre poste)
4. **N'essayez pas de restaurer** vous-même — l'IT doit sécuriser l'environnement d'abord

---

## Votre rôle dans la prévention

- Ne cliquez pas sur des pièces jointes ou liens inattendus
- Utilisez un mot de passe fort et unique sur votre VPN et vos accès distants
- Activez la MFA sur tous vos accès
- Signalez tout comportement bizarre de votre machine
- Gardez votre système et applications à jour

---

## À retenir

- **Le ransomware entre souvent par un seul clic** — le vôtre peut être ce clic
- **Il attend des semaines** avant de frapper — c'est pour ça qu'il est dévastateur
- **Ne payez pas** — cela ne garantit rien et finance les attaquants
- **Déconnectez et signalez** dès le moindre doute — chaque minute compte
