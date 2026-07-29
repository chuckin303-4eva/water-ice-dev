export interface LocationSummary {
  id: string
  address: string
  latitude: number
  longitude: number
  status: string
}

export interface LocationDetail extends LocationSummary {
  state_code: string
  county_name: string
  city_name: string
  zip_code: string
  serves_ice: boolean
  serves_water: boolean
  machine_type: string | null
  is_inside: boolean | null
  property_owner_name: string | null
  property_owner_phone: string | null
  property_management_company: string | null
  property_management_contact_name: string | null
  property_management_contact_phone: string | null
  primary_contact_name: string | null
  primary_contact_phone: string | null
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

export interface CreateLocationInput {
  address?: string
  latitude?: number
  longitude?: number
}

export interface CallNote {
  id: number
  note_text: string
  call_date: string
  follow_up_at: string | null
  created_by: number
}
