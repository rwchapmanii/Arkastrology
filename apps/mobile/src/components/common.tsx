import { Feather, Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Switch, Text, TextInput, View } from 'react-native';
import { palette, radii } from '../constants/theme';

export function Field({
  label,
  value,
  onChangeText,
  placeholder,
  keyboardType,
  secureTextEntry,
  autoCapitalize,
}: {
  label: string;
  value: string;
  onChangeText: (text: string) => void;
  placeholder?: string;
  keyboardType?: 'default' | 'numeric' | 'email-address' | 'decimal-pad';
  secureTextEntry?: boolean;
  autoCapitalize?: 'none' | 'sentences' | 'words' | 'characters';
}) {
  return (
    <View style={styles.fieldWrap}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={palette.muted}
        keyboardType={keyboardType}
        style={styles.input}
        secureTextEntry={secureTextEntry}
        autoCapitalize={autoCapitalize ?? 'none'}
      />
    </View>
  );
}

export function SurfaceCard({
  title,
  subtitle,
  children,
  accent = false,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  accent?: boolean;
}) {
  return (
    <View style={[styles.card, accent && styles.cardAccent]}>
      <View style={styles.cardHeader}>
        <Text style={styles.cardTitle}>{title}</Text>
        {subtitle ? <Text style={styles.cardSubtitle}>{subtitle}</Text> : null}
      </View>
      {children}
    </View>
  );
}

export function StepPill({ label, active }: { label: string; active: boolean }) {
  return (
    <View style={[styles.stepPill, active && styles.stepPillActive]}>
      <Text style={[styles.stepPillText, active && styles.stepPillTextActive]}>{label}</Text>
    </View>
  );
}

export function MetricChip({ label, value, icon }: { label: string; value: string; icon?: React.ReactNode }) {
  return (
    <View style={styles.metricChip}>
      <View style={styles.metricTopRow}>
        {icon}
        <Text style={styles.metricLabel}>{label}</Text>
      </View>
      <Text style={styles.metricValue}>{value}</Text>
    </View>
  );
}

export function PrimaryButton({
  label,
  onPress,
  disabled,
  loading,
  icon,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
  icon?: React.ReactNode;
}) {
  return (
    <Pressable style={({ pressed }) => [styles.primaryButton, (disabled || loading) && styles.buttonDisabled, pressed && styles.buttonPressed]} onPress={onPress} disabled={disabled || loading}>
      {loading ? <ActivityIndicator color={palette.white} /> : <View style={styles.buttonContent}>{icon}<Text style={styles.primaryButtonText}>{label}</Text></View>}
    </Pressable>
  );
}

export function SecondaryButton({
  label,
  onPress,
  disabled,
  icon,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  icon?: React.ReactNode;
}) {
  return (
    <Pressable style={({ pressed }) => [styles.secondaryButton, disabled && styles.buttonDisabled, pressed && styles.buttonPressed]} onPress={onPress} disabled={disabled}>
      <View style={styles.buttonContent}>{icon}<Text style={styles.secondaryButtonText}>{label}</Text></View>
    </Pressable>
  );
}

export function ToggleTile({
  label,
  description,
  value,
  onValueChange,
}: {
  label: string;
  description: string;
  value: boolean;
  onValueChange: (value: boolean) => void;
}) {
  return (
    <View style={styles.toggleTile}>
      <View style={styles.toggleTextWrap}>
        <Text style={styles.toggleLabel}>{label}</Text>
        <Text style={styles.toggleDescription}>{description}</Text>
      </View>
      <Switch value={value} onValueChange={onValueChange} trackColor={{ false: '#D6D6CF', true: palette.ink }} thumbColor={palette.white} />
    </View>
  );
}

