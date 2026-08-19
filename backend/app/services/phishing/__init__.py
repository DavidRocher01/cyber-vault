"""Domaine phishing — simulation de campagnes.

Ce paquet ne re-exporte RIEN, volontairement : un `__init__` qui re-exporte ses
sous-modules les invite a importer leur propre paquet, et c'est ainsi que
naissent les cycles (cf. `tests/test_cycles_imports.py`).

    from app.services.phishing import sending
"""
