import {
  AccountProfileResponse,
  AnyReadingResponse,
  AuthSessionResponse,
  AuthState,
  GroundedChatResponse,
  GroundedChatTurn,
  PasswordResetConfirmResponse,
  PlaceResolveResponse,
  ReadingHistoryDetailResponse,
  ReadingHistoryListResponse,
  SessionStatusResponse,
  TokenDeliveryResponse,
  VerificationConfirmResponse,
} from '../types/app';
import { AppDraft, PersonDraft } from '../types/app';
import { sanitizeReadingHistoryDetailResponse, sanitizeReadingHistoryListResponse, sanitizeReadingResponse } from '../utils/reading';

function buildHeaders(sessionToken?: string, json = true) {
  return {
    ...(json ? { 'Content-Type': 'application/json' } : {}),
    ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
  };
}

function normalizeBaseUrl(baseUrl: string) {
  return baseUrl.trim().replace(/\/$/, '');
}

async function readError(response: Response) {
  try {
    const data = (await response.json()) as { detail?: string };
    return data.detail || `Request failed (${response.status}).`;
  } catch {
    return `Request failed (${response.status}).`;
  }
}

async function requestJson<T>(baseUrl: string, path: string, init: RequestInit = {}) {
  const normalizedBaseUrl = normalizeBaseUrl(baseUrl);
  let response: Response;
  try {
    response = await fetch(`${normalizedBaseUrl}${path}`, init);
  } catch (error) {
    const reason = error instanceof Error && error.message ? error.message : 'Network request failed.';
    throw new Error(`Could not reach The Ark API at ${normalizedBaseUrl}. Make sure the local API server is running. ${reason}`);
  }
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as T;
}

function buildPersonPayload(person: PersonDraft) {
  const normalizedPrecision = person.timePrecision.trim().toLowerCase() || 'approximate';
  const normalizedBirthTime = person.birthTime.trim() || (normalizedPrecision === 'exact' ? '' : '12:00');
  const latitude = person.latitude.trim() ? Number(person.latitude) : undefined;
  const longitude = person.longitude.trim() ? Number(person.longitude) : undefined;
  const currentLatitude = person.currentLatitude.trim() ? Number(person.currentLatitude) : undefined;
  const currentLongitude = person.currentLongitude.trim() ? Number(person.currentLongitude) : undefined;
  if ((person.latitude.trim() && Number.isNaN(latitude)) || (person.longitude.trim() && Number.isNaN(longitude))) {
    throw new Error('Latitude and longitude must be valid decimal numbers when provided.');
  }
  if ((person.currentLatitude.trim() && Number.isNaN(currentLatitude)) || (person.currentLongitude.trim() && Number.isNaN(currentLongitude))) {
    throw new Error('Current latitude and longitude must be valid decimal numbers when provided.');
  }

  const payload: Record<string, string | number> = {
    name: person.name,
    birth_date: person.birthDate,
    birth_time: normalizedBirthTime,
    birth_city: person.birthCity,
    birth_country: person.birthCountry,
    time_precision: normalizedPrecision,
  };

  if (typeof latitude === 'number') payload.latitude = latitude;
  if (typeof longitude === 'number') payload.longitude = longitude;
  if (person.utcOffset.trim()) payload.utc_offset = person.utcOffset.trim();
  if (person.timezoneName.trim()) payload.timezone_name = person.timezoneName.trim();
  if (typeof currentLatitude === 'number') payload.current_latitude = currentLatitude;
  if (typeof currentLongitude === 'number') payload.current_longitude = currentLongitude;
  if (person.currentUtcOffset.trim()) payload.current_utc_offset = person.currentUtcOffset.trim();
  if (person.currentTimezoneName.trim()) payload.current_timezone_name = person.currentTimezoneName.trim();
  return payload;
}

export async function registerWithPassword(baseUrl: string, email: string, password: string) {
  return requestJson<AuthSessionResponse>(baseUrl, '/v1/auth/register', {
    method: 'POST',
    headers: buildHeaders(undefined),
    body: JSON.stringify({ email: email.trim(), password }),
  });
}

export async function loginWithPassword(baseUrl: string, email: string, password: string) {
  return requestJson<AuthSessionResponse>(baseUrl, '/v1/auth/login', {
    method: 'POST',
    headers: buildHeaders(undefined),
    body: JSON.stringify({ email: email.trim(), password }),
  });
}

export async function fetchSession(baseUrl: string, sessionToken: string) {
  return requestJson<SessionStatusResponse>(baseUrl, '/v1/auth/session', {
    method: 'GET',
    headers: buildHeaders(sessionToken, false),
  });
}

export async function logoutSession(baseUrl: string, sessionToken: string) {
  return requestJson<{ status: string }>(baseUrl, '/v1/auth/logout', {
    method: 'POST',
    headers: buildHeaders(sessionToken, false),
  });
}

export async function requestEmailVerification(baseUrl: string, email: string) {
  return requestJson<TokenDeliveryResponse>(baseUrl, '/v1/auth/verify-email/request', {
    method: 'POST',
    headers: buildHeaders(undefined),
    body: JSON.stringify({ email: email.trim() }),
  });
}

export async function confirmEmailVerification(baseUrl: string, email: string, token: string) {
  return requestJson<VerificationConfirmResponse>(baseUrl, '/v1/auth/verify-email/confirm', {
    method: 'POST',
    headers: buildHeaders(undefined),
    body: JSON.stringify({ email: email.trim(), token: token.trim() }),
  });
}

