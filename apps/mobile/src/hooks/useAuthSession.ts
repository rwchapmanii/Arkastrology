import AsyncStorage from '@react-native-async-storage/async-storage';
import { useEffect, useState } from 'react';
import {
  confirmEmailVerification,
  confirmPasswordReset,
  fetchSession,
  loginWithPassword,
  logoutSession,
  registerWithPassword,
  requestEmailVerification,
  requestPasswordReset,
  updateAccountPreferences,
} from '../services/api';
import { clearStoredAuthToken, getStoredAuthToken, setStoredAuthToken } from '../services/secureStorage';
import { AuthState } from '../types/app';
import { AUTH_STORAGE_KEY, LEGACY_AUTH_STORAGE_KEYS, defaultAuthState } from '../utils/app';

async function readStoredAuthState() {
  const current = await AsyncStorage.getItem(AUTH_STORAGE_KEY);
  if (current) return current;

  for (const legacyKey of LEGACY_AUTH_STORAGE_KEYS) {
    const legacyValue = await AsyncStorage.getItem(legacyKey);
    if (legacyValue) {
      await AsyncStorage.setItem(AUTH_STORAGE_KEY, legacyValue);
      return legacyValue;
    }
  }

  return null;
}

function buildSessionState(session: {
  account: {
    user_id: string;
    email: string;
    display_name?: string | null;
    plan: string;
    preferences: AuthState['preferences'];
    email_verified: boolean;
    timezone_name?: string | null;
    bio?: string | null;
  };
  session_expires_at: string;
}, token: string, apiBaseUrl: string): AuthState {
  return {
    mode: 'authenticated',
    userId: session.account.user_id,
    email: session.account.email,
    token,
    apiBaseUrl: apiBaseUrl.trim(),
    displayName: session.account.display_name ?? undefined,
    plan: session.account.plan,
    sessionExpiresAt: session.session_expires_at,
    emailVerified: session.account.email_verified,
    timezoneName: session.account.timezone_name ?? undefined,
    bio: session.account.bio ?? undefined,
    preferences: session.account.preferences,
  };
}

