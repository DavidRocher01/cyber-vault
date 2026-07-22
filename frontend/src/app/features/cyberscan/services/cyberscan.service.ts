/**
 * Types partagés du domaine cyberscan (anciennement portés par le
 * god-service CyberscanService, désormais éclaté en services par domaine :
 * BillingService, SiteApiService, ScanApiService, UrlScanApiService,
 * CodeScanApiService, NotificationApiService, PublicScanApiService,
 * ComplianceApiService, InvoiceApiService).
 */

export interface Plan {
  id: number;
  name: string;
  display_name: string;
  price_eur: number;
  max_sites: number;
  scan_interval_days: number;
  tier_level: number;
  stripe_price_id: string;
}

export interface Subscription {
  id: number;
  plan_id: number;
  status: string;
  current_period_start: string;
  current_period_end: string;
  plan: Plan;
  extra_sites: number;
}

export interface CheckoutSession {
  checkout_url: string;
}

export interface Site {
  id: number;
  url: string;
  name: string;
  is_active: boolean;
  created_at: string;
}

export interface SiteCreate {
  url: string;
  name: string;
}

export interface SiteDomainStatus {
  domain: string;
  verified: boolean;
}

export interface SiteDomainVerify {
  domain: string;
  verified: boolean;
  verification_token: string;
  dns_record_name: string;
  dns_record_type: string;
  dns_record_value: string;
  instructions: string;
}

export interface Scan {
  id: number;
  site_id: number;
  status: string;
  overall_status: string | null;
  pdf_path: string | null;
  results_json: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
}

export interface PaginatedScans {
  items: Scan[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface UrlScan {
  id: number;
  user_id: number;
  url: string;
  status: string;
  verdict: 'safe' | 'suspicious' | 'malicious' | null;
  threat_type: string | null;
  threat_score: number | null;
  screenshot_path: string | null;
  results_json: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface PaginatedUrlScans {
  items: UrlScan[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface CodeScan {
  id: number;
  user_id: number;
  repo_url: string;
  repo_name: string | null;
  status: string;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  results_json: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface PaginatedCodeScans {
  items: CodeScan[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface FindingStatus {
  module_key: string;
  status: 'todo' | 'in_progress' | 'resolved' | 'accepted_risk';
  note: string | null;
  updated_at: string;
}

export interface AppNotification {
  id: number;
  type: string;
  title: string;
  body: string | null;
  link: string | null;
  read: boolean;
  created_at: string;
}

export interface NotificationList {
  items: AppNotification[];
  unread_count: number;
}

export interface PublicScanResult {
  token: string;
  status: string;
  overall_status: string | null;
  results_json: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface Invoice {
  id: number;
  invoice_number: string;
  type: 'subscription' | 'audit';
  client_name: string;
  client_email: string;
  client_address: string | null;
  description: string;
  amount_cents: number;
  amount_eur: number;
  status: string;
  issue_date: string;
  created_at: string;
}

export interface PaginatedInvoices {
  items: Invoice[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface SubdomainEntry {
  subdomain: string;
  ip: string;
}

export interface SubdomainResult {
  site_url: string;
  subdomains: SubdomainEntry[];
  zone_transfer: { vulnerable: boolean; nameservers: string[]; records_found: string[] } | null;
  total_found: number;
  scan_date: string | null;
}

/** Réponse des endpoints d'auto-évaluation de conformité (NIS2 / ISO 27001). */
export interface ComplianceAssessment {
  items: Record<string, string>;
  score: number;
  updated_at: string | null;
  categories?: unknown[];
}
