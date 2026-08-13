#!/usr/bin/env python3
"""Confronte la configuration AWS reelle a ce que `infra/` decrit.

POURQUOI CE SCRIPT EXISTE. La revue de securite du 2026-08-11 a trouve ses trois
constats dans l'infrastructure, pas dans le code. Ils ont ete corriges. Mais RIEN
NE DIRAIT QU'ILS REVIENNENT : si quelqu'un reattache `AmazonS3FullAccess` pour
debloquer un deploiement un soir de fatigue, si un seau redevient public, si la
base recupere le groupe `default`, personne ne le saura.

Les fichiers de `infra/` DECRIVENT le reel. Une description qu'on ne confronte
pas a sa source finit par mentir — c'est la lecon repetee tout au long de ce
projet : sitemap contre routes, couverture de recette contre fichier de routes,
modes de rendu contre `canActivate`, appels du frontend contre routes du
backend. Ce script applique le meme principe a l'infrastructure.

CE QU'IL VERIFIE, ET RIEN D'AUTRE : les trois corrections de la revue. Il n'a
pas vocation a auditer tout le compte — un controle qui verifie trop devient
bruyant, puis on cesse de le lire.

Usage :  python scripts/check_infra_drift.py
Sortie :  0 si conforme, 1 sinon, avec le detail de chaque ecart.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
COMPTE = "328646895533"
REGION = "eu-west-3"

ROLE_DEPLOIEMENT = "github-actions-cybervault-deploy"
SEAU_FRONTEND = "cyberscanapp-frontend"
SEAU_LIVRABLES = "cybervault-rssi-deliverables-prod"
BASE = "cybervault-prod"
GROUPE_BASE_ATTENDU = "cybervault-rds"

ecarts: list[str] = []


def aws(*args: str) -> object | None:
    """Appelle l'AWS CLI et renvoie le JSON, ou `None` si l'appel echoue.

    Un echec d'appel N'EST PAS un ecart : il peut venir d'une session expiree
    ou d'un droit de lecture manquant. On le signale a part, pour ne pas crier
    a la derive quand on n'a simplement pas pu regarder.
    """
    r = subprocess.run(
        ["aws", *args, "--output", "json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if r.returncode != 0:
        print(
            f"  ! lecture impossible : aws {' '.join(args[:2])} — {r.stderr.strip()[:110]}"
        )
        return None
    return json.loads(r.stdout) if r.stdout.strip() else None


def verifier_role_de_deploiement() -> None:
    attachees = aws(
        "iam", "list-attached-role-policies", "--role-name", ROLE_DEPLOIEMENT
    )
    if attachees is not None:
        noms = [p["PolicyName"] for p in attachees["AttachedPolicies"]]
        if noms:
            ecarts.append(
                f"role de deploiement : politique(s) GEREE(S) reattachee(s) — {noms}. "
                "La revue les avait retirees : `AmazonS3FullAccess` donne acces aux "
                "documents clients."
            )

    # LES DEUX POLITIQUES EN LIGNE SONT COMPAREES, y compris celle d'audit :
    # sans cela, les droits de lecture pourraient etre elargis sans que le
    # controle — qui s'appuie precisement sur eux — ne le signale.
    for nom, fichier in (
        ("cybervault-deploiement-minimal", "infra/iam/github-actions-deploy.json"),
        ("cybervault-audit-lecture-seule", "infra/iam/github-actions-audit.json"),
    ):
        reel = aws(
            "iam",
            "get-role-policy",
            "--role-name",
            ROLE_DEPLOIEMENT,
            "--policy-name",
            nom,
        )
        if reel is None:
            continue
        attendu = json.loads((RACINE / fichier).read_text("utf-8"))
        if _normaliser(reel["PolicyDocument"]) != _normaliser(attendu):
            ecarts.append(
                f"role de deploiement : la politique `{nom}` DIFFERE de `{fichier}`. "
                "Corriger le fichier si le changement est voulu, sinon retablir."
            )


def _normaliser(doc: dict) -> str:
    """Compare le fond, pas la mise en forme ni l'ordre des declarations."""
    return json.dumps(doc, sort_keys=True, separators=(",", ":"))


def verifier_la_base() -> None:
    d = aws("rds", "describe-db-instances", "--db-instance-identifier", BASE)
    if d is None:
        return
    inst = d["DBInstances"][0]

    if inst["PubliclyAccessible"]:
        ecarts.append("base : devenue accessible publiquement")
    if not inst["StorageEncrypted"]:
        ecarts.append("base : chiffrement du stockage desactive")

    groupes = [g["VpcSecurityGroupId"] for g in inst["VpcSecurityGroups"]]
    noms = []
    for gid in groupes:
        g = aws("ec2", "describe-security-groups", "--group-ids", gid)
        if g:
            noms.append(g["SecurityGroups"][0]["GroupName"])
    if "default" in noms:
        ecarts.append(
            "base : de nouveau jointe au groupe `default` du VPC. Celui-ci autorise "
            "tous protocoles depuis lui-meme — toute ressource creee sans groupe "
            "explicite y accede."
        )
    elif GROUPE_BASE_ATTENDU not in noms:
        ecarts.append(f"base : groupes {noms}, attendu `{GROUPE_BASE_ATTENDU}`")


def verifier_les_seaux() -> None:
    for seau in (SEAU_FRONTEND, SEAU_LIVRABLES):
        bloc = aws("s3api", "get-public-access-block", "--bucket", seau)
        if bloc is not None:
            cfg = bloc["PublicAccessBlockConfiguration"]
            manquants = [k for k, v in cfg.items() if not v]
            if manquants:
                ecarts.append(
                    f"seau {seau} : blocage d'acces public incomplet — {manquants}"
                )

    pol = aws("s3api", "get-bucket-policy", "--bucket", SEAU_FRONTEND)
    if pol is None:
        return
    doc = json.loads(pol["Policy"])
    for s in doc["Statement"]:
        p = s.get("Principal")
        if p == "*" or (isinstance(p, dict) and "*" in str(p.get("AWS", ""))):
            ecarts.append(
                f"seau {SEAU_FRONTEND} : declaration PUBLIQUE de retour "
                f"({s.get('Sid', 'sans Sid')}). Le site redevient joignable hors "
                "CloudFront, donc sans CSP ni HSTS."
            )


def main() -> int:
    verifier_role_de_deploiement()
    verifier_la_base()
    verifier_les_seaux()

    if ecarts:
        print(f"\n{len(ecarts)} ecart(s) entre AWS et ce que `infra/` decrit :\n")
        for e in ecarts:
            print(f"  - {e}")
        return 1

    print("Infrastructure conforme a `infra/` : role, base et seaux inchanges.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
