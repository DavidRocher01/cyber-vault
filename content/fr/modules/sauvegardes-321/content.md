# La règle 3-2-1 des sauvegardes

> **60 % des PME qui perdent leurs données suite à un sinistre majeur ferment dans les 6 mois.** (National Cyber Security Alliance) La règle 3-2-1 est la différence entre survivre et disparaître.

## 🎯 Ce que vous apprendrez

- Comprendre pourquoi une seule sauvegarde ne suffit pas
- Appliquer la règle 3-2-1 à votre situation personnelle et professionnelle
- Connaître les pièges spécifiques aux ransomwares

---

## Scénario réel

*En 2021, une PME de 40 personnes dans le secteur du conseil subit une attaque ransomware. Tous leurs fichiers sont chiffrés — devis, contrats, bases clients, données comptables. Leur "sauvegarde" ? Un disque externe branché en permanence au serveur principal. Le ransomware l'a chiffré en même temps. Résultat : 3 semaines d'interruption, 120 000 € de coûts de récupération et reconstruction, et la perte définitive de 6 mois de données.*

Une sauvegarde déconnectée ou une copie cloud aurait sauvé l'entreprise.

---

## La règle 3-2-1 expliquée

**3** copies de vos données

**2** supports de stockage différents (technologies distinctes)

**1** copie hors site ou hors ligne (physiquement séparée du reste)

### Exemple concret

- **Copie 1** — fichiers sur votre poste ou serveur (l'original)
- **Copie 2** — sauvegarde sur un NAS ou disque externe au bureau
- **Copie 3** — sauvegarde cloud (OneDrive, SharePoint, S3, Backblaze...)

La copie hors site garantit que même un incendie, une inondation, ou un ransomware qui chiffre tout le réseau local ne peut pas détruire toutes vos données.

---

## Pourquoi 3 copies et pas 2

Les pannes arrivent rarement seules. Un disque externe stocké dans le même bureau que le serveur disparaît en cas d'incendie ou de vol. Un ransomware qui se propage sur le réseau local chiffre simultanément le serveur ET le disque externe connecté.

La troisième copie, hors ligne ou hors site, reste intacte dans ces scénarios.

---

## Le piège spécifique des ransomwares

Les ransomwares modernes sont patients. Ils peuvent rester dormants **2 à 8 semaines** avant de se déclencher — le temps que leurs copies chiffrées remplacent vos bonnes sauvegardes automatiques.

Le jour où ils frappent, vos sauvegardes automatiques des dernières semaines contiennent déjà des fichiers chiffrés.

**La solution** : conserver des **versions historiques** datant d'au moins 30 jours, pas seulement la dernière version. La plupart des solutions cloud (SharePoint, OneDrive, Google Drive) le font automatiquement — vérifiez que c'est activé.

---

## Une sauvegarde non testée n'est pas une sauvegarde

**Testez la restauration** au moins une fois par an :

- Restaurez un fichier spécifique depuis la sauvegarde
- Chronométrez combien de temps prend une restauration complète
- Vérifiez que tous les fichiers importants sont bien inclus

Des entreprises ont découvert le jour d'une attaque que leur sauvegarde était vide depuis des mois à cause d'une configuration silencieusement cassée.

---

## Ce que vous devez faire personnellement

1. **Vérifiez** que vos documents importants sont synchronisés sur le cloud d'entreprise (SharePoint, OneDrive, Google Drive)
2. **Ne stockez pas** de données critiques uniquement sur votre disque local sans sauvegarde externe
3. **Vérifiez l'historique des versions** de vos documents cloud — il doit être activé
4. **Signalez** à votre IT si vous n'avez pas accès à un système de sauvegarde

---

## À retenir

- **3 copies, 2 supports, 1 hors site** — c'est la règle minimale
- Un disque externe branché en permanence n'est pas une sauvegarde sécurisée
- **Conservez plusieurs versions** dans le temps — pas seulement la dernière
- Une sauvegarde non testée peut être une fausse sécurité
