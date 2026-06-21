export interface Province {
  id: string;
  name: string;
  markets: string[];
}

export interface UserProfile {
  id: string;
  phone: string;
  display_name: string | null;
  province_id: string | null;
  avatar_url: string | null;
  reports_count: number;
  created_at: string;
}

export interface Product {
  id: string;
  name: string;
  category: string;
  unit: string;
  image_url: string | null;
  created_at: string;
}

export interface PriceReport {
  id: string;
  user_id: string;
  product_id: string;
  province_id: string;
  market: string;
  price_aoa: number;
  price_usd: number | null;
  notes: string | null;
  image_url: string | null;
  created_at: string;
}

export interface PriceAggregate {
  product_id: string;
  province_id: string;
  avg_price_aoa: number;
  min_price_aoa: number;
  max_price_aoa: number;
  reports_count: number;
  last_updated: string;
  product: Product;
}

export interface ActivityItem {
  id: string;
  type: 'price_report' | 'price_change' | 'new_product';
  user_id: string;
  product_id: string;
  province_id: string;
  price_aoa: number;
  delta_pct: number | null;
  created_at: string;
  product: Product;
  profile: Pick<UserProfile, 'display_name' | 'avatar_url'>;
}

export interface ExtractedPrice {
  product: string;
  price: number;
  unit: string;
  currency: 'AOA' | 'USD';
  confidence: number;
}

export interface ExtractError {
  error: string;
}
