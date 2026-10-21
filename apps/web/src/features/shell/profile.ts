/**
 * P7 submit gate for the new password: 8–128 characters, counted by code point like the API
 * (Python len), so the API never answers with its generic schema error. The letter + digit
 * rule stays with the API, whose message is shown as is.
 */
export function newPasswordFits(value: string): boolean {
  const length = [...value].length;
  return length >= 8 && length <= 128;
}
