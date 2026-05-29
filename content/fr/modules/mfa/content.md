# Pourquoi et comment activer la MFA partout

Même avec un mot de passe parfait, un seul point de défaillance reste trop fragile. La **MFA (Multi-Factor Authentication)** ajoute une deuxième couche — et elle change tout.

---

## Qu'est-ce que la MFA ?

La MFA exige **deux preuves d'identité** pour se connecter :

1. **Ce que vous savez** — votre mot de passe
2. **Ce que vous avez** — votre téléphone (SMS, application) ou une clé physique

Même si un attaquant vole votre mot de passe, il ne peut pas se connecter sans le deuxième facteur qu'il n'a pas.

---

## L'impact réel

Microsoft a analysé ses données : **la MFA bloque 99,9% des attaques automatisées** sur les comptes. C'est la mesure de sécurité individuelle la plus efficace qui existe.

---

## Les différents types de MFA

| Type | Exemple | Sécurité |
|------|---------|----------|
| **SMS** | Code envoyé par texto | Bonne (mais SIM swap possible) |
| **Application TOTP** | Google Authenticator, Authy | Très bonne |
| **Notification push** | Microsoft Authenticator | Très bonne |
| **Clé physique** | YubiKey | Excellente |

**Recommandation :** Préférez une application TOTP ou une notification push au SMS.

---

## Où activer la MFA en priorité

1. **Email professionnel** — c'est la clé de voûte : qui contrôle votre email contrôle tous vos comptes
2. **Outils collaboratifs** — Microsoft 365, Google Workspace, Slack
3. **VPN et accès distant**
4. **Banque et outils financiers**
5. **Gestionnaire de mots de passe**

---

## Comment activer la MFA (en 3 étapes)

1. Allez dans les **paramètres de sécurité** du compte concerné
2. Cherchez **"Authentification à deux facteurs"**, **"2FA"** ou **"Vérification en deux étapes"**
3. Suivez le guide — vous devrez scanner un QR code avec une application comme **Authy** ou **Google Authenticator**

---

## Les codes de récupération

Lors de l'activation, vous recevrez des **codes de récupération** (backup codes). Notez-les et conservez-les en lieu sûr hors ligne — ils sont votre filet de secours si vous perdez votre téléphone.

---

## La fatigue MFA — un piège à connaître

Certains attaquants envoient des dizaines de demandes MFA push dans l'espoir que vous cliquiez "Approuver" par erreur ou fatigue. **Règle absolue : n'approuvez jamais une demande MFA que vous n'avez pas initiée vous-même.**
