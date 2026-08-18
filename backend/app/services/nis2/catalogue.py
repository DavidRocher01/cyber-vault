"""Catalogue des criteres NIS2 — source unique de verite.

POURQUOI CE MODULE EXISTE. Ce catalogue vivait dans
`app/api/v1/endpoints/nis2.py`, qui pesait 505 lignes contre 43 pour son
service : la couche de routage portait les donnees metier, a rebours de la
regle de couches du projet.

Il a maintenant plus d'un consommateur — les endpoints, les deux generateurs de
PDF, et bientot le rattachement de preuves aux criteres. Le laisser dans un
routeur obligerait chacun d'eux a importer un endpoint pour lire une donnee de
reference.

Le contenu ci-dessous est INCHANGE : deplacement pur, sans reecriture.
"""

# ---------------------------------------------------------------------------
# Valid statuses
# ---------------------------------------------------------------------------
VALID_STATUSES = {"compliant", "partial", "non_compliant", "na"}


# ---------------------------------------------------------------------------
# NIS2 items definition (single source of truth)
#
# Chaque item porte un champ `article` le rattachant a la directive (UE)
# 2022/2555 :
#   Art. 20      gouvernance, responsabilite et formation des organes de direction
#   Art. 21(2)   mesures de gestion des risques, alineas (a) a (j)
#   Art. 23      obligations de notification des incidents
#   Art. 3 / 27  identification et enregistrement des entites
#
# Ce rattachement est ce qui distingue un diagnostic d'un questionnaire maison :
# face a un auditeur ou un donneur d'ordre, chaque reponse renvoie a une
# exigence precise du texte.
#
# ATTENTION : rattachement INDICATIF, destine a orienter la lecture du rapport.
# Il ne constitue pas une analyse juridique et n'engage pas la conformite reelle
# de l'entite, qui depend de sa qualification (entite essentielle ou importante)
# et de sa transposition nationale.
# ---------------------------------------------------------------------------
NIS2_CATEGORIES = [
    {
        "id": "governance",
        "label": "Gouvernance",
        "icon": "policy",
        "items": [
            {
                "id": "rssi",
                "label": "Désignation d'un RSSI ou responsable cyber",
                "desc": "Une personne identifiée est responsable de la sécurité des systèmes d'information.",
                "article": "Art. 20(1)",
                "remediation": {
                    "produit": "RSSI externalisé",
                    "route": "/rssi-externalise",
                },
            },
            {
                "id": "policy",
                "label": "Politique de sécurité SI documentée et approuvée",
                "desc": "Une politique formelle existe, est à jour et a été validée par la direction.",
                "article": "Art. 21(2)(a)",
            },
            {
                "id": "mgmt_training",
                "label": "Implication et formation de la direction",
                "desc": "Les dirigeants ont été sensibilisés aux risques cyber et à leurs responsabilités NIS2.",
                "article": "Art. 20(2)",
                "remediation": {
                    "produit": "Sensibilisation NIS2 — parcours Direction",
                    "route": "/sensibilisation",
                },
            },
            {
                "id": "policy_review",
                "label": "Revue annuelle de la politique de sécurité",
                "desc": "La politique est révisée au moins une fois par an et après chaque incident majeur.",
                "article": "Art. 21(2)(f)",
            },
        ],
    },
    {
        "id": "risk",
        "label": "Gestion des risques",
        "icon": "security",
        "items": [
            {
                "id": "risk_analysis",
                "label": "Analyse de risques formelle (EBIOS RM / ISO 27005)",
                "desc": "Une analyse de risques structurée a été réalisée et documentée.",
                "article": "Art. 21(2)(a)",
            },
            {
                "id": "risk_treatment",
                "label": "Plan de traitement des risques avec suivi",
                "desc": "Chaque risque identifié dispose d'un plan d'action suivi régulièrement.",
                "article": "Art. 21(2)(a)",
            },
            {
                "id": "asset_inventory",
                "label": "Inventaire des actifs critiques",
                "desc": "Tous les systèmes, données et services critiques sont répertoriés.",
                "article": "Art. 21(2)(i)",
            },
            {
                "id": "data_classif",
                "label": "Classification des données",
                "desc": "Les données sont classifiées selon leur sensibilité (public, interne, confidentiel, secret).",
                "article": "Art. 21(2)(i)",
            },
        ],
    },
    {
        "id": "access",
        "label": "Sécurité des accès",
        "icon": "lock",
        "items": [
            {
                "id": "mfa",
                "label": "MFA sur tous les accès critiques",
                "desc": "L'authentification multi-facteurs est déployée sur les systèmes et comptes critiques.",
                "article": "Art. 21(2)(j)",
            },
            {
                "id": "password_policy",
                "label": "Politique de mots de passe robuste",
                "desc": "Longueur minimale 12 caractères, complexité, renouvellement, pas de réutilisation.",
                "article": "Art. 21(2)(i)",
            },
            {
                "id": "pam",
                "label": "Gestion des comptes à privilèges (PAM)",
                "desc": "Les accès administrateurs sont tracés, justifiés et revus régulièrement.",
                "article": "Art. 21(2)(i)",
            },
            {
                "id": "access_review",
                "label": "Revue périodique des droits d'accès",
                "desc": "Les droits sont revus au minimum trimestriellement et lors de changements RH.",
                "article": "Art. 21(2)(i)",
            },
        ],
    },
    {
        "id": "systems",
        "label": "Sécurité des systèmes",
        "icon": "computer",
        "items": [
            {
                "id": "patch_mgmt",
                "label": "Gestion des correctifs (patch critique < 72h)",
                "desc": "Un processus formel garantit l'application rapide des correctifs de sécurité critiques.",
                "article": "Art. 21(2)(e)",
            },
            {
                "id": "encryption",
                "label": "Chiffrement des données sensibles (transit + repos)",
                "desc": "TLS 1.2+ en transit, chiffrement au repos pour les données sensibles.",
                "article": "Art. 21(2)(h)",
            },
            {
                "id": "hardening",
                "label": "Configuration sécurisée des systèmes",
                "desc": "Les systèmes sont configurés selon des référentiels de durcissement (CIS Benchmarks, ANSSI).",
                "article": "Art. 21(2)(e)",
            },
            {
                "id": "edr",
                "label": "Antivirus / EDR sur tous les postes",
                "desc": "Une solution de détection d'endpoint est déployée et maintenue à jour.",
                "article": "Art. 21(2)(e)",
            },
        ],
    },
    {
        "id": "incidents",
        "label": "Gestion des incidents",
        "icon": "warning",
        "items": [
            {
                "id": "incident_proc",
                "label": "Procédure de détection et réponse documentée",
                "desc": "Une procédure formelle de réponse aux incidents est documentée et connue des équipes.",
                "article": "Art. 21(2)(b)",
            },
            {
                "id": "soc",
                "label": "CERT/SOC ou capacité de surveillance",
                "desc": "Une capacité de détection et de réponse aux incidents est opérationnelle.",
                "article": "Art. 21(2)(b)",
            },
            {
                "id": "anssi_notif",
                "label": "Notification ANSSI sous 24h (incidents significatifs)",
                "desc": "Le processus de notification à l'ANSSI est connu et testé.",
                "article": "Art. 23",
            },
            {
                "id": "post_mortem",
                "label": "Post-mortem et retour d'expérience",
                "desc": "Chaque incident donne lieu à un rapport d'analyse et des actions correctives.",
                "article": "Art. 21(2)(b)",
            },
        ],
    },
    {
        "id": "continuity",
        "label": "Continuité d'activité",
        "icon": "restore",
        "items": [
            {
                "id": "pca",
                "label": "Plan de continuité (PCA) documenté et testé",
                "desc": "Un PCA existe, est tenu à jour et a été testé lors d'un exercice.",
                "article": "Art. 21(2)(c)",
            },
            {
                "id": "pra",
                "label": "Plan de reprise (PRA) avec RTO/RPO définis",
                "desc": "Les objectifs de reprise (délai et point de reprise) sont formalisés et atteignables.",
                "article": "Art. 21(2)(c)",
            },
            {
                "id": "backups",
                "label": "Sauvegardes testées et déconnectées du réseau",
                "desc": "Les sauvegardes sont régulières, chiffrées, testées, et au moins une copie est hors ligne.",
                "article": "Art. 21(2)(c)",
            },
        ],
    },
    {
        "id": "supply_chain",
        "label": "Chaîne d'approvisionnement",
        "icon": "account_tree",
        "items": [
            {
                "id": "vendor_audit",
                "label": "Évaluation sécurité des fournisseurs critiques",
                "desc": "Les fournisseurs ayant accès aux SI critiques font l'objet d'une évaluation de sécurité.",
                "article": "Art. 21(2)(d)",
            },
            {
                "id": "vendor_contracts",
                "label": "Clauses de sécurité dans les contrats fournisseurs",
                "desc": "Les contrats incluent des exigences de sécurité, de notification d'incidents et d'audit.",
                "article": "Art. 21(2)(d)",
            },
            {
                "id": "sca",
                "label": "Inventaire des dépendances logicielles (SCA)",
                "desc": "Les composants open source et tiers sont inventoriés et surveillés pour les vulnérabilités.",
                "article": "Art. 21(2)(e)",
                "remediation": {
                    "produit": "Analyse de code (SAST/SCA)",
                    "route": "/code-scan",
                },
            },
        ],
    },
    {
        "id": "network",
        "label": "Sécurité réseau",
        "icon": "hub",
        "items": [
            {
                "id": "segmentation",
                "label": "Segmentation réseau (isolation des systèmes critiques)",
                "desc": "Les systèmes critiques sont isolés dans des zones réseau distinctes avec contrôle des flux.",
                "article": "Art. 21(2)(e)",
            },
            {
                "id": "ids",
                "label": "Surveillance des flux réseau (IDS/IPS)",
                "desc": "Une solution de détection d'intrusion surveille les flux réseau en continu.",
                "article": "Art. 21(2)(b)",
            },
            {
                "id": "vpn",
                "label": "VPN sécurisé pour les accès distants",
                "desc": "Tous les accès distants passent par un VPN avec authentification forte.",
                "article": "Art. 21(2)(j)",
            },
        ],
    },
    {
        "id": "training",
        "label": "Formation & sensibilisation",
        "icon": "school",
        "items": [
            {
                "id": "awareness",
                "label": "Programme de formation cyber pour les employés",
                "desc": "Tous les employés suivent une formation annuelle de sensibilisation à la cybersécurité.",
                "article": "Art. 21(2)(g)",
                "remediation": {
                    "produit": "Sensibilisation NIS2",
                    "route": "/sensibilisation",
                },
            },
            {
                "id": "phishing_sim",
                "label": "Exercices de phishing simulé",
                "desc": "Des campagnes de phishing simulé sont menées régulièrement pour évaluer la vigilance.",
                "article": "Art. 21(2)(g)",
                "remediation": {
                    "produit": "Simulation de phishing",
                    "route": "/simulation-phishing",
                },
            },
            {
                "id": "it_training",
                "label": "Formation spécifique pour l'équipe IT/sécurité",
                "desc": "L'équipe technique reçoit des formations adaptées aux menaces actuelles.",
                "article": "Art. 21(2)(g)",
                "remediation": {
                    "produit": "Sensibilisation NIS2 — parcours Équipes techniques",
                    "route": "/sensibilisation",
                },
            },
        ],
    },
    {
        "id": "compliance",
        "label": "Enregistrement & conformité",
        "icon": "verified",
        "items": [
            {
                "id": "anssi_registration",
                "label": "Enregistrement sur le portail ANSSI",
                "desc": "L'entité est enregistrée sur monespacenis2.anssi.fr (obligatoire pour les entités concernées).",
                "article": "Art. 3 et 27",
            },
            {
                "id": "annual_audit",
                "label": "Audit de conformité annuel",
                "desc": "Un audit interne ou externe de conformité NIS2 est réalisé chaque année.",
                "article": "Art. 21(2)(f)",
            },
        ],
    },
]

# Pre-compute flat item list for validation
ALL_ITEM_IDS = {item["id"] for cat in NIS2_CATEGORIES for item in cat["items"]}
