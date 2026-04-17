import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
    selector: 'app-cgu',
    imports: [RouterLink, MatIconModule, NavButtonsComponent],
    templateUrl: './cgu.component.html'
})
export class CguComponent {}
