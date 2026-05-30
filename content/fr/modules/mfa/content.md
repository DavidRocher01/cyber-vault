# Pourquoi et comment activer la MFA partout

> **La MFA bloque 99,9 % des attaques automatisées sur les comptes.** (Microsoft, analyse sur 300 millions d'utilisateurs) C'est la mesure de sécurité individuelle la plus efficace qui existe — et elle prend 2 minutes à activer.

## 🎯 Ce que vous apprendrez

- Comprendre pourquoi un mot de passe seul ne suffit plus
- Différencier les types de MFA et choisir le meilleur
- Reconnaître et résister à l'attaque "MFA fatigue"

---

## Scénario réel

*En 2022, un employé de Uber reçoit des dizaines de notifications push demandant l'approbation d'une connexion. Il finit par approuver pour que ça s'arrête — ou parce qu'il pense à une erreur système. L'attaquant entre dans le réseau interne d'Uber avec ses identifiants et son approbation MFA. Résultat : accès aux systèmes internes, données clients, code source. Uber confirme la compromission le lendemain.*

Ce type d'attaque s'appelle la **MFA fatigue** — elle contourne la meilleure des protections par épuisement psychologique.

---

## Qu'est-ce que la MFA ?

La MFA (Multi-Factor Authentication) exige **deux preuves d'identité distinctes** :

1. **Ce que vous savez** — votre mot de passe
2. **Ce que vous avez** — votre téléphone, une clé physique

Même si un attaquant vole votre mot de passe, il ne peut pas se connecter sans le deuxième facteur qu'il n'a pas.

---

## Les types de MFA du moins au plus sécurisé

| Type | Exemples | Niveau |
|------|----------|--------|
| SMS | Code par texto | ⚠️ Bien (mais SIM swap possible) |
| Application TOTP | Authy, Google Authenticator | ✅ Très bien |
| Notification push | Microsoft Authenticator | ✅ Très bien |
| Clé physique | YubiKey, clé FIDO2 | ✅✅ Excellent |

**Recommandation** : préférez une application TOTP ou une notification push au SMS. Le SMS peut être intercepté via une attaque SIM swap (l'opérateur transfère votre numéro à l'attaquant).

---

## Où activer la MFA en priorité

1. **Email professionnel** — qui contrôle votre email contrôle tout le reste (réinitialisations de mot de passe)
2. **Outils collaboratifs** — Microsoft 365, Google Workspace, Slack, Teams
3. **VPN et accès distant**
4. **Gestionnaire de mots de passe**
5. **Banque et outils financiers**

---

## Activer la MFA en 3 étapes

1. Allez dans les **paramètres de sécurité** du compte
2. Cherchez **"Authentification à deux facteurs"**, **"2FA"** ou **"Vérification en deux étapes"**
3. Scannez le QR code avec **Authy** ou **Google Authenticator** — c'est fait

**Conservez vos codes de récupération** (backup codes) en lieu sûr hors ligne. C'est votre filet de secours si vous perdez votre téléphone.

---

## L'attaque MFA fatigue — comment la reconnaître

Les attaquants envoient des dizaines de notifications push en espérant que vous approuvez par erreur, par fatigue, ou pour que ça s'arrête.

**Signes d'une attaque en cours :**

- Vous recevez une notification MFA alors que vous n'essayez pas de vous connecter
- Vous en recevez plusieurs d'affilée
- Quelqu'un vous appelle en se faisant passer pour l'IT pour "vérifier votre identité"

**Règle absolue : n'approuvez jamais une demande MFA que vous n'avez pas initiée.**

Si cela arrive : refusez, changez votre mot de passe immédiatement, et signalez à votre IT.

---

## MFA vs. Authentification passwordless

Les systèmes modernes évoluent vers le **passwordless** : clés FIDO2, passkeys, biométrie + clé physique. Plus de mot de passe du tout. Si votre entreprise propose cette option, adoptez-la.

---

## À retenir

- **La MFA bloque 99,9 % des attaques automatisées** — activez-la partout
- **Préférez une application** (Authy, Google Authenticator) au SMS
- **N'approuvez jamais** une notification push que vous n'avez pas déclenchée
- Si vous recevez une avalanche de demandes MFA — c'est une attaque, signalez immédiatement
