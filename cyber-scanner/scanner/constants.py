"""
Shared constants for the Cyber-Scanner modules.
Import from here instead of re-declaring in each module.
"""

PORT_NAMES: dict[int, str] = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    3306: "MySQL",
    5432: "PostgreSQL",
    6379: "Redis",
    27017: "MongoDB",
    8080: "HTTP-Alt",
    8443: "HTTPS-Alt",
}

SENSITIVE_PORTS: list[int] = [21, 22, 23, 25, 3306, 5432, 6379, 27017, 8080, 8443]
CRITICAL_PORTS: set[int] = {5432, 3306, 6379, 27017, 23, 21}

SECURITY_HEADERS: list[str] = [
    "Content-Security-Policy",
    "X-Frame-Options",
    "X-Content-Type-Options",
    "Strict-Transport-Security",
    "Referrer-Policy",
    "Permissions-Policy",
]

HEADER_RECOMMENDATIONS: dict[str, str] = {
    "Content-Security-Policy": "Ajouter Content-Security-Policy pour prévenir les attaques XSS",
    "X-Frame-Options": "Ajouter X-Frame-Options pour bloquer le clickjacking",
    "X-Content-Type-Options": "Ajouter X-Content-Type-Options: nosniff pour éviter le MIME-sniffing",
    "Strict-Transport-Security": "Ajouter Strict-Transport-Security (HSTS) pour forcer HTTPS",
    "Referrer-Policy": "Ajouter Referrer-Policy pour contrôler les informations de référent",
    "Permissions-Policy": "Ajouter Permissions-Policy pour restreindre les API du navigateur",
}
