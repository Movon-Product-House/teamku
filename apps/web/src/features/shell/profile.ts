/** 8–128 code points, like the API's len(); the letter + digit rule stays server-side. */
export function newPasswordFits(value: string): boolean {
  const length = [...value].length;
  return length >= 8 && length <= 128;
}
