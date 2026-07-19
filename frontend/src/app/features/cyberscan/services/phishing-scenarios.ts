// Scenarios de phishing - donnees de reference (source unique).
// Auparavant definies dans le composant vitrine phishing.component.ts.

export interface PhishingScenario {
  id: string;
  name: string;
  description: string;
  difficulty: 'Facile' | 'Moyen' | 'Difficile';
  vector: string;
  icon: string;
}

export const PHISHING_SCENARIOS: PhishingScenario[] = [
  {
    id: 'ceo-fraud',
    name: 'Fraude au Président',
    description:
      'Email usurpant le dirigeant pour demander un virement urgent ou des informations confidentielles.',
    difficulty: 'Difficile',
    vector: 'Email',
    icon: 'account_balance',
  },
  {
    id: 'fake-invoice',
    name: 'Fausse Facture Fournisseur',
    description:
      'Notification de facture impayée avec lien vers un portail de paiement frauduleux.',
    difficulty: 'Moyen',
    vector: 'Email',
    icon: 'receipt_long',
  },
  {
    id: 'o365-credentials',
    name: 'Credentials Office 365',
    description:
      'Page de connexion Microsoft clonée pour capturer identifiants email professionnels.',
    difficulty: 'Facile',
    vector: 'Email + Page web',
    icon: 'login',
  },
  {
    id: 'bank-phishing',
    name: 'Phishing Bancaire',
    description:
      'Alerte de sécurité bancaire demandant confirmation des coordonnées ou un code SMS.',
    difficulty: 'Facile',
    vector: 'SMS / Email',
    icon: 'credit_card',
  },
  {
    id: 'parcel-tracking',
    name: 'Colis Suspect',
    description:
      "Notification de livraison échouée avec demande de frais de réexpédition ou d'informations.",
    difficulty: 'Facile',
    vector: 'SMS',
    icon: 'local_shipping',
  },
  {
    id: 'it-password',
    name: 'Mise à Jour Mot de Passe IT',
    description:
      'Email DSI urgent demandant de changer son mot de passe via un portail interne cloné.',
    difficulty: 'Moyen',
    vector: 'Email interne',
    icon: 'lock_reset',
  },
  {
    id: 'prize',
    name: "Gain d'un Concours",
    description:
      'Notification de lot à récupérer nécessitant des informations personnelles ou bancaires.',
    difficulty: 'Facile',
    vector: 'Email',
    icon: 'emoji_events',
  },
  {
    id: 'invoice-pdf',
    name: 'PDF Malveillant',
    description:
      "Facture PDF avec macro cachée simulant l'exécution d'un ransomware (mode exercice).",
    difficulty: 'Difficile',
    vector: 'Email + Pièce jointe',
    icon: 'picture_as_pdf',
  },
  {
    id: 'vpn-update',
    name: 'Mise à Jour VPN',
    description:
      "Alerte de sécurité réseau demandant d'installer une mise à jour critique du client VPN.",
    difficulty: 'Difficile',
    vector: 'Email interne',
    icon: 'vpn_key',
  },
  {
    id: 'hr-document',
    name: 'Document RH Confidentiel',
    description:
      'Email RH avec grille de salaires ou document stratégique à télécharger après authentification.',
    difficulty: 'Moyen',
    vector: 'Email interne',
    icon: 'folder_shared',
  },
  {
    id: 'teams-message',
    name: 'Notification Teams',
    description:
      'Email de notification Microsoft Teams avec pièce jointe, redirigeant vers une page de connexion Microsoft.',
    difficulty: 'Moyen',
    vector: 'Email + Page web',
    icon: 'chat',
  },
  {
    id: 'sharepoint-share',
    name: 'Partage SharePoint',
    description:
      'Document partagé via Microsoft SharePoint nécessitant une authentification Microsoft pour y accéder.',
    difficulty: 'Moyen',
    vector: 'Email + Page web',
    icon: 'cloud_upload',
  },
  {
    id: 'it-ticket',
    name: 'Ticket Helpdesk IT',
    description:
      "Ticket d'assistance DSI haute priorité redigeant vers le portail SSO interne pour traitement urgent.",
    difficulty: 'Difficile',
    vector: 'Email interne',
    icon: 'support_agent',
  },
];
