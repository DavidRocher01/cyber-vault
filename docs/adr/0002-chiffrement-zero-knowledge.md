# ADR 0002 — Chiffrement zero-knowledge côté client

**Statut** : Accepté
**Date** : 2024-01

---

## Contexte

Le module Vault stocke des mots de passe et données sensibles des utilisateurs. La question centrale est : où s'effectue le chiffrement ?

Les utilisateurs doivent pouvoir faire confiance à la plateforme sans avoir à vérifier le code serveur — c'est-à-dire que même un opérateur malveillant ou une fuite de la base de données ne doit pas exposer leurs données.

## Options évaluées

| Approche | Description | Sécurité | Complexité |
|----------|-------------|----------|------------|
| **Chiffrement serveur** | Serveur chiffre/déchiffre, clé stockée côté serveur | Faible (serveur peut lire les données) | Faible |
| **Chiffrement côté client** | Client chiffre avant envoi, serveur ne voit jamais les données en clair | Haute (zero-knowledge) | Moyenne |
| **HSM / KMS serveur** | Clés gérées dans un HSM, serveur orchestre | Haute mais complexe | Très haute |

## Décision

**Chiffrement côté client (zero-knowledge)** avec :

- **PBKDF2** (600 000 itérations, SHA-256) pour dériver la clé AES à partir du mot de passe maître
- **AES-256-GCM** pour chiffrer chaque entrée du vault
- **Web Crypto API** (natif navigateur) — pas de dépendance cryptographique externe
- Le mot de passe maître et la clé AES restent **uniquement en mémoire côté client**

## Conséquences

**Positives :**
- Même en cas de fuite DB, les données chiffrées sont inexploitables sans la clé
- Le serveur ne peut pas lire les données des utilisateurs (confiance renforcée)
- Conformité RGPD simplifiée : le serveur traite des données opaque
- Argument commercial fort : "zero-knowledge by design"

**Négatives :**
- **Récupération impossible** : si l'utilisateur oublie son mot de passe maître, les données sont perdues
- Pas de recherche full-text sur le contenu du vault côté serveur
- Le mot de passe maître doit être géré avec soin par l'utilisateur
- Tests d'intégration E2E plus complexes (crypto dans le navigateur)

**Mitigation :**
- UI claire avertissant l'utilisateur de l'irréversibilité
- Export chiffré régulier conseillé
- Le mot de passe maître est distinct du mot de passe de compte
