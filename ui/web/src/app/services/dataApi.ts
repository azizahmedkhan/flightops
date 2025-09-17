const API_BASE_URL = process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8080'

export interface Flight {
  flight_no: string
  flight_date: string
  origin: string
  destination: string
  sched_dep_time: string
  sched_arr_time: string
  status: string
  tail_number: string
}

export interface Booking {
  flight_no: string
  flight_date: string
  pnr: string
  passenger_name: string
  has_connection: string
  connecting_flight_no: string
}

export interface CrewRoster {
  flight_no: string
  flight_date: string
  crew_id: string
  crew_role: string
}

export interface CrewDetail {
  crew_id: string
  crew_name: string
  duty_start_time: string
  max_duty_hours: number
}

export interface AircraftStatus {
  tail_number: string
  current_location: string
  status: string
}

export interface Policy {
  id: number
  title: string
  content: string
  meta: any
  embedding?: number[]
}

// Generic API functions
async function apiRequest(endpoint: string, options: RequestInit = {}) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })

  if (!response.ok) {
    throw new Error(`API request failed: ${response.statusText}`)
  }

  return response.json()
}

// Flights API
export const flightsApi = {
  getAll: (): Promise<Flight[]> => apiRequest('/data/flights'),
  getById: (id: string): Promise<Flight> => apiRequest(`/data/flights/${id}`),
  create: (data: Omit<Flight, 'id'>): Promise<Flight> => 
    apiRequest('/data/flights', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<Flight>): Promise<Flight> => 
    apiRequest(`/data/flights/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id: string): Promise<void> => 
    apiRequest(`/data/flights/${id}`, { method: 'DELETE' }),
}

// Bookings API
export const bookingsApi = {
  getAll: (): Promise<Booking[]> => apiRequest('/data/bookings'),
  getById: (id: string): Promise<Booking> => apiRequest(`/data/bookings/${id}`),
  create: (data: Omit<Booking, 'id'>): Promise<Booking> => 
    apiRequest('/data/bookings', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<Booking>): Promise<Booking> => 
    apiRequest(`/data/bookings/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id: string): Promise<void> => 
    apiRequest(`/data/bookings/${id}`, { method: 'DELETE' }),
}

// Crew Roster API
export const crewRosterApi = {
  getAll: (): Promise<CrewRoster[]> => apiRequest('/data/crew_roster'),
  getById: (id: string): Promise<CrewRoster> => apiRequest(`/data/crew_roster/${id}`),
  create: (data: Omit<CrewRoster, 'id'>): Promise<CrewRoster> => 
    apiRequest('/data/crew_roster', { method: 'POST', body: JSON.stringify(data) }),
  update: (flight_no: string, crew_id: string, data: Partial<CrewRoster>): Promise<CrewRoster> => 
    apiRequest(`/data/crew_roster/${flight_no}/${crew_id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (flight_no: string, crew_id: string): Promise<void> => 
    apiRequest(`/data/crew_roster/${flight_no}/${crew_id}`, { method: 'DELETE' }),
}

// Crew Details API
export const crewDetailsApi = {
  getAll: (): Promise<CrewDetail[]> => apiRequest('/data/crew_details'),
  getById: (id: string): Promise<CrewDetail> => apiRequest(`/data/crew_details/${id}`),
  create: (data: Omit<CrewDetail, 'id'>): Promise<CrewDetail> => 
    apiRequest('/data/crew_details', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<CrewDetail>): Promise<CrewDetail> => 
    apiRequest(`/data/crew_details/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id: string): Promise<void> => 
    apiRequest(`/data/crew_details/${id}`, { method: 'DELETE' }),
}

// Aircraft Status API
export const aircraftStatusApi = {
  getAll: (): Promise<AircraftStatus[]> => apiRequest('/data/aircraft_status'),
  getById: (id: string): Promise<AircraftStatus> => apiRequest(`/data/aircraft_status/${id}`),
  create: (data: Omit<AircraftStatus, 'id'>): Promise<AircraftStatus> => 
    apiRequest('/data/aircraft_status', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<AircraftStatus>): Promise<AircraftStatus> => 
    apiRequest(`/data/aircraft_status/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id: string): Promise<void> => 
    apiRequest(`/data/aircraft_status/${id}`, { method: 'DELETE' }),
}

// Policies API
export const policiesApi = {
  getAll: (): Promise<Policy[]> => apiRequest('/data/policies'),
  getById: (id: string): Promise<Policy> => apiRequest(`/data/policies/${id}`),
  create: (data: Omit<Policy, 'id'>): Promise<Policy> => 
    apiRequest('/data/policies', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<Policy>): Promise<Policy> => 
    apiRequest(`/data/policies/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id: string): Promise<void> => 
    apiRequest(`/data/policies/${id}`, { method: 'DELETE' }),
  search: (query: string): Promise<Policy[]> => 
    apiRequest('/data/policies/search', { method: 'POST', body: JSON.stringify({ query }) }),
}

// Clear all data
export const clearAllData = (): Promise<{ ok: boolean; message: string; counts: any }> => 
  apiRequest('/data/clear', { method: 'DELETE' })

// Regenerate embeddings
export const regenerateEmbeddings = (): Promise<{ ok: boolean; message: string; updated_count: number }> => 
  apiRequest('/data/policies/regenerate-embeddings', { method: 'POST' })

// Debug policies
export const debugPolicies = (): Promise<{ total_docs: number; total_embeddings: number; docs_without_embeddings: number; docs_without_embeddings_list: any[]; embedding_dimensions: number[] }> => 
  apiRequest('/data/policies/debug')

// Force regenerate embeddings
export const forceRegenerateEmbeddings = (): Promise<{ ok: boolean; message: string; updated_count: number }> => 
  apiRequest('/data/policies/force-regenerate-embeddings', { method: 'POST' })
