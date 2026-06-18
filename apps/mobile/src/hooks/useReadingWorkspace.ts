import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';
import { useEffect, useMemo, useState } from 'react';
import { requestReading, resolvePlace } from '../services/api';
import {
  AnyReadingResponse,
  AuthState,
  BasicProfileResponse,
  PlaceResolveResponse,
  PersonDraft,
  PersonSlot,
  SavedPerson,
} from '../types/app';
import {
  APP_DRAFT_STORAGE_KEY,
  LEGACY_APP_DRAFT_STORAGE_KEYS,
  LEGACY_PERSON_STORAGE_KEYS,
  PERSON_STORAGE_KEY,
  defaultAppDraft,
  formatUtcOffset,
  getDeviceTimezoneName,
  getStepLabels,
  resolveApiBaseUrl,
} from '../utils/app';

async function readFirstAvailableStorageValue(primaryKey: string, legacyKeys: string[]) {
  const primaryValue = await AsyncStorage.getItem(primaryKey);
  if (primaryValue) return primaryValue;

  for (const legacyKey of legacyKeys) {
    const legacyValue = await AsyncStorage.getItem(legacyKey);
    if (legacyValue) {
      await AsyncStorage.setItem(primaryKey, legacyValue);
      return legacyValue;
    }
  }

  return null;
}

