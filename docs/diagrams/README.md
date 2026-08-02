# Schémas d'architecture

**La source est [`../ARCHITECTURE.md`](../ARCHITECTURE.md).** Les blocs
```` ```mermaid ```` qu'il contient sont la seule version à éditer. Tout le reste
de ce dossier en dérive.

```bash
python scripts/generate_diagrams.py            # régénère les .mmd
python scripts/generate_diagrams.py --check    # échoue si désynchronisé (tourne en CI)
```

## Pourquoi ce garde-fou

Les neuf `.mmd` avaient été extraits une seule fois, puis plus jamais. Le
2026-08-02, `02.mmd` décrivait encore un frontend « Angular 20 » que
`ARCHITECTURE.md` annonçait en 21. Rien ne le signalait : aucun lien ne pointe
vers ces fichiers, donc personne ne les rouvre.

C'est le même mécanisme qui a laissé un article de blog annoncer un tarif huit
fois inférieur au prix réel — une copie qu'on oublie parce qu'on ne la regarde
jamais.

## Contenu

| Fichier | Sujet | Type |
|---------|-------|------|
| `01` | Architecture système (déploiement AWS) | flowchart |
| `02` | Architecture applicative (couches) | flowchart |
| `03` | Carte des domaines | flowchart |
| `04` | Cœur — utilisateur, facturation, scan, vault | ERD |
| `05` | Awareness / e-learning | ERD |
| `06` | Authentification (login + 2FA + JWT) | séquence |
| `07` | Vault zero-knowledge (chiffrement côté client) | séquence |
| `08` | Abonnement Stripe (checkout + webhook) | séquence |
| `09` | Scan de sécurité (déclenchement + anti-SSRF) | séquence |

## Les `.svg` ne sont pas régénérés automatiquement

Leur rendu demande `mermaid-cli`, qui n'est **pas** une dépendance du projet.
Ils peuvent donc retarder sur les `.mmd`, et aucun contrôle ne le détecte.

Pour les rafraîchir ponctuellement, sans rien installer durablement :

```bash
npx -y @mermaid-js/mermaid-cli -i docs/diagrams/02.mmd -o docs/diagrams/02.svg
```

Aucun document du dépôt ne les référence aujourd'hui : ils servent à illustrer
un support externe (présentation, dossier client, due diligence). Si cet usage
disparaît, mieux vaut les supprimer que les laisser diverger — GitHub rend les
blocs Mermaid de `ARCHITECTURE.md` nativement.
