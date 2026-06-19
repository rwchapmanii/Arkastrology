import { Feather } from '@expo/vector-icons';
import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { BrandMark } from '../components/BrandMark';
import { palette } from '../constants/theme';
import { Field, PrimaryButton, SecondaryButton, SurfaceCard } from '../components/common';

export function AuthScreen({
  email,
  password,
  resetToken,
  newPassword,
  authMode,
  onEmailChange,
  onPasswordChange,
  onResetTokenChange,
  onNewPasswordChange,
  onAuthModeChange,
  onSignIn,
  onRegister,
  onRequestPasswordReset,
  onConfirmPasswordReset,
}: {
  email: string;
  password: string;
  resetToken: string;
  newPassword: string;
  authMode: 'sign in' | 'register' | 'reset';
  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onResetTokenChange: (value: string) => void;
  onNewPasswordChange: (value: string) => void;
  onAuthModeChange: (value: 'sign in' | 'register' | 'reset') => void;
  onSignIn: () => void;
  onRegister: () => void;
  onRequestPasswordReset: () => void;
  onConfirmPasswordReset: () => void;
}) {
  const isRegister = authMode === 'register';
  const isReset = authMode === 'reset';

  return (
    <SurfaceCard
      title={isReset ? 'Reset password' : isRegister ? 'Create your account' : 'Sign in'}
      subtitle={isReset ? 'Request a reset code, then set a new password.' : isRegister ? 'Create an account to enter The Ark.' : 'Enter your email and password to continue into The Ark.'}
    >
      <View style={styles.stack}>
        <View style={styles.brandMarkWrap}>
          <BrandMark size={72} />
        </View>

        <View style={styles.toggleWrap}>
          <Pressable style={[styles.togglePill, authMode === 'sign in' && styles.togglePillActive]} onPress={() => onAuthModeChange('sign in')}>
            <Text style={[styles.toggleText, authMode === 'sign in' && styles.toggleTextActive]}>Sign in</Text>
          </Pressable>
          <Pressable style={[styles.togglePill, authMode === 'register' && styles.togglePillActive]} onPress={() => onAuthModeChange('register')}>
            <Text style={[styles.toggleText, authMode === 'register' && styles.toggleTextActive]}>Register</Text>
          </Pressable>
          <Pressable style={[styles.togglePill, isReset && styles.togglePillActive]} onPress={() => onAuthModeChange('reset')}>
            <Text style={[styles.toggleText, isReset && styles.toggleTextActive]}>Reset</Text>
          </Pressable>
        </View>

        <Field label="Email" value={email} onChangeText={onEmailChange} placeholder="ron@example.com" keyboardType="email-address" autoCapitalize="none" />
        {!isReset ? (
          <Field label="Password" value={password} onChangeText={onPasswordChange} placeholder="At least 8 characters" secureTextEntry autoCapitalize="none" />
        ) : (
          <>
            <Field label="Reset code" value={resetToken} onChangeText={onResetTokenChange} placeholder="6+ characters" autoCapitalize="none" />
            <Field label="New password" value={newPassword} onChangeText={onNewPasswordChange} placeholder="At least 8 characters" secureTextEntry autoCapitalize="none" />
            <View style={styles.resetActions}>
              <SecondaryButton
                label="Send reset code"
                onPress={onRequestPasswordReset}
                icon={<Feather name="mail" size={15} color={palette.ink} />}
              />
              <PrimaryButton
                label="Set new password"
                onPress={onConfirmPasswordReset}
                icon={<Feather name="key" size={15} color={palette.white} />}
              />
            </View>
          </>
        )}

        {!isReset ? (
          <>
            <PrimaryButton
              label={isRegister ? 'Create account' : 'Sign in'}
              onPress={isRegister ? onRegister : onSignIn}
              icon={<Feather name={isRegister ? 'user-plus' : 'log-in'} size={15} color={palette.white} />}
            />
            {!isRegister ? (
              <Pressable onPress={() => onAuthModeChange('reset')}>
                <Text style={styles.resetLink}>Forgot password?</Text>
              </Pressable>
            ) : null}
          </>
        ) : null}

        <Text style={styles.caption}>
          {isReset
            ? 'Request the reset code at the email above, then enter the code and your new password here.'
            : isRegister
            ? 'Use the fields above to create a new Ark account.'
            : 'Use your existing Ark email and password to continue into The Ark.'}
        </Text>
      </View>
    </SurfaceCard>
  );
}

const styles = StyleSheet.create({
  stack: { gap: 18 },
  brandMarkWrap: { alignItems: 'center', marginBottom: 6 },
  toggleWrap: {
    flexDirection: 'row',
    backgroundColor: palette.surface,
    borderWidth: 1,
    borderColor: palette.border,
    borderRadius: 16,
    padding: 4,
    gap: 4,
  },
  togglePill: {
    flex: 1,
    minHeight: 42,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  togglePillActive: {
    backgroundColor: palette.action,
  },
  toggleText: { fontSize: 13, lineHeight: 17, fontWeight: '700', color: palette.muted },
  toggleTextActive: { color: palette.white },
  resetActions: { gap: 10 },
  resetLink: { fontSize: 13, lineHeight: 18, color: palette.action, fontWeight: '700', textAlign: 'center' },
  caption: { fontSize: 13, lineHeight: 20, color: palette.muted },
});
