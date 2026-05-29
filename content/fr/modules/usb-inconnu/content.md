# Clés USB inconnues et matériel piégé

> **Dans une étude menée sur des parkings d'entreprises, 45 % des clés USB trouvées et branchées l'ont été par des employés.** (Université de l'Illinois, 2016) Cette technique d'attaque fonctionne — et elle est encore utilisée aujourd'hui.

## 🎯 Ce que vous apprendrez

- Comprendre comment une simple clé USB peut compromettre un réseau entier
- Reconnaître les différentes formes d'attaque matérielle
- Appliquer la règle absolue sans exception

---

## Scénario réel

*En 2010, la centrale nucléaire iranienne de Natanz est sabotée par un malware — Stuxnet — introduit via des clés USB dans un réseau entièrement isolé d'Internet. L'opération a nécessité des mois de préparation, mais le vecteur d'entrée était un employé qui a branché une clé contaminée. En 2023, des entreprises industrielles européennes subissent encore des attaques similaires via des clés USB abandonnées près de leurs usines.*

Si cette technique est utilisée contre des installations nucléaires, elle peut cibler n'importe quelle entreprise.

---

## Comment fonctionne une attaque par USB

**Étape 1** — L'attaquant dépose des clés USB infectées dans des lieux fréquentés par les employés : parking, hall d'entrée, salle de réunion, toilettes, près des distributeurs automatiques.

**Étape 2** — Un employé trouve la clé. Par curiosité, pour identifier le propriétaire, ou simplement pour l'utiliser, il la branche sur son poste professionnel.

**Étape 3** — Le malware s'installe. Parfois automatiquement (exploitation d'une fonctionnalité Windows). Parfois en se déguisant en fichier légitime. L'employé ne voit rien d'inhabituel.

---

## Les différents types d'attaques matérielles

**USB Drop** — clé USB infectée abandonnée "par hasard". La plus courante.

**BadUSB** — un périphérique qui se présente comme un clavier et tape automatiquement des commandes malveillantes dès le branchement. Invisible, instantané, dévastateur.

**USB Killer** — matériel qui envoie une décharge électrique et détruit physiquement le port USB et la carte mère. Utilisé pour du sabotage.

**Câbles et chargeurs piégés** — des câbles USB d'apparence normale contenant un microcontrôleur capable d'exécuter du code. Vendus en ligne, distribués lors de salons.

**Cadeaux empoisonnés** — clés USB offertes lors d'événements professionnels (conférences, salons) préinstallées avec des malwares.

---

## La règle absolue : jamais, sans exception

Aucune clé USB, aucun câble, aucun périphérique d'origine inconnue ou non vérifiée sur un poste professionnel.

Cela inclut :

- Une clé trouvée dans le parking, la salle de réunion, les toilettes
- Une clé reçue par courrier sans demande préalable
- Un câble ou chargeur offert lors d'un salon ou conférence
- Une clé appartenant à un visiteur externe ou à quelqu'un que vous connaissez peu
- Une clé personnelle utilisée sur un autre ordinateur non maîtrisé

---

## Que faire si vous trouvez une clé USB

1. **Ne la branchez pas** — ni au travail, ni chez vous
2. **Remettez-la à votre IT ou à la sécurité de l'accueil** en décrivant où vous l'avez trouvée
3. L'IT peut l'analyser dans un environnement isolé si nécessaire

---

## Et si mes ports USB sont bloqués ?

Certaines organisations bloquent les ports USB par politique de sécurité. Si vous avez un besoin légitime (transférer un fichier, connecter un périphérique approuvé), demandez une exception formelle à votre IT. C'est une procédure normale — ne la contournez pas.

---

## À retenir

- **Curiosité + USB inconnue = risque majeur** — la clé la plus dangereuse est celle qui semble inoffensive
- La règle s'applique même aux câbles et chargeurs "offerts"
- Remettez toute clé trouvée à votre IT, ne la branchez jamais
- Si vos ports USB sont bloqués, c'est une protection — respectez-la
