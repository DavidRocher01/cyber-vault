import { Component, Input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { ActivityLogEntry } from '../../../services/rssi.service';

@Component({
  standalone: true,
  selector: 'app-activity-feed',
  imports: [MatIconModule],
  template: `
    <div>
      <h2 class="text-sm font-semibold text-gray-300 mb-4">Journal d'activité</h2>
      @if (entries.length === 0) {
        <div class="text-center py-12 text-gray-500 text-sm">Aucune activité enregistrée</div>
      } @else {
        <div class="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          @for (entry of entries; track entry.id) {
            <div
              class="flex items-center gap-3 px-4 py-3 border-b border-gray-800/50 last:border-0"
            >
              <mat-icon
                class="text-cyan-500/60 shrink-0"
                style="font-size: 16px; height: 16px; width: 16px"
              >
                history
              </mat-icon>
              <div class="flex-1 min-w-0">
                <span class="text-sm text-gray-200">{{ activityLabel(entry.action_type) }}</span>
                @if (entry.resource_id) {
                  <span class="text-xs text-gray-500 ml-1">#{{ entry.resource_id }}</span>
                }
              </div>
              <span class="text-xs text-gray-500 shrink-0">{{
                formatDateTime(entry.performed_at)
              }}</span>
            </div>
          }
        </div>
      }
    </div>
  `,
})
export class ActivityFeedComponent {
  @Input() entries: ActivityLogEntry[] = [];

  activityLabel(type: string): string {
    const map: Record<string, string> = {
      view_client: 'Consultation fiche client',
      view_sites: 'Consultation des sites',
      view_scans: 'Consultation des scans',
      view_findings: 'Consultation des findings',
      generate_report: 'Génération de rapport',
      send_deliverable: "Envoi d'un livrable",
      create_action: "Création d'une action",
      update_action: "Mise à jour d'une action",
      create_visit: "Planification d'une visite",
      update_visit: "Mise à jour d'une visite",
    };
    return map[type] ?? type;
  }

  formatDateTime(d: string): string {
    return new Date(d).toLocaleString('fr-FR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
}
