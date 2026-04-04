import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-mentions-legales',
  standalone: true,
  imports: [RouterLink, MatIconModule],
  templateUrl: './mentions-legales.component.html',
})
export class MentionsLegalesComponent {}
