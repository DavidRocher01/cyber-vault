import { Component, inject, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Title, Meta } from '@angular/platform-browser';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { CommonModule } from '@angular/common';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

export const AUDIT_OFFERS = [
  {
    name: 'Audit Flash',
    price: '290',
    duration: '½ journée',
    target: 'Sites vitrines, blogs pro, e-commerce simples',
    icon: 'flash_on',
    color: 'border-cyan-600',
    badge: 'text-cyan-300 bg-cyan-900/40',
    features: [
      'Analyse SSL/TLS complète (grade A-F)',
      'Headers HTTP de sécurité',
      'Technologies exposées + CVE',
      'Réputation IP et blacklists',
      'Configuration DNS (SPF, DKIM, DMARC)',
      'Rapport PDF 8-12 pages',
      'Plan d\'action sous 24 h',
    ],
  },
  {
    name: 'App-Check',
    price: '725',
    duration: '1,5 jour',
    target: 'SaaS, applications métier, e-commerce complexe',
    icon: 'manage_search',
    color: 'border-purple-600',
    badge: 'text-purple-300 bg-purple-900/40',
    popular: true,
    features: [
      'Tout l\'Audit Flash +',
      'Revue de code source (si accès)',
      'Tests API (SQLi, XSS, IDOR, CSRF)',
      'Gestion sessions / tokens JWT',
      'Contrôles RGPD',
      'Rapport 20-30 pages',
      'Atelier restitution 1 h',
      'Plan de remédiation chiffré',
    ],
  },
  {
    name: 'Pentest léger',
    price: '1 900',
    duration: '4 jours',
    target: 'E-commerce, données sensibles, obligations légales',
    icon: 'bug_report',
    color: 'border-red-600',
    badge: 'text-red-300 bg-red-900/40',
    features: [
      'Tout l\'App-Check +',
      'Tests d\'intrusion actifs',
      'Proof of concept d\'exploitation',
      'Escalade de privilèges',
      'Rapport technique + version dirigeant',
      'Présentation au COMEX si besoin',
    ],
  },
];

export const AUDIT_SUBSCRIPTIONS = [
  {
    name: 'Vigie',
    price: '~99',
    icon: 'visibility',
    color: 'border-gray-600',
    features: ['Scan hebdomadaire automatisé', 'Alerte immédiate nouveau risque', 'Rapport mensuel synthétique'],
  },
  {
    name: 'Sentinelle',
    price: '~199',
    icon: 'shield',
    color: 'border-cyan-600',
    popular: true,
    features: ['Scan quotidien', 'Rapport mensuel détaillé', 'Ligne directe en cas d\'incident', 'Veille CVE sur vos dépendances'],
  },
  {
    name: 'Blindage 360',
    price: '~499',
    icon: 'security',
    color: 'border-purple-600',
    features: ['Surveillance continue 24/7', 'Audit trimestriel', 'Revue de code mensuelle', 'Conseil stratégique RSSI externalisé'],
  },
];

export const AUDIT_FAQS = [
  { q: 'Combien de temps dure un audit Flash ?', a: 'Un audit Flash dure une demi-journée (environ 4 heures). Vous recevez le rapport PDF sous 24 h après la réalisation.' },
  { q: 'Mes données sont-elles protégées pendant l\'audit ?', a: 'Oui. Un accord de confidentialité (NDA) est signé avant tout accès. Aucune donnée n\'est conservée après la mission.' },
  { q: 'Dois-je être présent tout au long de l\'audit ?', a: 'Un appel de cadrage de 30 minutes suffit au départ pour définir le périmètre. Le reste est réalisé de façon autonome.' },
  { q: 'Que se passe-t-il si vous trouvez des failles critiques ?', a: 'Vous êtes alerté dans la journée, avec une description claire de la faille, son niveau de risque, et les mesures correctives à appliquer en priorité.' },
  { q: 'Proposez-vous de corriger les failles trouvées ?', a: 'La correction peut être réalisée par votre équipe grâce au plan d\'action fourni. Si vous souhaitez déléguer les corrections, un devis séparé peut être établi.' },
  { q: 'Êtes-vous couvert par une assurance professionnelle ?', a: 'Oui, l\'activité est couverte par une assurance RC Pro adaptée aux prestations de cybersécurité et d\'audit.' },
  { q: 'Est-ce compatible avec une exigence NIS2 ou ISO 27001 ?', a: 'L\'App-Check et le Pentest léger produisent des livrables compatibles avec les exigences de ces référentiels. Un accompagnement dédié est disponible.' },
];

@Component({
  standalone: true,
  selector: 'app-audit-pme',
  imports: [RouterLink, MatIconModule, MatButtonModule, CommonModule, NavButtonsComponent],
  templateUrl: './audit-pme.component.html',
})
export class AuditPmeComponent implements OnInit {
  private titleService = inject(Title);
  private meta = inject(Meta);

  openFaqIndex = signal<number | null>(null);

  readonly offers = AUDIT_OFFERS;
  readonly subscriptions = AUDIT_SUBSCRIPTIONS;
  readonly faqs = AUDIT_FAQS;

  toggleFaq(i: number) {
    this.openFaqIndex.update(v => (v === i ? null : i));
  }

  ngOnInit() {
    this.titleService.setTitle('Audit cybersécurité PME — Flash, App-Check, Pentest | CyberScan');
    this.meta.updateTag({
      name: 'description',
      content: 'Audit cybersécurité pour TPE/PME à partir de 290 € HT. Flash, App-Check, Pentest. Développeur full-stack ET auditeur : rapport PDF + plan d\'action sous 24 h. Zone Auvergne-Rhône-Alpes.',
    });
    this.meta.updateTag({ property: 'og:title', content: 'Audit cybersécurité PME — CyberScan' });
    this.meta.updateTag({ property: 'og:description', content: 'Audit de sécurité web pour TPE/PME à partir de 290 € HT. Rapport + plan d\'action concret sous 24 h.' });
    this.meta.updateTag({ name: 'robots', content: 'index, follow' });
  }
}
