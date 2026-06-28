# Runbook — Réponse à incident

> Procédure de réponse aux incidents de sécurité / disponibilité pour Cyber-Vault.
> À garder court et actionnable. Mettre à jour après chaque incident (post-mortem).

## Niveaux de sévérité

| Niveau | Définition | Délai de prise en charge |
|--------|-----------|--------------------------|
| **SEV1** | Fuite de données, compromission, prod down | Immédiat (< 15 min) |
| **SEV2** | Fonction critique cassée (auth, paiement, scan) | < 1 h |
| **SEV3** | Dégradation partielle, bug non bloquant | < 1 jour |

## Boucle de réponse (toute sévérité)

1. **Constater & déclarer** — noter heure, périmètre, sévérité.
2. **Contenir** — stopper la propagation (révoquer une clé, couper une route, scale down).
3. **Éradiquer** — corriger la cause.
4. **Restaurer** — redéployer / restaurer la DB, vérifier.
5. **Post-mortem** — sous 72 h : timeline, cause racine, actions correctives (ajouter ici).

## Playbooks par type

### Compromission d'un secret (SECRET_KEY, ADMIN_API_KEY, clé Stripe…)
1. Générer un nouveau secret, le mettre à jour (Secrets Manager / env de la plateforme).
2. Redéployer.
3. ⚠️ **SECRET_KEY** : sert aussi à chiffrer les graines TOTP (2FA). La rotation
   **casse le déchiffrement des secrets TOTP chiffrés** → les utilisateurs 2FA ne
   pourront plus se connecter. Avant rotation : prévoir une clé dédiée
   `TOTP_ENC_KEY` (séparée) ou un re-chiffrement des graines. Cf. `docs/DEPLOY.md`.
4. Invalider les sessions : la rotation de SECRET_KEY invalide déjà les access
   tokens JWT (signés avec). Les refresh tokens sont en DB (révocables).

### Fuite de credentials utilisateurs / accès DB
1. Snapshot DB immédiat (preuve).
2. Forcer un reset de mot de passe (le reset révoque les sessions — cf. P0-2).
3. Évaluer l'obligation de notification RGPD (72 h à la CNIL si données perso).

### DDoS / abus
1. Vérifier le rate-limiting (slowapi) et le WAF CloudFront (si activé).
2. Bloquer les IP/patterns au niveau CDN/ALB.
3. Scale horizontal si légitime.

### Corruption / perte de données DB
1. Ne pas écrire davantage. Snapshot de l'état courant.
2. Restaurer depuis le dernier snapshot sain (cf. `docs/DEPLOY.md` § Rollback DB).
3. Rejouer les écritures manquantes si possible.

### Webhook Stripe compromis / rejeu
1. Vérifier `STRIPE_WEBHOOK_SECRET` (signature). Rotater si besoin (dashboard Stripe).
2. Vérifier l'idempotence du traitement (pas de double-crédit).

## Contacts & ressources
- Sentry (erreurs backend) — à documenter (projet / accès).
- CNIL — notification violation : https://www.cnil.fr/fr/notifier-une-violation-de-donnees-personnelles
- Snapshots / restore : `docs/DEPLOY.md`.

## Journal des incidents
_(Ajouter ici chaque incident : date, sévérité, résumé, lien post-mortem.)_
