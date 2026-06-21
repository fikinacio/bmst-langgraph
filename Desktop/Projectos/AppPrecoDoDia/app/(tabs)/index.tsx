import { View, Text, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { FlashList } from '@shopify/flash-list';
import { useState, useEffect, useCallback } from 'react';
import { supabase } from '../../lib/supabase';
import { useProvince } from '../../lib/hooks/useProvince';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import type { PriceAggregate } from '../../lib/types';

function PriceCard({ item }: { item: PriceAggregate }) {
  const formattedPrice = item.avg_price_aoa.toLocaleString('pt-AO') + ' Kz';

  return (
    <Card className="mx-4 mb-3">
      <View className="flex-row items-center justify-between">
        <View className="flex-1 gap-1">
          <Text
            className="text-slate-100 font-semibold text-base"
            style={{ fontFamily: 'Inter_600SemiBold' }}
          >
            {item.product?.name ?? '—'}
          </Text>
          <Text className="text-slate-400 text-sm">{item.product?.unit}</Text>
        </View>
        <View className="items-end gap-1">
          <Text
            className="text-emerald-400 font-bold text-lg"
            style={{ fontFamily: 'Inter_700Bold' }}
          >
            {formattedPrice}
          </Text>
          <Badge label={`${item.reports_count} relatórios`} variant="default" />
        </View>
      </View>
    </Card>
  );
}

function SkeletonCard() {
  return (
    <View className="mx-4 mb-3 bg-surface border border-border rounded-xl p-4">
      <View className="flex-row items-center justify-between">
        <View className="gap-2">
          <View className="w-32 h-4 bg-border rounded-md" />
          <View className="w-20 h-3 bg-border rounded-md" />
        </View>
        <View className="w-24 h-6 bg-border rounded-md" />
      </View>
    </View>
  );
}

export default function HomeScreen() {
  const { province } = useProvince();
  const [aggregates, setAggregates] = useState<PriceAggregate[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchAggregates = useCallback(async () => {
    const { data } = await supabase
      .from('price_aggregates')
      .select('*, product:products(*)')
      .eq('province_id', province.id)
      .order('last_updated', { ascending: false })
      .limit(50);
    setAggregates(data ?? []);
    setLoading(false);
  }, [province.id]);

  useEffect(() => {
    setLoading(true);
    fetchAggregates();

    const channel = supabase
      .channel(`aggregates-${province.id}`)
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'price_aggregates' },
        fetchAggregates
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [province.id, fetchAggregates]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchAggregates();
    setRefreshing(false);
  }, [fetchAggregates]);

  return (
    <SafeAreaView className="flex-1 bg-bg" edges={['top']}>
      <View className="px-4 py-4 border-b border-border">
        <Text
          className="text-xl font-bold text-slate-100"
          style={{ fontFamily: 'Inter_700Bold' }}
        >
          {province.name}
        </Text>
        <Text className="text-slate-400 text-sm">Preços actualizados hoje</Text>
      </View>

      {loading ? (
        <View className="pt-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </View>
      ) : (
        <FlashList
          data={aggregates}
          keyExtractor={(item) => `${item.product_id}-${item.province_id}`}
          renderItem={({ item }) => <PriceCard item={item} />}
          estimatedItemSize={88}
          contentContainerStyle={{ paddingTop: 12, paddingBottom: 100 }}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor="#10b981"
            />
          }
          ListEmptyComponent={
            <View className="items-center py-20 gap-3">
              <Text className="text-4xl">📭</Text>
              <Text className="text-slate-400 text-center">
                Sem preços reportados para {province.name} ainda.{'\n'}Seja o primeiro a
                reportar!
              </Text>
            </View>
          }
        />
      )}
    </SafeAreaView>
  );
}
