# S6 — Durcissement auth admin frontend : actions infra utilisateur

Le **volet code** de S6 est livré (voir `admin-auth.service.ts`) : la clé admin
`X-Admin-Key` n'est plus persistée nulle part (mémoire seule, re-saisie par
session), et l'accès `sessionStorage` non gardé du constructeur a disparu
(SSR-safe par construction). Ce document liste les actions **infra**, à réaliser
côté AWS, qui complètent la défense en profondeur.

## 1. Rotation d'`ADMIN_API_KEY` (recommandé — action simple)

La clé admin est un **secret partagé statique, long-lived**. Le fix code réduit
sa surface d'exposition côté navigateur, mais la clé elle-même devrait tourner :

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
| Rotation `ADMIN_API_KEY` | Infra | ⏳ à faire (user) |
| CSP SPA CloudFront | Infra | ⏸️ différé (décision 2026-07-22) |
