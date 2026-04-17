import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
    standalone: true,
    selector: 'app-mentions-legales',
    imports: [RouterLink, MatIconModule, NavButtonsComponent],
    templateUrl: './mentions-legales.component.html'
})
export class MentionsLegalesComponent {}
