import { useState, useCallback } from 'react';
import { MMKV } from 'react-native-mmkv';
import { PROVINCES, ProvinceData } from '../../constants/provinces';

const storage = new MMKV({ id: 'province-storage' });
const PROVINCE_KEY = 'selected_province_id';

export function useProvince() {
  const [provinceId, setProvinceIdState] = useState<string>(
    () => storage.getString(PROVINCE_KEY) ?? 'luanda'
  );

  const setProvince = useCallback((id: string) => {
    storage.set(PROVINCE_KEY, id);
    setProvinceIdState(id);
  }, []);

  const province: ProvinceData = PROVINCES.find((p) => p.id === provinceId) ?? PROVINCES[0];

  return { province, setProvince, provinces: PROVINCES };
}
