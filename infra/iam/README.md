# Politiques IAM — source de vérité

Ces documents décrivent les droits réellement attachés dans AWS. **Ils ne sont
pas appliqués automatiquement** : il n'y a pas d'infrastructure-as-code sur ce
projet. Ils sont ici pour être **relus, versionnés et comparés** à l'existant.

## `github-actions-deploy.json`

Attachée en ligne au rôle `github-actions-cybervault-deploy` sous le nom
`cybervault-deploiement-minimal`.

**Pourquoi elle existe.** Ce rôle portait auparavant `AmazonS3FullAccess`,
`AmazonECS_FullAccess`, `CloudFrontFullAccess` et `AmazonEC2ContainerRegistryPowerUser`.
`AmazonS3FullAccess` signifie `s3:*` sur **tous** les seaux du compte — dont
`cybervault-rssi-deliverables-prod`, qui contient les documents de conformité
des clients. Une dépendance compromise dans un workflow, ou un accès en écriture
sur `master`, suffisait à les lire et les supprimer.

`AmazonECS_FullAccess` permettait en outre d'enregistrer une définition de tâche
arbitraire et de la faire tourner avec le rôle applicatif — donc d'obtenir les
accès du backend.

**Ce qu'elle autorise, et rien de plus :** le seau du frontend, l'invalidation
et la fonction de routage de la distribution nommée, le dépôt d'images unique,
le service ECS nommé, et `iam:PassRole` sur les deux seuls rôles de tâche,
conditionné à `ecs-tasks.amazonaws.com`.

**Vérifiée au simulateur IAM avant retrait des politiques larges** : les douze
actions du workflow sont autorisées, et l'accès au seau des livrables clients
est refusé.

## Vérifier que le réel correspond

```bash
aws iam get-role-policy --role-name github-actions-cybervault-deploy \
  --policy-name cybervault-deploiement-minimal --query PolicyDocument
```

Toute divergence est soit une correction non consignée ici, soit un
élargissement à expliquer.
