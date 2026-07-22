import { roleProbeGuard } from './role-probe.guard';

/**
 * Protège l'espace client RSSI : autorise seulement un compte rattaché à un
 * RssiClient. On s'appuie sur /portal/me (200 => client lié, 403 => non).
 */
export const rssiClientGuard = roleProbeGuard('/api/v1/portal/me', () => true);
