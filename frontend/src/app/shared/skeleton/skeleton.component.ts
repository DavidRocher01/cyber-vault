import { Component, Input } from '@angular/core';

@Component({
  standalone: true,
  selector: 'app-skeleton',
  imports: [],
  template: `
    <div
      [class]="'skeleton-shimmer rounded-lg ' + cssClass"
      [style.height]="height"
      [style.width]="width"
    ></div>
  `,
})
export class SkeletonComponent {
  @Input() height = '1rem';
  @Input() width = '100%';
  @Input() cssClass = '';
}
