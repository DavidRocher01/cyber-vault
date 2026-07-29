# Audit sécurité exhaustif — 2026-07-27 (axes A-K, revue multi-agents)

Revue frais/complet post refonte tarifaire. 8 chercheurs + vérif adverse + synthèse. 21 findings retenus (REFUTED écartés), consolidés en 17.

## Synthèse exécutive

Synthèse RSSI — audit sécurité CyberScan (post-vérification adverse, 2026-07-27). 22 findings bruts consolidés en 17 après déduplication (les deux entrées sur /public-scans/{token}/unlock — axes A+B et J — décrivent la MÊME vulnérabilité et sont fusionnées). Aucune vulnérabilité HIGH exploitable de façon autonome (pas de RCE, pas d'authz-bypass, pas de SSRF interne — les correctifs S-1/S-5 de l'audit 2026-07-19 tiennent, aucune régression). Le risque dominant est concentré sur la SURFACE PUBLIQUE NON AUTHENTIFIÉE nouvellement introduite (refonte tarifaire / scan gratuit anonyme / gate lead) : 6 findings MEDIUM y convergent. Priorités : (1) l'endpoint /public-scans/{token}/unlock permet un mailbombing illimité vers des adresses tierces arbitraires depuis le domaine réputé de l'éditeur (aucun rate-limit, quota per-email inefficace, faux consentement RGPD horodaté) ; (2) le scan public anonyme réalise de la reconnaissance active (énumération ~60 sous-domaines + tentatives AXFR) sur des domaines tiers non consentants, transformant l'infra ECS en proxy OSINT/recon avec exposition juridique ; (3) le rate-limiting est structurellement faible (compteurs slowapi en mémoire non partagés entre tâches ECS + garde X-Forwarded-For défectueux permettant le spoof de la clé de limitation si l'ALB est atteignable en direct) ; (4) injections HTML dans les e-mails transactionnels (formulaire de contact non-auth → boîte admin) ; (5) contournement trivial du quota freemium (5 scans URL/mois) par suppression-puis-rescan (hard delete + comptage sur lignes vivantes). Les findings LOW/INFO relèvent du durcissement, de la conformité RGPD (export Art.20 incomplet, absence de purge/rétention, Sentry sans scrubbing) et de la dette connue déjà différée par décision utilisateur (phishing mandate S-6, Dark Web emails tiers). ROI maximal : le lot S1 (durcissement surface publique, code pur) neutralise à lui seul 3 MEDIUM sans dépendance infra.

## Répartition

HIGH: 0 | MEDIUM: 6 | LOW: 7 | INFO: 4

## Findings (par sévérité puis CVSS)

### 1. [MEDIUM · CVSS 6.1] Mailbombing / relais d'e-mails vers des adresses tierces arbitraires via POST /public-scans/{token}/unlock (aucun rate-limit, quota per-email inefficace, faux consentement RGPD horodaté)
- **Axe** : A+B access-control / J logs-privacy (fusion de 2 findings)
- **Localisation** : backend/app/api/v1/endpoints/public_scans.py:72-111 (route unlock, aucun @limiter.limit) ; backend/app/services/public_scan_service.py:220-255 (unlock_public_scan) ; backend/app/services/email_service/scan.py:77-107 (envoi)
- **Vecteur** : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:N/I:L/A:N
- **Scénario** : Un attaquant crée 1 seul scan public (dans le quota 3/h/IP), attend status='done', puis boucle POST /{token}/unlock {email:victimeN,consent:true} un nombre ILLIMITÉ de fois. Le garde idempotent (public_scan_service.py:242) exige scan.email==email : un email différent le contourne. _unlocked_domains_for_email compte par email destinataire → {} pour toute nouvelle adresse → len(0)<3, jamais QuotaExceededError. Les lignes 249-252 réécrivent scan.email et horodatent email_consent_at=now() (faux consentement RGPD), puis send_public_scan_report(scan.email,...) part inconditionnellement via le SMTP réputé (Resend, rochercybersecurite.com). Résultat : mailbombing/harcèlement de tiers depuis le domaine officiel, dégradation SPF/DKIM (délivrabilité des mails transactionnels réels : reset MDP, factures), coût quota Resend, registre de consentement pollué.
- **Remédiation** : 1) Double opt-in : n'horodater email_consent_at et n'envoyer l'e-mail qu'au clic d'un lien de confirmation à usage unique. À défaut : 2) @limiter.limit('5/hour') sur la route unlock ET throttle persisté PAR adresse destinataire (1 e-mail/adresse/heure) indépendant du token/IP. 3) Figer l'email au premier déblocage effectif d'un token (rejeter tout changement d'email sur un scan déjà débloqué). 4) Ajouter le CAPTCHA/Turnstile prévu (lot 2).

