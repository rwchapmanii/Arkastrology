import { useEffect, useState } from 'react';
import { AuthState, DirectoryProfile, RelationshipEntry } from '../types/app';
import {
  addRelationship,
  fetchPublicChartProfile,
  fetchRelationships,
  removeRelationship,
  savePublicChartProfile,
  searchDirectoryProfiles,
} from '../services/api';
import { PersonDraft } from '../types/app';

type PublicDraft = {
  headline: string;
  biography: string;
  isDiscoverable: boolean;
};

function buildPersonPayload(person: PersonDraft) {
  const payload: Record<string, string | number> = {
    name: person.name,
    birth_date: person.birthDate,
    birth_time: person.birthTime.trim() || (person.timePrecision.trim().toLowerCase() === 'exact' ? '' : '12:00'),
    birth_city: person.birthCity,
    birth_country: person.birthCountry,
    time_precision: person.timePrecision.trim().toLowerCase() || 'approximate',
  };
  const numberFields: Array<[keyof PersonDraft, string]> = [
    ['latitude', 'latitude'],
    ['longitude', 'longitude'],
    ['currentLatitude', 'current_latitude'],
    ['currentLongitude', 'current_longitude'],
  ];
  for (const [sourceKey, targetKey] of numberFields) {
    const value = person[sourceKey].trim();
    if (value) payload[targetKey] = Number(value);
  }
  if (person.utcOffset.trim()) payload.utc_offset = person.utcOffset.trim();
  if (person.timezoneName.trim()) payload.timezone_name = person.timezoneName.trim();
  if (person.currentUtcOffset.trim()) payload.current_utc_offset = person.currentUtcOffset.trim();
  if (person.currentTimezoneName.trim()) payload.current_timezone_name = person.currentTimezoneName.trim();
  return payload;
}

