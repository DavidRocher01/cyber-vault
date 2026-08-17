# Brouillons d'articles de blog

**Ces fichiers ne sont PAS ce que le site publie.** La source de vérité des
articles est la **base de données**, alimentée par l'interface d'administration.
Ce dossier ne sert qu'à écrire et conserver un texte avant sa mise en ligne, et à
en garder l'historique dans Git.

## La règle, et pourquoi elle compte

Modifier un fichier ici **ne change rien sur le site**. Il faut reporter la
modification dans l'administration.

C'est exactement le genre de duplication qui a coûté cher à ce projet : le
sitemap a longtemps existé en deux exemplaires — un fichier statique servi aux
moteurs, un endpoint dynamique que personne n'atteignait — et les deux ont
divergé pendant des mois sans qu'aucun signal ne le dise. On accepte la
duplication ici parce qu'un brouillon **n'est pas** du contenu publié : tant que
`is_published: false`, il n'existe nulle part ailleurs. Le jour où l'article
part en ligne, c'est la base qui fait foi, et ce fichier devient une archive.

Ne jamais écrire de script qui synchronise ce dossier vers la base. Ce serait
créer la divergence qu'on veut éviter.

## Organisation

```
content/fr/blog/<slug>/
├── article.html   # le contenu a coller dans le champ `htmlContent`
└── meta.yaml      # les autres champs du formulaire
```

L'importateur de sensibilisation (`awareness_content_importer.py`) ne balaie que
`content/fr/modules/` et `content/fr/programs/` : ce dossier lui est invisible.

## Publier

1. Créer l'article dans l'administration avec les champs de `meta.yaml`.
2. Coller le contenu d'`article.html` dans `htmlContent`.
3. Laisser `isPublished` décoché tant que la relecture n'est pas faite — un
   article non publié est exclu du sitemap, c'est vérifié par
   `backend/tests/test_sitemap_robots.py`.
4. Publier. Le sitemap l'annonce alors tout seul, avec sa date.
