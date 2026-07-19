# CSP de la SPA (CloudFront) — S6 audit sécurité

## Contexte
Le backend FastAPI pose déjà une CSP stricte (`SecurityHeadersMiddleware`, `app/main.py`) sur
les réponses **API**. Mais l'application (index.html + bundles Angular) est servie par
**CloudFront/S3**, qui ne passe pas par ce middleware → la SPA n'a **pas** de CSP
(finding audit G, sévérité low, défense en profondeur).

Les headers CloudFront sont gérés par une **Response Headers Policy** AWS (hors repo).
Cette CSP doit y être ajoutée. On la déploie en **deux temps** pour ne rien casser
(le piège classique = un `script-src`/`style-src` trop strict qui casse Angular).

## Valeur CSP (miroir de la CSP backend, adaptée SPA)
```
default-src 'self';
script-src 'self';
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
font-src 'self' https://fonts.gstatic.com;
img-src 'self' data: https://rochercybersecurite.com https://*.rochercybersecurite.com https://www.gravatar.com;
connect-src 'self';
frame-ancestors 'none';
base-uri 'self';
form-action 'self'
```
Notes :
- `script-src 'self'` sans `unsafe-inline` : les bundles Angular sont externes → OK. Si un
  `onload`/handler inline traîne dans l'index.html, la phase Report-Only le révélera.
- `connect-src 'self'` : l'API est same-origin (`/api/*` via le comportement CloudFront → ALB).
- `style-src 'unsafe-inline'` : requis par les styles inline d'Angular (déjà toléré côté backend).

## Étape 1 — Report-Only (aucun blocage, on observe)
Ajouter dans la Response Headers Policy CloudFront un **Custom Header** :
- Header : `Content-Security-Policy-Report-Only`
- Value : la chaîne ci-dessus (sur une ligne)

CLI (adapter `<POLICY_ID>` / `<ETAG>` ; récupérables via `aws cloudfront list-response-headers-policies`) :
```bash
aws cloudfront get-response-headers-policy-config --id <POLICY_ID>   # note l'ETag + le JSON actuel
# éditer le JSON : ajouter l'entrée CustomHeaders 'Content-Security-Policy-Report-Only'
aws cloudfront update-response-headers-policy \
  --id <POLICY_ID> --if-match <ETAG> \
  --response-headers-policy-config file://policy-with-csp-reportonly.json
```
Observer la console navigateur (ou un endpoint report-uri si configuré) pendant quelques jours
sur les parcours réels (auth, vault, awareness, phishing, scan).

## Étape 2 — Enforce (après observation, zéro violation)
Remplacer `Content-Security-Policy-Report-Only` par `Content-Security-Policy` (même valeur).

## Rappel
- Changement **réversible** (retirer le header). Report-Only ne bloque JAMAIS.
- Ne PAS enforce directement : valider en Report-Only d'abord (leçon `project_vitrine_security`).
