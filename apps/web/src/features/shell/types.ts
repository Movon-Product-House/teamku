export type Role = "employee" | "manager" | "hr_admin";

export type Me = {
  user: {
    id: string;
    name: string;
    email: string;
    role: Role;
    department: string;
    title: string;
    is_remote: boolean;
    work_location: { name: string; radius_meters: number } | null;
  };
  tenant: { id: string; name: string; slug: string };
};

export type Notification = {
  id: string;
  title: string;
  detail: string;
  target: string;
  created_at: string;
  read: boolean;
};

export type NotificationList = { items: Notification[]; unread: number };

export type AttendanceState = "not_checked_in" | "checked_in" | "completed";

export type TodayAttendance = {
  state: AttendanceState;
  pending_reverification: { id: string; due_at: string } | null;
};

export const roleLabels: Record<Role, string> = {
  employee: "Employee",
  manager: "Manager",
  hr_admin: "HR Admin",
};
