# S6 — Durcissement auth admin frontend

> **Soldé le 2026-08-03**, sauf la CSP (§2), volontairement différée.
>
> La bascule est terminée de bout en bout : le rôle `users.is_admin` existe, un
> compte admin nominatif avec 2FA est en production, le code de la clé partagée
> a été retiré du backend comme du frontend, et `ADMIN_API_KEY` a été supprimée
> de Secrets Manager — vérifié le 2026-08-03, la clé n'y figure plus.
>
> La procédure ci-dessous est conservée parce qu'elle documente l'ordre suivi,
> et que cet ordre est ce qui a évité de rendre le back-office inaccessible. La
> section « rotation de la clé » a été retirée : elle décrivait comment faire
> tourner un secret qui n'existe plus.

## 0. Bascule vers un vrai rôle admin — **remplace la rotation**

> Décidé le 2026-08-02. La rotation décrite au §1 ne fait que renouveler un
> secret partagé ; elle ne lui donne ni identité, ni révocation, ni 2FA. La
> réponse de fond est `users.is_admin` (migration `4b6fae2210d3`) : le droit est
> porté par un compte.

`require_admin` accepte **les deux voies** depuis cette migration — un compte
`is_admin`, ou la clé historique. Ce double support est temporaire : couper la
clé avant qu'un compte admin n'existe en base rendrait le back-office de
production inaccessible.

### Séquence, dans cet ordre

1. **Déployer** la migration `4b6fae2210d3` (colonne à `false` pour tous — aucun
   compte n'est promu automatiquement, c'est délibéré).

2. **Créer le compte admin**, en accès direct au conteneur — donc avec des
   droits AWS, jamais depuis le produit :

   ```bash
   TASK_ID=$(aws ecs list-tasks --cluster cybervault-prod \
     --service-name cybervault-prod --query 'taskArns[0]' --output text --region eu-west-3)

   aws ecs execute-command --cluster cybervault-prod --task "$TASK_ID" \
     --container cybervault-backend --interactive --region eu-west-3 \
     --command "python scripts/create_admin.py vous@exemple.fr 'MotDePasseFort123!'"
   ```

3. **Vérifier** que le compte ouvre bien le back-office, et **activer sa 2FA** —
   c'est tout l'intérêt de la manœuvre.

4. **Alors seulement**, retirer la voie de repli : supprimer la branche
   `X-Admin-Key` de `require_admin`, l'écran de saisie de clé côté front, puis
   `ADMIN_API_KEY` de Secrets Manager et de `$secret_names` dans `deploy.yml`.

⚠️ **Ne pas sauter l'étape 3.** Tant qu'elle n'est pas faite, la clé reste le
seul accès garanti.

Les nouvelles surfaces d'administration n'utilisent pas `require_admin` mais
`get_admin_user`, qui **n'accepte que des comptes** : ce qu'on construit
aujourd'hui n'hérite pas du secret qu'on retire.

## 1. CSP sur la SPA — **déjà acté DIFFÉRÉ** (ne pas relancer spontanément)

L'audit recommande une CSP sur la SPA (CloudFront) pour couper le canal
d'exfiltration en cas de XSS. **Cette action fait partie des items volontairement
différés par décision utilisateur du 2026-07-22** (voir mémoire
`project_security_deferred_actions` : « CSP+TT CloudFront (SPA) »), en raison des
pièges connus (inline `onload`, Trusted Types incompatibles avec certains
bindings Angular). Elle n'est PAS relancée ici.

Si un jour reprise : poser la CSP en `Content-Security-Policy-Report-Only`
d'abord (report-uri), monitorer les violations réelles de la SPA compilée, puis
basculer en mode bloquant une fois les sources légitimes recensées.

## Récapitulatif

| Action | Type | Statut |
|--------|------|--------|
| Clé admin non persistée + SSR-safe | Code | ✅ livré (S6) |
| Rôle `users.is_admin` + double voie d'accès | Code | ✅ livré (2026-08-02) |
| Créer le compte admin en prod, activer sa 2FA | Infra | ✅ fait (2026-08-02) |
| Retirer `X-Admin-Key` du code et du front | Code | ✅ fait (2026-08-02 / 08-03) |
| Supprimer `ADMIN_API_KEY` de Secrets Manager | Infra | ✅ fait et vérifié (2026-08-03) |
| CSP SPA CloudFront | Infra | ⏸️ différé (décision 2026-07-22) |
