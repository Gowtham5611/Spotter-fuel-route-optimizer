/**
 * TypeScript types for the Spotter Fuel Route Optimizer API.
 * These mirror the Django API response schema exactly.
 */

export interface RouteGeometry {
  type: 'LineString';
  coordinates: [number, number][]; // [longitude, latitude]
}

export interface RouteInfo {
  distance_miles: number;
  duration_minutes: number | null;
  geometry: RouteGeometry;
}

export interface FuelStop {
  station_id: number;
  name: string;
  address: string;
  city: string;
  state: string;
  latitude: number;
  longitude: number;
  price_per_gallon: number;
  distance_from_start_miles: number;
  gallons_purchased: number;
  cost: number;
}

export interface FuelSummary {
  total_gallons: number;
  total_cost: number;
}

export interface VehicleInfo {
  max_range_miles: number;
  fuel_efficiency_mpg: number;
}

export interface Meta {
  external_api_calls: number;
  cached: boolean;
}

export interface RouteOptimizeResponse {
  request: {
    start: string;
    destination: string;
  };
  vehicle: VehicleInfo;
  route: RouteInfo;
  fuel_stops: FuelStop[];
  fuel_summary: FuelSummary;
  meta: Meta;
}

export interface RouteOptimizeRequest {
  start: string;
  destination: string;
}

export interface APIError {
  error: string;
  details?: Record<string, string[]>;
}
