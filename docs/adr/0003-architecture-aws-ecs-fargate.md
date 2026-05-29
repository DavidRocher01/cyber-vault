# ADR 0003 — Déploiement sur AWS ECS Fargate

**Statut** : Accepté  
**Date** : 2024-06

---

## Contexte

La plateforme doit être déployée en production avec les contraintes suivantes :

- Haute disponibilité (SaaS B2B)
- Scalabilité automatique selon la charge
- Sécurité des secrets (clés API, DB credentials)
- Coût maîtrisé (startup, pas de trafic massif initial)
- Déploiement continu via GitHub Actions

## Options évaluées

| Infrastructure | Avantages | Inconvénients |
|----------------|-----------|---------------|
| **ECS Fargate** | Serverless containers, pas de gestion serveurs, intégration AWS native | Plus cher que EC2 à pleine charge |
| **EC2 + Docker** | Contrôle total, moins cher à fort trafic | Maintenance serveur, patching OS |
| **Kubernetes (EKS)** | Très flexible, standard industrie | Complexité opérationnelle excessive pour le contexte |
| **Heroku / Render** | Simplicité | Vendor lock-in, moins de contrôle sécurité, coût |

## Décision

**AWS ECS Fargate** avec l'architecture suivante :

- **ECS Fargate** : conteneurs backend + worker sans gestion serveur
- **RDS PostgreSQL** : base de données managée avec backups automatiques
- **S3** : stockage fichiers (livrables RSSI, exports)
- **CloudFront** : CDN + terminaison TLS pour le frontend Angular (fichiers statiques)
- **Route 53** : DNS avec `cyberscanapp.com`
- **AWS Secrets Manager** : gestion des secrets (plus de `.env` en production)
- **GitHub Actions OIDC** : déploiement CI/CD sans credentials AWS statiques

## Conséquences

**Positives :**
- Zéro gestion de serveur (OS, patching, scaling)
- Secrets Manager élimine les secrets dans les variables d'environnement ECS
- OIDC GitHub Actions : pas de clés AWS dans les secrets GitHub
- RDS multi-AZ disponible pour la haute disponibilité
- CloudFront réduit la latence frontend

**Négatives :**
- Coût légèrement supérieur à EC2 à fort trafic
- Cold start possible sur Fargate si le service scale à 0
- Dépendance à l'écosystème AWS

**Mitigation :**
- Service ECS configuré avec minimum 1 task pour éviter le cold start
- Budget AWS Budgets configuré avec alertes
- Architecture documentée pour migration potentielle vers d'autres clouds
