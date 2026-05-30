# Chiffrement : quoi, quand et comment protéger vos données

> **Seuls 45 % des employés savent que les fichiers envoyés par email ne sont pas chiffrés par défaut.** (Ponemon Institute 2023)

## 🎯 Ce que vous apprendrez
- Ce qu'est le chiffrement et pourquoi c'est indispensable
- Quelles données vous devez chiffrer et lesquelles sont déjà protégées
- Les outils simples à votre disposition au quotidien

---

## Scénario réel

*Karim, commercial itinérant, perd son ordinateur portable dans un train. Il contient des propositions commerciales, des fichiers RH et les coordonnées bancaires de plusieurs clients. Son ordinateur n'est pas chiffré. Quelques jours plus tard, ces données apparaissent à la vente sur le dark web. L'entreprise fait face à une amende CNIL et perd plusieurs contrats.*

Si le disque dur avait été chiffré, la perte de l'ordinateur aurait été anodine. Sans la clé de déchiffrement, les données sont illisibles — même pour un voleur professionnel.

---

## C'est quoi le chiffrement ?

Le chiffrement transforme vos données en données illisibles pour quiconque ne possède pas la clé. C'est l'équivalent numérique d'un coffre-fort.

**Sans chiffrement :** vos fichiers ressemblent à un livre ouvert. N'importe qui avec accès au disque peut les lire.

**Avec chiffrement :** vos fichiers ressemblent à du bruit aléatoire. Sans la clé, impossible de les reconstituer.

Il existe deux grandes catégories :
- **Chiffrement au repos** : protège les données stockées (disque dur, clé USB, serveur)
- **Chiffrement en transit** : protège les données pendant leur transmission (email, transfert de fichiers)

---

## Ce qui est déjà chiffré (sans que vous le sachiez)

Bonne nouvelle : beaucoup de chiffrement se fait déjà automatiquement autour de vous.

✅ **HTTPS** : quand vous voyez le cadenas dans votre navigateur, la connexion au site est chiffrée
✅ **WhatsApp, Signal** : chiffrement de bout en bout activé par défaut
✅ **Votre téléphone** : les smartphones modernes (iOS et Android récents) chiffrent leur stockage par défaut
✅ **Vos sessions VPN d'entreprise** : le tunnel VPN chiffre tout le trafic

---

## Ce qui n'est PAS chiffré par défaut

❌ **Les emails** : un email standard (sans S/MIME ou PGP) circule comme une carte postale — lisible par votre fournisseur, le fournisseur du destinataire, et potentiellement par des tiers
❌ **Les clés USB** : sauf configuration spécifique, elles ne sont pas chiffrées
❌ **Les disques durs d'ordinateurs portables** : selon les configurations, ils peuvent ne pas l'être
❌ **Les fichiers partagés via liens** : un lien de partage sans mot de passe est accessible à quiconque le possède
❌ **Les sauvegardes** : si votre sauvegarde n'est pas chiffrée, elle est aussi vulnérable que l'original

---

## Quelles données chiffrer en priorité ?

Appliquez une règle simple : **chiffrez ce dont la divulgation causerait un préjudice**.

| Type de donnée | Niveau de risque | Chiffrement recommandé |
|----------------|-----------------|------------------------|
| Données RH (salaires, contrats) | 🔴 Critique | Oui, toujours |
| Données clients (coordonnées, contrats) | 🔴 Critique | Oui, toujours |
| Données financières | 🔴 Critique | Oui, toujours |
| Documents internes confidentiels | 🟠 Élevé | Oui, recommandé |
| Présentations commerciales | 🟡 Modéré | Selon contexte |
| Documents publics | 🟢 Faible | Non nécessaire |

---

## Les outils à votre disposition

### Sur votre ordinateur — BitLocker (Windows) / FileVault (Mac)
Ces outils intégrés chiffrent l'intégralité de votre disque dur. Renseignez-vous auprès de votre IT pour savoir s'il est activé sur votre machine.

**Vérification rapide sous Windows :**
1. Touche Windows → tapez "BitLocker"
2. Si actif, vous verrez "Chiffrement de lecteur BitLocker — Activé"

### Pour les clés USB — VeraCrypt
VeraCrypt est un outil gratuit et open source qui permet de créer des volumes chiffrés sur une clé USB. Demandez à votre IT de vous l'installer si vous transportez des données sensibles.

### Pour les emails — Utilisez votre messagerie d'entreprise
Les grandes messageries d'entreprise (Microsoft 365, Google Workspace) proposent des options de chiffrement des emails. Demandez à votre IT comment activer cette option pour les échanges sensibles.

**Alternative simple :** envoyez le document chiffré avec un mot de passe, et transmettez le mot de passe par un autre canal (SMS, appel téléphonique).

### Pour les partages de fichiers — Protégez vos liens
Sur SharePoint, OneDrive, Google Drive :
- Ajoutez un **mot de passe** sur les liens de partage
- Définissez une **date d'expiration** sur les liens temporaires
- Ne partagez jamais avec "Tout le monde" si le document est sensible

---

## Ce que vous devez retenir

Le chiffrement n'est pas une technologie complexe réservée aux experts. C'est une pratique que vous pouvez et devez adopter pour les données sensibles que vous manipulez.

**Vos 3 actions prioritaires :**
1. Vérifiez avec votre IT que votre disque dur est chiffré (BitLocker / FileVault)
2. N'envoyez jamais de données sensibles par email non sécurisé — utilisez les plateformes de partage de votre organisation
3. Protégez toujours vos clés USB contenant des données professionnelles

---

## Résumé

| Ce qui est chiffré par défaut | Ce qui ne l'est pas |
|------------------------------|---------------------|
| HTTPS (navigateur) | Emails standard |
| Applications de messagerie modernes | Clés USB |
| Smartphones récents | Disques durs (selon config) |
| VPN entreprise | Sauvegardes (selon config) |

Le chiffrement est votre assurance contre la perte ou le vol. Activez-le sur vos équipements, utilisez les outils mis à disposition par votre organisation, et n'hésitez pas à demander de l'aide à votre équipe IT.
