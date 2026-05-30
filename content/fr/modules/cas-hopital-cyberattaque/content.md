# Étude de cas : cyberattaque contre un hôpital

> **Les hôpitaux sont la cible la plus fréquente des ransomwares en France. En 2022, un hôpital était attaqué toutes les semaines.** (ANSSI, Panorama de la menace informatique 2022)

## 🎯 Ce que vous apprendrez
- Comment une cyberattaque se déroule concrètement dans une organisation
- Les erreurs humaines qui ont permis l'intrusion
- Les conséquences réelles pour les patients et le personnel
- Ce que vous pouvez faire pour éviter le même scénario

---

## Le contexte

Les attaques contre les hôpitaux français se sont multipliées depuis 2019. Les cas du Centre Hospitalier de Dax (2021), du CH de Villefranche-sur-Saône (2021), du GHT Cœur Grand Est (2022) et du CH de Versailles (2022) ont chacun fait l'objet de rapports publics de l'ANSSI. Cette étude de cas est une synthèse composite de plusieurs incidents réels, volontairement rendue anonyme.

---

## Chronologie de l'attaque

### J-45 : L'entrée discrète

*Tout commence par un email.*

Un agent administratif reçoit un email semblant provenir de la Caisse Primaire d'Assurance Maladie, avec un objet : "Mise à jour procédure télétransmission — action requise avant le 15". L'email contient un lien vers un formulaire à remplir.

L'agent clique. La page ressemble parfaitement au site CPAM. Il saisit ses identifiants de messagerie professionnelle pour "se connecter". Il ne se passe rien d'apparent. L'agent pense à un bug et passe à autre chose.

Ce qu'il ne sait pas : ses identifiants viennent d'être envoyés à un serveur en Roumanie.

### J-30 : La reconnaissance silencieuse

Avec les identifiants volés, les attaquants se connectent discrètement à la messagerie de l'agent. Ils ne font rien de visible. Ils lisent les emails, cartographient l'organisation, identifient les personnes ayant des accès privilégiés (DSI, directeur financier, responsable RH).

Ils envoient des emails depuis le compte compromis à quelques collègues — des emails qui semblent normaux, avec des pièces jointes. Ces pièces jointes contiennent un malware qui s'installe silencieusement.

### J-15 : L'escalade des privilèges

Le malware se propage latéralement sur le réseau interne. Les attaquants obtiennent progressivement des accès administrateurs. Ils identifient les serveurs de sauvegarde et les systèmes critiques (dossiers patients, PACS imagerie, logiciel de pharmacie).

Ils attendent le moment idéal.

### J-0 : Vendredi 23h30 — Le déclenchement

Les attaquants déclenchent le ransomware un vendredi soir, tard, quand les équipes IT sont squelettiques.

En moins de 4 heures :
- Les serveurs de fichiers sont chiffrés
- Les sauvegardes connectées au réseau sont chiffrées
- Les postes de travail dans les services commencent à afficher le message de rançon

**Samedi 2h du matin :** Un infirmier de nuit essaie d'accéder au dossier d'un patient aux urgences. L'écran affiche un message en anglais : *"Your files have been encrypted. Pay 1.2 million USD in Bitcoin to recover them."*

---

## Les conséquences réelles

### Sur les soins
- **Retour au papier** : toute la documentation passe en mode manuel. Les ordonnances, les transmissions entre équipes, les résultats de biologie — tout s'écrit à la main.
- **Annulations** : des opérations programmées sont reportées (accès aux dossiers impossible, équipements non fonctionnels).
- **Redirection des urgences** : certains patients des urgences sont redirigés vers d'autres établissements.
- **Imagerie inaccessible** : le PACS (système d'imagerie médicale) est hors ligne. Les médecins ne peuvent pas accéder aux radios et scanners.

### Sur le personnel
- **Surcharge massive** : les soignants travaillent avec des procédures dégradées pendant 4 semaines.
- **Stress** : les médecins prennent des décisions sans avoir accès à l'historique complet des patients.
- **Heures supplémentaires** : les équipes IT travaillent 16h/jour pendant 3 semaines pour reconstruire l'infrastructure.

### Sur l'organisation
- **Coût total estimé** : entre 10 et 15 millions d'euros (reconstruction IT, personnel supplémentaire, pertes d'activité).
- **Durée de reprise** : 5 semaines pour retrouver un fonctionnement quasi-normal.
- **Données perdues** : malgré les sauvegardes, certaines données récentes (les 48h précédant l'attaque) ont été perdues.

### La rançon
L'hôpital ne paie pas. La doctrine française (ANSSI, gouvernement) est de ne pas payer — car payer finance les attaquants et n'est pas une garantie de récupération.

---

## Analyse : les erreurs qui ont tout déclenché

### Erreur 1 : Le clic sur le lien de phishing
L'agent administratif n'avait pas reçu de formation récente sur le phishing. L'email était convaincant — logo CPAM, tournure officielle, urgence artificielle.

**Ce qu'on peut faire différemment :** Avant de cliquer sur un lien dans un email, survolez-le pour voir l'URL réelle. Un email de la CPAM ne vous redirigera jamais vers un domaine en `.xyz` ou `.top`.

### Erreur 2 : La saisie d'identifiants sur un site non vérifié
L'agent a saisi ses identifiants professionnels sur une page externe sans vérifier l'URL.

**Ce qu'on peut faire différemment :** Vos identifiants professionnels ne doivent être saisis que sur des sites ou applications reconnus et validés par votre IT. En cas de doute, appelez le service demandeur directement.

### Erreur 3 : Les sauvegardes connectées au réseau
Les sauvegardes étaient accessibles depuis le réseau infecté. Le ransomware les a chiffrées en même temps que les données.

**Ce qu'on peut faire différemment :** Votre IT doit s'assurer que les sauvegardes suivent la règle 3-2-1, avec au moins une copie hors-ligne ou hors-réseau.

### Erreur 4 : L'absence de MFA
Si un second facteur d'authentification avait été en place sur la messagerie, le vol des identifiants aurait été insuffisant pour se connecter.

**Ce qu'on peut faire différemment :** Activez la MFA sur tous les services qui le permettent, et demandez à votre IT de l'imposer sur les accès professionnels.

---

## Ce que ce cas vous enseigne

| Maillon | Ce qui a failli | Ce qui protège |
|---------|----------------|----------------|
| Email | Clic sur lien phishing | Formation, vérification des URLs |
| Identifiants | Saisis sur faux site | MFA, vigilance avant saisie |
| Réseau | Propagation latérale | Segmentation réseau (rôle IT) |
| Sauvegardes | Chiffrées en même temps | Règle 3-2-1, sauvegarde hors-ligne |
| Détection | Aucune alarme pendant 45 jours | SIEM, EDR (rôle IT) |

---

## Résumé

Cette attaque aurait pu être évitée à plusieurs moments. Le point de départ — un email de phishing convaincant — est le vecteur le plus courant. La formation, la vigilance et la MFA sont les boucliers les plus efficaces à votre niveau.

**Votre rôle n'est pas de tout savoir sur la cybersécurité. Votre rôle est de ne pas être le point d'entrée.**
