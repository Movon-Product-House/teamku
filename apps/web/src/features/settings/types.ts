import type { LocationOut } from "@/shared/api/generated/model";

/** Form state for a work location: a LocationOut whose id is unknown until it is saved. */
export type AttendanceSettings = Omit<LocationOut, "id" | "is_primary"> &
  Partial<Pick<LocationOut, "id" | "is_primary">>;
