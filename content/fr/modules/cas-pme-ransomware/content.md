# Étude de cas : PME victime de ransomware

> **51 % des PME françaises ont subi au moins une cyberattaque en 2023. 60 % de celles touchées par un ransomware déposent le bilan dans les 6 mois.** (Cybermalveillance.gouv.fr & CESIN 2023)

## 🎯 Ce que vous apprendrez
- Comment un ransomware se déploie dans une PME réelle
- Les erreurs humaines et techniques qui l'ont rendu possible
- Le coût réel pour les employés et l'entreprise
- Les mesures concrètes qui auraient tout changé

---

## L'entreprise

**Mécatech Solutions** (nom fictif) : PME de 45 employés spécialisée dans la fabrication de pièces mécaniques pour l'automobile. Chiffre d'affaires : 8 millions d'euros. Système informatique géré par un prestataire externe qui intervient à la demande.

---

## La chronologie heure par heure

### Lundi 8h17 : L'incident démarre

Stéphane, responsable commercial, arrive à son bureau. Il ouvre sa messagerie et trouve un email de son "fournisseur habituel" Dupont Matériaux avec un bon de commande en pièce jointe. Il l'ouvre sans réfléchir — il travaille avec ce fournisseur depuis 6 ans.

La pièce jointe est un fichier Excel avec une macro. Excel affiche un avertissement : "Les macros ont été désactivées pour des raisons de sécurité. Activer le contenu ?" Stéphane clique sur "Activer le contenu" pour voir le bon de commande.

Il ne voit jamais le bon de commande. Un message d'erreur apparaît. Il ferme le fichier et rappelle son fournisseur par téléphone.

### 8h17 à 11h00 : La propagation silencieuse

Dans l'ombre, le malware vient de s'installer. Il effectue une reconnaissance du réseau, identifie les partages réseau, les sauvegardes connectées, et commence à contacter ses serveurs de commande pour télécharger la charge finale (le ransomware).

Personne ne voit rien. Les antivirus installés sur les postes ne détectent pas cette phase.

### 11h34 : Le déclenchement

Les premiers fichiers commencent à être chiffrés sur le serveur de fichiers partagés. Les extensions des fichiers changent : `facture-mars.xlsx` devient `facture-mars.xlsx.LOCKED`.

### 11h47 : La découverte

Nadine, assistante comptable, essaie d'ouvrir un fichier de facturation. L'ordinateur rame, puis affiche un message en anglais avec un compte à rebours et une demande de rançon : **85 000 euros en Bitcoin**.

Elle appelle Stéphane. Stéphane appelle le prestataire informatique. Le prestataire est en intervention chez un autre client.

### 12h05 : La panique et les mauvaises décisions

En attendant le prestataire, un employé IT autodidacte tente de "nettoyer" le virus sur son poste. Il exécute un scan avec un outil gratuit téléchargé en urgence. Ce faisant, il perturbe les logs qui auraient permis l'analyse forensique.

Un autre employé, croyant bien faire, **branche une clé USB** avec une copie de sauvegarde personnelle qu'il avait faite la semaine dernière. La clé est immédiatement chiffrée elle aussi.

### 14h30 : L'arrivée du prestataire

Le prestataire arrive et prend la situation en main. Son premier geste : **déconnecter tous les postes du réseau**. Trop tard — 3 serveurs sur 4 sont chiffrés, y compris le serveur de sauvegarde (branché en permanence sur le réseau).

### 14h30 — J+21 : Trois semaines d'agonie

**Jours 1-3 :** Tentative de décryptage sans payer la rançon. Échec — le chiffrement AES-256 utilisé est incassable sans la clé.

**Jours 4-7 :** Reconstruction partielle depuis une sauvegarde sur bande magnétique (la seule hors-ligne, faite il y a 3 semaines). Perte de 3 semaines de données.

**Semaines 2-3 :** Reconstruction manuelle des données perdues depuis les emails et les documents papier. Les employés travaillent sans ERP, sans CRM, sans serveur de fichiers partagés.

**J+21 :** Reprise quasi-normale. La PME a reconstitué environ 70 % des données perdues.

---

## Le bilan financier

| Poste | Montant estimé |
|-------|---------------|
| Prestataire IT (reconstruction) | 28 000 € |
| Perte de production (3 semaines) | 145 000 € |
| Heures supplémentaires employés | 18 000 € |
| Données définitivement perdues | Non quantifiable |
| Clients perdus (2 contrats résiliés) | 340 000 € |
| **Total** | **~530 000 €** |

La PME n'a pas payé la rançon (85 000 €). Elle a perdu bien plus.

Elle n'avait pas d'assurance cyber.

---

## Les erreurs et ce qui aurait changé

### Erreur 1 : Activer les macros sur un document non sollicité
Stéphane n'attendait pas de bon de commande sous cette forme. Il aurait dû appeler son fournisseur avant d'activer les macros.

**Règle :** N'activez jamais les macros sur un document Office que vous n'attendiez pas explicitement. Même d'un expéditeur connu — son compte email peut avoir été compromis.

### Erreur 2 : Ne pas signaler immédiatement l'anomalie
Stéphane a trouvé bizarre que le fichier ne s'ouvre pas. Il a appelé le fournisseur par téléphone. Il n'a pas signalé l'incident à son IT.

**Règle :** Tout comportement anormal d'un fichier ou d'un email doit être signalé à l'IT immédiatement, même si vous pensez que ce n'est "probablement rien".

### Erreur 3 : Tenter de "réparer" soi-même
L'employé autodidacte qui a lancé un scan a détruit des preuves précieuses et potentiellement aggravé la situation.

**Règle :** En cas de suspicion de malware, ne touchez rien. Appelez l'IT. Chaque action non coordonnée peut compliquer la récupération.

### Erreur 4 : Brancher une clé USB en plein incident
La clé USB a été chiffrée immédiatement — et la sauvegarde personnelle perdue.

**Règle :** Pendant un incident, ne branchez rien sans l'accord explicite de l'IT. Aucune clé USB, aucun disque dur externe, aucun appareil.

### Erreur 5 : Sauvegarde connectée en permanence
La sauvegarde était branchée en réseau — elle a été chiffrée comme le reste.

**Règle :** Les sauvegardes doivent suivre la règle 3-2-1, avec au minimum une copie hors-ligne ou hors-réseau.

---

## Ce que cette PME a mis en place après l'incident

- **MFA** sur tous les accès distants et la messagerie
- **Règle de filtrage des macros** : les macros sont désactivées par défaut, seuls les fichiers provenant de sources vérifiées peuvent les activer
- **Formation** de tous les employés sur le phishing (une heure)
- **Sauvegarde 3-2-1** avec une copie hors-ligne testée chaque mois
- **Assurance cyber** souscrite (prime : 4 500€/an)
- **Procédure d'incident** affichée dans chaque bureau : que faire, qui appeler

Coût total de ces mesures : **environ 12 000 €**. Soit 2 % du coût de l'incident.

---

## Résumé

Cette PME a frôlé la faillite à cause d'un clic. Les coûts réels d'un ransomware sont toujours 5 à 10 fois supérieurs au montant de la rançon.

**La bonne nouvelle :** la grande majorité des incidents comme celui-ci sont évitables avec des mesures simples et peu coûteuses. Votre vigilance sur les emails, les macros et les signalements vaut des centaines de milliers d'euros.
