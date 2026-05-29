# Les risques du Wi-Fi public

> **Un attaquant peut monter un faux point d'accès Wi-Fi en moins de 5 minutes avec du matériel grand public.** Ce que vous envoyez sur ce réseau lui appartient.

## 🎯 Ce que vous apprendrez

- Comprendre ce qu'un attaquant voit réellement sur un Wi-Fi public
- Appliquer les règles de base pour travailler en déplacement en sécurité
- Savoir quand utiliser un VPN et pourquoi

---

## Scénario réel

*Lors d'une conférence professionnelle, un consultant se connecte au Wi-Fi "Conference_Guest". Il consulte ses emails, accède au CRM client, envoie un devis. Ce qu'il ne sait pas : "Conference_Guest" est un faux réseau créé par un chercheur en sécurité présent dans la salle, pour démontrer la vulnérabilité. En 20 minutes, le chercheur a capturé 3 sessions authentifiées, dont une sur un outil de gestion de projet contenant des données clients.*

Cet exercice de démonstration est réalisé régulièrement dans des événements de sécurité — et les vrais attaquants font pareil, sans prévenir.

---

## Ce qu'un attaquant peut faire sur un Wi-Fi public

**Attaque Man-in-the-Middle (MITM)**
L'attaquant se positionne entre vous et Internet. Il voit, peut modifier, et peut enregistrer tout votre trafic non chiffré.

**Evil Twin (faux point d'accès)**
Il crée un réseau avec un nom identique ou très proche du réseau légitime. Votre téléphone ou ordinateur se connecte automatiquement s'il reconnaît le nom. Vous n'êtes jamais sur le bon réseau.

**Session hijacking**
Même sur HTTPS, certains cookies de session peuvent être volés si la connexion n'est pas parfaitement configurée — permettant à l'attaquant de prendre le contrôle de vos comptes sans connaître votre mot de passe.

---

## Ce que vous risquez concrètement

- Accès à vos emails professionnels et documents partagés
- Vol de session sur vos outils métier (CRM, ERP, intranet)
- Interception de documents envoyés ou reçus
- Installation de malware via injection dans des téléchargements

---

## Les règles à respecter

**VPN obligatoire sur tout réseau public**
Le VPN chiffre tout votre trafic dans un tunnel sécurisé. Même si quelqu'un intercepte vos données, il ne voit qu'un flux chiffré inutilisable. Si votre entreprise fournit un VPN, utilisez-le systématiquement en déplacement.

**Vérifiez le HTTPS**
Le cadenas dans la barre d'adresse signifie que la connexion entre votre navigateur et le site est chiffrée. En 2024, la quasi-totalité des sites professionnels utilisent HTTPS — mais cela ne protège pas contre un faux point d'accès.

**Désactivez la connexion automatique**
Sur votre téléphone et ordinateur, désactivez la reconnexion automatique aux réseaux connus. Un attaquant peut créer un réseau avec le même nom que votre café habituel.

**Données mobiles plutôt que Wi-Fi public**
En l'absence de VPN, votre connexion 4G/5G est nettement plus sûre qu'un Wi-Fi public. Pour les tâches sensibles, préférez votre partage de connexion mobile.

---

## Ce qu'il ne faut jamais faire sur un Wi-Fi public sans VPN

- ❌ Accéder à votre messagerie professionnelle
- ❌ Vous connecter au VPN ou aux outils internes
- ❌ Effectuer des opérations bancaires ou financières
- ❌ Transmettre des données clients ou confidentielles
- ❌ Laisser votre téléphone se connecter automatiquement

---

## Configuration rapide à faire maintenant

1. Installez et activez le VPN fourni par votre entreprise
2. Désactivez la reconnexion automatique aux Wi-Fi publics sur vos appareils
3. Activez le mode "Réseau public" ou "Réseau non approuvé" lors de connexions hors bureau

---

## À retenir

- **Wi-Fi public = réseau ennemi** — traitez-le comme tel
- **VPN obligatoire** dès que vous quittez votre réseau d'entreprise
- Sans VPN, utilisez votre 4G/5G pour les tâches sensibles
- Désactivez la connexion automatique aux réseaux connus
