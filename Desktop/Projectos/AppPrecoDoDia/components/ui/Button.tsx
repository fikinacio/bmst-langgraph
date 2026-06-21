import { TouchableOpacity, Text, ActivityIndicator } from 'react-native';
import * as Haptics from 'expo-haptics';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Size = 'sm' | 'md' | 'lg';

interface ButtonProps {
  label: string;
  onPress: () => void;
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  disabled?: boolean;
}

const variantStyles: Record<Variant, string> = {
  primary: 'bg-emerald-500 active:bg-emerald-600',
  secondary: 'bg-surface border border-border active:bg-border',
  ghost: 'bg-transparent active:bg-surface',
  danger: 'bg-rose-500 active:bg-rose-600',
};

const sizeStyles: Record<Size, { container: string; text: string }> = {
  sm: { container: 'px-4 py-2 rounded-md', text: 'text-sm font-medium' },
  md: { container: 'px-6 py-3.5 rounded-lg', text: 'text-base font-semibold' },
  lg: { container: 'px-8 py-4 rounded-xl', text: 'text-lg font-bold' },
};

export function Button({
  label,
  onPress,
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
}: ButtonProps) {
  const handlePress = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    onPress();
  };

  const textColor =
    variant === 'secondary' || variant === 'ghost' ? 'text-slate-100' : 'text-white';

  return (
    <TouchableOpacity
      onPress={handlePress}
      disabled={disabled || loading}
      className={`items-center justify-center flex-row gap-2 ${variantStyles[variant]} ${sizeStyles[size].container} ${disabled ? 'opacity-50' : ''}`}
    >
      {loading ? (
        <ActivityIndicator color="#fff" size="small" />
      ) : (
        <Text className={`${textColor} ${sizeStyles[size].text}`}>{label}</Text>
      )}
    </TouchableOpacity>
  );
}
