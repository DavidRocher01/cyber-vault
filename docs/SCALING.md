# Capacité & scaling — Rocher Cybersécurité

> Mémo pour savoir **quand** et **comment** scaler. À ton stade (pré-prospection,
> 1 instance), tu es très loin des limites — ce doc sert pour « le jour où ça marche fort ».

## Configuration actuelle (prod)

| Élément | Valeur | Source |
|---|---|---|
| Instances backend | **1** | ECS Fargate, service `cybervault-backend-service-av2ii2n3` |
| Workers uvicorn | **1** (process async) | `backend/Dockerfile` (`--workers 1`) |
| CPU / RAM | **1 vCPU / 2 Go** | `deploy.yml` (cpu=1024, memory=2048) |
| Pool connexions DB | **20 + 10 overflow = 30** | `backend/app/core/database.py` |
| RDS | t4g.micro (PostgreSQL) | infra AWS |
| Scheduler | APScheduler **in-memory** (pas de Redis) | `scheduler.py` |

## Capacité d'une instance (estimation)

FastAPI est **asynchrone** : une requête qui *attend* (DB, API externe) ne bloque pas
les autres. Il n'y a donc pas un chiffre unique — ça dépend du type de charge.

| Type de charge | Capacité ~ |
|---|---|
| Connexions ouvertes/inactives (navigation normale) | plusieurs centaines à ~1000+ |
| Requêtes touchant la DB **en parallèle** | **~30** (plafond du pool), au-delà = file d'attente |
| Requêtes **lourdes CPU** (login bcrypt, PDF, scans) | une poignée en parallèle (1 vCPU) |

**Ordre de grandeur confortable : 100-300 utilisateurs connectés simultanés** en
navigation, **~20-30 requêtes actives en parallèle** sans ralentissement.

## Goulots d'étranglement (dans l'ordre où ils saturent)

1. **CPU sur opérations lourdes** (1 vCPU) — bcrypt (login ~100-200 ms), génération
   PDF (reportlab), scans. C'est ce qui sature **en premier** sous charge.
2. **Pool DB (30)** — plafonne les requêtes simultanées en base.
3. **RDS t4g.micro** — `max_connections` limité (~80-100).
4. Connexions réseau brutes — **pas** un souci avant longtemps.

## Signaux qui indiquent qu'il faut scaler

- Latence p95 qui monte (CloudWatch / Sentry) sur les endpoints courants
- `502`/timeouts en pic d'affluence
- CPU ECS soutenu > 70-80 %
- Erreurs « QueuePool limit ... timed out » (pool DB saturé)
- RDS proche de `max_connections`

## Leviers de scaling (dans l'ordre de simplicité/coût)

1. **Vertical — grossir l'instance** : passer Fargate à 2 vCPU / 4 Go, puis augmenter
   les workers uvicorn (≈ 1 worker par vCPU). Le plus simple, aucun changement de code.
2. **Augmenter le pool DB** (`database.py`) si la base suit (sinon grossir la RDS d'abord).
3. **Horizontal — passer à 2+ instances** (ECS desiredCount > 1, derrière l'ALB).
   ⚠️ **Nécessite Redis** : sans jobstore partagé, chaque instance exécute le scheduler
   → **double exécution** des tâches planifiées (scans, emails, monitoring). Voir
   `scheduler.py` (fallback in-memory si `REDIS_URL` absent) — le code est déjà prêt,
   il suffit de provisionner ElastiCache et de définir `REDIS_URL`.
4. **Grossir la RDS** (t4g.micro → instance supérieure) si la base devient le goulot.

## Mesurer pour de vrai

Les chiffres ci-dessus sont **indicatifs**. Pour connaître la vraie limite, faire un
**test de charge** (k6 ou Locust) sur les endpoints réels (login, scan, dashboard) et
observer latence + taux d'erreur. Prématuré tant que le trafic est faible.
