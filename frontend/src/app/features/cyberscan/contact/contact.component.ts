import { Component, inject, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Title, Meta } from '@angular/platform-browser';
import { MatIconModule } from '@angular/material/icon';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

// ⚠️ Remplacez cette URL par votre vrai lien Calendly
export const CALENDLY_URL = 'https://calendly.com/david-rocher-cyberscan/audit-decouverte';

@Component({
  standalone: true,
  selector: 'app-contact',
  imports: [RouterLink, MatIconModule, NavButtonsComponent],
  templateUrl: './contact.component.html',
})
export class ContactComponent implements OnInit {
  private titleService = inject(Title);
  private meta = inject(Meta);

  readonly calendlyUrl = CALENDLY_URL;

  ngOnInit() {
    this.titleService.setTitle('Contact — Réserver un audit cybersécurité | CyberScan');
    this.meta.updateTag({
      name: 'description',
      content: 'Prenez rendez-vous pour un audit cybersécurité. Appel découverte gratuit de 15 minutes. David Rocher — développeur full-stack et auditeur, Trévoux (01).',
    });
  }
}