### 2. [MEDIUM · CVSS 5.8] Reconnaissance active anonyme de domaines tiers non consentants via /public-scans (énumération sous-domaines + tentative AXFR, aucune preuve de propriété)
- **Axe** : D offensive-tooling
- **Localisation** : backend/app/api/v1/endpoints/public_scans.py:39-58 → backend/app/services/public_scan_service.py:97 → cyber-scanner/scanner/dns_scanner.py:76 (scan_subdomains) + :43-73 (_try_zone_transfer / AXFR)
- **Vecteur** : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:L/I:N/A:N
- **Scénario** : POST /public-scans est non authentifié (seule barrière 3/h/IP, contournable par rotation d'IP puisque la clé de limitation = IP). create_public_scan lance _run_demo_scan_sync qui appelle inconditionnellement scan_subdomains(hostname) : boucle sur ~60 sous-domaines sensibles (admin/vpn/db/backup/staging/jenkins…) via socket.gethostbyname, puis _try_zone_transfer TENTE dns.query.xfr (AXFR) sur chaque NS. Aucun gate de propriété n'existe (pas de compte). L'infra ECS de l'éditeur devient un proxy de recon/OSINT gratuit et anonyme contre des tiers : attribution de l'IP éditeur, AXFR non mandaté, exposition juridique. Angle NON couvert par S-1 (qui gate le chemin AUTHENTIFIÉ) ni S-5 (SSRF/rebinding).
- **Remédiation** : Retirer scan_subdomains (énumération + AXFR) du subset public anonyme ; ne conserver que les modules passifs (GET page + headers/CORS/CMS/WAF/SSL). Réserver scan_subdomains/AXFR aux comptes ayant prouvé la propriété du domaine (gate DNS TXT, comme le phishing). Throttle global (pas seulement par IP) + journalisation des cibles publiques pour détection d'abus.

### 3. [MEDIUM · CVSS 5.4] Injection HTML dans l'e-mail de notification admin via le formulaire de contact public (non authentifié)
- **Axe** : E+F injection-inputs
- **Localisation** : backend/app/services/email_service/alerts.py:190-227 (html_owner) ; backend/app/api/v1/endpoints/contact.py:30-62 (endpoint public) ; backend/app/schemas/contact.py:19-41 (borne longueur seulement) ; backend/app/services/email_service/base.py:30-47 (rendu HTML)
- **Vecteur** : CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N
- **Scénario** : POST /api/v1/contact anonyme (3/h, aucune auth) avec message contenant <a href=phishing> + <img beacon>. alerts.py:218 injecte {message} brut dans <div white-space:pre-wrap>, et {name}/{email}/{site_url} (l.202,206,214) sont aussi interpolés sans html.escape. base.py:36 attache MIMEText(html,'html') → HTML rendu par le client mail de l'admin (settings.CONTACT_EMAIL). Résultat : e-mail stylé aux couleurs de la plateforme, livré à l'admin, avec liens de spear-phishing + pixel de tracking. Pas d'exécution JS (clients mail neutralisent script) → impact = phishing/tracking de l'admin amplifié par le branding usurpé. Sink DISTINCT du S-7 (reportlab PDF) → finding neuf.
- **Remédiation** : Échapper (html.escape / markupsafe.escape) name, email, site_url, phone, need_label et message avant interpolation dans html_owner ET html_confirm ; idéalement migrer vers Jinja2 autoescape=True. Conserver le plain-text tel quel. Appliquer aux autres builders HTML f-string du package (dont send_monitoring_alert).

### 4. [MEDIUM · CVSS 5.3] Spoofing d'IP client (X-Forwarded-For) via connexion directe à l'ALB — le garde anti-spoof documenté n'est pas implémenté dans _get_real_ip
- **Axe** : H+I secrets-infra
- **Localisation** : backend/app/core/limiter.py:40-45 (garde len(ips) >= n au lieu de > n) + docstring l.31-34 (défense revendiquée mais absente)
- **Vecteur** : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:L/A:L
- **Scénario** : Le docstring l.31-34 revendique un fallback si moins de N+1 IPs dans la chaîne, mais le code teste len(ips) >= n (l.40), pas >= n+1. Avec N=2, un attaquant frappe l'ALB en direct avec X-Forwarded-For: 9.9.9.9 ; l'ALB AWS append l'IP TCP → chaîne [9.9.9.9, attacker_ip], len=2>=n=2 → candidate=ips[-2]=9.9.9.9, _is_public_ip=True → retourné comme clé de rate-limit. L'attaquant CONTRÔLE la clé : bypass du 3/h scan public, du gate lead IP-haché, et framing du lockout login sur une IP victime. Le test test_limiter.py:134 ne couvre que XFF vide (len=1), jamais le spoof len=2. Contingent à l'atteignabilité directe de l'ALB (non prouvable depuis le repo, ALB/CloudFront non géré en IaC ici) → si l'ALB est verrouillé côté AWS, l'impact retombe à LOW.
- **Remédiation** : Corriger limiter.py:40 : remplacer len(ips) >= n par len(ips) > n (exiger la chaîne complète des N proxys de confiance PLUS l'IP client) ; si chaîne trop courte, retomber sur request.client.host (IP TCP non-spoofable), PAS sur reversed(ips). Ajouter un test XFF spoofé len==n. Infra : verrouiller l'ALB derrière CloudFront (header X-Origin-Verify exigé par règle de listener, ou security-group limité au prefix-list com.amazonaws.global.cloudfront.origin-facing).

### 5. [MEDIUM · CVSS 5.3] Rate-limiting slowapi en mémoire, non partagé entre les tâches ECS (limites multipliées par N, non collantes derrière l'ALB)
- **Axe** : K+billing abuse-billing
- **Localisation** : backend/app/core/limiter.py:71 (Limiter(key_func=...) sans storage_uri)
- **Vecteur** : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:L
- **Scénario** : limiter = Limiter(key_func=_rate_limit_key) est instancié SANS storage_uri (l.71) ; slowapi retombe sur memory:// in-process, propre à chaque tâche ECS Fargate. Derrière l'ALB round-robin, les limites déclaratives (public-scans 3/h, contact 3/h, url-scans 10/min, login) sont effectivement multipliées par N tâches et non-collantes : un attaquant réparti sur les tâches obtient N×le quota. L'affaiblissement le plus net porte sur les endpoints publics non-auth (scan public, contact) qui n'ont pas de second rempart. Pour le login, le verrouillage de compte persistant en base (failed_login_attempts) subsiste comme rempart partagé.
- **Remédiation** : Configurer Limiter(key_func=..., storage_uri=settings.REDIS_URL) sur le Redis/ElastiCache déjà prévu (documenté 'reste-à-faire' dans la mémoire projet) pour rendre les compteurs globaux à toutes les tâches. À défaut : réduire les seuils et s'appuyer sur le verrouillage de compte persistant pour l'auth.

### 6. [MEDIUM · CVSS 5] Contournement du quota freemium de scans URL (5/mois) par suppression-puis-rescan
- **Axe** : K+billing abuse-billing
- **Localisation** : backend/app/services/url_scan_service.py:555-562 (count_url_scans_since) + :596-599 (delete_url_scan hard delete) + backend/app/api/v1/endpoints/url_scans.py:52-62 (gate 429)
- **Vecteur** : CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:L/A:L
- **Scénario** : delete_url_scan (l.598) fait un HARD delete (await db.delete(scan)), aucune colonne deleted_at. count_url_scans_since (l.557-562) compte SELECT count(*) sur les lignes VIVANTES uniquement, et le gate 429 (url_scans.py:54-55) lit ce même compteur. Aucun compteur cumulatif sur user/subscription. Le rapport métier est récupérable AVANT suppression via GET /{scan_id} et /{scan_id}/pdf. Boucle triviale : 5 scans → download → DELETE /{id}×5 → count=0 → rejouer indéfiniment. Gate de monétisation neutralisé + abus réseau sortant à coût nul. TOCTOU secondaire (count l.54 puis insert l.64 sans verrou) réel mais borné par 10/min.
- **Remédiation** : Compter la consommation via un compteur monotone indépendant des suppressions : table/colonne d'usage horodatée incrémentée à la création et jamais décrémentée (purge par fenêtre glissante), OU soft-delete (deleted_at) des url_scans en incluant les lignes soft-deleted dans count_url_scans_since. Ajouter SELECT ... FOR UPDATE sur une ligne d'usage pour fermer le TOCTOU concurrent.

### 7. [LOW · CVSS 4.3] Injection de formule CSV dans l'export du dossier Dark Web (colonne Email)
- **Axe** : E+F injection-inputs
- **Localisation** : backend/app/services/darkweb_dossier/ingestion.py:146-169 (export_dossier_csv, t.email écrit brut) ; source backend/app/api/v1/endpoints/darkweb_dossier.py:106-126 (_parse_emails_csv)
- **Vecteur** : CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:N/I:L/A:N
- **Scénario** : La validation d'upload (_parse_emails_csv l.123) n'exige que '@' in val et un domaine avec '.', acceptant =1+1@victime.tld. export_dossier_csv (l.159-168) écrit t.email via csv.writer sans neutraliser les préfixes =,+,-,@ → cellule formule stockée puis ré-exportée verbatim. Risque tiers conditionnel au partage du livrable (portail client/consultant RSSI — plausible en B2B) et à l'exécution de la formule par le tableur du destinataire. Gated tier≥3.
- **Remédiation** : Neutraliser toute cellule commençant par =,+,-,@,TAB,CR en préfixant par une apostrophe (helper _csv_safe appliqué à toutes les valeurs de writerow) et/ou durcir _parse_emails_csv pour rejeter ces caractères en amont.

### 8. [LOW · CVSS 3.7] Clé admin statique (X-Admin-Key) persistée en sessionStorage et rejouée depuis le navigateur, sans rotation ni expiration
- **Axe** : G web-frontend
- **Localisation** : frontend/src/app/features/cyberscan/admin/admin-auth.service.ts:13,21,33
- **Vecteur** : CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:L/A:N
- **Scénario** : login() écrit la clé brute en clair via sessionStorage.setItem (l.33), le constructeur la relit (l.13), headers()/verify() la réémettent telle quelle dans X-Admin-Key (l.21,26). Secret partagé statique, long-lived, sans rotation ni expiration côté client (contrairement au JWT rotaté). Exploitation CONDITIONNELLE à une XSS s'exécutant dans la session de l'admin : aucun vecteur XSS n'est démontré ici (Angular assainit les bindings, trustStaticHtml n'accepte que du HTML littéral). Impact fort SI XSS (contrôle total de plan-override), mais pré-requis non prouvé → PLAUSIBLE.
- **Remédiation** : Remplacer le secret partagé statique par un jeton admin de session court (login admin serveur → JWT/rôle admin expirant) ; à défaut, ne pas persister la clé (signal en mémoire, re-saisie par session) et faire tourner ADMIN_API_KEY (openssl rand -hex 32, non réutilisée). Attacher une CSP sur la SPA pour couper le canal d'exfiltration.

### 9. [LOW · CVSS 3.7] Gate lead du scan gratuit : email non vérifié (plafond 3 domaines contournable) et scan coûteux exécuté avant le gate
- **Axe** : K+billing abuse-billing
- **Localisation** : backend/app/services/public_scan_service.py:32 (MAX_DOMAINS_PER_EMAIL) + :206-255 (unlock/quota) + backend/app/api/v1/endpoints/public_scans.py:39-58
- **Vecteur** : CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:L
- **Scénario** : unlock_public_scan (l.238-254) pose scan.email sans confirmation ; le quota compte par PublicScan.email → varier l'email (a@a.com, b@b.com…) repart de zéro, plafond de 3 domaines trivialement contourné. Le travail coûteux (9 modules réseau sortant) s'exécute AVANT tout gate (background_tasks au POST), le gate email ne protège que la révélation du rapport. Rempart amont = 3/h/IP, lui-même affaibli (findings limiter mémoire + XFF spoof). Atténué : SSRF re-validé à l'exécution (l.156-165), modules non-destructifs, compromis assumé et documenté côté produit.
- **Remédiation** : Si l'enforcement doit tenir : lier le déblocage à un email VÉRIFIÉ (magic-link) avant de servir le rapport, ou corréler sur ip_hash (déjà stocké) pour détecter la rotation d'emails. Plafonner les scans publics par domaine cible et globalement (pas seulement par IP) et/ou exiger le gate avant de lancer le scan de fond.

### 10. [LOW · CVSS 3.7] TRUSTED_PROXY_COUNT non injecté par deploy.yml — drift possible vers count=1 (rate-limit mutualisé par PoP CloudFront)
- **Axe** : H+I secrets-infra
- **Localisation** : .github/workflows/deploy.yml:96-107 ($env_overrides) + backend/app/core/config.py:99 (défaut=1)
- **Vecteur** : CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:N/A:L
- **Scénario** : $env_overrides (deploy.yml:97) ne liste que STRIPE_PUBLISHABLE_KEY et S3_BUCKET_NAME ; TRUSTED_PROXY_COUNT en est absent et le défaut applicatif est 1 (config.py:99). Impact ATTÉNUÉ : deploy.yml:105 préserve les entrées existantes non listées dans $managed, donc la valeur 2 posée manuellement est reportée à chaque déploiement normal — pas de régression active. Le risque ne se matérialise que lors d'une recréation de task def from-scratch sans report manuel → retombée à 1 → via CloudFront ips[-1]=IP edge partagée → clé de rate-limit mutualisée par PoP (DoS faux-positifs). Dépendance à un état manuel non versionné.
- **Remédiation** : Ajouter {"name":"TRUSTED_PROXY_COUNT","value":"2"} dans $env_overrides (deploy.yml:97) pour versionner la valeur. Alternative : faire échouer le démarrage si APP_ENV=production et TRUSTED_PROXY_COUNT laissé au défaut (validation Pydantic dans config.py).

### 11. [LOW · CVSS 3.1] Le gating de plan ignore current_period_end : abonnement expiré dont le webhook est manqué reste 'active'
- **Axe** : K+billing abuse-billing
- **Localisation** : backend/app/services/subscription_service.py:42-50 (get_active_plan) + backend/app/api/v1/endpoints/webhooks.py:54-56 / 133-149
- **Vecteur** : CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:U/C:N/I:L/A:N
- **Scénario** : Gap de robustesse, non déclenchable directement par un attaquant. get_active_plan (l.42-46) filtre uniquement Subscription.status=='active' sans jamais lire current_period_end (pourtant écrit en base). Aucun job de reconciliation (grep reconcil/Subscription.retrieve = néant). Si l'endpoint webhook reste KO au-delà des retries Stripe (72h) sur un paiement échoué, le statut local reste 'active' pour toujours → le tier payé est conservé sans paiement. Nécessite un incident opérationnel prolongé + échec de paiement simultané ; Stripe alerte sur les webhooks en échec.
- **Remédiation** : Filet indépendant des webhooks : dans get_active_plan, exiger aussi current_period_end > now() (avec marge de grâce), et/ou job scheduler quotidien réconciliant via stripe.Subscription.retrieve les abonnements dont current_period_end est dépassé. Alerter sur les webhooks en échec répété.

### 12. [LOW · CVSS 0] Export RGPD (portabilité, Art.20) incomplet — seuls compte/sites/scans sont exportés
- **Axe** : J logs-privacy
- **Localisation** : backend/app/api/v1/endpoints/users.py:112-163 (export_my_data)
- **Vecteur** : N/A (conformité, pas de scénario d'attaque)
- **Scénario** : Aucun (défaut de conformité, non exploitable par un adversaire). export_my_data (l.138-154) ne sérialise que account, sites et scans ; aucune requête vers évaluations NIS2/ISO, training_progress, darkweb_*, subscriptions, invoices/quotes, brand_profiles, notifications. Le Content-Disposition (l.161) prétend livrer 'mes_donnees' complètes → gap Art.20.
- **Remédiation** : Étendre l'export aux tables enfant listées dans la migration d'effacement (NIS2/ISO, training_progress, darkweb_*, subscriptions, invoices/quotes, brand_profiles, notifications) ou documenter honnêtement le périmètre couvert.

### 13. [LOW · CVSS 0] Absence de rétention/purge sur public_scans et darkweb_dossiers (PII conservée indéfiniment)
- **Axe** : J logs-privacy
- **Localisation** : backend/app/models/public_scan.py:33-44 (email+ip_hash+results, aucun TTL) ; services/scheduler/* sans job de purge
- **Vecteur** : N/A (conformité Art.5-1-e, aggravant en cas de fuite)
- **Scénario** : Aucun scénario d'attaque direct. Le modèle public_scan stocke email (l.33, indexé), ip_hash salé (l.37) et results_json (l.26) sans colonne d'expiration. Le scheduler ne contient qu'un job _run_darkweb_monitoring (surveillance/alerte), jamais de purge/anonymisation. Conservation indéfinie de PII (leads + e-mails de tiers exposés) = manquement Art.5-1-e, aggravant en cas de fuite ultérieure.
- **Remédiation** : Ajouter un job scheduler périodique purgeant/anonymisant les public_scans après N jours (ex. 90j) et un TTL/anonymisation des dossiers Dark Web ; documenter les durées.

### 14. [INFO · CVSS 3.1] Lecture non bornée du CSV en mémoire avant contrôle de taille (upload Dark Web)
- **Axe** : E+F injection-inputs
- **Localisation** : backend/app/api/v1/endpoints/darkweb_dossier.py:190 (raw = await emails_csv.read())
- **Vecteur** : CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:L
- **Scénario** : raw = await emails_csv.read() charge tout le fichier en RAM ; seul _MAX_EMAILS=500 est appliqué APRÈS parsing (l.194), aucun cap d'octets, aucun middleware global de taille de corps. DoS mémoire applicatif à coût faible, mais surface limitée aux comptes payants (gated tier≥3). NON régressé — identique au [low][F-input] de l'audit 2026-07 (docs/SECURITY_AUDIT_2026-07.md:101).
- **Remédiation** : Lire de façon bornée (content = await emails_csv.read(MAX+1) puis rejeter si len>MAX) avant parsing, en s'alignant sur storage.MAX_UPLOAD_BYTES des livrables RSSI.

### 15. [INFO · CVSS 2] Injection HTML dans l'e-mail d'alerte de monitoring Dark Web (emails CSV / company_name non échappés)
- **Axe** : E+F injection-inputs
- **Localisation** : backend/app/services/darkweb_dossier/ingestion.py:182,199 (new_list_html + company_name) ; validation faible backend/app/api/v1/endpoints/darkweb_dossier.py:123 ; déclencheur backend/app/services/scheduler/darkweb.py:61-77
- **Vecteur** : CVSS:3.1/AV:N/AC:H/PR:L/UI:R/S:U/C:N/I:L/A:N
- **Scénario** : ingestion.py:182 interpole {e} brut dans un <li> et l.199 {company_name} brut, sans échappement ; _parse_emails_csv laisse passer x<img src=y>@evil.com. Exploitabilité quasi nulle : (1) le destinataire est TOUJOURS user.email (propriétaire du dossier) → self-dirigé, aucun impact cross-tenant ; (2) new_exposed ne contient que des adresses flaggées 'exposed' par HIBP — une adresse fabriquée n'apparaît dans aucune fuite réelle. Le vecteur company_name (Form) est injectable de façon fiable mais toujours self-dirigé. Gated tier≥3.
- **Remédiation** : Échapper e, company_name et domain (html.escape) dans send_monitoring_alert et durcir _parse_emails_csv (regex/EmailStr strict rejetant <,>,espace). Durcissement défense-en-profondeur, priorité faible — à traiter avec le fix HTML du formulaire de contact.

### 16. [INFO · CVSS 0] Sentry initialisé sans hook before_send de scrubbing PII
- **Axe** : J logs-privacy
- **Localisation** : backend/app/main.py:27-33 (sentry_sdk.init)
- **Vecteur** : N/A (durcissement défensif, risque théorique)
- **Scénario** : Aucun scénario actif. sentry_sdk.init ne passe que dsn, traces_sample_rate=0.1, environment ; pas de before_send/before_breadcrumb, send_default_pii non défini (défaut False → limite le risque). Durcissement contre une future régression qui interpolerait une PII dans une exception envoyée à Sentry.
- **Remédiation** : Ajouter un before_send/before_breadcrumb appliquant mask_email + retrait de motifs token/clé, et confirmer explicitement send_default_pii=False.

### 17. [INFO · CVSS 0] Dette connue déjà différée par décision utilisateur — phishing sans preuve de mandat (S-6), Dark Web emails tiers, TOTP replay standard, isPlatformBrowser admin-auth
- **Axe** : D offensive-tooling / C crypto-vault / G web-frontend (regroupement)
- **Localisation** : backend/app/api/v1/endpoints/phishing.py:509-524 (S-6, différé) ; backend/app/services/darkweb_dossier/ingestion.py:58 ([D-offensif] audit 2026-07) ; backend/app/api/v1/endpoints/auth.py:150 (TOTP valid_window=1, sans anti-rejeu) ; frontend/.../admin-auth.service.ts:13 (accès sessionStorage sans isPlatformBrowser)
- **Vecteur** : N/A (déjà documenté/différé ou hors périmètre exploitabilité)
- **Scénario** : Regroupement des findings confirmés mais NON NOUVEAUX ou hors sécurité. (1) Phishing launch_campaign : gate = case CGU auto-déclarée, domain_verified jamais lu comme garde — c'est EXACTEMENT S-6, acté DIFFÉRÉ par l'utilisateur ; atténuants réels (from_email fixe, templates serveur, record_submit ne capture rien). (2) Dark Web ingestion.py:58 interroge HIBP/LeakCheck sur des emails tiers arbitraires — item low [D-offensif] déjà listé, resté ouvert par choix. (3) TOTP rejouable dans sa fenêtre ~90s : limitation standard de TOTP, non-autonome (mot de passe requis), garde-fous présents (lockout comptant les échecs TOTP, 5/min). (4) admin-auth constructeur accède à sessionStorage sans isPlatformBrowser : bug de robustesse SSR, pas un vecteur d'attaque. AUCUNE régression sur ces points.
- **Remédiation** : Ne PAS re-remonter S-6 ni l'énumération breach comme nouveaux (décision de différé actée, project_security_deferred_actions). Si un jour repris : gate DNS TXT réutilisable (propriété du domaine) pour phishing ET Dark Web. TOTP : optionnellement persister last_totp_step (usage strictement unique) ou documenter l'acceptation du risque. admin-auth : injecter PLATFORM_ID et garder isPlatformBrowser() (robustesse, à traiter avec S6 frontend).

## Thèmes transverses

- Surface publique NON AUTHENTIFIÉE sous-durcie (refonte tarifaire / scan gratuit anonyme) : 3 MEDIUM y convergent (mailbombing unlock, recon/AXFR anonyme, injection HTML contact) + le gate lead contournable — c'est le vecteur de risque n°1 introduit par le code neuf, aucun rempart robuste en amont.
- Rate-limiting structurellement faible et non fiable : compteurs slowapi en mémoire non partagés entre tâches ECS (limiter.py:71 sans storage_uri) ET clé de limitation spoofable via X-Forwarded-For (limiter.py:40 garde >= n au lieu de > n) ET valeur TRUSTED_PROXY_COUNT non versionnée. Les trois se composent : la seule barrière des endpoints publics (3/h, 10/min) est simultanément multipliable, spoofable et fragile au drift.
- Authz de l'outillage offensif sans preuve de propriété/mandat : scan public (subdomain enum + AXFR), phishing (S-6 différé), Dark Web breach lookup — tous permettent d'agir contre des tiers non consentants sans gate DNS TXT. Risque dominant juridique/attribution plutôt que compromission technique. Un gate DNS TXT réutilisable résoudrait les trois.
- Absence d'échappement HTML dans les builders d'e-mails f-string (email_service/alerts.py, darkweb_dossier/ingestion.py) : cause racine unique = interpolation directe sans html.escape/Jinja2 autoescape. Le formulaire de contact (non-auth → boîte admin) est le vecteur exploitable ; les autres sont self-dirigés.
- Intégrité de la monétisation / anti-abus facturation : quota freemium contournable (hard delete + comptage sur lignes vivantes), gate plan ignorant current_period_end sans reconciliation, gate lead sans email vérifié. Cause commune = enforcement basé sur l'état courant mutable plutôt que sur un compteur/état monotone et réconcilié.
- Conformité RGPD lacunaire (non directement exploitable mais dette réglementaire) : export Art.20 incomplet, absence de purge/rétention (Art.5-1-e) sur public_scans et darkweb_dossiers, Sentry sans scrubbing PII, faux consentement horodaté au unlock. À traiter en lot conformité distinct.

## Lots correctifs proposés

### S1 — Durcir la surface publique non-auth (ROI max, code pur, zéro dépendance infra) : rate-limit + figer email/double opt-in sur /public-scans/{token}/unlock, retirer subdomain-enum/AXFR du scan public anonyme, échapper le HTML du formulaire de contact _(code)_
  - Mailbombing / relais d'e-mails via POST /public-scans/{token}/unlock
  - Reconnaissance active anonyme de domaines tiers via /public-scans (subdomain enum + AXFR)
  - Injection HTML dans l'e-mail de notification admin via le formulaire de contact public
  - Injection HTML dans l'e-mail d'alerte de monitoring Dark Web

### S2 — Fiabiliser le rate-limiting : compteurs partagés Redis (storage_uri) + fix du garde X-Forwarded-For anti-spoof + versionnement TRUSTED_PROXY_COUNT ; volet infra = verrouiller l'ALB derrière CloudFront (X-Origin-Verify / prefix-list) _(mixte)_
  - Rate-limiting slowapi en mémoire, non partagé entre les tâches ECS
  - Spoofing d'IP client (X-Forwarded-For) via connexion directe à l'ALB
  - TRUSTED_PROXY_COUNT non injecté par deploy.yml

### S3 — Intégrité de la monétisation et anti-abus : compteur d'usage monotone (soft-delete ou table d'usage) pour le quota freemium + fermeture TOCTOU, gate plan filtrant current_period_end + job de reconciliation Stripe, plafond scan public par domaine/global _(code)_
  - Contournement du quota freemium de scans URL (5/mois) par suppression-puis-rescan
  - Le gating de plan ignore current_period_end : abonnement expiré reste 'active'
  - Gate lead du scan gratuit : email non vérifié et scan coûteux exécuté avant le gate

### S4 — Injection & robustesse des entrées : neutralisation CSV-injection à l'export Dark Web (_csv_safe) + durcissement _parse_emails_csv, lecture bornée du CSV uploadé _(code)_
  - Injection de formule CSV dans l'export du dossier Dark Web
  - Lecture non bornée du CSV en mémoire avant contrôle de taille

### S5 — Conformité RGPD / privacy : compléter l'export Art.20, jobs de purge/rétention (public_scans + darkweb, 90j), before_send Sentry de scrubbing PII, n'horodater le consentement qu'au double opt-in (couvert par S1) _(code)_
  - Export RGPD (portabilité, Art.20) incomplet
  - Absence de rétention/purge sur public_scans et darkweb_dossiers
  - Sentry initialisé sans hook before_send de scrubbing PII

### S6 — Durcissement de l'authentification admin frontend : remplacer la clé statique X-Admin-Key par un jeton de session court (JWT/rôle admin expirant), ne pas persister le secret, garde isPlatformBrowser ; volet infra = CSP sur la SPA + rotation ADMIN_API_KEY dans Secrets Manager _(mixte)_
  - Clé admin statique (X-Admin-Key) persistée en sessionStorage sans rotation ni expiration
  - admin-auth.service accède à sessionStorage dans le constructeur sans garde isPlatformBrowser

### S7 — Dette connue / décisions produit (aucune action de code sauf reprise explicite) : phishing mandate (S-6, DIFFÉRÉ acté), Dark Web breach lookup emails tiers (low ouvert), TOTP anti-rejeu (risque standard accepté) — documenter l'acceptation du risque, ré-évaluer si passage B2C/premiers contrats clients _(code)_
  - Dette connue déjà différée par décision utilisateur — phishing S-6, Dark Web emails tiers, TOTP replay, isPlatformBrowser admin-auth
