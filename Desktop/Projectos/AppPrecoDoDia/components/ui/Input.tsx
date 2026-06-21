import { View, Text, TextInput, TextInputProps } from 'react-native';

interface InputProps extends TextInputProps {
  label?: string;
  error?: string;
  leftElement?: React.ReactNode;
  rightElement?: React.ReactNode;
}

export function Input({ label, error, leftElement, rightElement, ...props }: InputProps) {
  return (
    <View className="gap-1.5">
      {label && <Text className="text-sm font-medium text-slate-300">{label}</Text>}
      <View
        className={`flex-row items-center bg-surface border rounded-xl px-4 ${error ? 'border-rose-500' : 'border-border'}`}
      >
        {leftElement}
        <TextInput
          className="flex-1 py-3.5 text-slate-100 text-base"
          placeholderTextColor="#475569"
          selectionColor="#10b981"
          {...props}
        />
        {rightElement}
      </View>
      {error && <Text className="text-xs text-rose-400">{error}</Text>}
    </View>
  );
}
