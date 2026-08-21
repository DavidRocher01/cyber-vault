"""Garde-fou : tout réglage sans valeur par défaut est provisionné, ou assumé.

POURQUOI CE FICHIER EXISTE.

`Settings` déclare 39 réglages, dont 17 ont pour défaut la chaîne vide. Une
chaîne vide ne lève pas : le code démarre, la fonctionnalité se tait. Trois
d'entre eux étaient dans cet état en production le 2026-08-20, sans que rien ne
le signale :

  - `HIBP_API_KEY` — CE N'EST PAS UN TROU, et la première version de ce fichier
    l'annonçait à tort comme tel. `check_email_breaches` interroge LeakCheck,
    gratuit et sans clé, et ne passe par HIBP que si une clé est fournie. Le
    catalogue de fuites est lui aussi en accès libre. La surveillance Dark Web
    fonctionne donc sans rien payer — la clé n'achèterait qu'une meilleure
    couverture.
  - `RESEND_WEBHOOK_SECRET` — l'endpoint de rebonds refuse tout, par
    construction. Il resterait inerte même après création du secret chez
    Resend, puisque le déploiement ne l'injecte pas.
  - `ADDON_EXTRA_SITES_STRIPE_PRICE_ID` — l'option « sites supplémentaires »
    à 9 € par mois ne peut pas être vendue.

Aucun n'était une décision : c'étaient des oublis, invisibles parce qu'un
réglage absent se comporte exactement comme un réglage inutilisé.

CE QUE CE TEST IMPOSE. Chaque réglage à défaut vide appartient à EXACTEMENT une
catégorie ci-dessous. En ajouter un sans le classer fait échouer le test — il
faut alors décider où il est provisionné, ou écrire pourquoi il ne l'est pas.
C'est la même règle que les exclusions de couverture et les écrans de recette :
une absence doit être une décision datée, jamais un silence.

CE QU'IL NE PEUT PAS VOIR. La définition de tâche ECS de base n'est pas dans le
dépôt. Les réglages de `PAR_DEFINITION_DE_TACHE` sont donc déclarés ici de
confiance, d'après ce que la production répond réellement — relevé le
2026-08-20 via `aws ecs describe-task-definition`.
"""

import ast
import pathlib
import re

RACINE = pathlib.Path(__file__).resolve().parents[2]
CONFIG = RACINE / "backend" / "app" / "core" / "config.py"
DEPLOIEMENT = RACINE / ".github" / "workflows" / "deploy.yml"

# ── Où chaque réglage à défaut vide est provisionné ──────────────────────────

#: Tirés de Secrets Manager par le déploiement (`$secret_names`).
PAR_SECRET = {
    "SECRET_KEY",
    "DATABASE_URL",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "SMTP_PASSWORD",
    "RESEND_API_KEY",
    "SENTRY_DSN",
    "ORIGIN_VERIFY_SECRET",
    "PHISHING_FROM_EMAIL",
}

#: Réinjectés en clair par le déploiement (`$env_overrides`).
PAR_VARIABLE = {
    "STRIPE_PUBLISHABLE_KEY",
    "S3_BUCKET_NAME",
}

#: Posés dans la définition de tâche de base, hors dépôt. Vérifié en production.
PAR_DEFINITION_DE_TACHE = {
    "SMTP_USER",
    "SMTP_FROM",
}

#: Volontairement non provisionnés — chaque entrée porte sa raison et sa date.
ABSENT_ASSUME = {
    "REDIS_URL": (
        "Différé le 2026-07-30, assumé. Le service tourne à une seule tâche et "
        "un seul worker : les compteurs `memory://` du rate-limiting sont donc "
        "de fait globaux. Prérequis de scalabilité, pas faille active. "
        "~10,51 $/mois le jour venu (Valkey)."
    ),
    "HIBP_API_KEY": (
        "Absence ASSUMEE, et non un oubli — verifie le 2026-08-21 dans "
        "`darkweb_service.check_email_breaches`. Le fournisseur par defaut est "
        "LeakCheck, gratuit et sans cle ; HIBP n'est interroge QUE si une cle "
        "est fournie, et le catalogue de fuites est en acces libre. La "
        "fonctionnalite marche donc sans depense. La cle achèterait une "
        "meilleure couverture et supprimerait la limite de debit de LeakCheck "
        "(~1 requete toutes les 2-3 s, d'ou `_BATCH_DELAY = 2.5`). A prendre le "
        "jour ou un client se plaindra de dossiers incomplets, pas avant."
    ),
    "RESEND_WEBHOOK_SECRET": (
        "MANQUANT, constaté le 2026-08-20. Le webhook de rebonds refuse tout "
        "tant que le secret est vide — comportement voulu, mais l'endpoint est "
        "donc inerte depuis sa mise en production. ORDRE IMPÉRATIF quand il "
        "sera créé : déposer dans Secrets Manager D'ABORD, ajouter à "
        "`$secret_names` ENSUITE. L'inverse empêche la tâche ECS de démarrer."
    ),
    "ADDON_EXTRA_SITES_STRIPE_PRICE_ID": (
        "MANQUANT, constaté le 2026-08-20. L'option « sites supplémentaires » à "
        "9 €/mois est pourtant livrée : bouton au tableau de bord, endpoint, "
        "tests. Sans identifiant de prix, `POST /subscriptions/addons/"
        "extra-sites` répond 400 « Add-on non configuré » — un client payant qui "
        "clique se prend une erreur. L'echec est donc visible, pas silencieux. "
        "Le montant et le nombre de sites, eux, ont un défaut de classe."
    ),
}


