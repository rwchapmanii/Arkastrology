import { Feather } from '@expo/vector-icons';
import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { BrandMark } from '../components/BrandMark';
import { palette } from '../constants/theme';
import { Field, PrimaryButton, SurfaceCard } from '../components/common';

export function AuthScreen({
  email,
  password,
  authMode,
  onEmailChange,
  onPasswordChange,
  onAuthModeChange,
  onSignIn,
  onRegister,
}: {
  email: string;
  password: string;
  authMode: 'sign in' | 'register';
  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onAuthModeChange: (value: 'sign in' | 'register') => void;
  onSignIn: () => void;
  onRegister: () => void;
}) {
  const isRegister = authMode === 'register';

  return (
    <SurfaceCard title={isRegister ? 'Create your account' : 'Sign in'} subtitle={isRegister ? 'Create an account to enter The Ark.' : 'Enter your email and password to continue into The Ark.'}>
      <View style={styles.stack}>
        <View style={styles.brandMarkWrap}>
          <BrandMark size={72} />
        </View>

        <View style={styles.toggleWrap}>
          <Pressable style={[styles.togglePill, !isRegister && styles.togglePillActive]} onPress={() => onAuthModeChange('sign in')}>
            <Text style={[styles.toggleText, !isRegister && styles.toggleTextActive]}>Sign in</Text>
          </Pressable>
          <Pressable style={[styles.togglePill, isRegister && styles.togglePillActive]} onPress={() => onAuthModeChange('register')}>
            <Text style={[styles.toggleText, isRegister && styles.toggleTextActive]}>Register</Text>
          </Pressable>
        </View>

        <Field label="Email" value={email} onChangeText={onEmailChange} placeholder="ron@example.com" keyboardType="email-address" autoCapitalize="none" />
        <Field label="Password" value={password} onChangeText={onPasswordChange} placeholder="At least 8 characters" secureTextEntry autoCapitalize="none" />

        <PrimaryButton
          label={isRegister ? 'Create account' : 'Sign in'}
          onPress={isRegister ? onRegister : onSignIn}
          icon={<Feather name={isRegister ? 'user-plus' : 'log-in'} size={15} color={palette.white} />}
        />

        <Text style={styles.caption}>
          {isRegister
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
    backgroundColor: palette.accent,
  },
  toggleText: { fontSize: 13, lineHeight: 17, fontWeight: '700', color: palette.muted },
  toggleTextActive: { color: palette.white },
  caption: { fontSize: 13, lineHeight: 20, color: palette.muted },
});
