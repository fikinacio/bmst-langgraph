import { View, Text, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { useAuth } from '../../lib/hooks/useAuth';
import { useProvince } from '../../lib/hooks/useProvince';
import { toast } from '../../components/ui/Toast';

export default function ProfileScreen() {
  const { session, signOut } = useAuth();
  const { province, provinces, setProvince } = useProvince();

  const handleSignOut = async () => {
    try {
      await signOut();
    } catch (e: any) {
      toast.error(e.message ?? 'Erro ao terminar sessão');
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-bg" edges={['top']}>
      <ScrollView
        className="flex-1 px-4"
        contentContainerStyle={{ paddingBottom: 100 }}
      >
        <View className="py-4 gap-5">
          <Text
            className="text-xl font-bold text-slate-100"
            style={{ fontFamily: 'Inter_700Bold' }}
          >
            Perfil
          </Text>

          <Card>
            <View className="gap-2">
              <Text className="text-slate-400 text-sm">Telemóvel</Text>
              <Text className="text-slate-100 font-medium">
                {session?.user.phone ?? '—'}
              </Text>
            </View>
          </Card>

          <View className="gap-3">
            <Text className="text-sm font-medium text-slate-300">Província activa</Text>
            <View className="gap-2">
              {provinces.map((p) => (
                <Card
                  key={p.id}
                  onPress={() => setProvince(p.id)}
                  className={p.id === province.id ? 'border-emerald-500' : ''}
                >
                  <View className="flex-row items-center justify-between">
                    <Text
                      className={`font-medium ${p.id === province.id ? 'text-emerald-400' : 'text-slate-100'}`}
                    >
                      {p.name}
                    </Text>
                    {p.id === province.id ? (
                      <Text className="text-emerald-400 text-lg">✓</Text>
                    ) : null}
                  </View>
                </Card>
              ))}
            </View>
          </View>

          <Button label="Terminar sessão" onPress={handleSignOut} variant="danger" />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
