import { useState } from 'react';
import { View, Text, TextInput, KeyboardAvoidingView, Platform } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Button } from '../../components/ui/Button';
import { useAuth } from '../../lib/hooks/useAuth';
import { toast } from '../../components/ui/Toast';

export default function VerifyScreen() {
  const { phone } = useLocalSearchParams<{ phone: string }>();
  const router = useRouter();
  const { verifyOTP } = useAuth();
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);

  const handleVerify = async () => {
    if (code.length !== 6) return;
    setLoading(true);
    try {
      await verifyOTP(phone, code);
      // AuthGuard em _layout.tsx redireciona automaticamente para (tabs)
    } catch (e: any) {
      toast.error(e.message ?? 'Código inválido');
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
            Verificar código
          </Text>
          <Text className="text-slate-400">
            Introduza o código de 6 dígitos enviado para{'\n'}
            <Text className="text-slate-200 font-medium">{phone}</Text>
          </Text>
        </View>

        <View className="gap-4">
          <TextInput
            className="bg-surface border border-border rounded-xl px-6 py-4 text-slate-100 text-3xl text-center tracking-widest font-bold"
            placeholder="------"
            placeholderTextColor="#475569"
            keyboardType="number-pad"
            maxLength={6}
            value={code}
            onChangeText={setCode}
            autoFocus
          />
          <Button
            label="Confirmar"
            onPress={handleVerify}
            loading={loading}
            disabled={code.length !== 6}
          />
          <Button label="Reenviar código" onPress={() => router.back()} variant="ghost" />
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
