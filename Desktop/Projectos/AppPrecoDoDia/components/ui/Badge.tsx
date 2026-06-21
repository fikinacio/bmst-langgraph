import { View, Text } from 'react-native';

type BadgeVariant = 'emerald' | 'amber' | 'rose' | 'default';

interface BadgeProps {
  label: string;
  variant?: BadgeVariant;
}

const badgeStyles: Record<BadgeVariant, { container: string; text: string }> = {
  emerald: { container: 'bg-emerald-500/20', text: 'text-emerald-400' },
  amber: { container: 'bg-amber-500/20', text: 'text-amber-400' },
  rose: { container: 'bg-rose-500/20', text: 'text-rose-400' },
  default: { container: 'bg-slate-700/50', text: 'text-slate-300' },
};

export function Badge({ label, variant = 'default' }: BadgeProps) {
  return (
    <View className={`px-2.5 py-1 rounded-md self-start ${badgeStyles[variant].container}`}>
      <Text className={`text-xs font-medium ${badgeStyles[variant].text}`}>{label}</Text>
    </View>
  );
}
