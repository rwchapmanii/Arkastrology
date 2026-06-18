import { Platform } from 'react-native';
import { AppDraft, AuthState, PersonDraft, ReadingMode } from '../types/app';

export const APP_DRAFT_STORAGE_KEY = 'the_ark_app_draft_v1';
export const PERSON_STORAGE_KEY = 'the_ark_people_v1';
export const AUTH_STORAGE_KEY = 'the_ark_auth_v1';

export const LEGACY_APP_DRAFT_STORAGE_KEYS = ['jung_tetrabiblos_app_draft_v4'];
export const LEGACY_PERSON_STORAGE_KEYS = ['jung_tetrabiblos_people_v1'];
export const LEGACY_AUTH_STORAGE_KEYS = ['jung_tetrabiblos_auth_v2'];

function normalizeUrl(value: string) {
  return value.trim().replace(/\/$/, '');
}

function isLoopbackUrl(value: string) {
  return /https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?$/i.test(normalizeUrl(value));
}

function isNonLocalWebRuntime() {
  return Platform.OS === 'web'
    && typeof window !== 'undefined'
    && window.location.hostname !== 'localhost'
    && window.location.hostname !== '127.0.0.1';
}

export function getDefaultApiBaseUrl() {
  const configured = process.env.EXPO_PUBLIC_API_BASE_URL?.trim();
  if (configured) return normalizeUrl(configured);

  if (Platform.OS !== 'web' || typeof window === 'undefined') {
    return 'http://127.0.0.1:8000';
  }

  const { protocol, hostname, origin } = window.location;
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return `${protocol}//${hostname}:8000`;
  }

  return origin;
}

export function resolveApiBaseUrl(candidate?: string) {
  const configured = process.env.EXPO_PUBLIC_API_BASE_URL?.trim();
  if (configured && isNonLocalWebRuntime()) {
    return normalizeUrl(configured);
  }

  const cleanCandidate = candidate?.trim();
  if (!cleanCandidate) {
    return getDefaultApiBaseUrl();
  }

  const normalizedCandidate = normalizeUrl(cleanCandidate);
  if (
    isNonLocalWebRuntime() &&
    isLoopbackUrl(normalizedCandidate) &&
    !configured
  ) {
    return getDefaultApiBaseUrl();
  }

  return normalizedCandidate;
}

export const defaultAuthState: AuthState = {
  mode: 'signed_out',
  preferences: {
    include_jungian_default: false,
    include_red_book_prompts_default: false,
  },
};

export const blankPerson = (label: string, defaults?: Partial<PersonDraft>): PersonDraft => ({
  profileLabel: label,
  name: '',
  birthDate: '',
  birthTime: '',
  birthCity: '',
  birthCountry: '',
  timePrecision: 'exact',
  latitude: '',
  longitude: '',
  utcOffset: '',
  timezoneName: '',
  currentLatitude: '',
  currentLongitude: '',
  currentUtcOffset: '',
  currentTimezoneName: '',
  ...defaults,
});

export const defaultAppDraft: AppDraft = {
  apiBaseUrl: getDefaultApiBaseUrl(),
  readingMode: 'natal',
  includeJungian: false,
  includeRedBookPrompts: false,
  primary: blankPerson('Person A', {
    name: 'Ron',
    profileLabel: 'Ron — Detroit',
    birthDate: '1979-01-01',
    birthTime: '12:00',
    birthCity: 'Detroit',
    birthCountry: 'USA',
  }),
  secondary: blankPerson('Person B', {
    name: 'Andrea',
    profileLabel: 'Andrea — Chicago',
    birthDate: '1981-05-10',
    birthTime: '09:30',
    birthCity: 'Chicago',
    birthCountry: 'USA',
  }),
};

export function formatUtcOffset(date = new Date()) {
  const minutes = -date.getTimezoneOffset();
  const sign = minutes >= 0 ? '+' : '-';
  const absolute = Math.abs(minutes);
  const hours = String(Math.floor(absolute / 60)).padStart(2, '0');
  const remainder = String(absolute % 60).padStart(2, '0');
  return `${sign}${hours}:${remainder}`;
}

export function getDeviceTimezoneName() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || '';
  } catch {
    return '';
  }
}

export function getStepLabels(mode: ReadingMode) {
  return mode === 'synastry' ? ['Setup', 'Review'] : ['Setup', 'Review'];
}
