import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
    selector: 'app-politique-confidentialite',
    imports: [CommonModule, RouterLink, MatIconModule, NavButtonsComponent],
    templateUrl: './politique-confidentialite.component.html'
})
export class PolitiqueConfidentialiteComponent {}
