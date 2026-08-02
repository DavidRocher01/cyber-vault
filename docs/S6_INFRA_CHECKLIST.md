# S6 — Durcissement auth admin frontend : actions infra utilisateur

Le **volet code** de S6 est livré (voir `admin-auth.service.ts`) : la clé admin
`X-Admin-Key` n'est plus persistée nulle part (mémoire seule, re-saisie par
session), et l'accès `sessionStorage` non gardé du constructeur a disparu
(SSR-safe par construction). Ce document liste les actions **infra**, à réaliser
côté AWS, qui complètent la défense en profondeur.

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

## 1. Rotation d'`ADMIN_API_KEY` — utile seulement si la bascule tarde

Si la bascule du §0 n'est pas menée à court terme, faire tourner la clé en
attendant. Ce n'est qu'une mesure d'attente : elle renouvelle le secret sans
corriger ce qui est reproché — un secret partagé statique, sans identité :

```bash
# Générer une nouvelle clé (32 octets hex, non réutilisée)
NEW_KEY=$(openssl rand -hex 32)

# Mettre à jour le secret dans Secrets Manager (prod eu-west-3)
aws secretsmanager put-secret-value \
  --secret-id cybervault/prod \
  --secret-string "$(aws secretsmanager get-secret-value --secret-id cybervault/prod \
      --query SecretString --output text \
      | jq --arg k "$NEW_KEY" '.ADMIN_API_KEY=$k')" \
  --region eu-west-3

# Forcer un nouveau déploiement ECS pour recharger le secret
aws ecs update-service --cluster cybervault-prod --service cybervault-prod \
  --force-new-deployment --region eu-west-3
```

Après rotation : la nouvelle clé doit être re-saisie dans l'écran de connexion
admin (`/admin/...`). L'ancienne clé cesse immédiatement d'être valide.

## 2. CSP sur la SPA — **déjà acté DIFFÉRÉ** (ne pas relancer spontanément)

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
| Créer le compte admin en prod, activer sa 2FA | Infra | ⏳ à faire (user) |
| Retirer `X-Admin-Key` (code, front, Secrets Manager) | Code + infra | ⏳ après vérification |
| Rotation `ADMIN_API_KEY` | Infra | ↩️ remplacée par la bascule ci-dessus |
| CSP SPA CloudFront | Infra | ⏸️ différé (décision 2026-07-22) |
