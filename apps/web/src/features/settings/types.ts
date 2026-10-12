export type AttendanceSettings = {
  id?: string;
  is_primary?: boolean;
  name: string;
  latitude: number;
  longitude: number;
  radius_meters: number;
  reverify_enabled: boolean;
  reverify_count_per_day: number;
  reverify_window_start_minutes: number;
  reverify_window_end_minutes: number;
  alerts_enabled: boolean;
  clock_in_reminder_time: string;
  clock_out_reminder_time: string;
  max_open_hours: number;
  alert_managers: boolean;
};
