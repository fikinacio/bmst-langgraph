import { useState } from 'react';
import { View, Text, ScrollView, KeyboardAvoidingView, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { useProvince } from '../../lib/hooks/useProvince';
import { useProducts } from '../../lib/hooks/useProducts';
import { useAuth } from '../../lib/hooks/useAuth';
import { extractPriceFromText } from '../../lib/claude';
import { supabase } from '../../lib/supabase';
import { toast } from '../../components/ui/Toast';
import type { Product } from '../../lib/types';

export default function ReportScreen() {
  const { session } = useAuth();
  const { province } = useProvince();
  const [search, setSearch] = useState('');
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [market, setMarket] = useState('');
  const [price, setPrice] = useState('');
  const [freeText, setFreeText] = useState('');
  const [extracting, setExtracting] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const { products } = useProducts(search);

  const handleExtract = async () => {
    if (!freeText.trim()) return;
    setExtracting(true);
    try {
      const extracted = await extractPriceFromText(freeText, province.name);
      setPrice(String(extracted.price));
      toast.success(
        `Extraído: ${extracted.product} — ${extracted.price} ${extracted.currency}`
      );
    } catch (e: any) {
      toast.error(e.message ?? 'Erro ao extrair preço');
    } finally {
      setExtracting(false);
    }
  };

  const handleSubmit = async () => {
    if (!selectedProduct || !price || !market || !session) return;
    setSubmitting(true);
    try {
      const { error } = await supabase.from('price_reports').insert({
        user_id: session.user.id,
        product_id: selectedProduct.id,
        province_id: province.id,
        market,
        price_aoa: parseFloat(price),
      });
      if (error) throw error;
      toast.success('Preço reportado com sucesso!');
      setSelectedProduct(null);
      setPrice('');
      setMarket('');
      setFreeText('');
      setSearch('');
    } catch (e: any) {
      toast.error(e.message ?? 'Erro ao submeter');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-bg" edges={['top']}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        className="flex-1"
      >
        <ScrollView
          className="flex-1 px-4"
          contentContainerStyle={{ paddingBottom: 100 }}
        >
          <View className="py-4 gap-1">
            <Text
              className="text-xl font-bold text-slate-100"
              style={{ fontFamily: 'Inter_700Bold' }}
            >
              Reportar Preço
            </Text>
            <Text className="text-slate-400 text-sm">{province.name}</Text>
          </View>

          <View className="gap-5">
            <View className="gap-2">
              <Text className="text-sm font-medium text-slate-300">
                Descrever em texto (opcional)
              </Text>
              <Input
                placeholder="Ex: Açúcar Quitubia a 850 kz o saco no Roque Santeiro"
                value={freeText}
                onChangeText={setFreeText}
                multiline
              />
              {freeText.trim() ? (
                <Button
                  label="Extrair com IA"
                  onPress={handleExtract}
                  variant="secondary"
                  loading={extracting}
                />
              ) : null}
            </View>

            <Input
              label="Produto"
              placeholder="Pesquisar produto..."
              value={search}
              onChangeText={setSearch}
            />
            {search.trim()
              ? products.slice(0, 5).map((product) => (
                  <Card
                    key={product.id}
                    onPress={() => {
                      setSelectedProduct(product);
                      setSearch(product.name);
                    }}
                  >
                    <View className="flex-row items-center justify-between">
                      <Text className="text-slate-100 font-medium">{product.name}</Text>
                      <Badge label={product.unit} variant="default" />
                    </View>
                  </Card>
                ))
              : null}

            {selectedProduct ? (
              <View className="flex-row items-center gap-2 px-1">
                <Text className="text-emerald-400 text-sm">✓ {selectedProduct.name}</Text>
                <Badge label={selectedProduct.unit} variant="emerald" />
              </View>
            ) : null}

            <Input
              label="Mercado"
              placeholder={province.markets[0]}
              value={market}
              onChangeText={setMarket}
            />

            <Input
              label="Preço (Kz)"
              placeholder="Ex: 1500"
              keyboardType="decimal-pad"
              value={price}
              onChangeText={setPrice}
              rightElement={<Text className="text-slate-400 ml-2">AOA</Text>}
            />

            <Button
              label="Submeter preço"
              onPress={handleSubmit}
              loading={submitting}
              disabled={!selectedProduct || !price || !market}
            />
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
