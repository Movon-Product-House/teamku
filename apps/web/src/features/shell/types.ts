import type { Role } from "@/shared/api/generated/model";

export const roleLabels: Record<Role, string> = {
  employee: "Employee",
  manager: "Manager",
  hr_admin: "HR Admin",
};
