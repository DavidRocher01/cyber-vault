"""Domaine sensibilisation NIS2 — 14 modules, ~3 200 lignes.

Ce paquet ne re-exporte RIEN, volontairement. Un `__init__` qui re-exporte ses
sous-modules les invite a importer leur propre paquet, et c'est ainsi que
naissent les cycles : `pdf_brand` et `pdf_covers` s'importaient mutuellement par
un re-export de compatibilite, et changer l'ordre d'import levait une
ImportError (corrige le 2026-08-18, cf. `tests/test_cycles_imports.py`).

On importe donc toujours le sous-module directement :

    from app.services.awareness import progression
"""