export function useRelationshipDirectory(authState: AuthState) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<DirectoryProfile[]>([]);
  const [relationships, setRelationships] = useState<RelationshipEntry[]>([]);
  const [publicDraft, setPublicDraft] = useState<PublicDraft>({ headline: '', biography: '', isDiscoverable: true });
  const [directoryLoading, setDirectoryLoading] = useState(false);
  const [relationshipLoading, setRelationshipLoading] = useState(false);
  const [publicProfileLoading, setPublicProfileLoading] = useState(false);
  const [publicProfileId, setPublicProfileId] = useState<string | null>(null);
  const [directoryError, setDirectoryError] = useState<string | null>(null);

  const canUseDirectory = authState.mode === 'authenticated' && !!authState.token && !!authState.apiBaseUrl;

  async function refreshRelationships(apiBaseUrl?: string) {
    if (!canUseDirectory || !(apiBaseUrl || authState.apiBaseUrl) || !authState.token) return [];
    setRelationshipLoading(true);
    try {
      const response = await fetchRelationships(apiBaseUrl || authState.apiBaseUrl || '', authState.token);
      setRelationships(response.items);
      return response.items;
    } catch (err) {
      setDirectoryError(err instanceof Error ? err.message : 'Could not load relationships.');
      return [];
    } finally {
      setRelationshipLoading(false);
    }
  }

  async function refreshPublicProfile(apiBaseUrl?: string) {
    if (!canUseDirectory || !(apiBaseUrl || authState.apiBaseUrl) || !authState.token) return null;
    setPublicProfileLoading(true);
    try {
      const response = await fetchPublicChartProfile(apiBaseUrl || authState.apiBaseUrl || '', authState.token);
      setPublicProfileId(response.public_profile?.profile_id || null);
      setPublicDraft({
        headline: response.public_profile?.headline || '',
        biography: response.public_profile?.biography || '',
        isDiscoverable: response.public_profile?.is_discoverable ?? true,
      });
      return response.public_profile || null;
    } catch (err) {
      setDirectoryError(err instanceof Error ? err.message : 'Could not load public chart profile.');
      return null;
    } finally {
      setPublicProfileLoading(false);
    }
  }

  async function searchDirectory(apiBaseUrl?: string, nextQuery?: string) {
    if (!canUseDirectory || !(apiBaseUrl || authState.apiBaseUrl) || !authState.token) return [];
    setDirectoryLoading(true);
    setDirectoryError(null);
    try {
      const response = await searchDirectoryProfiles(apiBaseUrl || authState.apiBaseUrl || '', authState.token, nextQuery ?? query, 24);
      setResults(response.items);
      return response.items;
    } catch (err) {
      setDirectoryError(err instanceof Error ? err.message : 'Could not search the directory.');
      return [];
    } finally {
      setDirectoryLoading(false);
    }
  }

  async function addRelationshipEntry(profileId: string, apiBaseUrl?: string) {
    if (!canUseDirectory || !(apiBaseUrl || authState.apiBaseUrl) || !authState.token) {
      throw new Error('Sign in to add people to relationships.');
    }
    setRelationshipLoading(true);
    setDirectoryError(null);
    try {
      const response = await addRelationship(apiBaseUrl || authState.apiBaseUrl || '', authState.token, profileId);
      setRelationships(response.items);
      setResults((current) => current.map((item) => item.profile_id === profileId ? { ...item, relationship_added: true } : item));
      return response.items;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not add relationship.';
      setDirectoryError(message);
      throw new Error(message);
    } finally {
      setRelationshipLoading(false);
    }
  }

  async function removeRelationshipEntry(profileId: string, apiBaseUrl?: string) {
    if (!canUseDirectory || !(apiBaseUrl || authState.apiBaseUrl) || !authState.token) {
      throw new Error('Sign in to remove people from relationships.');
    }
    setRelationshipLoading(true);
    setDirectoryError(null);
    try {
      const response = await removeRelationship(apiBaseUrl || authState.apiBaseUrl || '', authState.token, profileId);
      setRelationships(response.items);
      setResults((current) => current.map((item) => item.profile_id === profileId ? { ...item, relationship_added: false } : item));
      return response.items;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not remove relationship.';
      setDirectoryError(message);
      throw new Error(message);
    } finally {
      setRelationshipLoading(false);
    }
  }

  async function publishFromPerson(person: PersonDraft, apiBaseUrl?: string) {
    if (!canUseDirectory || !(apiBaseUrl || authState.apiBaseUrl) || !authState.token) {
      throw new Error('Sign in to publish your chart profile.');
    }
    setPublicProfileLoading(true);
    setDirectoryError(null);
    try {
      const response = await savePublicChartProfile(apiBaseUrl || authState.apiBaseUrl || '', authState.token, {
        profile: buildPersonPayload(person),
        headline: publicDraft.headline,
        biography: publicDraft.biography,
        is_discoverable: publicDraft.isDiscoverable,
      });
      setPublicProfileId(response.public_profile?.profile_id || null);
      return response.public_profile || null;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not publish chart profile.';
      setDirectoryError(message);
      throw new Error(message);
    } finally {
      setPublicProfileLoading(false);
    }
  }

  useEffect(() => {
    if (!canUseDirectory) {
      setResults([]);
      setRelationships([]);
      setPublicProfileId(null);
      return;
    }
    void Promise.all([
      refreshRelationships(authState.apiBaseUrl),
      refreshPublicProfile(authState.apiBaseUrl),
      searchDirectory(authState.apiBaseUrl, ''),
    ]);
  }, [canUseDirectory, authState.apiBaseUrl, authState.token]);

  return {
    query,
    setQuery,
    results,
    relationships,
    publicDraft,
    publicProfileId,
    directoryLoading,
    relationshipLoading,
    publicProfileLoading,
    directoryError,
    canUseDirectory,
    setPublicDraft,
    setDirectoryError,
    refreshRelationships,
    refreshPublicProfile,
    searchDirectory,
    addRelationshipEntry,
    removeRelationshipEntry,
    publishFromPerson,
  };
}
