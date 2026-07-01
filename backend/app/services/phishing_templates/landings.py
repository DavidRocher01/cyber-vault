"""Pages atterrissage + donnees sensibilisation (constantes)."""

_DEFAULT_SCENARIO_KEY = "o365-credentials"


_SCENARIO_LANDING: dict[str, str] = {
    "o365-credentials": "microsoft",
    "bank-phishing": "bank",
    "it-password": "it",
    "vpn-update": "it",
    "invoice-pdf": "docusign",
    "parcel-tracking": "parcel",
    "prize": "prize",
    "fake-invoice": "payment",
    "hr-document": "hr",
    "ceo-fraud": "ceo",
}


_LANDING_MICROSOFT = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Se connecter — Microsoft</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{background:#f2f2f2;font-family:'Segoe UI',Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}.w{background:#fff;width:440px;padding:44px;box-shadow:0 2px 8px rgba(0,0,0,.2)}h1{font-size:24px;font-weight:600;color:#1b1b1b;margin:20px 0 16px}input{width:100%;border:1px solid #666;padding:6px 10px;font-size:15px;height:38px;margin-bottom:12px;outline:none;font-family:inherit}input:focus{border-color:#0078d4;box-shadow:0 0 0 1px #0078d4}.btn{width:100%;background:#0078d4;color:#fff;border:none;height:38px;font-size:15px;cursor:pointer}.btn:hover{background:#106ebe}.lnk{margin-top:12px;font-size:13px}.lnk a{color:#0078d4;text-decoration:none}.ft{margin-top:32px;font-size:11px;color:#666;display:flex;gap:16px}.ft a{color:#666;text-decoration:none}</style></head>
<body><div class="w">
<svg width="108" height="24" viewBox="0 0 120 24" xmlns="http://www.w3.org/2000/svg"><rect width="10.5" height="10.5" fill="#F35325"/><rect x="12" width="10.5" height="10.5" fill="#81BC06"/><rect y="12" width="10.5" height="10.5" fill="#05A6F0"/><rect x="12" y="12" width="10.5" height="10.5" fill="#FFBA08"/><text x="28" y="18" font-family="Segoe UI,Arial" font-size="18" font-weight="300" fill="#1b1b1b">Microsoft</text></svg>
<h1>Se connecter</h1>
<form method="POST" action="ACTION_URL">
<input type="email" name="username" placeholder="Adresse e-mail, téléphone ou Skype" autocomplete="email">
<input type="password" name="password" placeholder="Mot de passe" autocomplete="current-password">
<button type="submit" class="btn">Se connecter</button></form>
<div class="lnk"><a href="#">Mot de passe oublié ?</a></div>
<div class="ft"><a href="#">Conditions d'utilisation</a><a href="#">Confidentialité</a></div>
</div></body></html>"""


_LANDING_BANK = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Espace Client Sécurisé</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{background:#0d1b3e;font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}.card{background:#fff;width:400px;border-radius:4px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.4)}.hd{background:#0d1b3e;padding:24px;text-align:center;border-bottom:4px solid #c9a227}.hd p{color:#c9a227;font-size:18px;font-weight:700;letter-spacing:1px}.hd span{color:#fff;font-size:12px}.bd{padding:32px 28px}.ico{text-align:center;font-size:40px;margin-bottom:16px}h2{font-size:16px;color:#0d1b3e;text-align:center;margin-bottom:24px}label{display:block;font-size:12px;font-weight:700;color:#555;letter-spacing:.5px;margin-bottom:4px}input{width:100%;border:1px solid #ccc;padding:10px 12px;font-size:14px;margin-bottom:16px;border-radius:2px;outline:none}input:focus{border-color:#0d1b3e}.btn{width:100%;background:#0d1b3e;color:#fff;border:none;padding:12px;font-size:14px;font-weight:700;cursor:pointer;letter-spacing:.5px}.ft{padding:14px 28px;background:#f5f5f5;text-align:center;font-size:11px;color:#888;border-top:1px solid #eee}</style></head>
<body><div class="card"><div class="hd"><p>&#127974; ESPACE CLIENT</p><span>Connexion sécurisée — Authentification forte</span></div>
<div class="bd"><div class="ico">&#128274;</div><h2>Identifiez-vous pour sécuriser votre compte</h2>
<form method="POST" action="ACTION_URL">
<label>IDENTIFIANT CLIENT</label><input type="text" name="username" placeholder="N° client ou adresse e-mail" autocomplete="username">
<label>MOT DE PASSE</label><input type="password" name="password" placeholder="••••••••" autocomplete="current-password">
<button type="submit" class="btn">ACCÉDER À MON ESPACE</button></form></div>
<div class="ft">&#128274; Connexion chiffrée SSL/TLS — Données sécurisées</div></div></body></html>"""


_LANDING_IT = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Portail de Sécurité IT</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{background:#1e2a3a;font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}.card{background:#fff;width:420px;border-radius:6px;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,.4)}.hd{background:#1565c0;padding:18px 24px}.hd span{color:#fff;font-size:16px;font-weight:700}.alert{background:#fff3e0;border-left:4px solid #f57c00;padding:12px 16px;margin:20px 20px 0;font-size:13px;color:#e65100}.bd{padding:20px 24px}label{display:block;font-size:12px;font-weight:700;color:#555;margin-bottom:4px;margin-top:12px}input{width:100%;border:1px solid #ccc;padding:9px 12px;font-size:14px;border-radius:3px;outline:none}input:focus{border-color:#1565c0;box-shadow:0 0 0 2px rgba(21,101,192,.2)}.btn{width:100%;background:#1565c0;color:#fff;border:none;padding:12px;font-size:14px;font-weight:600;cursor:pointer;border-radius:3px;margin-top:20px}.ft{background:#f5f5f5;padding:12px 24px;font-size:11px;color:#888;border-top:1px solid #eee}</style></head>
<body><div class="card"><div class="hd"><span>&#128187; Portail SSO — Direction des Systèmes d'Information</span></div>
<div class="alert">&#9888;&#65039; Votre session a expiré. Veuillez vous reconnecter pour continuer.</div>
<div class="bd"><form method="POST" action="ACTION_URL">
<label>IDENTIFIANT RÉSEAU</label><input type="text" name="username" placeholder="prenom.nom" autocomplete="username">
<label>MOT DE PASSE ACTUEL</label><input type="password" name="password" placeholder="••••••••" autocomplete="current-password">
<button type="submit" class="btn">Se connecter</button></form></div>
<div class="ft">Portail DSI — Connexion sécurisée LDAP/AD · v3.4.1</div></div></body></html>"""


_LANDING_DOCUSIGN = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DocuSign — Signer le document</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{background:#f2f2f2;font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}.card{background:#fff;width:440px;border-radius:4px;box-shadow:0 2px 12px rgba(0,0,0,.15);overflow:hidden}.hd{background:#f5a81c;padding:16px 28px}.logo{font-size:22px;font-weight:900;color:#fff;letter-spacing:-.5px}.doc{background:#fafafa;border:1px solid #e0e0e0;margin:20px 28px 0;padding:14px;border-radius:4px;font-size:13px}.doc .from{color:#555;margin-bottom:4px}.doc .name{font-weight:700;color:#333;font-size:14px}.bd{padding:20px 28px 28px}h2{font-size:15px;color:#333;margin-bottom:16px}label{display:block;font-size:12px;font-weight:700;color:#555;margin-bottom:4px;margin-top:12px}input{width:100%;border:1px solid #ccc;padding:9px 12px;font-size:14px;border-radius:3px;outline:none}input:focus{border-color:#f5a81c}.btn{width:100%;background:#f5a81c;color:#fff;border:none;padding:12px;font-size:15px;font-weight:700;cursor:pointer;border-radius:3px;margin-top:20px}.ft{padding:12px 28px;border-top:1px solid #eee;font-size:11px;color:#999;text-align:center}</style></head>
<body><div class="card"><div class="hd"><div class="logo">DocuSign</div></div>
<div class="doc"><p class="from">Document envoyé par : Service Administratif</p><p class="name">&#128196; Document en attente de signature</p></div>
<div class="bd"><h2>Connectez-vous pour accéder au document</h2>
<form method="POST" action="ACTION_URL">
<label>E-MAIL</label><input type="email" name="username" placeholder="prenom.nom@entreprise.com" autocomplete="email">
<label>MOT DE PASSE</label><input type="password" name="password" placeholder="••••••••" autocomplete="current-password">
<button type="submit" class="btn">&#9998; Accéder au document</button></form></div>
<div class="ft">DocuSign — Signature électronique sécurisée · eIDAS conforme</div></div></body></html>"""


_LANDING_PARCEL = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Reprogrammer la livraison</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{background:#f5f5f5;font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}.card{background:#fff;width:440px;border-radius:6px;box-shadow:0 2px 12px rgba(0,0,0,.15);overflow:hidden}.hd{background:#e65100;padding:16px 28px}.hd h1{color:#fff;font-size:18px;font-weight:700}.st{background:#fff3e0;padding:12px 28px;border-bottom:1px solid #ffe0b2;font-size:13px;color:#e65100}.bd{padding:24px 28px}label{display:block;font-size:12px;font-weight:700;color:#555;margin-bottom:4px;margin-top:14px}input{width:100%;border:1px solid #ccc;padding:9px 12px;font-size:14px;border-radius:3px;outline:none}input:focus{border-color:#e65100}.row{display:flex;gap:12px}.row>div{flex:1}.amt{background:#e65100;color:#fff;text-align:center;padding:10px;border-radius:3px;font-size:16px;font-weight:700;margin:20px 0}.btn{width:100%;background:#e65100;color:#fff;border:none;padding:12px;font-size:15px;font-weight:700;cursor:pointer;border-radius:3px}.ft{padding:12px 28px;background:#f9f9f9;border-top:1px solid #eee;font-size:11px;color:#888;text-align:center}</style></head>
<body><div class="card"><div class="hd"><h1>&#128230; Reprogrammer la livraison</h1></div>
<div class="st">&#9888;&#65039; Votre colis est en attente — frais de réexpédition à régler</div>
<div class="bd"><form method="POST" action="ACTION_URL">
<label>NOM SUR LA CARTE</label><input type="text" name="cardholder" placeholder="JEAN DUPONT">
<label>NUMÉRO DE CARTE</label><input type="text" name="card_number" placeholder="•••• •••• •••• ••••" maxlength="19">
<div class="row"><div><label>EXPIRATION</label><input type="text" name="expiry" placeholder="MM/AA" maxlength="5"></div><div><label>CVV</label><input type="text" name="cvv" placeholder="•••" maxlength="3"></div></div>
<div class="amt">&#128179; À payer : 2,50 €</div>
<button type="submit" class="btn">Confirmer le paiement</button></form></div>
<div class="ft">&#128274; Paiement sécurisé 3D Secure · SSL/TLS</div></div></body></html>"""


_LANDING_PRIZE = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Réclamer mon lot</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{background:linear-gradient(135deg,#1b5e20,#2e7d32);font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}.card{background:#fff;width:440px;border-radius:8px;box-shadow:0 8px 32px rgba(0,0,0,.3);overflow:hidden}.hd{background:#f9a825;padding:24px;text-align:center}.hd h1{font-size:22px;color:#fff;font-weight:700}.hd .prize{font-size:36px;font-weight:900;color:#fff;margin-top:8px}.bd{padding:28px}p{font-size:14px;color:#555;margin-bottom:20px;line-height:1.5}label{display:block;font-size:12px;font-weight:700;color:#555;margin-bottom:4px;margin-top:12px}input{width:100%;border:1px solid #ccc;padding:9px 12px;font-size:14px;border-radius:3px;outline:none}input:focus{border-color:#f9a825}.btn{width:100%;background:#f9a825;color:#fff;border:none;padding:13px;font-size:15px;font-weight:700;cursor:pointer;border-radius:4px;margin-top:20px}.exp{font-size:12px;color:#e65100;text-align:center;margin-top:12px;font-weight:600}</style></head>
<body><div class="card"><div class="hd"><h1>&#127873; Félicitations !</h1><div class="prize">Carte cadeau Amazon</div></div>
<div class="bd"><p>Pour recevoir votre lot, confirmez vos coordonnées afin que nous puissions vous envoyer votre carte cadeau.</p>
<form method="POST" action="ACTION_URL">
<label>NOM COMPLET</label><input type="text" name="full_name" placeholder="Jean Dupont" autocomplete="name">
<label>ADRESSE E-MAIL</label><input type="email" name="username" placeholder="jean.dupont@entreprise.com" autocomplete="email">
<label>MOT DE PASSE (vérification d'identité)</label><input type="password" name="password" placeholder="••••••••" autocomplete="current-password">
<button type="submit" class="btn">&#127881; Réclamer mon lot</button></form>
<p class="exp">&#9200; Offre expire dans : 47h 23min</p></div></div></body></html>"""


_LANDING_PAYMENT = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Portail de paiement</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{background:#f5f5f5;font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}.card{background:#fff;width:440px;border-radius:6px;box-shadow:0 2px 12px rgba(0,0,0,.15);overflow:hidden}.hd{background:#1565c0;padding:16px 28px}.hd h1{color:#fff;font-size:17px;font-weight:700}.inv{margin:20px 28px 0;padding:16px;background:#e3f2fd;border-radius:4px;border:1px solid #bbdefb}.inv .ref{font-size:12px;color:#555;margin-bottom:4px}.inv .amt{font-size:28px;font-weight:700;color:#1565c0}.inv .st{font-size:12px;color:#e53935;font-weight:600;margin-top:4px}.bd{padding:20px 28px}h2{font-size:14px;color:#333;margin-bottom:14px}label{display:block;font-size:12px;font-weight:700;color:#555;margin-bottom:4px;margin-top:12px}input{width:100%;border:1px solid #ccc;padding:9px 12px;font-size:14px;border-radius:3px;outline:none}input:focus{border-color:#1565c0}.row{display:flex;gap:12px}.row>div{flex:1}.btn{width:100%;background:#1565c0;color:#fff;border:none;padding:12px;font-size:15px;font-weight:600;cursor:pointer;border-radius:3px;margin-top:20px}.ft{padding:12px 28px;border-top:1px solid #eee;font-size:11px;color:#888;text-align:center}</style></head>
<body><div class="card"><div class="hd"><h1>&#128179; Portail de Paiement Sécurisé</h1></div>
<div class="inv"><div class="ref">Facture en attente de règlement</div><div class="amt">En attente</div><div class="st">&#9888;&#65039; IMPAYÉE — Pénalités de retard en cours</div></div>
<div class="bd"><h2>Règlement par carte bancaire</h2>
<form method="POST" action="ACTION_URL">
<label>NOM SUR LA CARTE</label><input type="text" name="cardholder" placeholder="NOM PRÉNOM">
<label>NUMÉRO DE CARTE</label><input type="text" name="card_number" placeholder="•••• •••• •••• ••••" maxlength="19">
<div class="row"><div><label>EXPIRATION</label><input type="text" name="expiry" placeholder="MM/AA" maxlength="5"></div><div><label>CVV</label><input type="text" name="cvv" placeholder="•••" maxlength="3"></div></div>
<button type="submit" class="btn">Payer maintenant</button></form></div>
<div class="ft">&#128274; Paiement 3D Secure — Données chiffrées SSL/TLS</div></div></body></html>"""


_LANDING_HR = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Portail RH — Document confidentiel</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{background:#eceff1;font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}.card{background:#fff;width:420px;border-radius:6px;box-shadow:0 2px 12px rgba(0,0,0,.12);overflow:hidden}.hd{background:#37474f;padding:18px 28px}.hd h1{color:#fff;font-size:16px;font-weight:700}.prev{margin:20px 28px 0;border:1px solid #e0e0e0;border-radius:4px;overflow:hidden}.prev-hd{background:#37474f;padding:10px 14px;color:#fff;font-size:12px;font-weight:700;letter-spacing:1px}.prev-bd{padding:16px;background:#fafafa;font-size:13px;color:#777;text-align:center;position:relative}.blur{filter:blur(4px);user-select:none;line-height:1.8}.ov{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:13px;color:#37474f;font-weight:700;background:rgba(255,255,255,.7)}.bd{padding:20px 28px}label{display:block;font-size:12px;font-weight:700;color:#555;margin-bottom:4px;margin-top:12px}input{width:100%;border:1px solid #ccc;padding:9px 12px;font-size:14px;border-radius:3px;outline:none}input:focus{border-color:#37474f}.btn{width:100%;background:#37474f;color:#fff;border:none;padding:12px;font-size:14px;font-weight:600;cursor:pointer;border-radius:3px;margin-top:20px}.ft{padding:12px 28px;background:#f5f5f5;border-top:1px solid #eee;font-size:11px;color:#888;text-align:center}</style></head>
<body><div class="card"><div class="hd"><h1>&#128101; Portail RH — Document Confidentiel</h1></div>
<div class="prev"><div class="prev-hd">&#128274; GRILLE DE RÉMUNÉRATION — CONFIDENTIEL</div>
<div class="prev-bd"><div class="blur">Niveau 1 — 28 000 € — 31 000 €<br>Niveau 2 — 34 000 € — 38 000 €<br>Niveau 3 — 42 000 € — 48 000 €<br>Augmentation moyenne : +3.4%</div>
<div class="ov">&#128274; Authentification requise</div></div></div>
<div class="bd"><form method="POST" action="ACTION_URL">
<label>IDENTIFIANT</label><input type="text" name="username" placeholder="prenom.nom" autocomplete="username">
<label>MOT DE PASSE</label><input type="password" name="password" placeholder="••••••••" autocomplete="current-password">
<button type="submit" class="btn">&#128275; Accéder au document</button></form></div>
<div class="ft">Document confidentiel — accès restreint au personnel autorisé</div></div></body></html>"""


_LANDING_CEO = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Confirmation de disponibilité</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{background:#f5f5f5;font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}.card{background:#fff;width:420px;border-radius:6px;box-shadow:0 2px 12px rgba(0,0,0,.12);overflow:hidden}.hd{background:#1a73e8;padding:18px 28px}.hd h1{color:#fff;font-size:16px;font-weight:600}.bd{padding:28px}.ctx{background:#e8f0fe;border-radius:4px;padding:14px 16px;font-size:13px;color:#1a73e8;margin-bottom:20px;line-height:1.5}label{display:block;font-size:12px;font-weight:700;color:#555;margin-bottom:4px;margin-top:14px}input[type=text],input[type=password]{width:100%;border:1px solid #ccc;padding:9px 12px;font-size:14px;border-radius:3px;outline:none}input:focus{border-color:#1a73e8}.rg{display:flex;gap:16px;margin-top:6px}.rg label{display:flex;align-items:center;gap:6px;font-size:14px;font-weight:400;cursor:pointer;margin-top:0}.btn{width:100%;background:#1a73e8;color:#fff;border:none;padding:12px;font-size:14px;font-weight:600;cursor:pointer;border-radius:3px;margin-top:24px}.ft{padding:12px 28px;border-top:1px solid #eee;font-size:11px;color:#888}</style></head>
<body><div class="card"><div class="hd"><h1>&#128203; Confirmation de disponibilité</h1></div>
<div class="bd"><div class="ctx">&#128204; Message de la Direction Générale — Opération confidentielle. Votre confirmation est requise avant 17h.</div>
<form method="POST" action="ACTION_URL">
<label>VOTRE NOM</label><input type="text" name="full_name" placeholder="Prénom Nom" autocomplete="name">
<label>MOT DE PASSE (authentification)</label><input type="password" name="password" placeholder="••••••••" autocomplete="current-password">
<label>DISPONIBILITÉ</label><div class="rg"><label><input type="radio" name="available" value="yes"> Disponible</label><label><input type="radio" name="available" value="no"> Non disponible</label></div>
<button type="submit" class="btn">Confirmer</button></form></div>
<div class="ft">Communication interne confidentielle — ne pas transférer</div></div></body></html>"""


_LANDING_TEMPLATES: dict[str, str] = {
    "microsoft": _LANDING_MICROSOFT,
    "bank": _LANDING_BANK,
    "it": _LANDING_IT,
    "docusign": _LANDING_DOCUSIGN,
    "parcel": _LANDING_PARCEL,
    "prize": _LANDING_PRIZE,
    "payment": _LANDING_PAYMENT,
    "hr": _LANDING_HR,
    "ceo": _LANDING_CEO,
}


_SCENARIO_AWARENESS: dict[str, dict] = {
    "ceo-fraud": {
        "label": "une fraude au Président",
        "icon": "🏦",
        "red_flags": [
            "La demande était urgente et confidentielle — deux leviers classiques de manipulation",
            "Le message vous demandait d'agir sans passer par les procédures habituelles",
            "Aucun virement ne devrait être effectué sans double validation orale en interne",
        ],
    },
    "o365-credentials": {
        "label": "un faux email Microsoft 365",
        "icon": "🔒",
        "red_flags": [
            "L'URL du lien n'était pas login.microsoftonline.com",
            "Microsoft n'envoie jamais d'alertes vous demandant de cliquer sur un lien par email",
            "La localisation distante et l'urgence étaient créées artificiellement",
        ],
    },
    "fake-invoice": {
        "label": "une fausse relance comptable",
        "icon": "📄",
        "red_flags": [
            "Le lien pointait vers un portail de paiement externe non vérifié",
            "Toute demande de paiement doit être confirmée par téléphone auprès du fournisseur",
            "L'urgence (48h, pénalités) est une technique de pression courante",
        ],
    },
    "bank-phishing": {
        "label": "une fausse alerte bancaire",
        "icon": "🏛️",
        "red_flags": [
            "Votre banque ne vous demandera jamais vos identifiants via un lien email",
            "L'URL de la page de connexion n'était pas celle de votre banque officielle",
            "Le compte à rebours (2 heures) est un mécanisme de pression pour vous faire agir vite",
        ],
    },
    "parcel-tracking": {
        "label": "un faux avis de livraison",
        "icon": "📦",
        "red_flags": [
            "Les transporteurs ne demandent jamais de coordonnées bancaires via un lien email",
            "L'URL du formulaire n'était pas le site officiel du transporteur",
            "En cas de doute, suivez votre colis directement sur le site officiel du transporteur",
        ],
    },
    "it-password": {
        "label": "un faux email DSI",
        "icon": "💻",
        "red_flags": [
            "La DSI communique les renouvellements de mot de passe via le portail officiel, pas par email",
            "L'URL du portail de connexion était différente du portail DSI habituel",
            "En cas de doute, appelez directement le helpdesk IT pour confirmer",
        ],
    },
    "prize": {
        "label": "une fausse notification RH",
        "icon": "🎁",
        "red_flags": [
            "Le CE n'organise pas de tirages au sort distribués par email avec un mot de passe à entrer",
            "Demander votre mot de passe professionnel pour réclamer un lot est une arnaque classique",
            "La curiosité et l'appât du gain sont délibérément exploités pour vous faire baisser la garde",
        ],
    },
    "invoice-pdf": {
        "label": "une fausse demande de signature électronique",
        "icon": "✍️",
        "red_flags": [
            "DocuSign ne vous envoie pas de lien vous demandant votre mot de passe Microsoft",
            "Vérifiez toujours l'adresse réelle de l'expéditeur (pas seulement le nom affiché)",
            "Ouvrez les documents à signer directement depuis le portail officiel docusign.com",
        ],
    },
    "vpn-update": {
        "label": "une fausse alerte de sécurité VPN",
        "icon": "🔒",
        "red_flags": [
            "Les mises à jour VPN ne s'installent jamais depuis un lien dans un email",
            "Téléchargez les mises à jour uniquement depuis le portail officiel de la DSI",
            "CVE + CVSS élevé + urgence = technique de manipulation très utilisée en phishing",
        ],
    },
    "hr-document": {
        "label": "un faux document RH confidentiel",
        "icon": "📊",
        "red_flags": [
            "La DRH ne diffuse pas la grille des salaires via un lien email avec authentification",
            "L'accès à un document 'confidentiel' via un lien email est un piège classique",
            "La curiosité (salaires des collègues) est délibérément exploitée pour vous faire cliquer",
        ],
    },
    "teams-message": {
        "label": "une fausse notification Microsoft Teams",
        "icon": "💬",
        "red_flags": [
            "Microsoft Teams n'envoie pas de liens de connexion par email pour accéder à un message",
            "L'URL de la page de connexion n'était pas login.microsoftonline.com",
            "Les pièces jointes Teams s'ouvrent directement dans l'application, pas via un navigateur",
        ],
    },
    "sharepoint-share": {
        "label": "un faux partage SharePoint",
        "icon": "📁",
        "red_flags": [
            "L'URL de connexion n'était pas login.microsoftonline.com",
            "SharePoint ne vous demande pas de vous reconnecter via un email pour accéder à un partage",
            "Un nom d'expéditeur peut être usurpé facilement — vérifiez toujours l'adresse réelle",
        ],
    },
    "it-ticket": {
        "label": "un faux ticket helpdesk DSI",
        "icon": "🎧",
        "red_flags": [
            "Le helpdesk DSI n'assigne pas de tickets urgents avec un lien SSO dans un email",
            "Vérifiez dans le portail helpdesk officiel si le ticket existe réellement",
            "La haute priorité et le délai 'avant fin de journée' créent une pression artificielle",
        ],
    },
}


_PIXEL_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"
    b"!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
    b"\x00\x00\x02\x02D\x01\x00;"
)
