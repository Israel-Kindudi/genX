export function getPasswordStrength(password: string): number {
  if (!password) return 0;

  const score = [
    password.length >= 8,
    /[a-z]/.test(password) && /[A-Z]/.test(password),
    /\d/.test(password),
    /[^a-zA-Z0-9]/.test(password),
  ].filter(Boolean).length;

  return password.length < 8 ? 1 : score;
}
