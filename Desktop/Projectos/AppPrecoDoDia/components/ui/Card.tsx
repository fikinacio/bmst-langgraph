import { TouchableOpacity, View } from 'react-native';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  onPress?: () => void;
}

export function Card({ children, className = '', onPress }: CardProps) {
  if (onPress) {
    return (
      <TouchableOpacity
        onPress={onPress}
        className={`bg-surface border border-border rounded-xl p-4 ${className}`}
        activeOpacity={0.75}
      >
        {children}
      </TouchableOpacity>
    );
  }

  return (
    <View className={`bg-surface border border-border rounded-xl p-4 ${className}`}>
      {children}
    </View>
  );
}
