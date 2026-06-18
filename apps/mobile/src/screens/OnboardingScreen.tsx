import { Feather, Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { palette } from '../constants/theme';
import { MetricChip, SecondaryButton, StepPill, SurfaceCard, Field, ToggleTile, PrimaryButton } from '../components/common';
import { AppDraft, PersonDraft, PersonSlot, ReadingMode, SavedPerson } from '../types/app';

type PlaceCandidate = {
  normalized_name: string;
  latitude: number;
  longitude: number;
  timezone_name?: string | null;
  utc_offset?: string | null;
};

function PersonPanel({
  slot,
  title,
  subtitle,
  person,
  helperLoading,
  placeCandidates,
  onChange,
  onResolveBirthplace,
  onApplyResolvedPlace,
  onUseCurrentLocation,
  onUseDeviceOffset,
  onSavePerson,
}: {
  slot: PersonSlot;
  title: string;
  subtitle: string;
  person: PersonDraft;
  helperLoading: boolean;
  placeCandidates: PlaceCandidate[];
  onChange: (key: keyof PersonDraft, value: string) => void;
  onResolveBirthplace: () => void;
  onApplyResolvedPlace: (candidate: PlaceCandidate) => void;
  onUseCurrentLocation: () => void;
  onUseDeviceOffset: () => void;
  onSavePerson: () => void;
}) {
  return (
    <>
      <SurfaceCard title={title} subtitle={subtitle} accent>
        <View style={styles.personHeader}>
          <View style={styles.personBadge}>{slot === 'primary' ? <Ionicons name="person-outline" size={18} color={palette.accent} /> : <Ionicons name="people-outline" size={18} color={palette.accent} />}</View>
          <View style={styles.personHeaderText}>
            <Text style={styles.personHeaderTitle}>{person.name || person.profileLabel}</Text>
            <Text style={styles.personHeaderSubtitle}>{person.birthCity || 'Birthplace pending'} • {person.birthDate || 'No date yet'}</Text>
          </View>
        </View>
      </SurfaceCard>

      <SurfaceCard title="Birth details" subtitle="The more accurate these details are, the more accurate the reading will be.">
        <Field label="Saved label" value={person.profileLabel} onChangeText={(value) => onChange('profileLabel', value)} placeholder={slot === 'primary' ? 'Person A' : 'Person B'} />
        <Field label="Name" value={person.name} onChangeText={(value) => onChange('name', value)} placeholder="Name" />
        <Field label="Birth date" value={person.birthDate} onChangeText={(value) => onChange('birthDate', value)} placeholder="YYYY-MM-DD" />
        <Field label="Birth time" value={person.birthTime} onChangeText={(value) => onChange('birthTime', value)} placeholder={person.timePrecision.trim().toLowerCase() === 'exact' ? 'HH:MM' : 'Optional for fallback mode'} />
        <Field label="Birth city" value={person.birthCity} onChangeText={(value) => onChange('birthCity', value)} placeholder="Detroit" />
        <Field label="Birth country" value={person.birthCountry} onChangeText={(value) => onChange('birthCountry', value)} placeholder="USA" />
        <Field label="How exact is the birth time?" value={person.timePrecision} onChangeText={(value) => onChange('timePrecision', value)} placeholder="exact, approximate, or unknown" />
        <Text style={styles.mutedText}>Use <Text style={styles.emphasis}>exact</Text> if you know the birth time. If the time is approximate or unknown, The Ark switches into a simpler mode that avoids overclaiming.</Text>
      </SurfaceCard>

      <SurfaceCard title="Find the birth location" subtitle="Use this to fill in coordinates and timezone information for the birth place.">
        <View style={styles.inlineActions}>
          <SecondaryButton label={helperLoading ? 'Finding place…' : 'Find place'} onPress={onResolveBirthplace} disabled={helperLoading} icon={<Feather name="map-pin" size={15} color={palette.ink} />} />
          <SecondaryButton label="Use device time" onPress={onUseDeviceOffset} icon={<Ionicons name="time-outline" size={16} color={palette.ink} />} />
          <SecondaryButton label="Save this person" onPress={onSavePerson} icon={<Feather name="save" size={15} color={palette.ink} />} />
        </View>
        <View style={styles.twoColumnRow}>
          <View style={styles.column}><Field label="Latitude" value={person.latitude} onChangeText={(value) => onChange('latitude', value)} placeholder="Auto if blank" keyboardType="decimal-pad" /></View>
          <View style={styles.column}><Field label="Longitude" value={person.longitude} onChangeText={(value) => onChange('longitude', value)} placeholder="Auto if blank" keyboardType="decimal-pad" /></View>
        </View>
        <Field label="Timezone name" value={person.timezoneName} onChangeText={(value) => onChange('timezoneName', value)} placeholder="America/Detroit" />
        <Field label="UTC offset" value={person.utcOffset} onChangeText={(value) => onChange('utcOffset', value)} placeholder="-05:00" />
        {placeCandidates.length > 1 ? (
          <View style={styles.candidateStack}>
            <Text style={styles.candidateTitle}>Choose the correct place</Text>
            {placeCandidates.map((candidate) => (
              <View key={`${candidate.normalized_name}-${candidate.latitude}-${candidate.longitude}`} style={styles.candidateCard}>
                <View style={styles.candidateTextWrap}>
                  <Text style={styles.candidateName}>{candidate.normalized_name}</Text>
                  <Text style={styles.candidateMeta}>{candidate.timezone_name || 'Timezone unknown'} • {candidate.utc_offset || 'Offset pending'}</Text>
                </View>
                <SecondaryButton label="Use this" onPress={() => onApplyResolvedPlace(candidate)} icon={<Feather name="check" size={15} color={palette.ink} />} />
              </View>
            ))}
          </View>
        ) : null}
      </SurfaceCard>

      <SurfaceCard title="Current location for timing" subtitle="This helps with time-sensitive transit timing. If you leave it blank, the app uses the birth location instead.">
        <View style={styles.inlineActions}>
          <SecondaryButton label={helperLoading ? 'Finding current location…' : 'Use current location'} onPress={onUseCurrentLocation} disabled={helperLoading} icon={<Feather name="navigation" size={15} color={palette.ink} />} />
        </View>
        <View style={styles.twoColumnRow}>
          <View style={styles.column}><Field label="Current latitude" value={person.currentLatitude} onChangeText={(value) => onChange('currentLatitude', value)} placeholder="Optional" keyboardType="decimal-pad" /></View>
          <View style={styles.column}><Field label="Current longitude" value={person.currentLongitude} onChangeText={(value) => onChange('currentLongitude', value)} placeholder="Optional" keyboardType="decimal-pad" /></View>
        </View>
        <Field label="Current timezone name" value={person.currentTimezoneName} onChangeText={(value) => onChange('currentTimezoneName', value)} placeholder="America/Detroit" />
        <Field label="Current UTC offset" value={person.currentUtcOffset} onChangeText={(value) => onChange('currentUtcOffset', value)} placeholder="-04:00" />
      </SurfaceCard>
    </>
  );
}

export function OnboardingScreen({
  draft,
  onboardingStep,
  helperLoading,
  canAdvance,
  stepLabels,
  savedPeople,
  onSetReadingMode,
  onApiBaseUrlChange,
  placeCandidates,
  onPersonChange,
  onResolveBirthplace,
  onApplyResolvedPlace,
  onUseCurrentLocation,
  onUseDeviceOffset,
  onSavePerson,
  onLoadSavedPerson,
  onDeleteSavedPerson,
  onToggleJungian,
  onToggleRedBook,
  onNext,
  onBack,
  onSubmit,
  onReset,
  loading,
}: {
  draft: AppDraft;
  onboardingStep: number;
  helperLoading: boolean;
  canAdvance: boolean;
  stepLabels: string[];
  savedPeople: SavedPerson[];
  onSetReadingMode: (value: ReadingMode) => void;
  onApiBaseUrlChange: (value: string) => void;
  placeCandidates: Record<PersonSlot, PlaceCandidate[]>;
  onPersonChange: (slot: PersonSlot, key: keyof PersonDraft, value: string) => void;
  onResolveBirthplace: (slot: PersonSlot) => void;
  onApplyResolvedPlace: (slot: PersonSlot, candidate: PlaceCandidate) => void;
  onUseCurrentLocation: (slot: PersonSlot) => void;
  onUseDeviceOffset: (slot: PersonSlot) => void;
  onSavePerson: (slot: PersonSlot) => void;
  onLoadSavedPerson: (saved: SavedPerson, slot: PersonSlot) => void;
  onDeleteSavedPerson: (id: string) => void;
  onToggleJungian: (value: boolean) => void;
  onToggleRedBook: (value: boolean) => void;
  onNext: () => void;
  onBack: () => void;
  onSubmit: () => void;
  onReset: () => void;
  loading: boolean;
}) {
  const maxStepIndex = stepLabels.length - 1;

  function renderSetup() {
    return (
      <>
        <SurfaceCard title="How The Ark works" subtitle="The app keeps the real astrology, but it teaches as it goes.">
          <View style={styles.teachingStack}>
            <Text style={styles.mutedText}><Text style={styles.emphasis}>Natal reading</Text> means one person's birth chart.</Text>
            <Text style={styles.mutedText}><Text style={styles.emphasis}>Relationship reading</Text> compares two charts to show attraction, friction, and repeated patterns.</Text>
            <Text style={styles.mutedText}><Text style={styles.emphasis}>Exact birth time</Text> gives the most accurate houses, angles, and timing.</Text>
            <Text style={styles.mutedText}>If the birth time is approximate or unknown, The Ark switches to a simpler mode instead of pretending to know more than it does.</Text>
          </View>
        </SurfaceCard>

        <SurfaceCard title="Reading type" subtitle="Choose whether you want a reading for one person or a relationship reading for two people.">
          <View style={styles.modeRow}>
            <PressableModePill active={draft.readingMode === 'natal'} label="Birth chart" icon={<Ionicons name="sunny-outline" size={18} color={draft.readingMode === 'natal' ? palette.white : palette.accent} />} onPress={() => onSetReadingMode('natal')} />
            <PressableModePill active={draft.readingMode === 'synastry'} label="Relationship" icon={<Ionicons name="people-outline" size={18} color={draft.readingMode === 'synastry' ? palette.white : palette.accent} />} onPress={() => onSetReadingMode('synastry')} />
          </View>
          <Text style={styles.mutedText}>Enter the chart details directly on this screen, then move to review when you are ready.</Text>
        </SurfaceCard>

        <SurfaceCard title="Connection" subtitle="This is the API endpoint the app will use for readings, accounts, and chart calculations.">
          <Field label="API base URL" value={draft.apiBaseUrl} onChangeText={onApiBaseUrlChange} placeholder="https://api.theark.app" autoCapitalize="none" />
          <Text style={styles.mutedText}>For local web development this is usually <Text style={styles.emphasis}>http://127.0.0.1:8000</Text>. For a deployed web app, point this at the live Ark API or same-origin backend.</Text>
        </SurfaceCard>

        <SurfaceCard title="Saved people" subtitle="Reuse saved birth profiles instead of retyping the same information.">
          {savedPeople.length === 0 ? (
            <Text style={styles.mutedText}>No saved people yet. Save one from Person A or Person B after entering the birth details.</Text>
          ) : (
            savedPeople.map((saved) => (
              <View key={saved.id} style={styles.savedCard}>
                <View style={styles.savedTopRow}>
                  <View style={styles.savedTextWrap}>
                    <Text style={styles.savedTitle}>{saved.label}</Text>
                    <Text style={styles.savedMeta}>{saved.person.birthDate} • {saved.person.birthCity}, {saved.person.birthCountry}</Text>
                  </View>
                  <Text style={styles.savedDate}>{new Date(saved.savedAt).toLocaleDateString()}</Text>
                </View>
                <View style={styles.savedActionsWrap}>
                  <SecondaryButton label="Use for Person A" onPress={() => onLoadSavedPerson(saved, 'primary')} icon={<Ionicons name="person-outline" size={16} color={palette.ink} />} />
                  {draft.readingMode === 'synastry' ? <SecondaryButton label="Use for Person B" onPress={() => onLoadSavedPerson(saved, 'secondary')} icon={<Ionicons name="people-outline" size={16} color={palette.ink} />} /> : null}
                  <SecondaryButton label="Delete" onPress={() => onDeleteSavedPerson(saved.id)} icon={<Feather name="trash-2" size={15} color={palette.ink} />} />
                </View>
              </View>
            ))
          )}
        </SurfaceCard>

        <PersonPanel slot="primary" title={draft.readingMode === 'natal' ? 'Natal subject' : 'Person A'} subtitle={draft.readingMode === 'natal' ? 'This person becomes the single natal chart for the reading.' : 'The first chart anchors the synastry comparison.'} person={draft.primary} helperLoading={helperLoading} placeCandidates={placeCandidates.primary} onChange={(key, value) => onPersonChange('primary', key, value)} onResolveBirthplace={() => onResolveBirthplace('primary')} onApplyResolvedPlace={(candidate) => onApplyResolvedPlace('primary', candidate)} onUseCurrentLocation={() => onUseCurrentLocation('primary')} onUseDeviceOffset={() => onUseDeviceOffset('primary')} onSavePerson={() => onSavePerson('primary')} />

        {draft.readingMode === 'synastry' ? (
          <PersonPanel slot="secondary" title="Person B" subtitle="The second chart is compared against Person A for relational patterning." person={draft.secondary} helperLoading={helperLoading} placeCandidates={placeCandidates.secondary} onChange={(key, value) => onPersonChange('secondary', key, value)} onResolveBirthplace={() => onResolveBirthplace('secondary')} onApplyResolvedPlace={(candidate) => onApplyResolvedPlace('secondary', candidate)} onUseCurrentLocation={() => onUseCurrentLocation('secondary')} onUseDeviceOffset={() => onUseDeviceOffset('secondary')} onSavePerson={() => onSavePerson('secondary')} />
        ) : null}
      </>
    );
  }

  function renderReview() {
    return (
      <>
        <SurfaceCard title="Review" subtitle="Check the reading type, selected people, and explanation settings before you generate the reading.">
          <View style={styles.metricGrid}>
            <MetricChip label="API" value={draft.apiBaseUrl.replace(/^https?:\/\//, '')} icon={<Feather name="link" size={14} color={palette.muted} />} />
            <MetricChip label="Mode" value={draft.readingMode === 'natal' ? 'Natal' : 'Synastry'} icon={<MaterialCommunityIcons name="orbit" size={14} color={palette.muted} />} />
            <MetricChip label="Person A" value={draft.primary.name || 'Unnamed'} icon={<Ionicons name="person-outline" size={14} color={palette.muted} />} />
            {draft.readingMode === 'synastry' ? <MetricChip label="Person B" value={draft.secondary.name || 'Unnamed'} icon={<Ionicons name="people-outline" size={14} color={palette.muted} />} /> : null}
          </View>
        </SurfaceCard>

      <SurfaceCard title="Optional overlays" subtitle="The traditional chart structure stays primary. These switches add modern reflective layers on top.">
        <ToggleTile label="Add Jungian insights" description="Optional modern psychological overlay." value={draft.includeJungian} onValueChange={onToggleJungian} />
        <ToggleTile label="Add reflective prompts" description="Optional journaling and imaginal overlay." value={draft.includeRedBookPrompts} onValueChange={onToggleRedBook} />
      </SurfaceCard>
      </>
    );
  }

  let content: React.ReactNode = null;
  if (onboardingStep === 0) content = renderSetup();
  else content = renderReview();

  return (
    <>
      <View style={styles.stepRow}>
        {stepLabels.map((label, index) => <StepPill key={label} label={`${index + 1}. ${label}`} active={index === onboardingStep} />)}
      </View>
      {content}
      <View style={styles.footerActions}>
        <View style={styles.footerButton}><SecondaryButton label="Back" onPress={onBack} disabled={onboardingStep === 0} icon={<Feather name="arrow-left" size={15} color={palette.ink} />} /></View>
        <View style={styles.footerButton}>
          {onboardingStep < maxStepIndex ? (
            <PrimaryButton label="Next" onPress={onNext} disabled={!canAdvance} icon={<Feather name="arrow-right" size={15} color={palette.white} />} />
          ) : (
            <PrimaryButton label={draft.readingMode === 'natal' ? 'Create birth chart reading' : 'Create relationship reading'} onPress={onSubmit} disabled={!canAdvance} loading={loading} icon={<Feather name="star" size={15} color={palette.white} />} />
          )}
        </View>
      </View>
      <SecondaryButton label="Reset draft" onPress={onReset} icon={<Feather name="rotate-ccw" size={15} color={palette.ink} />} />
    </>
  );
}

function PressableModePill({ active, label, icon, onPress }: { active: boolean; label: string; icon: React.ReactNode; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [styles.modePill, active && styles.modePillActive, pressed && styles.modePillPressed]}>
      <View style={styles.modePillInner}>
        {icon}
        <Text style={[styles.modePillLabel, active && styles.modePillLabelActive]}>{label}</Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  modeRow: { flexDirection: 'row', gap: 12 },
  modePill: {
    flex: 1,
    minHeight: 58,
    borderRadius: 15,
    borderWidth: 1,
    borderColor: palette.border,
    backgroundColor: palette.surface,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 18,
  },
  modePillActive: { backgroundColor: palette.accent, borderColor: palette.accent },
  modePillPressed: { opacity: 0.92, transform: [{ scale: 0.985 }] },
  modePillInner: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  modePillLabel: { fontSize: 15, lineHeight: 19, fontWeight: '700', color: palette.ink },
  modePillLabelActive: { color: palette.white },
  stepRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  inlineActions: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  twoColumnRow: { flexDirection: 'row', gap: 12 },
  column: { flex: 1 },
  metricGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  teachingStack: { gap: 10 },
  personHeader: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  personBadge: { width: 42, height: 42, borderRadius: 21, backgroundColor: palette.surface, borderWidth: 1, borderColor: palette.border, alignItems: 'center', justifyContent: 'center' },
  personHeaderText: { flex: 1, gap: 4 },
  personHeaderTitle: { fontSize: 19, lineHeight: 24, color: palette.ink, fontWeight: '700' },
  personHeaderSubtitle: { fontSize: 13, lineHeight: 19, color: palette.muted },
  mutedText: { fontSize: 15, lineHeight: 22, color: palette.muted },
  emphasis: { color: palette.ink, fontWeight: '700' },
  candidateStack: { gap: 12 },
  candidateTitle: { fontSize: 12, letterSpacing: 1.4, textTransform: 'uppercase', color: palette.ink, fontWeight: '700' },
  candidateCard: { gap: 12, borderWidth: 1, borderColor: palette.border, backgroundColor: palette.surface, borderRadius: 16, padding: 14 },
  candidateTextWrap: { gap: 5 },
  candidateName: { fontSize: 15, lineHeight: 21, color: palette.ink, fontWeight: '700' },
  candidateMeta: { fontSize: 12, lineHeight: 18, color: palette.muted },
  savedCard: { borderTopWidth: 1, borderTopColor: palette.border, paddingTop: 14, paddingBottom: 14, gap: 12 },
  savedTopRow: { flexDirection: 'row', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start' },
  savedTextWrap: { flex: 1, gap: 5 },
  savedTitle: { fontSize: 17, lineHeight: 22, fontWeight: '700', color: palette.ink },
  savedMeta: { fontSize: 13, lineHeight: 19, color: palette.muted },
  savedDate: { fontSize: 12, color: palette.muted },
  savedActionsWrap: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  footerActions: { flexDirection: 'row', gap: 10 },
  footerButton: { flex: 1 },
});