export async function requestPasswordReset(baseUrl: string, email: string) {
  return requestJson<TokenDeliveryResponse>(baseUrl, '/v1/auth/password-reset/request', {
    method: 'POST',
    headers: buildHeaders(undefined),
    body: JSON.stringify({ email: email.trim() }),
  });
}

export async function confirmPasswordReset(baseUrl: string, email: string, token: string, newPassword: string) {
  return requestJson<PasswordResetConfirmResponse>(baseUrl, '/v1/auth/password-reset/confirm', {
    method: 'POST',
    headers: buildHeaders(undefined),
    body: JSON.stringify({ email: email.trim(), token: token.trim(), new_password: newPassword }),
  });
}

export async function updateAccountPreferences(
  baseUrl: string,
  sessionToken: string,
  preferences: Partial<AuthState['preferences']>,
) {
  return requestJson<{ status: string; preferences: AuthState['preferences'] }>(baseUrl, '/v1/account/preferences', {
    method: 'PATCH',
    headers: buildHeaders(sessionToken),
    body: JSON.stringify(preferences),
  });
}

export async function fetchAccountProfile(baseUrl: string, sessionToken: string) {
  return requestJson<AccountProfileResponse>(baseUrl, '/v1/account/profile', {
    method: 'GET',
    headers: buildHeaders(sessionToken, false),
  });
}

export async function updateAccountProfile(
  baseUrl: string,
  sessionToken: string,
  profile: { display_name?: string; timezone_name?: string; bio?: string },
) {
  return requestJson<AccountProfileResponse>(baseUrl, '/v1/account/profile', {
    method: 'PATCH',
    headers: buildHeaders(sessionToken),
    body: JSON.stringify(profile),
  });
}

export async function resolvePlace(baseUrl: string, person: PersonDraft, sessionToken?: string) {
  return requestJson<PlaceResolveResponse>(baseUrl, '/v1/places/resolve', {
    method: 'POST',
    headers: buildHeaders(sessionToken),
    body: JSON.stringify({
      city: person.birthCity,
      country: person.birthCountry,
      birth_date: person.birthDate,
      birth_time: person.birthTime,
      limit: 3,
    }),
  });
}

export async function fetchReadingHistory(
  baseUrl: string,
  sessionToken: string,
  options: {
    query?: string;
    favoriteOnly?: boolean;
    chartType?: 'all' | 'natal' | 'synastry';
    tag?: string | null;
    offset?: number;
    limit?: number;
  } = {},
) {
  const params = new URLSearchParams();
  if (options.query?.trim()) params.set('query', options.query.trim());
  if (options.favoriteOnly) params.set('favorite_only', 'true');
  if (options.chartType && options.chartType !== 'all') params.set('chart_type', options.chartType);
  if (options.tag?.trim()) params.set('tag', options.tag.trim());
  if (typeof options.offset === 'number' && options.offset > 0) params.set('offset', String(options.offset));
  if (typeof options.limit === 'number') params.set('limit', String(options.limit));
  const suffix = params.toString() ? `?${params.toString()}` : '';
  const response = await requestJson<ReadingHistoryListResponse>(baseUrl, `/v1/account/readings${suffix}`, {
    method: 'GET',
    headers: buildHeaders(sessionToken, false),
  });
  return sanitizeReadingHistoryListResponse(response);
}

export async function fetchReadingHistoryItem(baseUrl: string, sessionToken: string, readingId: string) {
  const response = await requestJson<ReadingHistoryDetailResponse>(baseUrl, `/v1/account/readings/${readingId}`, {
    method: 'GET',
    headers: buildHeaders(sessionToken, false),
  });
  return sanitizeReadingHistoryDetailResponse(response);
}

export async function updateReadingHistoryItem(
  baseUrl: string,
  sessionToken: string,
  readingId: string,
  updates: { favorite?: boolean; tags?: string[] },
) {
  return requestJson<ReadingHistoryDetailResponse>(baseUrl, `/v1/account/readings/${readingId}`, {
    method: 'PATCH',
    headers: buildHeaders(sessionToken),
    body: JSON.stringify(updates),
  });
}

export async function requestReading(baseUrl: string, draft: AppDraft, sessionToken?: string) {
  const primaryPayload = buildPersonPayload(draft.primary);
  const isNatal = draft.readingMode === 'natal';
  const path = isNatal ? '/v1/readings/natal' : '/v1/readings/synastry';
  const body = isNatal
    ? {
        profile: primaryPayload,
        include_technical: true,
        include_jungian: draft.includeJungian,
        include_red_book_prompts: draft.includeRedBookPrompts,
      }
    : {
        primary_profile: primaryPayload,
        secondary_profile: buildPersonPayload(draft.secondary),
        include_technical: true,
        include_jungian: draft.includeJungian,
        include_red_book_prompts: draft.includeRedBookPrompts,
      };

  const response = await requestJson<AnyReadingResponse>(baseUrl, path, {
    method: 'POST',
    headers: buildHeaders(sessionToken),
    body: JSON.stringify(body),
  });
  return sanitizeReadingResponse(response);
}

export async function askGroundedQuestion(
  baseUrl: string,
  question: string,
  readingPayload: AnyReadingResponse,
  history: GroundedChatTurn[] = [],
  sessionToken?: string,
) {
  return requestJson<GroundedChatResponse>(baseUrl, '/v1/chat/grounded', {
    method: 'POST',
    headers: buildHeaders(sessionToken),
    body: JSON.stringify({
      question,
      reading_payload: readingPayload,
      history,
    }),
  });
}
