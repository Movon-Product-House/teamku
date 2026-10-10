"use client";

import { ArrowRight, History, RotateCcw, Sparkles } from "lucide-react";
import type { ReactNode } from "react";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/ui/card";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/shared/ui/dialog";
import { Field, FieldDescription, FieldError, FieldLabel } from "@/shared/ui/field";
import { Input } from "@/shared/ui/input";
import { notify } from "@/shared/ui/notifications";
import { Textarea } from "@/shared/ui/textarea";

const colors = [
  ["background", "bg-background", "canvas · latar halaman"],
  ["card", "bg-card", "surface · kartu"],
  ["secondary", "bg-secondary", "surface-2 · pil, tab aktif"],
  ["border", "bg-border", "line · input, tabel"],
  ["faint-foreground", "bg-faint-foreground", "ink-3 · label"],
  ["muted-foreground", "bg-muted-foreground", "ink-2 · teks kedua"],
  ["foreground", "bg-foreground", "ink · teks, tombol utama"],
  ["sidebar", "bg-sidebar", "side · sidebar"],
  ["brand", "bg-brand", "mendesak"],
  ["success", "bg-success", "tepat / setuju"],
  ["warning", "bg-warning", "menunggu"],
  ["info", "bg-info", "cuti / info"],
  ["destructive", "bg-destructive", "ditolak / error"],
] as const;

const typeScale = [
  ["text-display", "Display 64 · angka utama desktop", "font-display text-display", "3j 18m"],
  [
    "text-title",
    "Title 46 · judul halaman desktop",
    "font-display text-title",
    "Selamat siang, Rina",
  ],
  ["text-headline", "Headline 34 · judul dialog", "font-display text-headline", "Terbitkan slip?"],
  ["text-title-sm", "Title 32 · judul halaman mobile", "font-display text-title-sm", "Cuti & Izin"],
  [
    "text-heading",
    "Heading 18/600 · judul kartu",
    "font-semibold text-heading",
    "Jam kerja minggu ini",
  ],
  [
    "text-body",
    "Body 15/500 · isi",
    "font-medium text-body",
    "Kirim selfie & lokasi sebelum 12.30.",
  ],
  ["text-caption", "Caption 13/500 · label", "font-medium text-caption", "Durasi kerja hari ini"],
] as const;

const tones = ["success", "warning", "info", "destructive", "neutral"] as const;
const toneLabels: Record<(typeof tones)[number], string> = {
  success: "Tepat waktu",
  warning: "Menunggu",
  info: "Cuti",
  destructive: "Ditolak",
  neutral: "Belum check-in",
};

