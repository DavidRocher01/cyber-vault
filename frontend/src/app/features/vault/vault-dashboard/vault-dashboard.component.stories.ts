import type { Meta, StoryObj } from '@storybook/angular';
import { moduleMetadata } from '@storybook/angular';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { NgxSkeletonLoaderModule } from 'ngx-skeleton-loader';
import { LucideAngularModule, Eye, EyeOff, Copy, Trash2, Download, LogOut, Plus, Search } from 'lucide-angular';
import { VaultDashboardComponent } from './vault-dashboard.component';

const meta: Meta<VaultDashboardComponent> = {
  title: 'Features/Vault/VaultDashboard',
  component: VaultDashboardComponent,
  tags: ['autodocs'],
  decorators: [
    moduleMetadata({
      imports: [
        CommonModule,
        ReactiveFormsModule,
        MatToolbarModule,
        MatButtonModule,
        MatCardModule,
        MatFormFieldModule,
        MatInputModule,
        MatIconModule,
        MatTooltipModule,
        NgxSkeletonLoaderModule,
        LucideAngularModule.pick({ Eye, EyeOff, Copy, Trash2, Download, LogOut, Plus, Search }),
      ],
      providers: [],
    }),
  ],
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component:
          'The main vault dashboard component. Displays stored password entries and allows creating, revealing, copying, and deleting them.',
      },
    },
  },
};

export default meta;
type Story = StoryObj<VaultDashboardComponent>;

export const Default: Story = {
  name: 'Default (empty vault)',
};

export const WithForm: Story = {
  name: 'With Add-Entry Form Open',
  play: async ({ canvasElement }) => {
    const button = canvasElement.querySelector<HTMLButtonElement>(
      'button[mat-flat-button]'
    );
    button?.click();
  },
};
