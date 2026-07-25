import { roleProbeGuard } from './role-probe.guard';

/** Protège l'espace consultant RSSI : seul un compte `is_rssi_consultant` passe. */
export const rssiGuard = roleProbeGuard(
  '/api/v1/users/me',
  body => !!(body as { is_rssi_consultant?: boolean }).is_rssi_consultant
);