export function useReadingWorkspace(authState: AuthState) {
  const [draft, setDraft] = useState(defaultAppDraft);
  const [savedPeople, setSavedPeople] = useState<SavedPerson[]>([]);
  const [onboardingStep, setOnboardingStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [helperLoading, setHelperLoading] = useState(false);
  const [draftLoaded, setDraftLoaded] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnyReadingResponse | null>(null);
  const [placeCandidates, setPlaceCandidates] = useState<Record<PersonSlot, NonNullable<PlaceResolveResponse['place_candidates']>>>({ primary: [], secondary: [] });

  const stepLabels = useMemo(() => getStepLabels(draft.readingMode), [draft.readingMode]);
  const maxStepIndex = stepLabels.length - 1;

  useEffect(() => {
    async function loadStoredState() {
      try {
        const [savedDraft, savedPeopleRaw] = await Promise.all([
          readFirstAvailableStorageValue(APP_DRAFT_STORAGE_KEY, LEGACY_APP_DRAFT_STORAGE_KEYS),
          readFirstAvailableStorageValue(PERSON_STORAGE_KEY, LEGACY_PERSON_STORAGE_KEYS),
        ]);

        if (savedDraft) {
          const parsedDraft = JSON.parse(savedDraft) as Partial<typeof defaultAppDraft>;
          setDraft({
            ...defaultAppDraft,
            ...parsedDraft,
            apiBaseUrl: resolveApiBaseUrl(parsedDraft.apiBaseUrl),
            primary: { ...defaultAppDraft.primary, ...(parsedDraft.primary || {}) },
            secondary: { ...defaultAppDraft.secondary, ...(parsedDraft.secondary || {}) },
          });
        }

        if (savedPeopleRaw) {
          setSavedPeople(JSON.parse(savedPeopleRaw) as SavedPerson[]);
        }
      } catch {
        setSaveMessage('Saved Ark workspace state could not be loaded cleanly.');
      } finally {
        setDraftLoaded(true);
      }
    }

    void loadStoredState();
  }, []);

  useEffect(() => {
    if (!draftLoaded) return;
    const timer = setTimeout(() => {
      void AsyncStorage.setItem(APP_DRAFT_STORAGE_KEY, JSON.stringify(draft));
    }, 250);
    return () => clearTimeout(timer);
  }, [draft, draftLoaded]);

  useEffect(() => {
    if (!draftLoaded) return;
    void AsyncStorage.setItem(PERSON_STORAGE_KEY, JSON.stringify(savedPeople));
  }, [draftLoaded, savedPeople]);

  function personReady(person: PersonDraft) {
    const baseReady = [person.name, person.birthDate, person.birthCity, person.birthCountry].every((value) => value.trim().length > 0);
    if (!baseReady) return false;
    const precision = person.timePrecision.trim().toLowerCase();
    if (precision === 'exact') {
      return person.birthTime.trim().length > 0;
    }
    return true;
  }

  const isPrimaryReady = useMemo(() => personReady(draft.primary), [draft.primary]);

  const isSecondaryReady = useMemo(() => personReady(draft.secondary), [draft.secondary]);

  const canAdvance = useMemo(() => {
    if (onboardingStep === 0) {
      if (!draft.apiBaseUrl.trim().length) return false;
      if (!isPrimaryReady) return false;
      if (draft.readingMode === 'synastry' && !isSecondaryReady) return false;
      return true;
    }
    return true;
  }, [draft.apiBaseUrl, draft.readingMode, isPrimaryReady, isSecondaryReady, onboardingStep]);

  function updateDraftField<K extends keyof typeof defaultAppDraft>(key: K, value: (typeof defaultAppDraft)[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  function updatePerson(slot: PersonSlot, key: keyof PersonDraft, value: string) {
    setDraft((current) => ({
      ...current,
      [slot]: {
        ...current[slot],
        [key]: value,
      },
    }));
  }

  function applyAccountPreferences(preferences: AuthState['preferences']) {
    setDraft((current) => ({
      ...current,
      includeJungian: preferences.include_jungian_default,
      includeRedBookPrompts: preferences.include_red_book_prompts_default,
    }));
  }

  async function resolveBirthplace(slot: PersonSlot) {
    const person = draft[slot];
    setError(null);
    if (!person.birthCity.trim() || !person.birthCountry.trim()) {
      setError('Enter birth city and country before resolving place data.');
      return;
    }

    setHelperLoading(true);
    try {
      const data = await resolvePlace(draft.apiBaseUrl, person, authState.token);
      const resolved = data.resolved_place;
      if (!resolved) {
        throw new Error('Birthplace resolution returned no usable result.');
      }
      setPlaceCandidates((current) => ({ ...current, [slot]: data.place_candidates ?? [] }));
      setDraft((current) => ({
        ...current,
        [slot]: {
          ...current[slot],
          latitude: String(resolved.latitude),
          longitude: String(resolved.longitude),
          timezoneName: resolved.timezone_name ?? current[slot].timezoneName,
          utcOffset: resolved.utc_offset ?? current[slot].utcOffset,
        },
      }));
      setSaveMessage(data.notes.join(' '));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Birthplace resolution failed.');
    } finally {
      setHelperLoading(false);
    }
  }

  function applyResolvedPlaceCandidate(slot: PersonSlot, candidate: NonNullable<PlaceResolveResponse['place_candidates']>[number]) {
    setDraft((current) => ({
      ...current,
      [slot]: {
        ...current[slot],
        latitude: String(candidate.latitude),
        longitude: String(candidate.longitude),
        timezoneName: candidate.timezone_name ?? current[slot].timezoneName,
        utcOffset: candidate.utc_offset ?? current[slot].utcOffset,
      },
    }));
    setSaveMessage(`Birthplace set to ${candidate.normalized_name}.`);
  }

  async function useCurrentLocation(slot: PersonSlot) {
    setError(null);
    setHelperLoading(true);
    try {
      const permission = await Location.requestForegroundPermissionsAsync();
      if (permission.status !== 'granted') {
        throw new Error('Location permission was not granted.');
      }
      const currentLocation = await Location.getCurrentPositionAsync({});
      setDraft((current) => ({
        ...current,
        [slot]: {
          ...current[slot],
          currentLatitude: currentLocation.coords.latitude.toFixed(6),
          currentLongitude: currentLocation.coords.longitude.toFixed(6),
          currentTimezoneName: getDeviceTimezoneName() || current[slot].currentTimezoneName,
          currentUtcOffset: formatUtcOffset(),
        },
      }));
      setSaveMessage('Current transit location filled from this device. Birthplace inputs were left untouched.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Current-location lookup failed.');
    } finally {
      setHelperLoading(false);
    }
  }

  function useDeviceOffset(slot: PersonSlot) {
    updatePerson(slot, 'utcOffset', formatUtcOffset());
    updatePerson(slot, 'currentUtcOffset', formatUtcOffset());
    updatePerson(slot, 'currentTimezoneName', getDeviceTimezoneName());
    setSaveMessage('UTC offset filled from this device. Review it for historical birth data.');
  }

  function savePerson(slot: PersonSlot) {
    const person = draft[slot];
    const normalizedLabel = person.profileLabel.trim() || `${person.name || slot} — ${person.birthCity || 'Unknown'}`;
    const nextPerson: SavedPerson = {
      id: normalizedLabel.toLowerCase().replace(/\s+/g, '-'),
      label: normalizedLabel,
      person: { ...person, profileLabel: normalizedLabel },
      savedAt: new Date().toISOString(),
    };
    setSavedPeople((current) => {
      const idx = current.findIndex((entry) => entry.id === nextPerson.id);
      if (idx === -1) return [nextPerson, ...current];
      const copy = [...current];
      copy[idx] = nextPerson;
      return copy;
    });
    updatePerson(slot, 'profileLabel', normalizedLabel);
    setSaveMessage(`Saved profile: ${normalizedLabel}.`);
  }

  function loadSavedPerson(saved: SavedPerson, slot: PersonSlot) {
    setDraft((current) => ({ ...current, [slot]: saved.person }));
    setSaveMessage(`Loaded ${saved.label} into ${slot === 'primary' ? 'Person A' : 'Person B'}.`);
  }

  function deleteSavedPerson(id: string) {
    setSavedPeople((current) => current.filter((entry) => entry.id !== id));
    setSaveMessage('Saved person removed.');
  }

  function syncResolvedPerson(slot: PersonSlot, profile?: BasicProfileResponse) {
    if (!profile) return;
    setDraft((current) => ({
      ...current,
      [slot]: {
        ...current[slot],
        latitude: typeof profile.latitude === 'number' ? String(profile.latitude) : current[slot].latitude,
        longitude: typeof profile.longitude === 'number' ? String(profile.longitude) : current[slot].longitude,
        utcOffset: profile.utc_offset ?? current[slot].utcOffset,
        timezoneName: profile.timezone_name ?? current[slot].timezoneName,
      },
    }));
  }

  async function submitReading() {
    setError(null);
    setResult(null);
    try {
      const reading = await requestReading(draft.apiBaseUrl, draft, authState.token);
      setResult(reading);
      syncResolvedPerson('primary', reading.profile || reading.primary_profile);
      syncResolvedPerson('secondary', reading.secondary_profile);
      return reading;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to reach the API.';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }

  async function generateReading() {
    setLoading(true);
    try {
      return await submitReading();
    } finally {
      setLoading(false);
    }
  }

  async function resetDraft() {
    const reset = {
      ...defaultAppDraft,
      includeJungian: authState.preferences.include_jungian_default,
      includeRedBookPrompts: authState.preferences.include_red_book_prompts_default,
      apiBaseUrl: resolveApiBaseUrl(draft.apiBaseUrl),
    };
    setDraft(reset);
    setPlaceCandidates({ primary: [], secondary: [] });
    setResult(null);
    setOnboardingStep(0);
    setError(null);
    await AsyncStorage.setItem(APP_DRAFT_STORAGE_KEY, JSON.stringify(reset));
    setSaveMessage('Draft reset to defaults.');
  }

  function setResultFromHistory(reading: AnyReadingResponse) {
    setResult(reading);
    syncResolvedPerson('primary', reading.profile || reading.primary_profile);
    syncResolvedPerson('secondary', reading.secondary_profile);
    setError(null);
  }

  return {
    draft,
    savedPeople,
    onboardingStep,
    loading,
    helperLoading,
    placeCandidates,
    saveMessage,
    error,
    result,
    canAdvance,
    stepLabels,
    maxStepIndex,
    draftLoaded,
    setOnboardingStep,
    setSaveMessage,
    setError,
    updateDraftField,
    updatePerson,
    applyAccountPreferences,
    resolveBirthplace,
    applyResolvedPlaceCandidate,
    useCurrentLocation,
    useDeviceOffset,
    savePerson,
    loadSavedPerson,
    deleteSavedPerson,
    generateReading,
    resetDraft,
    setResultFromHistory,
    nextStep: () => setOnboardingStep((current) => Math.min(current + 1, maxStepIndex)),
    previousStep: () => setOnboardingStep((current) => Math.max(current - 1, 0)),
  };
}