export function useAuthSession() {
  const [authState, setAuthState] = useState<AuthState>(defaultAuthState);
  const [authReady, setAuthReady] = useState(false);
  const [restoreError, setRestoreError] = useState<string | null>(null);

  async function clearPersistedAuthState() {
    await Promise.all([AsyncStorage.removeItem(AUTH_STORAGE_KEY), clearStoredAuthToken()]);
  }

  useEffect(() => {
    async function restore() {
      try {
        const [saved, secureToken] = await Promise.all([
          readStoredAuthState(),
          getStoredAuthToken(),
        ]);
        if (!saved) {
          setAuthReady(true);
          return;
        }

        const rawParsed = JSON.parse(saved) as Partial<AuthState>;
        const parsed = {
          ...defaultAuthState,
          ...rawParsed,
          token: secureToken || undefined,
          preferences: {
            ...defaultAuthState.preferences,
            ...(rawParsed.preferences || {}),
          },
        } as AuthState;

        if (parsed.mode === 'authenticated') {
          if (!parsed.token || !parsed.apiBaseUrl) {
            setAuthState(defaultAuthState);
            setRestoreError(null);
            await clearPersistedAuthState();
          } else {
            try {
              const restored = await fetchSession(parsed.apiBaseUrl, parsed.token);
              setAuthState(buildSessionState(restored, parsed.token, parsed.apiBaseUrl));
            } catch {
              setAuthState(defaultAuthState);
              setRestoreError(null);
              await clearPersistedAuthState();
            }
          }
        } else {
          setAuthState(parsed);
        }
      } catch {
        setAuthState(defaultAuthState);
        setRestoreError(null);
        await clearPersistedAuthState();
      } finally {
        setAuthReady(true);
      }
    }

    void restore();
  }, []);

  useEffect(() => {
    if (!authReady) return;
    const persistedState: AuthState = {
      ...authState,
      token: undefined,
    };
    void AsyncStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(persistedState));
  }, [authReady, authState]);

  async function continueAsGuest(apiBaseUrl: string) {
    await clearStoredAuthToken();
    const nextState: AuthState = {
      ...defaultAuthState,
      mode: 'guest',
      apiBaseUrl: apiBaseUrl.trim(),
    };
    setAuthState(nextState);
    return nextState;
  }

  async function refreshSession(apiBaseUrl?: string) {
    const effectiveBaseUrl = apiBaseUrl || authState.apiBaseUrl;
    if (authState.mode !== 'authenticated' || !authState.token || !effectiveBaseUrl) {
      return authState;
    }
    const response = await fetchSession(effectiveBaseUrl, authState.token);
    const nextState = buildSessionState(response, authState.token, effectiveBaseUrl);
    setAuthState(nextState);
    return nextState;
  }

  async function authenticate(mode: 'sign in' | 'register', apiBaseUrl: string, email: string, password: string) {
    const cleanEmail = email.trim();
    if (!cleanEmail) {
      throw new Error(`Enter an email to ${mode}.`);
    }
    if (password.trim().length < 8) {
      throw new Error('Use a password with at least 8 characters.');
    }

    const response = mode === 'register'
      ? await registerWithPassword(apiBaseUrl, cleanEmail, password)
      : await loginWithPassword(apiBaseUrl, cleanEmail, password);

    const nextState = buildSessionState(response, response.session_token, apiBaseUrl);
    await setStoredAuthToken(response.session_token);
    setAuthState(nextState);
    setRestoreError(null);
    return { state: nextState, notes: response.notes };
  }

  async function signOut(apiBaseUrl?: string) {
    if (authState.mode === 'authenticated' && authState.token) {
      try {
        await logoutSession(apiBaseUrl || authState.apiBaseUrl || '', authState.token);
      } catch {
        // Clear local session even if the backend is unavailable.
      }
    }
    setAuthState(defaultAuthState);
    await Promise.all([AsyncStorage.removeItem(AUTH_STORAGE_KEY), clearStoredAuthToken()]);
  }

  async function savePreferences(apiBaseUrl: string, updates: Partial<AuthState['preferences']>) {
    if (authState.mode === 'authenticated' && authState.token) {
      const response = await updateAccountPreferences(apiBaseUrl, authState.token, updates);
      const nextState: AuthState = {
        ...authState,
        apiBaseUrl: apiBaseUrl.trim(),
        preferences: response.preferences,
      };
      setAuthState(nextState);
      return nextState;
    }

    const nextState: AuthState = {
      ...authState,
      mode: authState.mode === 'signed_out' ? 'guest' : authState.mode,
      apiBaseUrl: apiBaseUrl.trim(),
      preferences: {
        ...authState.preferences,
        ...updates,
      },
    };
    setAuthState(nextState);
    return nextState;
  }

  async function sendVerification(apiBaseUrl: string, email: string) {
    return requestEmailVerification(apiBaseUrl, email);
  }

  async function verifyEmail(apiBaseUrl: string, email: string, token: string) {
    const response = await confirmEmailVerification(apiBaseUrl, email, token);
    if (authState.mode === 'authenticated' && authState.email?.toLowerCase() === email.trim().toLowerCase()) {
      await refreshSession(apiBaseUrl);
    }
    return response;
  }

  async function sendPasswordReset(apiBaseUrl: string, email: string) {
    return requestPasswordReset(apiBaseUrl, email);
  }

  async function resetPassword(apiBaseUrl: string, email: string, token: string, newPassword: string) {
    const response = await confirmPasswordReset(apiBaseUrl, email, token, newPassword);
    if (authState.email?.toLowerCase() === email.trim().toLowerCase()) {
      await signOut(apiBaseUrl);
    }
    return response;
  }

  return {
    authState,
    authReady,
    restoreError,
    clearRestoreError: () => setRestoreError(null),
    continueAsGuest,
    authenticate,
    signOut,
    savePreferences,
    refreshSession,
    sendVerification,
    verifyEmail,
    sendPasswordReset,
    resetPassword,
  };
}
