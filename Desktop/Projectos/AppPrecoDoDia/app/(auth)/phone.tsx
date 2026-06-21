import { useState } from 'react';
import { View, Text, KeyboardAvoidingView, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { useAuth } from '../../lib/hooks/useAuth';
import { toast } from '../../components/ui/Toast';

export default function PhoneScreen() {
  const router = useRouter();
  const { signInWithPhone } = useAuth();
  const [phone, setPhone] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSend = async () => {
    const cleaned = phone.replace(/\s/g, '');
    if (cleaned.length < 9) {
      setError('Número inválido. Ex: 923 456 789');
      return;
    }

    setError('');
    setLoading(true);
    try {
      const fullPhone = `+244${cleaned}`;
      await signInWithPhone(fullPhone);
      router.push({ pathname: '/(auth)/verify', params: { phone: fullPhone } });
    } catch (e: any) {
      toast.error(e.message ?? 'Erro ao enviar SMS');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-bg">
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        className="flex-1 px-6 pt-8 gap-8"
      >
        <View className="gap-2">
          <Text
            className="text-2xl font-bold text-slate-100"
            style={{ fontFamily: 'Inter_700Bold' }}
          >
            O seu número
          </Text>
          <Text className="text-slate-400">
            Enviamos um código SMS para confirmar a sua identidade.
          </Text>
        </View>

        <View className="gap-4">
          <Input
            label="Número de telemóvel"
            placeholder="923 456 789"
            keyboardType="phone-pad"
            value={phone}
            onChangeText={setPhone}
            error={error}
            leftElement={<Text className="text-slate-400 mr-2 text-base">🇦🇴 +244</Text>}
          />
          <Button
            label="Enviar código"
            onPress={handleSend}
            loading={loading}
            disabled={phone.replace(/\s/g, '').length < 9}
          />
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
