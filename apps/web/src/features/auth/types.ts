/** `GET /invites/{token}`: who is invited, by whom, and until when. */
export type InvitePreview = {
  email: string;
  name: string;
  company: string;
  role: string;
  department: string;
  title: string;
  invited_by: string | null;
  expires_at: string;
};

/** `GET /auth/reset-password/{token}`. */
export type ResetPreview = { email: string };
