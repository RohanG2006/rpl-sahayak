"use client";
import { useRouter } from "next/navigation";
import Brand from "@/components/Brand";
import LangToggle from "@/components/LangToggle";
import ProfileWizard from "@/components/ProfileWizard";
import { registerWorker } from "@/lib/data/worker";
import { useT } from "@/lib/i18n";

export default function RegisterPage() {
  const { t } = useT();
  const router = useRouter();
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="mx-auto flex h-14 w-full max-w-xl items-center justify-between px-4"><Brand /><LangToggle /></header>
      <main className="mx-auto w-full max-w-xl flex-1 px-4 pt-4">
        <h1 className="mb-5 text-2xl font-semibold tracking-tight">{t("reg.title")}</h1>
        <ProfileWizard mode="register" onSave={async (f) => {
          await registerWorker({ ...f, pin: f.pin ?? "" });
          router.replace("/worker/experience");
        }} />
      </main>
    </div>
  );
}
