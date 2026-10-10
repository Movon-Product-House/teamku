// Next hanya mendeklarasikan *.module.css. TS 6 menyalakan noUncheckedSideEffectImports
// secara default, jadi import CSS global (app/layout.tsx) butuh deklarasi ini.
declare module "*.css";
