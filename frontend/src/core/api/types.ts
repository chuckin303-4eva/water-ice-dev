export interface LocationSummary {
  id: string
  address: string
  latitude: number
  longitude: number
  status: string
  opportunity_score: number | null
}

export interface LocationDetail extends LocationSummary {
  state_code: string
  county_name: string
  city_name: string
  zip_code: string
  brand_id: string | null
  brand_name: string | null
  serves_ice: boolean
  serves_water: boolean
  machine_type: string | null
  host_business_id: string | null
  host_business_name: string | null
  host_business_category: string | null
  is_inside: boolean | null
  visibility_rating: number | null
  traffic_score: number | null
  competition_score: number | null
  confidence_score: number | null
  property_owner_name: string | null
  property_owner_phone: string | null
  property_management_company: string | null
  property_management_contact_name: string | null
  property_management_contact_phone: string | null
  primary_contact_name: string | null
  primary_contact_phone: string | null
  primary_contact_email: string | null
  website: string | null
  expected_unit_size: string | null
  power_connection_location: string | null
  power_company: string | null
  power_voltage: string | null
  water_connection_location: string | null
  water_company: string | null
  sewer_connection_availability: string | null
  sewer_connection_location: string | null
  pricing_estimate_monthly: number | null
  pricing_estimate_notes: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface LocationImportRowError {
  row: number
  message: string
}

export interface LocationImportSummary {
  total_rows: number
  created: number
  queued: number
  errors: LocationImportRowError[]
}

export interface ValidationQueueItem {
  id: number
  entity_type: string
  entity_id: string | null
  proposed_changes: Record<string, unknown>
  reason: string | null
  submitted_by: number | null
  submitted_by_email: string | null
  status: string
  reviewed_by: number | null
  reviewed_at: string | null
  created_at: string
}

/** Distinguishes a real LocationDetail from a queued-for-review response
 * -- both can come back from the same create/update call depending on
 * whether the org requires review and the caller is an admin (ADR-0014).
 */
export function isPendingReview(value: unknown): value is ValidationQueueItem {
  return (
    typeof value === 'object' &&
    value !== null &&
    'entity_type' in value &&
    'proposed_changes' in value
  )
}

export interface OrganizationSettings {
  require_review_for_submissions: boolean
}

export interface LocationFilters {
  statuses?: string[]
  serves_ice?: boolean
  serves_water?: boolean
  min_opportunity_score?: number
}

export interface CompetitorFilters {
  serves_ice?: boolean
  serves_water?: boolean
  brand?: string
}

export interface CreateLocationInput {
  address?: string
  latitude?: number
  longitude?: number
  brand_id?: string
  website?: string
  primary_contact_name?: string
  primary_contact_phone?: string
  primary_contact_email?: string
}

export interface UpdateLocationInput {
  visibility_rating?: number
  traffic_score?: number
  host_business_id?: string
  brand_id?: string
}

export interface HostBusiness {
  id: string
  name: string
  category: string | null
  phone: string | null
  website: string | null
  created_at: string
  updated_at: string
}

export interface CreateHostBusinessInput {
  name: string
  category?: string
  phone?: string
  website?: string
}

export interface Brand {
  id: string
  name: string
  description: string | null
  logo_url: string | null
  created_at: string
  updated_at: string
}

export interface CreateBrandInput {
  name: string
  description?: string
  logo_url?: string
}

export interface CallNote {
  id: number
  note_text: string
  call_date: string
  follow_up_at: string | null
  created_by: number
}

export interface CompetitorSummary {
  id: string
  name: string
  address: string
  latitude: number
  longitude: number
  serves_ice: boolean
  serves_water: boolean
}

export interface CompetitorDetail extends CompetitorSummary {
  state_code: string
  county_name: string
  city_name: string
  brand: string | null
  website: string | null
  phone: string | null
  contact_name: string | null
  contact_email: string | null
  follow_up_at: string | null
  machine_type: string | null
  machine_size: string | null
  is_inside: boolean | null
  ice_price: number | null
  water_price: number | null
  price_notes: string | null
  last_observed_date: string | null
  source: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface CreateCompetitorInput {
  address?: string
  latitude?: number
  longitude?: number
  name: string
  brand?: string
  website?: string
  phone?: string
  contact_name?: string
  contact_email?: string
  follow_up_at?: string
}

export interface UpdateCompetitorInput {
  name?: string
  brand?: string
  website?: string
  phone?: string
  contact_name?: string
  contact_email?: string
  follow_up_at?: string
  serves_ice?: boolean
  serves_water?: boolean
  machine_type?: string
  machine_size?: string
  is_inside?: boolean
  ice_price?: number
  water_price?: number
  price_notes?: string
  source?: string
  notes?: string
}

export interface CompetitorCalendarLinks {
  google: string
  outlook: string
}
