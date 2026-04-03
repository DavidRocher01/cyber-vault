import { Injectable, signal } from '@angular/core';

export type Lang = 'fr' | 'en';

const TRANSLATIONS: Record<Lang, Record<string, string>> = {
  fr: {
    'nav.home': 'Accueil',
    'nav.dashboard': 'Dashboard',
    'nav.logout': 'Déconnexion',
    'nav.profile': 'Profil',
    'hero.title': 'Scannez votre site web,',
    'hero.subtitle': 'protégez votre réputation',
    'hero.cta': 'Commencer gratuitement',
    'hero.pricing': 'Voir les tarifs',
    'pricing.title': 'Tarifs simples et transparents',
    'pricing.subtitle': 'Choisissez le plan adapté à vos besoins',
    'pricing.monthly': '/mois',
    'pricing.choose': 'Choisir',
    'faq.title': 'Questions fréquentes',
    'dashboard.sites': 'Mes sites',
    'dashboard.add': 'Ajouter un site',
    'dashboard.scan': 'Lancer un scan',
    'dashboard.noSites': 'Aucun site configuré',
    'scan.all': 'Tous',
    'scan.done': 'Terminés',
    'scan.running': 'En cours',
    'scan.error': 'Erreurs',
    'plan.manage': 'Gérer l\'abonnement',
  },
  en: {
    'nav.home': 'Home',
    'nav.dashboard': 'Dashboard',
    'nav.logout': 'Logout',
    'nav.profile': 'Profile',
    'hero.title': 'Scan your website,',
    'hero.subtitle': 'protect your reputation',
    'hero.cta': 'Get started for free',
    'hero.pricing': 'View pricing',
    'pricing.title': 'Simple, transparent pricing',
    'pricing.subtitle': 'Choose the plan that fits your needs',
    'pricing.monthly': '/month',
    'pricing.choose': 'Choose',
    'faq.title': 'Frequently asked questions',
    'dashboard.sites': 'My sites',
    'dashboard.add': 'Add a site',
    'dashboard.scan': 'Run a scan',
    'dashboard.noSites': 'No site configured',
    'scan.all': 'All',
    'scan.done': 'Done',
    'scan.running': 'Running',
    'scan.error': 'Errors',
    'plan.manage': 'Manage subscription',
  },
};

@Injectable({ providedIn: 'root' })
export class I18nService {
  private readonly STORAGE_KEY = 'cs_lang';
  lang = signal<Lang>((localStorage.getItem(this.STORAGE_KEY) as Lang) ?? 'fr');

  t(key: string): string {
    return TRANSLATIONS[this.lang()][key] ?? key;
  }

  toggle() {
    const next: Lang = this.lang() === 'fr' ? 'en' : 'fr';
    this.lang.set(next);
    localStorage.setItem(this.STORAGE_KEY, next);
  }
}