def _reglages_sans_defaut() -> set[str]:
    """Les champs de `Settings` qui n'ont aucune valeur utilisable par défaut.

    TROIS FORMES, et il faut les trois — la première version n'en voyait qu'une,
    et déclarait donc orphelines cinq entrées pourtant justes :

        SECRET_KEY: str                    -> aucun défaut (pydantic exige)
        SENTRY_DSN: str | None = None      -> défaut None
        HIBP_API_KEY: str = ""             -> défaut vide
    """
    arbre = ast.parse(CONFIG.read_text(encoding="utf-8"))
    classe = next(n for n in arbre.body if isinstance(n, ast.ClassDef) and n.name == "Settings")
    vides = set()
    for noeud in classe.body:
        if not (isinstance(noeud, ast.AnnAssign) and isinstance(noeud.target, ast.Name)):
            continue
        if noeud.value is None:  # aucun défaut : pydantic refusera de démarrer sans
            vides.add(noeud.target.id)
            continue
        try:
            if ast.literal_eval(noeud.value) in ("", None):
                vides.add(noeud.target.id)
        except (ValueError, TypeError):
            continue  # défaut calculé : il y a une valeur, donc rien à provisionner
    return vides


def _liste_du_deploiement(variable: str) -> set[str]:
    """Extrait `$secret_names` ou les noms de `$env_overrides` de deploy.yml."""
    texte = DEPLOIEMENT.read_text(encoding="utf-8")
    if variable == "secret_names":
        bloc = re.search(r"\(\[([^\]]*)\]\) as \$secret_names", texte)
    else:
        bloc = re.search(r"\(\[([^\]]*)\]\) as \$env_overrides", texte)
    assert bloc, f"${variable} introuvable dans deploy.yml — le motif a-t-il change ?"
    # `[A-Z0-9_]+` et non `[A-Z_]+` : S3_BUCKET_NAME porte un chiffre, et une
    # classe trop etroite le rendait invisible sans rien signaler.
    return set(re.findall(r'"name"\s*:\s*"([A-Z0-9_]+)"', bloc.group(1))) or set(
        re.findall(r'"([A-Z0-9_]+)"', bloc.group(1))
    )


def test_l_extraction_fonctionne():
    """Garde-fou du garde-fou : des listes vides feraient passer tout le reste."""
    assert len(_reglages_sans_defaut()) > 10, "aucun reglage extrait de Settings"
    assert len(_liste_du_deploiement("secret_names")) > 5, "aucun secret extrait"
    assert len(_liste_du_deploiement("env_overrides")) > 2, "aucune variable extraite"


def test_chaque_reglage_vide_est_classe():
    """Un nouveau réglage sans défaut oblige à dire où il est provisionné."""
    classes = PAR_SECRET | PAR_VARIABLE | PAR_DEFINITION_DE_TACHE | set(ABSENT_ASSUME)
    non_classes = sorted(_reglages_sans_defaut() - classes)

    assert not non_classes, (
        "Reglage(s) sans valeur par defaut et non classe(s) :\n  "
        + "\n  ".join(non_classes)
        + "\n\nUn defaut vide ne leve pas : la fonctionnalite se tait. Declarez "
        "ou le reglage est provisionne (PAR_SECRET / PAR_VARIABLE / "
        "PAR_DEFINITION_DE_TACHE), ou pourquoi il ne l'est pas (ABSENT_ASSUME)."
    )


def test_la_carte_ne_decrit_que_des_reglages_existants():
    """Une entrée qui ne correspond plus à rien ferait mentir la carte."""
    vides = _reglages_sans_defaut()
    orphelins = sorted(
        (PAR_SECRET | PAR_VARIABLE | PAR_DEFINITION_DE_TACHE | set(ABSENT_ASSUME)) - vides
    )

    assert not orphelins, (
        "Entree(s) sans reglage correspondant — supprimez-les :\n  " + "\n  ".join(orphelins)
    )


def test_les_secrets_declares_sont_ceux_du_deploiement():
    """Dans les deux sens : rien d'oublie, rien d'invente."""
    reel = _liste_du_deploiement("secret_names")

    manquants = sorted(PAR_SECRET - reel)
    en_trop = sorted(reel - PAR_SECRET)

    assert not manquants, (
        "Declare(s) PAR_SECRET mais absent(s) de $secret_names dans deploy.yml — "
        "le conteneur ne les recevra pas :\n  " + "\n  ".join(manquants)
    )
    assert not en_trop, (
        "Injecte(s) par deploy.yml mais absent(s) de PAR_SECRET :\n  " + "\n  ".join(en_trop)
    )


def test_les_variables_declarees_sont_celles_du_deploiement():
    reel = _liste_du_deploiement("env_overrides")
    manquants = sorted(PAR_VARIABLE - reel)

    assert not manquants, (
        "Declare(s) PAR_VARIABLE mais absent(s) de $env_overrides :\n  " + "\n  ".join(manquants)
    )


def test_chaque_absence_porte_une_raison_ecrite():
    """Une exclusion sans justification finit par masquer un oubli — c'est
    exactement ce qui s'est produit pour les trois reglages de 2026-08-20."""
    trop_courtes = sorted(nom for nom, raison in ABSENT_ASSUME.items() if len(raison) < 80)

    assert not trop_courtes, "Absence(s) sans raison suffisante :\n  " + "\n  ".join(trop_courtes)
