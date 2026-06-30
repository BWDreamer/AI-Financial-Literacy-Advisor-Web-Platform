import { ApiError } from "./client";

const STORAGE_PREFIX = "financeai_extended_account";

export type ExtendedAccountSettings = {
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  age: string;
  mobile: string;
  region: string;
};

const emptySettings: ExtendedAccountSettings = {
  firstName: "",
  lastName: "",
  dateOfBirth: "",
  age: "",
  mobile: "",
  region: "",
};

const storageKey = (ownerKey = "anonymous") => `${STORAGE_PREFIX}:${ownerKey}`;

export async function getExtendedAccountSettings(ownerKey?: string) {
  // TODO: Replace this temporary client-side storage with a backend account profile endpoint.
  const stored = localStorage.getItem(storageKey(ownerKey));
  return stored ? { ...emptySettings, ...JSON.parse(stored) } : emptySettings;
}

export async function saveExtendedAccountSettings(settings: ExtendedAccountSettings, ownerKey?: string) {
  // TODO: Persist first name, last name, date of birth, age, mobile and region through the backend.
  localStorage.setItem(storageKey(ownerKey), JSON.stringify(settings));
  return settings;
}

export async function deleteAccount(_currentPassword: string) {
  // TODO: Replace with the real backend delete-account endpoint when it is available.
  throw new ApiError("Delete account API is not available yet.", 501);
}

export function clearExtendedAccountSettings(ownerKey?: string) {
  localStorage.removeItem(storageKey(ownerKey));
}
