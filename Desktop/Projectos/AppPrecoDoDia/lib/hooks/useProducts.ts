import { useState, useEffect } from 'react';
import { supabase } from '../supabase';
import type { Product } from '../types';

export function useProducts(query = '') {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const fetchProducts = async () => {
      setLoading(true);
      let q = supabase.from('products').select('*').order('name');

      if (query.trim()) {
        q = q.ilike('name', `%${query.trim()}%`);
      }

      const { data, error } = await q.limit(50);

      if (active) {
        if (error) setError(error.message);
        else setProducts(data ?? []);
        setLoading(false);
      }
    };

    fetchProducts();
    return () => { active = false; };
  }, [query]);

  return { products, loading, error };
}
