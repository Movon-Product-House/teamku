// DEMO-ONLY: pemilih akun seed. Untuk menghapus mode demo, hapus file ini dan
// pemakaiannya di halaman login (cari "DemoAccountPicker"), plus shared/api/demo-session.ts.
const DEMO_PASSWORD = "Demo123!";
const accounts = [
  { label: "HR Admin", email: "hr@movon.test" },
  { label: "Manager", email: "manager@movon.test" },
  { label: "Employee", email: "employee@movon.test" },
  { label: "Fresh check-in", email: "fresh@movon.test" },
];

export const demoCredentials = { email: "employee@movon.test", password: DEMO_PASSWORD };

type Props = {
  email: string;
  disabled: boolean;
  onPick: (credentials: { email: string; password: string }) => void;
};

export function DemoAccountPicker({ email, disabled, onPick }: Props) {
  return (
    <div className="login-demo">
      <b>Pilih akun demo</b>
      <div>
        {accounts.map((account) => (
          <button
            disabled={disabled}
            type="button"
            className={email === account.email ? "active" : ""}
            onClick={() => onPick({ email: account.email, password: DEMO_PASSWORD })}
            key={account.email}
          >
            {account.label}
          </button>
        ))}
      </div>
      <small>Semua akun menggunakan kata sandi {DEMO_PASSWORD}</small>
    </div>
  );
}
