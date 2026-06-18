import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

const AUTH_TOKEN_KEY = 'the_ark_auth_token_v1';
const LEGACY_AUTH_TOKEN_KEYS = ['jung_tetrabiblos_auth_token_v1'];

async function getWebStoredValue(key: string) {
  return AsyncStorage.getItem(key);
}

async function setWebStoredValue(key: string, value: string) {
  return AsyncStorage.setItem(key, value);
}

async function deleteWebStoredValue(key: string) {
  return AsyncStorage.removeItem(key);
}

async function getNativeStoredValue(key: string) {
  return SecureStore.getItemAsync(key);
}

async function setNativeStoredValue(key: string, value: string) {
  return SecureStore.setItemAsync(key, value, {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
}

async function deleteNativeStoredValue(key: string) {
  return SecureStore.deleteItemAsync(key);
}

function isWeb() {
  return Platform.OS === 'web';
}

export async function getStoredAuthToken() {
  const current = isWeb()
    ? await getWebStoredValue(AUTH_TOKEN_KEY)
    : await getNativeStoredValue(AUTH_TOKEN_KEY);
  if (current) return current;

  for (const legacyKey of LEGACY_AUTH_TOKEN_KEYS) {
    const legacyValue = isWeb()
      ? await getWebStoredValue(legacyKey)
      : await getNativeStoredValue(legacyKey);
    if (legacyValue) {
      if (isWeb()) {
        await setWebStoredValue(AUTH_TOKEN_KEY, legacyValue);
      } else {
        await setNativeStoredValue(AUTH_TOKEN_KEY, legacyValue);
      }
      return legacyValue;
    }
  }

  return null;
}

export async function setStoredAuthToken(token: string) {
  if (isWeb()) {
    return setWebStoredValue(AUTH_TOKEN_KEY, token);
  }
  return setNativeStoredValue(AUTH_TOKEN_KEY, token);
}

export async function clearStoredAuthToken() {
  if (isWeb()) {
    await Promise.all([
      deleteWebStoredValue(AUTH_TOKEN_KEY),
      ...LEGACY_AUTH_TOKEN_KEYS.map((key) => deleteWebStoredValue(key)),
    ]);
    return;
  }

  await Promise.all([
    deleteNativeStoredValue(AUTH_TOKEN_KEY),
    ...LEGACY_AUTH_TOKEN_KEYS.map((key) => deleteNativeStoredValue(key)),
  ]);
}
