import { describe, expect, it } from "vitest";
import {
  activeHref,
  activeTab,
  initials,
  MORE_HREF,
  moreGroups,
  navGroups,
  pageTitle,
  tabItems,
  workLocation,
} from "./nav";

const labels = (role: Parameters<typeof navGroups>[0]) =>
  navGroups(role, "Sales").map((group) => [group.label, group.items.map((item) => item.label)]);

describe("navGroups", () => {
  it("gives every role the Saya layer and adds Tim / Perusahaan by role", () => {
    expect(labels("employee")).toEqual([
      [undefined, ["Beranda", "Presensi", "Cuti & Izin", "Slip Gaji", "Ask Teamku"]],
      ["Pintasan", ["Ajukan cuti", "Riwayat presensi", "Kebijakan perusahaan"]],
    ]);
    expect(labels("manager").slice(1)).toEqual([["Tim · Sales", ["Tim Saya", "Persetujuan"]]]);
    expect(labels("hr_admin").slice(1)).toEqual([
      ["Tim", ["Karyawan", "Persetujuan"]],
      ["Perusahaan", ["Payroll", "Kebijakan", "Pengaturan"]],
    ]);
  });
});

describe("tabItems", () => {
  it("swaps Cuti for Persetujuan for managers and HR", () => {
    expect(tabItems("employee").map((item) => item.label)).toEqual([
      "Beranda",
      "Presensi",
      "Cuti",
      "Lainnya",
    ]);
    expect(tabItems("hr_admin").map((item) => item.label)).toEqual([
      "Beranda",
      "Presensi",
      "Persetujuan",
      "Lainnya",
    ]);
  });
});

describe("moreGroups", () => {
  it("lists only the pages that have no tab", () => {
    expect(
      moreGroups("employee", "Sales").map((group) => group.items.map((item) => item.label)),
    ).toEqual([["Slip Gaji", "Ask Teamku"]]);
    const hr = moreGroups("hr_admin", "HR");
    expect(hr.map((group) => group.label)).toEqual(["Saya", "Tim", "Perusahaan"]);
    expect(hr[0].items.map((item) => item.label)).toEqual([
      "Cuti & Izin",
      "Slip Gaji",
      "Ask Teamku",
    ]);
    expect(hr[1].items.map((item) => item.label)).toEqual(["Karyawan"]);
    expect(hr[2].items.every((item) => item.desktopOnly)).toBe(true);
  });
});

describe("activeHref", () => {
  const hrefs = ["/app/settings", "/app/settings/policies", "/app/people"];

  it("prefers the longest matching parent", () => {
    expect(activeHref("/app/settings/policies", hrefs)).toBe("/app/settings/policies");
    expect(activeHref("/app/settings", hrefs)).toBe("/app/settings");
    expect(activeHref("/app/people/123", hrefs)).toBe("/app/people");
  });

  it("does not match a sibling that only shares a prefix", () => {
    expect(activeHref("/app/peoplex", hrefs)).toBeUndefined();
  });
});

describe("activeTab", () => {
  it("falls back to Lainnya for pages without a tab", () => {
    expect(activeTab("/app/time/time-off", "employee")).toBe("/app/time/time-off");
    expect(activeTab("/app/time/time-off", "manager")).toBe(MORE_HREF);
    expect(activeTab("/app/payroll/payslips", "employee")).toBe(MORE_HREF);
  });
});

describe("pageTitle", () => {
  it("names the page after its nav item", () => {
    expect(pageTitle("/app/people/42", "manager", "Sales")).toBe("Tim Saya");
    expect(pageTitle("/app/people", "hr_admin", "HR")).toBe("Karyawan");
    expect(pageTitle(MORE_HREF, "employee", "Sales")).toBe("Lainnya");
    expect(pageTitle("/app/unknown", "employee", "Sales")).toBe("Teamku");
  });
});

describe("initials", () => {
  it("takes the first two words", () => {
    expect(initials("dewi wulandari putri")).toBe("DW");
    expect(initials("Rina")).toBe("R");
    expect(initials("  ")).toBe("--");
  });
});

describe("workLocation", () => {
  it("names the office, or field work for remote employees", () => {
    expect(workLocation({ is_remote: false, work_location: { name: "Kantor Pusat" } })).toBe(
      "Kantor Pusat",
    );
    expect(workLocation({ is_remote: true, work_location: null })).toBe("Pekerja lapangan");
    expect(workLocation({ is_remote: false, work_location: null })).toBe("Lokasi belum diatur");
  });
});
