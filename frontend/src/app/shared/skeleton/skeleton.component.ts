import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-skeleton',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div [class]="'animate-pulse bg-gray-700 rounded-lg ' + cssClass" [style.height]="height" [style.width]="width"></div>
  `,
})
export class SkeletonComponent {
  @Input() height = '1rem';
  @Input() width = '100%';
  @Input() cssClass = '';
}
