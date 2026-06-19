import { Feather, Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { palette } from '../constants/theme';
import { Field, MetricChip, PrimaryButton, SecondaryButton, SurfaceCard, ToggleTile } from '../components/common';
import { AuthState, RelationshipEntry, SavedPerson } from '../types/app';

type ProfileDraft = {
  displayName: string;
  timezoneName: string;
  bio: string;
};

export function AccountScreen({
  authState,
  savedPeople,
  relationships,
  relationshipsLoading,
  includeJungian,
  includeRedBookPrompts,
  profileDraft,
  profileLoading,
  onProfileChange,
  onSaveProfile,
  onRefreshProfile,
  onToggleJungian,
  onToggleRedBook,
  onOpenHistory,
  onRefreshRelationships,
  onRemoveRelationship,
  onRequestVerification,
  onBack,
  onSignOut,
}: {
  authState: AuthState;
  savedPeople: SavedPerson[];
  relationships: RelationshipEntry[];
  relationshipsLoading: boolean;
  includeJungian: boolean;
  includeRedBookPrompts: boolean;
  profileDraft: ProfileDraft;
  profileLoading: boolean;
  onProfileChange: (key: keyof ProfileDraft, value: string) => void;
  onSaveProfile: () => void;
  onRefreshProfile: () => void;
  onToggleJungian: (value: boolean) => void;
  onToggleRedBook: (value: boolean) => void;
  onOpenHistory: () => void;
  onRefreshRelationships: () => void;
  onRemoveRelationship: (profileId: string) => void;
  onRequestVerification: () => void;
  onBack: () => void;
  onSignOut: () => void;
}) {
  const planLabel = !authState.plan || authState.plan === 'prototype' ? 'Ark Beta' : authState.plan;

  return (
    <>
      <SurfaceCard title="Account" subtitle="This is where you manage your identity, saved readings, and default app behavior.">
        <View style={styles.metricGrid}>
          <MetricChip label="Mode" value={authState.mode === 'authenticated' ? 'Signed in' : 'Guest'} icon={<Ionicons name="person-circle-outline" size={14} color={palette.muted} />} />
          <MetricChip label="Email" value={authState.email || 'Guest session'} icon={<Feather name="mail" size={14} color={palette.muted} />} />
          <MetricChip label="Verified" value={authState.emailVerified ? 'Yes' : 'No'} icon={<Feather name="shield" size={14} color={palette.muted} />} />
          <MetricChip label="Saved people" value={String(savedPeople.length)} icon={<Ionicons name="people-outline" size={14} color={palette.muted} />} />
          <MetricChip label="Relationships" value={String(relationships.length)} icon={<MaterialCommunityIcons name="account-heart-outline" size={14} color={palette.muted} />} />
          <MetricChip label="Plan" value={planLabel} icon={<MaterialCommunityIcons name="star-four-points-outline" size={14} color={palette.muted} />} />
        </View>
      </SurfaceCard>

      <SurfaceCard title="Profile" subtitle="These details are saved to your account so the app can remember you across devices.">
        <Field label="Display name" value={profileDraft.displayName} onChangeText={(value) => onProfileChange('displayName', value)} placeholder="Ron Chapman" autoCapitalize="words" />
        <Field label="Timezone name" value={profileDraft.timezoneName} onChangeText={(value) => onProfileChange('timezoneName', value)} placeholder="America/Detroit" autoCapitalize="none" />
        <Field label="About you" value={profileDraft.bio} onChangeText={(value) => onProfileChange('bio', value)} placeholder="Lawyer, author, spiritually serious, tech-forward." autoCapitalize="sentences" />
        <View style={styles.row}>
          <View style={styles.flex}><SecondaryButton label={profileLoading ? 'Refreshing…' : 'Refresh profile'} onPress={onRefreshProfile} disabled={profileLoading} icon={<Feather name="refresh-cw" size={15} color={palette.ink} />} /></View>
          <View style={styles.flex}><PrimaryButton label={profileLoading ? 'Saving…' : 'Save profile'} onPress={onSaveProfile} disabled={profileLoading} icon={<Feather name="save" size={15} color={palette.white} />} /></View>
        </View>
      </SurfaceCard>

      <SurfaceCard title="Reading defaults" subtitle="Choose which optional modern overlays should be added on top of the traditional chart structure.">
        <ToggleTile label="Include Jungian insights" description="Optional modern psychological overlay for future readings." value={includeJungian} onValueChange={onToggleJungian} />
        <ToggleTile label="Include reflective prompts" description="Optional journaling and imaginal overlay for future readings." value={includeRedBookPrompts} onValueChange={onToggleRedBook} />
      </SurfaceCard>

      <SurfaceCard title="Session status" subtitle="This tells you whether you are signed in, verified, and saving work to your account.">
        <Text style={styles.body}>
          {authState.mode === 'authenticated'
            ? `Signed in as ${authState.email}. Your session is saved on this device and expires ${authState.sessionExpiresAt || 'on the normal account schedule'}.`
            : 'Guest mode is active. Your preferences stay on this device until you create an account.'}
        </Text>
        {authState.mode === 'authenticated' ? (
          <View style={styles.stack}>
            {!authState.emailVerified ? <SecondaryButton label="Send verification email" onPress={onRequestVerification} icon={<Feather name="send" size={15} color={palette.ink} />} /> : null}
            <SecondaryButton label="Open saved readings" onPress={onOpenHistory} icon={<Feather name="clock" size={15} color={palette.ink} />} />
          </View>
        ) : null}
      </SurfaceCard>

      <SurfaceCard title="Relationships" subtitle="These are the people you have saved from the directory for future relationship readings.">
        {relationships.length === 0 ? (
          <Text style={styles.body}>No relationships saved yet. Find people from the onboarding directory and add them here.</Text>
        ) : (
          <View style={styles.stack}>
            {relationships.map((entry) => (
              <View key={entry.relationship_id} style={styles.relationshipCard}>
                <View style={styles.relationshipText}>
                  <Text style={styles.relationshipName}>{entry.display_name}</Text>
                  <Text style={styles.relationshipMeta}>{entry.headline || entry.source_label || entry.kind}</Text>
                </View>
                <SecondaryButton label="Remove" onPress={() => onRemoveRelationship(entry.profile_id)} icon={<Feather name="x" size={15} color={palette.ink} />} />
              </View>
            ))}
          </View>
        )}
        <SecondaryButton label={relationshipsLoading ? 'Refreshing…' : 'Refresh relationships'} onPress={onRefreshRelationships} disabled={relationshipsLoading} icon={<Feather name="refresh-cw" size={15} color={palette.ink} />} />
      </SurfaceCard>

      <View style={styles.row}>
        <View style={styles.flex}><SecondaryButton label="Back" onPress={onBack} icon={<Feather name="arrow-left" size={15} color={palette.ink} />} /></View>
        <View style={styles.flex}><PrimaryButton label={authState.mode === 'authenticated' ? 'Sign out' : 'Exit guest mode'} onPress={onSignOut} icon={<Feather name="log-out" size={15} color={palette.white} />} /></View>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  metricGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  body: { fontSize: 15, lineHeight: 24, color: palette.ink },
  row: { flexDirection: 'row', gap: 10 },
  flex: { flex: 1 },
  stack: { gap: 12 },
  relationshipCard: {
    borderWidth: 1,
    borderColor: palette.border,
    borderRadius: 16,
    padding: 14,
    gap: 10,
  },
  relationshipText: { gap: 4 },
  relationshipName: { fontSize: 16, lineHeight: 22, color: palette.ink, fontWeight: '700' },
  relationshipMeta: { fontSize: 13, lineHeight: 18, color: palette.muted },
});