export function renderBlockIcon(blockType: string, size = 20) {
  switch (blockType) {
    case 'chart_foundation':
      return <MaterialCommunityIcons name="compass-rose" size={size} color={palette.accent} />;
    case 'fortune_spirit':
      return <MaterialCommunityIcons name="yin-yang" size={size} color={palette.ink} />;
    case 'annual_profection':
      return <MaterialCommunityIcons name="calendar-star" size={size} color={palette.accent} />;
    case 'solar_return':
      return <MaterialCommunityIcons name="weather-sunset-up" size={size} color={palette.accent} />;
    case 'year_map':
      return <MaterialCommunityIcons name="map-clock-outline" size={size} color={palette.accent} />;
    case 'topic_judgment':
      return <MaterialCommunityIcons name="scale-balance" size={size} color={palette.muted} />;
    case 'solar_identity':
      return <Ionicons name="sunny-outline" size={size} color={palette.accent} />;
    case 'lunar_pattern':
      return <Ionicons name="moon-outline" size={size} color={palette.ink} />;
    case 'rising_style':
      return <Feather name="arrow-up-right" size={size} color={palette.muted} />;
    case 'ontology_signature':
      return <MaterialCommunityIcons name="sitemap-outline" size={size} color={palette.accent} />;
    case 'levi_current':
      return <MaterialCommunityIcons name="lightning-bolt-outline" size={size} color={palette.accent} />;
    case 'transit_current':
      return <MaterialCommunityIcons name="orbit-variant" size={size} color={palette.accent} />;
    case 'house_focus':
      return <MaterialCommunityIcons name="home-city-outline" size={size} color={palette.muted} />;
    case 'relationship_climate':
      return <MaterialCommunityIcons name="scale-balance" size={size} color={palette.accent} />;
    case 'synastry_natal_frame':
      return <Feather name="user" size={size} color={palette.accent} />;
    case 'synastry_yearly_bridge':
      return <Feather name="git-merge" size={size} color={palette.accent} />;
    case 'synastry_topic_judgment':
      return <MaterialCommunityIcons name="handshake-outline" size={size} color={palette.accent} />;
    case 'major_aspect':
    case 'synastry_aspect':
      return <MaterialCommunityIcons name="vector-link" size={size} color={palette.muted} />;
    case 'planet_emphasis':
      return <MaterialCommunityIcons name="orbit" size={size} color={palette.accent} />;
    case 'jungian_trigger':
      return <MaterialCommunityIcons name="brain" size={size} color={palette.muted} />;
    case 'synastry_sign_pair':
      return <Ionicons name="people-outline" size={size} color={palette.accent} />;
    case 'synastry_core_bond':
      return <Ionicons name="heart-outline" size={size} color={palette.ink} />;
    case 'synastry_attraction':
      return <MaterialCommunityIcons name="magnet" size={size} color={palette.accent} />;
    case 'synastry_prompt':
    case 'imaginal_prompt':
      return <Ionicons name="book-outline" size={size} color={palette.muted} />;
    default:
      return <Feather name="square" size={size} color={palette.muted} />;
  }
}

const styles = StyleSheet.create({
  fieldWrap: { gap: 7 },
  fieldLabel: { fontSize: 12, lineHeight: 16, color: palette.muted, fontWeight: '600' },
  input: {
    borderWidth: 1,
    borderColor: palette.border,
    backgroundColor: palette.input,
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 14,
    fontSize: 16,
    color: palette.ink,
  },
  card: {
    backgroundColor: palette.surface,
    borderRadius: radii.card,
    padding: 20,
    borderWidth: 1,
    borderColor: palette.border,
    gap: 16,
    shadowColor: '#000000',
    shadowOpacity: 0,
    shadowRadius: 0,
    shadowOffset: { width: 0, height: 0 },
    elevation: 0,
  },
  cardAccent: { backgroundColor: palette.surfaceStrong, borderColor: palette.borderStrong },
  cardHeader: { gap: 6 },
  cardTitle: { fontSize: 11, letterSpacing: 1.5, textTransform: 'uppercase', color: palette.muted, fontWeight: '700' },
  cardSubtitle: { fontSize: 15, lineHeight: 22, color: palette.muted },
  stepPill: {
    borderWidth: 1,
    borderColor: palette.border,
    backgroundColor: palette.surface,
    borderRadius: 999,
    paddingHorizontal: 13,
    paddingVertical: 9,
  },
  stepPillActive: { backgroundColor: palette.accent, borderColor: palette.accent },
  stepPillText: { fontSize: 12, color: palette.muted, fontWeight: '700' },
  stepPillTextActive: { color: palette.white },
  metricChip: {
    backgroundColor: palette.surface,
    borderRadius: radii.chip,
    paddingHorizontal: 13,
    paddingVertical: 12,
    borderWidth: 1,
    borderColor: palette.border,
    minWidth: 120,
    gap: 5,
  },
  metricTopRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  metricLabel: { fontSize: 11, letterSpacing: 1.1, textTransform: 'uppercase', color: palette.muted, fontWeight: '700' },
  metricValue: { fontSize: 15, lineHeight: 20, color: palette.ink, fontWeight: '600' },
  buttonContent: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  primaryButton: {
    backgroundColor: palette.accent,
    borderRadius: radii.button,
    minHeight: 50,
    paddingHorizontal: 18,
    justifyContent: 'center',
    alignItems: 'center',
  },
  primaryButtonText: { fontSize: 14, lineHeight: 18, color: palette.white, fontWeight: '700' },
  secondaryButton: {
    backgroundColor: palette.surface,
    borderRadius: radii.button,
    minHeight: 50,
    paddingHorizontal: 18,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: palette.border,
  },
  secondaryButtonText: { fontSize: 14, lineHeight: 18, color: palette.ink, fontWeight: '700' },
  buttonDisabled: { opacity: 0.45 },
  buttonPressed: { transform: [{ scale: 0.985 }] },
  toggleTile: {
    borderWidth: 1,
    borderColor: palette.border,
    borderRadius: 16,
    padding: 16,
    backgroundColor: palette.surface,
    flexDirection: 'row',
    gap: 14,
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  toggleTextWrap: { flex: 1, gap: 5 },
  toggleLabel: { fontSize: 15, lineHeight: 20, color: palette.ink, fontWeight: '600' },
  toggleDescription: { fontSize: 13, lineHeight: 20, color: palette.muted },
});
