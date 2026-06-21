import { View, Text } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Button } from '../../components/ui/Button';

export default function OnboardingScreen() {
  const router = useRouter();

  return (
    <SafeAreaView className="flex-1 bg-bg">
      <View className="flex-1 items-center justify-center px-6 gap-8">
        <View className="items-center gap-4">
          <View className="w-24 h-24 rounded-3xl bg-emerald-500/20 items-center justify-center">
            <Text className="text-5xl">📊</Text>
          </View>
          <Text
            className="text-3xl font-extrabold text-slate-100 text-center"
            style={{ fontFamily: 'Inter_800ExtraBold' }}
          >
            Preço do Dia
          </Text>
          <Text className="text-slate-400 text-center text-base leading-6">
            Acompanhe e reporte preços de mercado em tempo real em toda Angola.
          </Text>
        </View>

        <View className="w-full gap-3">
          <View className="flex-row items-center gap-3 bg-surface border border-border rounded-xl p-4">
            <Text className="text-2xl">📍</Text>
            <View className="flex-1">
              <Text className="text-slate-100 font-semibold">Preços da sua zona</Text>
              <Text className="text-slate-400 text-sm">
                Mercados da sua província actualizados em tempo real
              </Text>
            </View>
          </View>
          <View className="flex-row items-center gap-3 bg-surface border border-border rounded-xl p-4">
            <Text className="text-2xl">✏️</Text>
            <View className="flex-1">
              <Text className="text-slate-100 font-semibold">Reporte preços</Text>
              <Text className="text-slate-400 text-sm">
                Ajude a comunidade com preços actualizados
              </Text>
            </View>
          </View>
          <View className="flex-row items-center gap-3 bg-surface border border-border rounded-xl p-4">
            <Text className="text-2xl">🤖</Text>
            <View className="flex-1">
              <Text className="text-slate-100 font-semibold">IA integrada</Text>
              <Text className="text-slate-400 text-sm">
                Extraímos preços automaticamente do seu texto
              </Text>
            </View>
          </View>
        </View>

        <View className="w-full">
          <Button
            label="Entrar com Telemóvel"
            onPress={() => router.push('/(auth)/phone')}
            size="lg"
          />
        </View>
      </View>
    </SafeAreaView>
  );
}