export function DesignSystemPage() {
  return (
    <main
      data-surface="v2"
      className="min-h-dvh bg-background px-5 py-10 font-sans text-foreground md:px-12 md:py-16"
    >
      <div className="mx-auto grid max-w-6xl gap-14">
        <header className="grid gap-3">
          <p className="font-semibold text-caption text-faint-foreground">Teamku · v2</p>
          <h1 className="font-display text-title-sm md:text-title">Design system</h1>
          <p className="max-w-[65ch] font-medium text-body text-muted-foreground">
            Token dan komponen dasar dari <code>mockups/design.pen</code>. Bandingkan halaman ini
            dengan papan “00 · Design System” sebelum memakai komponen di layar baru.
          </p>
        </header>

        <Section title="Warna">
          <ul className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-7">
            {colors.map(([name, swatch, role]) => (
              <li key={name} className="grid gap-2">
                <span className={`h-16 rounded-field ring-1 ring-foreground/5 ${swatch}`} />
                <span className="font-semibold text-caption">{name}</span>
                <span className="text-muted-foreground text-xs">{role}</span>
              </li>
            ))}
          </ul>
        </Section>

        <Section title="Tipografi">
          <dl className="grid gap-6">
            {typeScale.map(([token, label, className, sample]) => (
              <div key={token} className="grid gap-1 md:grid-cols-[240px_1fr] md:items-baseline">
                <dt className="font-medium text-caption text-faint-foreground">{label}</dt>
                <dd className={className}>{sample}</dd>
              </div>
            ))}
          </dl>
        </Section>

        <Section title="Tombol">
          <div className="grid gap-6">
            <Row label="Desktop · 42">
              <Button>
                <Sparkles /> Tanya Teamku
              </Button>
              <Button variant="secondary">
                <History /> Riwayat
              </Button>
              <Button variant="outline">Batal</Button>
              <Button variant="ghost">Lewati</Button>
              <Button variant="destructive">Tolak</Button>
              <Button variant="link">Lihat semua</Button>
              <Button disabled>Nonaktif</Button>
            </Row>
            <Row label="Mobile · 52">
              <Button size="lg">
                <ArrowRight /> Tombol utama
              </Button>
              <Button size="lg" variant="outline">
                <RotateCcw /> Tombol kedua
              </Button>
            </Row>
          </div>
        </Section>

        <Section title="Status">
          <div className="grid gap-4">
            <Row label="soft">
              {tones.map((tone) => (
                <Badge key={tone} tone={tone}>
                  {toneLabels[tone]}
                </Badge>
              ))}
            </Row>
            <Row label="plain">
              {tones.map((tone) => (
                <Badge key={tone} tone={tone} variant="plain">
                  {toneLabels[tone]}
                </Badge>
              ))}
            </Row>
          </div>
        </Section>

        <Section title="Isian">
          <div className="grid max-w-3xl gap-6 md:grid-cols-2">
            <Field>
              <FieldLabel htmlFor="ds-email">Email kerja</FieldLabel>
              <Input id="ds-email" type="email" placeholder="nama@perusahaan.co.id" />
              <FieldDescription>Keterangan singkat</FieldDescription>
            </Field>
            <Field>
              <FieldLabel htmlFor="ds-password">Kata sandi</FieldLabel>
              <Input
                id="ds-password"
                type="password"
                defaultValue="salah"
                aria-invalid
                aria-describedby="ds-password-error"
              />
              <FieldError id="ds-password-error">Email atau kata sandi salah.</FieldError>
            </Field>
            <Field>
              <FieldLabel htmlFor="ds-disabled">Departemen</FieldLabel>
              <Input id="ds-disabled" disabled defaultValue="Sales" />
            </Field>
            <Field>
              <FieldLabel htmlFor="ds-note">Catatan</FieldLabel>
              <Textarea id="ds-note" placeholder="Jelaskan keputusan untuk karyawan" />
            </Field>
          </div>
        </Section>

        <Section title="Kartu & dialog">
          <div className="grid gap-5 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Sisa cuti</CardTitle>
                <CardDescription>Periode 2026</CardDescription>
                <CardAction>
                  <Badge tone="info">Cuti</Badge>
                </CardAction>
              </CardHeader>
              <CardContent className="font-display text-display">8 hari</CardContent>
            </Card>
            <Card className="justify-between">
              <CardHeader>
                <CardTitle>Dialog & notifikasi</CardTitle>
                <CardDescription>Fokus, Escape, dan overlay ditangani Radix.</CardDescription>
              </CardHeader>
              <div className="flex flex-wrap gap-2">
                <ConfirmDialog />
                <Button
                  variant="outline"
                  onClick={() =>
                    notify({
                      type: "success",
                      title: "Keputusan tersimpan",
                      message: "Permohonan Rina Sari berhasil diproses.",
                    })
                  }
                >
                  Notifikasi
                </Button>
              </div>
            </Card>
          </div>
        </Section>
      </div>
    </main>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="grid gap-6">
      <h2 className="font-semibold text-heading">{title}</h2>
      {children}
    </section>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid gap-3">
      <p className="font-medium text-caption text-faint-foreground">{label}</p>
      <div className="flex flex-wrap items-center gap-3">{children}</div>
    </div>
  );
}

function ConfirmDialog() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button>Buka dialog</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Terbitkan slip September?</DialogTitle>
          <DialogDescription>
            48 karyawan akan menerima notifikasi dan bisa melihat slip gaji mereka.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline">Batal</Button>
          </DialogClose>
          <DialogClose asChild>
            <Button>Terbitkan</Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
