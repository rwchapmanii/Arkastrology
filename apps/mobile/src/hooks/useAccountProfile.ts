import { useEffect, useState } from 'react';
import { fetchAccountProfile, updateAccountProfile } from '../services/api';
import { AuthState } from '../types/app';

export type AccountProfileDraft = {
  displayName: string;
  timezoneName: string;
  bio: string;
};

export function useAccountProfile(authState: AuthState) {
  const [profileDraft, setProfileDraft] = useState<AccountProfileDraft>({ displayName: '', timezoneName: '', bio: '' });
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);

  async function refreshProfile(apiBaseUrl?: string) {
    if (authState.mode !== 'authenticated' || !authState.token || !(apiBaseUrl || authState.apiBaseUrl)) {
      setProfileDraft({ displayName: '', timezoneName: '', bio: '' });
      return null;
    }
    setProfileLoading(true);
    setProfileError(null);
    try {
      const response = await fetchAccountProfile(apiBaseUrl || authState.apiBaseUrl || '', authState.token);
      const next = {
        displayName: response.profile.display_name || '',
        timezoneName: response.profile.timezone_name || '',
        bio: response.profile.bio || '',
      };
      setProfileDraft(next);
      return response.profile;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not load account profile.';
      setProfileError(message);
      throw err;
    } finally {
      setProfileLoading(false);
    }
  }

  async function saveProfile(apiBaseUrl?: string) {
    if (authState.mode !== 'authenticated' || !authState.token || !(apiBaseUrl || authState.apiBaseUrl)) {
      throw new Error('Sign in to save an account profile.');
    }
    setProfileLoading(true);
    setProfileError(null);
    try {
      const response = await updateAccountProfile(apiBaseUrl || authState.apiBaseUrl || '', authState.token, {
        display_name: profileDraft.displayName,
        timezone_name: profileDraft.timezoneName,
        bio: profileDraft.bio,
      });
      setProfileDraft({
        displayName: response.profile.display_name || '',
        timezoneName: response.profile.timezone_name || '',
        bio: response.profile.bio || '',
      });
      return response.profile;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not save account profile.';
      setProfileError(message);
      throw err;
    } finally {
      setProfileLoading(false);
    }
  }

  useEffect(() => {
    if (authState.mode !== 'authenticated' || !authState.token || !authState.apiBaseUrl) {
      setProfileDraft({ displayName: authState.displayName || '', timezoneName: authState.timezoneName || '', bio: authState.bio || '' });
      return;
    }
    void refreshProfile(authState.apiBaseUrl).catch(() => {});
  }, [authState.mode, authState.token, authState.apiBaseUrl]);

  return {
    profileDraft,
    profileLoading,
    profileError,
    setProfileError,
    setProfileField: (key: keyof AccountProfileDraft, value: string) => setProfileDraft((current) => ({ ...current, [key]: value })),
    refreshProfile,
    saveProfile,
  };
}
