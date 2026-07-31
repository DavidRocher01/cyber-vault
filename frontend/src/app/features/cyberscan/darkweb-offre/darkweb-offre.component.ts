import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { Title, Meta } from '@angular/platform-browser';

import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

/**
 * Page vitrine PUBLIQUE de l'offre Dark Web Dossier.
 *
 * Créée le 2026-07-30 : le pied de page de la landing annonçait « Dark Web
 * Dossier » mais renvoyait vers /darkweb-dossier, qui est l'application
 * (authGuard). Un visiteur tombait sur le formulaire de connexion. Cette offre
 * était la seule des six du pied de page à n'avoir aucune page publique.
 *
 * Tout le contenu ci-dessous est tiré des capacités RÉELLES du produit
 * (app/models/darkweb_dossier.py, app/services/darkweb_dossier/) et du tarif
 * inscrit dans SALES-BRIEF.md §5. Rien n'est inventé — le brief l'interdit
 * explicitement.
 */
@Component({
  standalone: true,
  selector: 'app-darkweb-offre',
  imports: [RouterLink, MatIconModule, NavButtonsComponent],
  templateUrl: './darkweb-offre.component.html',
})
export class DarkwebOffreComponent {
  private title = inject(Title);
  private meta = inject(Meta);

  constructor() {
    this.title.setTitle('Dark Web Dossier — exposition de votre domaine | Rocher Cybersécurité');
    this.meta.updateTag({
      name: 'description',
      content:
        'Découvrez quelles adresses e-mail de votre entreprise circulent dans des fuites de ' +
        'données. Score de risque, sources identifiées, rapport PDF et surveillance continue.',
    });
  }

  /** Douleurs adressées — formulées côté client, pas côté système. */
  readonly douleurs = [
    {
      icon: 'help_outline',
      text: 'Vous ignorez si les adresses de vos salariés circulent déjà dans des fuites.',
    },
    {
      icon: 'inventory_2',
      text: 'Un client ou un assureur vous demande où vous en êtes, et vous n’avez rien à montrer.',
    },
    {
      icon: 'schedule',
      text: 'Une vérification ponctuelle vieillit mal : de nouvelles fuites sortent chaque mois.',
    },
  ];

  /** Ce que le dossier contient réellement (cf. modèle DarkwebDossier). */
  readonly contenu = [
    {
      icon: 'domain',
      titre: 'Exposition du domaine',
      desc: 'Les adresses de votre domaine retrouvées dans des fuites, et le nombre d’occurrences pour chacune.',
    },
    {
      icon: 'speed',
      titre: 'Score de risque',
      desc: 'Un score de risque et un score de sévérité, pour situer l’exposition plutôt que lister des lignes.',
    },
    {
      icon: 'source',
      titre: 'Sources identifiées',
      desc: 'Les principales fuites d’où proviennent les données, pour comprendre l’origine.',
    },
    {
      icon: 'checklist',
      titre: 'Recommandations',
      desc: 'Des actions concrètes déduites de ce qui a été trouvé, pas une liste générique.',
    },
    {
      icon: 'picture_as_pdf',
      titre: 'Rapport PDF',
      desc: 'Un document présentable à votre direction, à un client ou à un auditeur.',
    },
    {
      icon: 'monitor_heart',
      titre: 'Surveillance continue',
      desc: 'Le dossier peut rester sous surveillance et être recontrôlé automatiquement.',
    },
  ];
}
