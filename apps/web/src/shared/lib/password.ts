/** Mirrors `password_policy_error` in apps/api `core/security.py`. */
export const PASSWORD_MIN = 8;
export const PASSWORD_MAX = 128;

export type PasswordRule = { label: string; met: boolean };

export function passwordRules(password: string): PasswordRule[] {
  // Count code points like Python's len(), not UTF-16 units.
  const length = [...password].length;
  return [
    {
      label: `${PASSWORD_MIN}–${PASSWORD_MAX} karakter`,
      met: length >= PASSWORD_MIN && length <= PASSWORD_MAX,
    },
    { label: "Minimal satu huruf", met: /[A-Za-z]/.test(password) },
    { label: "Minimal satu angka", met: /\d/.test(password) },
  ];
}

export function passwordValid(password: string): boolean {
  return passwordRules(password).every((rule) => rule.met);
}
