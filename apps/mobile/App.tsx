import React, { useEffect, useMemo, useState } from 'react';
import { SafeAreaView, ScrollView, StatusBar, StyleSheet, Text, View } from 'react-native';
import { BrandMark } from './src/components/BrandMark';
import { PrimaryButton, SurfaceCard } from './src/components/common';
import { palette } from './src/constants/theme';
import { useAccountProfile } from './src/hooks/useAccountProfile';
import { useAuthSession } from './src/hooks/useAuthSession';
import { useReadingHistory } from './src/hooks/useReadingHistory';
import { useReadingWorkspace } from './src/hooks/useReadingWorkspace';
import { AccountScreen } from './src/screens/AccountScreen';
import { AuthScreen } from './src/screens/AuthScreen';
import { DetailScreen } from './src/screens/DetailScreen';
import { OnboardingScreen } from './src/screens/OnboardingScreen';
import { ReadingHistoryScreen } from './src/screens/ReadingHistoryScreen';
import { ReadingScreen } from './src/screens/ReadingScreen';
import { TechnicalChartScreen } from './src/screens/TechnicalChartScreen';
import { InterpretationBlock, ScreenMode } from './src/types/app';

export default function App() {
  const {
    authState,
    authReady,
    restoreError,
    clearRestoreError,
    continueAsGuest,
    authenticate,
    signOut,
    savePreferences,
    refreshSession,
    sendVerification,
    verifyEmail,
    sendPasswordReset,
    resetPassword,
  } = useAuthSession();
  const workspace = useReadingWorkspace(authState);
  const readingHistory = useReadingHistory(authState);
  const accountProfile = useAccountProfile(authState);

  const [screenMode, setScreenMode] = useState<ScreenMode>('auth');
  const [authMode, setAuthMode] = useState<'sign in' | 'register'>('sign in');
  const [selectedBlock, setSelectedBlock] = useState<InterpretationBlock | null>(null);
  const [emailDraft, setEmailDraft] = useState('');
  const [passwordDraft, setPasswordDraft] = useState('');
  const [verificationTokenDraft, setVerificationTokenDraft] = useState('');
  const [resetTokenDraft, setResetTokenDraft] = useState('');
  const [newPasswordDraft, setNewPasswordDraft] = useState('');

  const combinedMessage = useMemo(
    () => restoreError || workspace.error || readingHistory.historyError || accountProfile.profileError || workspace.saveMessage,
    [restoreError, workspace.error, readingHistory.historyError, accountProfile.profileError, workspace.saveMessage],
  );
  const isError = Boolean(restoreError || workspace.error || readingHistory.historyError || accountProfile.profileError);

  useEffect(() => {
    if (!authReady || !workspace.draftLoaded) return;
    if (authState.mode === 'signed_out') {
      setScreenMode('auth');
      return;
    }
    workspace.applyAccountPreferences(authState.preferences);
    setScreenMode(workspace.result ? 'reading' : 'onboarding');
  }, [
    authReady,
    workspace.draftLoaded,
    workspace.result,
    authState.mode,
    authState.preferences.include_jungian_default,
    authState.preferences.include_red_book_prompts_default,
  ]);

  function dismissNotice() {
    if (restoreError) clearRestoreError();
    if (workspace.error) workspace.setError(null);
    if (readingHistory.historyError) readingHistory.setHistoryError(null);
    if (accountProfile.profileError) accountProfile.setProfileError(null);
    if (workspace.saveMessage) workspace.setSaveMessage(null);
  }

  async function handleGuest() {
    const nextState = await continueAsGuest(workspace.draft.apiBaseUrl);
    workspace.applyAccountPreferences(nextState.preferences);
    setScreenMode('onboarding');
    workspace.setSaveMessage('Guest mode enabled.');
    workspace.setError(null);
  }

  async function handleAuth(mode: 'sign in' | 'register') {
    try {
      const { state, notes } = await authenticate(mode, workspace.draft.apiBaseUrl, emailDraft, passwordDraft);
      workspace.applyAccountPreferences(state.preferences);
      await Promise.all([
        readingHistory.refreshHistory({ apiBaseUrl: workspace.draft.apiBaseUrl }).catch(() => []),
        accountProfile.refreshProfile(workspace.draft.apiBaseUrl).catch(() => null),
      ]);
      workspace.setSaveMessage([
        `${mode === 'register' ? 'Account created' : 'Signed in'} as ${state.email}.`,
        ...notes,
      ].join(' '));
      workspace.setError(null);
      setPasswordDraft('');
      setScreenMode('onboarding');
    } catch (err) {
      const message = err instanceof Error ? err.message : `${mode} failed.`;
      if (mode === 'register' && message.toLowerCase().includes('already exists')) {
        setAuthMode('sign in');
        workspace.setError('An account already exists for that email. Use Sign in instead.');
        return;
      }
      workspace.setError(message);
    }
  }

  async function handleSignOut() {
    await signOut(workspace.draft.apiBaseUrl);
    setScreenMode('auth');
    workspace.setSaveMessage('Session cleared.');
    workspace.setError(null);
  }

  async function handlePreferenceChange(key: 'include_jungian_default' | 'include_red_book_prompts_default', value: boolean) {
    try {
      const nextState = await savePreferences(workspace.draft.apiBaseUrl, { [key]: value });
      workspace.applyAccountPreferences(nextState.preferences);
      workspace.setSaveMessage('Reading defaults updated.');
      workspace.setError(null);
    } catch (err) {
      workspace.setError(err instanceof Error ? err.message : 'Could not update preferences.');
    }
  }

  async function handleGenerateReading() {
    try {
      await workspace.generateReading();
      if (authState.mode === 'authenticated') {
        await readingHistory.refreshHistory({ apiBaseUrl: workspace.draft.apiBaseUrl }).catch(() => []);
      }
      setScreenMode('reading');
    } catch {
      // Error already surfaced through the workspace state.
    }
  }

  async function handleProfileSave() {
    try {
      await accountProfile.saveProfile(workspace.draft.apiBaseUrl);
      await refreshSession(workspace.draft.apiBaseUrl);
      workspace.setSaveMessage('Account profile synced.');
      workspace.setError(null);
    } catch (err) {
      workspace.setError(err instanceof Error ? err.message : 'Could not save profile.');
    }
  }

  async function handleRequestVerification() {
    try {
      const response = await sendVerification(workspace.draft.apiBaseUrl, emailDraft || authState.email || '');
      setVerificationTokenDraft(response.prototype_token || '');
      const debugNote = response.prototype_token ? ` Debug token: ${response.prototype_token}.` : '';
      workspace.setSaveMessage(`${response.notes.join(' ')} Delivery mode: ${response.delivery_mode}.${debugNote}`.trim());
      workspace.setError(null);
    } catch (err) {
      workspace.setError(err instanceof Error ? err.message : 'Could not request verification token.');
    }
  }

  async function handleConfirmVerification() {
    try {
      const response = await verifyEmail(workspace.draft.apiBaseUrl, emailDraft || authState.email || '', verificationTokenDraft);
      await refreshSession(workspace.draft.apiBaseUrl).catch(() => authState);
      workspace.setSaveMessage(response.notes.join(' ') || 'Email verified.');
      workspace.setError(null);
      setVerificationTokenDraft('');
    } catch (err) {
      workspace.setError(err instanceof Error ? err.message : 'Could not confirm verification token.');
    }
  }

  async function handleRequestPasswordReset() {
    try {
      const response = await sendPasswordReset(workspace.draft.apiBaseUrl, emailDraft || authState.email || '');
      setResetTokenDraft(response.prototype_token || '');
      const debugNote = response.prototype_token ? ` Debug token: ${response.prototype_token}.` : '';
      workspace.setSaveMessage(`${response.notes.join(' ')} Delivery mode: ${response.delivery_mode}.${debugNote}`.trim());
      workspace.setError(null);
    } catch (err) {
      workspace.setError(err instanceof Error ? err.message : 'Could not request password reset.');
    }
  }

  async function handleConfirmPasswordReset() {
    try {
      const response = await resetPassword(workspace.draft.apiBaseUrl, emailDraft || authState.email || '', resetTokenDraft, newPasswordDraft);
      workspace.setSaveMessage(`${response.notes.join(' ')} Sign in again with the new password.`);
      workspace.setError(null);
      setPasswordDraft('');
      setNewPasswordDraft('');
      setResetTokenDraft('');
      setScreenMode('auth');
    } catch (err) {
      workspace.setError(err instanceof Error ? err.message : 'Could not reset password.');
    }
  }

  function renderBody() {
    if (!authReady || !workspace.draftLoaded) {
      return (
        <SurfaceCard title="Loading" subtitle="Restoring local draft state and account session.">
          <Text style={styles.noticeText}>Bringing The Ark back into memory…</Text>
        </SurfaceCard>
      );
    }

    if (screenMode === 'auth') {
      return (
        <View style={styles.authShell}>
          <AuthScreen
            email={emailDraft}
            password={passwordDraft}
            authMode={authMode}
            onEmailChange={setEmailDraft}
            onPasswordChange={setPasswordDraft}
            onAuthModeChange={setAuthMode}
            onSignIn={() => void handleAuth('sign in')}
            onRegister={() => void handleAuth('register')}
          />
        </View>
      );
    }

    if (screenMode === 'account') {
      return (
        <AccountScreen
          authState={authState}
          savedPeople={workspace.savedPeople}
          includeJungian={workspace.draft.includeJungian}
          includeRedBookPrompts={workspace.draft.includeRedBookPrompts}
          profileDraft={accountProfile.profileDraft}
          profileLoading={accountProfile.profileLoading}
          onProfileChange={accountProfile.setProfileField}
          onSaveProfile={() => void handleProfileSave()}
          onRefreshProfile={() => void accountProfile.refreshProfile(workspace.draft.apiBaseUrl)}
          onToggleJungian={(value) => void handlePreferenceChange('include_jungian_default', value)}
          onToggleRedBook={(value) => void handlePreferenceChange('include_red_book_prompts_default', value)}
          onOpenHistory={() => setScreenMode('history')}
          onRequestVerification={() => void handleRequestVerification()}
          onBack={() => setScreenMode(workspace.result ? 'reading' : 'onboarding')}
          onSignOut={() => void handleSignOut()}
        />
      );
    }

    if (screenMode === 'detail' && selectedBlock) {
      return <DetailScreen block={selectedBlock} onBack={() => setScreenMode('reading')} />;
    }

    if (screenMode === 'history') {
      return (
        <ReadingHistoryScreen
          authState={authState}
          history={readingHistory.history}
          loading={readingHistory.historyLoading}
          error={readingHistory.historyError}
          query={readingHistory.query}
          favoriteOnly={readingHistory.favoriteOnly}
          chartTypeFilter={readingHistory.chartTypeFilter}
          tagFilter={readingHistory.tagFilter}
          totalCount={readingHistory.totalCount}
          favoritesCount={readingHistory.favoritesCount}
          hasMore={readingHistory.hasMore}
          visibleLimit={readingHistory.visibleLimit}
          availableTags={readingHistory.availableTags}
          chartTypeCounts={readingHistory.chartTypeCounts}
          onQueryChange={readingHistory.setQuery}
          onToggleFavoriteOnly={readingHistory.toggleFavoriteOnly}
          onSetChartTypeFilter={readingHistory.setChartTypeFilter}
          onSetTagFilter={readingHistory.setTagFilter}
          onClearFilters={readingHistory.clearFilters}
          onRefresh={() => void readingHistory.refreshHistory({ apiBaseUrl: workspace.draft.apiBaseUrl })}
          onLoadMore={() => void readingHistory.loadMoreHistory(workspace.draft.apiBaseUrl)}
          onOpenItem={(item) => {
            void readingHistory.loadHistoryItem(item.id, workspace.draft.apiBaseUrl).then((loaded) => {
              if (loaded) {
                workspace.setResultFromHistory(loaded.reading_payload);
                setScreenMode('reading');
              }
            }).catch((err) => {
              workspace.setError(err instanceof Error ? err.message : 'Could not open reading history item.');
            });
          }}
          onToggleFavorite={(item) => {
            void readingHistory.saveHistoryMetadata(item.id, { favorite: !item.favorite }, workspace.draft.apiBaseUrl).then((updated) => {
              workspace.setSaveMessage(updated.favorite ? 'Reading marked as favorite.' : 'Reading removed from favorites.');
            }).catch((err) => {
              workspace.setError(err instanceof Error ? err.message : 'Could not update favorite.');
            });
          }}
          onSaveTags={(item, tags) => {
            void readingHistory.saveHistoryMetadata(item.id, { tags }, workspace.draft.apiBaseUrl).then(() => {
              workspace.setSaveMessage('Reading tags updated.');
            }).catch((err) => {
              workspace.setError(err instanceof Error ? err.message : 'Could not update tags.');
            });
          }}
          onBack={() => setScreenMode('account')}
        />
      );
    }

    if (screenMode === 'technical' && workspace.result) {
      return <TechnicalChartScreen result={workspace.result} onBack={() => setScreenMode('reading')} />;
    }

    if (screenMode === 'reading' && workspace.result) {
      return (
        <ReadingScreen
          result={workspace.result}
          loading={workspace.loading}
          onEditOnboarding={() => setScreenMode('onboarding')}
          onRefresh={() => void handleGenerateReading()}
          onOpenDetail={(block) => {
            setSelectedBlock(block);
            setScreenMode('detail');
          }}
          onOpenAccount={() => setScreenMode('account')}
          onOpenTechnical={() => setScreenMode('technical')}
        />
      );
    }

    return (
      <OnboardingScreen
        draft={workspace.draft}
        onboardingStep={workspace.onboardingStep}
        helperLoading={workspace.helperLoading}
        canAdvance={workspace.canAdvance}
        stepLabels={workspace.stepLabels}
        savedPeople={workspace.savedPeople}
        placeCandidates={workspace.placeCandidates}
        onSetReadingMode={(value) => {
          workspace.updateDraftField('readingMode', value);
          workspace.setOnboardingStep(0);
        }}
        onPersonChange={workspace.updatePerson}
        onResolveBirthplace={(slot) => void workspace.resolveBirthplace(slot)}
        onApplyResolvedPlace={workspace.applyResolvedPlaceCandidate}
        onUseCurrentLocation={(slot) => void workspace.useCurrentLocation(slot)}
        onUseDeviceOffset={workspace.useDeviceOffset}
        onSavePerson={workspace.savePerson}
        onLoadSavedPerson={workspace.loadSavedPerson}
        onDeleteSavedPerson={workspace.deleteSavedPerson}
        onToggleJungian={(value) => void handlePreferenceChange('include_jungian_default', value)}
        onToggleRedBook={(value) => void handlePreferenceChange('include_red_book_prompts_default', value)}
        onNext={workspace.nextStep}
        onBack={workspace.previousStep}
        onSubmit={() => void handleGenerateReading()}
        onReset={() => void workspace.resetDraft()}
        loading={workspace.loading}
      />
    );
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="dark-content" />
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={[styles.hero, screenMode === 'auth' && styles.heroAuth]}>
          <BrandMark size={64} />
          <Text style={[styles.eyebrow, screenMode === 'auth' && styles.heroAuthText]}>The Ark</Text>
          <Text style={[styles.title, screenMode === 'auth' && styles.heroAuthText]}>Enter the chamber.</Text>
          <Text style={[styles.subtitle, screenMode === 'auth' && styles.heroAuthTextMuted]}>
            Sign in or create an account to begin.
          </Text>
        </View>

        {combinedMessage && (
          <SurfaceCard title={isError ? 'Attention' : 'Status'} subtitle={isError ? 'Something needs review before the next step.' : 'Latest local Ark update.'} accent={isError}>
            <Text style={[styles.noticeText, isError && styles.errorText]}>{combinedMessage}</Text>
            <PrimaryButton label="Dismiss" onPress={dismissNotice} />
          </SurfaceCard>
        )}

        {renderBody()}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: palette.background },
  scrollContent: {
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 40,
    gap: 18,
    width: '100%',
    maxWidth: 760,
    alignSelf: 'center',
  },
  authShell: {
    width: '100%',
    maxWidth: 460,
    alignSelf: 'center',
  },
  hero: {
    backgroundColor: palette.surface,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: palette.border,
    paddingHorizontal: 26,
    paddingVertical: 30,
    gap: 10,
    overflow: 'hidden',
  },
  heroAuth: {
    alignItems: 'center',
    paddingVertical: 42,
    maxWidth: 500,
    alignSelf: 'center',
    width: '100%',
  },
  eyebrow: {
    fontSize: 11,
    letterSpacing: 1.6,
    textTransform: 'uppercase',
    color: palette.muted,
    fontWeight: '700',
  },
  title: {
    fontSize: 34,
    lineHeight: 40,
    color: palette.ink,
    fontWeight: '700',
  },
  subtitle: {
    fontSize: 16,
    lineHeight: 24,
    color: palette.muted,
  },
  heroAuthText: {
    textAlign: 'center',
  },
  heroAuthTextMuted: {
    textAlign: 'center',
    maxWidth: 360,
  },
  noticeText: {
    fontSize: 15,
    lineHeight: 23,
    color: palette.ink,
  },
  errorText: {
    color: palette.danger,
  },
});
