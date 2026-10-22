import type { EmployeeRole } from "@/shared/api/generated/model";

export const roleLabels: Record<EmployeeRole, string> = {
  employee: "Employee",
  manager: "Manager",
  hr_admin: "HR Admin",
};
