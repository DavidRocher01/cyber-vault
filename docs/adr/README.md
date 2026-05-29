# Architecture Decision Records (ADR)

Ce dossier contient les décisions d'architecture importantes prises sur le projet Cyber-Vault.

## Pourquoi des ADRs ?

Les ADRs permettent de documenter **pourquoi** une décision a été prise, pas seulement **quoi**. Ils évitent de re-débattre des mêmes choix et aident les nouveaux contributeurs à comprendre le contexte.

## Format

Chaque ADR suit la structure :
- **Contexte** : situation et contraintes qui ont conduit à la décision
- **Options évaluées** : alternatives considérées
- **Décision** : choix retenu et justification
- **Conséquences** : impacts positifs et négatifs

## Cycle de vie

`Proposé` → `Accepté` → `Déprécié` → `Annulé`

## Index

| # | Titre | Statut |
|---|-------|--------|
| [0001](0001-choix-fastapi.md) | Choix de FastAPI pour le backend | Accepté |
| [0002](0002-chiffrement-zero-knowledge.md) | Chiffrement zero-knowledge côté client | Accepté |
| [0003](0003-architecture-aws-ecs-fargate.md) | Déploiement sur AWS ECS Fargate | Accepté |
| [0004](0004-choix-angular-standalone.md) | Angular 19 Standalone Components | Accepté |
