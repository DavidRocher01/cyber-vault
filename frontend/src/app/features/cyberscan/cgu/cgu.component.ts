import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-cgu',
  standalone: true,
  imports: [RouterLink, MatIconModule],
  templateUrl: './cgu.component.html',
})
export class CguComponent {}
