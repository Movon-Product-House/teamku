// DEMO-ONLY: pemilih akun seed. Untuk menghapus mode demo, hapus file ini dan
// pemakaiannya di halaman login (cari "DemoAccountPicker"), plus shared/api/demo-session.ts.
import { cn } from "@/shared/lib/cn";

const DEMO_PASSWORD = "Demo123!";
const accounts = [
  { label: "HR Admin", email: "hr@movon.test" },
  { label: "Manager", email: "manager@movon.test" },
  { label: "Employee", email: "employee@movon.test" },
  { label: "Fresh check-in", email: "fresh@movon.test" },
];

/** Opt-in: picker hanya tampil bila NEXT_PUBLIC_DEMO_ACCOUNTS=1 (lokal, preview Vercel). Tanpa env ini mati. */
export const showDemoAccounts = process.env.NEXT_PUBLIC_DEMO_ACCOUNTS === "1";

export const demoCredentials = showDemoAccounts
  ? { email: "employee@movon.test", password: DEMO_PASSWORD }
  : { email: "", password: "" };

type Props = {
  email: string;
  disabled: boolean;
  onPick: (credentials: { email: string; password: string }) => void;
};

export function DemoAccountPicker({ email, disabled, onPick }: Props) {
  return (
    <section
      aria-label="Akun demo"
      className="flex flex-col gap-2.5 rounded-field border border-border border-dashed p-3.5"
    >
      <p className="font-semibold text-caption">Pilih akun demo</p>
      <div className="flex flex-wrap gap-1.5">
        {accounts.map((account) => (
          <button
            disabled={disabled}
            type="button"
            aria-pressed={email === account.email}
            className={cn(
              "h-8 rounded-full border-0 px-3 font-semibold text-xs outline-none focus-visible:outline-2 focus-visible:outline-ring disabled:opacity-50",
              email === account.email ? "bg-primary text-primary-foreground" : "bg-secondary",
            )}
            onClick={() => onPick({ email: account.email, password: DEMO_PASSWORD })}
            key={account.email}
          >
            {account.label}
          </button>
        ))}
      </div>
      <p className="text-faint-foreground text-xs">Semua akun memakai kata sandi {DEMO_PASSWORD}</p>
    </section>
  );
}
