import { FormEvent, useState } from "react";
import { Camera, Trash2, UserRound, WalletCards } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { avatarUrl, deleteAccount, updateEmail, updatePassword, updateUsername, uploadAvatar } from "../api/auth";
import { FinancialProfile, saveFinancialProfile } from "../api/profile";
import { useUser } from "../store/UserProvider";
import FormInput from "./FormInput";
import Modal from "./Modal";
import PrimaryButton from "./PrimaryButton";

type ActionState = { loading: boolean; error: string; success: string };

function useAction() {
  const [state, setState] = useState<ActionState>({ loading: false, error: "", success: "" });
  async function run(action: () => Promise<unknown>, success: string) {
    setState({ loading: true, error: "", success: "" });
    try {
      await action(); setState({ loading: false, error: "", success }); return true;
    } catch (caught) {
      const error = caught instanceof Error ? caught.message : "Unable to save your changes.";
      setState({ loading: false, error, success: "" }); return false;
    }
  }
  return { state, run };
}

function ActionMessage({ state }: { state: ActionState }) {
  if (state.error) return <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{state.error}</p>;
  if (state.success) return <p role="status" className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-700">{state.success}</p>;
  return null;
}

const panelClass = "space-y-4 border-b border-slate-200 pb-7 last:border-0";

function SectionHeading({ title, detail }: { title: string; detail: string }) {
  return <div><h3 className="font-semibold text-slate-900">{title}</h3><p className="mt-1 text-sm text-slate-500">{detail}</p></div>;
}

function CurrentAvatar() {
  const { user } = useUser(); const src = avatarUrl(user?.avatar_url || null);
  if (src) return <img src={src} alt="Current avatar" className="size-16 rounded-2xl object-cover ring-1 ring-slate-200" />;
  return <span className="grid size-16 place-items-center rounded-2xl bg-blue-50 text-blue-600"><UserRound size={28} /></span>;
}

function AvatarForm() {
  const { refreshUser } = useUser(); const action = useAction();
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const file = new FormData(event.currentTarget).get("avatar");
    if (!(file instanceof File) || !file.size) return;
    await action.run(async () => { await uploadAvatar(file); await refreshUser(); }, "Avatar updated successfully.");
  }
  return <form className={panelClass} onSubmit={submit}><SectionHeading title="Profile photo" detail="JPEG, PNG or WebP up to the server upload limit." />
    <div className="flex items-center gap-4"><CurrentAvatar /><input id="avatar-file" name="avatar" type="file" accept="image/jpeg,image/png,image/webp" required className="sr-only" /><label htmlFor="avatar-file" className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700"><Camera size={16} /> Choose Image</label></div>
    <ActionMessage state={action.state} /><div className="flex justify-end"><PrimaryButton className="sm:w-auto" type="submit" disabled={action.state.loading}>{action.state.loading ? "Uploading..." : "Upload Photo"}</PrimaryButton></div>
  </form>;
}

function UsernameForm() {
  const { user, refreshUser } = useUser(); const action = useAction();
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const username = String(new FormData(event.currentTarget).get("username"));
    await action.run(async () => { await updateUsername(username); await refreshUser(); }, "Username updated successfully.");
  }
  return <form className={panelClass} onSubmit={submit}><SectionHeading title="Username" detail="This name appears in your FinanceAI profile." />
    <FormInput id="settings-username" name="username" label="Username" minLength={2} maxLength={50} defaultValue={user?.username || ""} required />
    <ActionMessage state={action.state} /><div className="flex justify-end"><PrimaryButton className="sm:w-auto" type="submit" disabled={action.state.loading}>{action.state.loading ? "Saving..." : "Save Username"}</PrimaryButton></div>
  </form>;
}

function EmailForm() {
  const { user, refreshUser } = useUser(); const action = useAction();
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const element = event.currentTarget; const form = new FormData(element);
    const saved = await action.run(async () => { await updateEmail(String(form.get("email")), String(form.get("password"))); await refreshUser(); }, "Email updated successfully.");
    if (saved) element.reset();
  }
  return <form className={panelClass} onSubmit={submit}><SectionHeading title="Email address" detail="Confirm your current password before changing your sign-in email." />
    <FormInput id="settings-email" name="email" type="email" label="New email" defaultValue={user?.email} required />
    <FormInput id="email-password" name="password" type="password" label="Current password" autoComplete="current-password" required />
    <ActionMessage state={action.state} /><div className="flex justify-end"><PrimaryButton className="sm:w-auto" type="submit" disabled={action.state.loading}>{action.state.loading ? "Saving..." : "Change Email"}</PrimaryButton></div>
  </form>;
}

function PasswordForm() {
  const action = useAction();
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const element = event.currentTarget; const form = new FormData(element);
    const saved = await action.run(() => updatePassword(String(form.get("current")), String(form.get("next"))), "Password updated successfully.");
    if (saved) element.reset();
  }
  return <form className={panelClass} onSubmit={submit}><SectionHeading title="Password" detail="Use at least eight characters for your new password." />
    <FormInput id="current-password" name="current" type="password" label="Current password" autoComplete="current-password" required />
    <FormInput id="new-password" name="next" type="password" label="New password" autoComplete="new-password" minLength={8} maxLength={72} required />
    <ActionMessage state={action.state} /><div className="flex justify-end"><PrimaryButton className="sm:w-auto" type="submit" disabled={action.state.loading}>{action.state.loading ? "Saving..." : "Change Password"}</PrimaryButton></div>
  </form>;
}

function DeleteAccountForm() {
  const action = useAction(); const { clearUser } = useUser(); const navigate = useNavigate();
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const password = String(new FormData(event.currentTarget).get("password"));
    const deleted = await action.run(() => deleteAccount(password), "Account deleted.");
    if (deleted) { clearUser(); navigate("/login", { replace: true }); }
  }
  return <form className="space-y-4" onSubmit={submit}><SectionHeading title="Delete account" detail="Permanently delete your account and saved data." />
    <FormInput id="delete-account-password" name="password" type="password" label="Current password" autoComplete="current-password" required />
    <ActionMessage state={action.state} /><div className="flex justify-end"><button type="submit" disabled={action.state.loading} className="inline-flex items-center gap-2 rounded-xl bg-red-600 px-4 py-3 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-60"><Trash2 size={16} />{action.state.loading ? "Deleting..." : "Delete Account"}</button></div>
  </form>;
}

function AccountTab() {
  return <div className="space-y-7"><AvatarForm /><UsernameForm /><EmailForm /><PasswordForm /><DeleteAccountForm /></div>;
}

function FinancialTab({ profile }: { profile: FinancialProfile | null }) {
  const { refreshProfile } = useUser(); const action = useAction();
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    const value = (key: string) => Number(form.get(key)) || 0;
    await action.run(async () => {
      await saveFinancialProfile({ region: String(form.get("region")), monthly_income: value("income"), fixed_expenses: value("expenses"), current_savings: value("savings"), initial_savings_target: value("target") });
      await refreshProfile();
    }, "Financial profile saved successfully.");
  }
  return <form onSubmit={submit} className="grid gap-5 md:grid-cols-2"><div className="md:col-span-2"><SectionHeading title="Financial profile" detail="Keep these figures current so FinanceAI can use accurate financial context." /></div>
    <FormInput id="profile-region" name="region" label="Region" minLength={2} maxLength={100} defaultValue={profile?.region || ""} required />
    <FormInput id="profile-income" name="income" type="number" min="0" step="0.01" label="Monthly income" defaultValue={profile?.monthly_income || 0} required />
    <FormInput id="profile-expenses" name="expenses" type="number" min="0" step="0.01" label="Fixed expenses" defaultValue={profile?.fixed_expenses || 0} required />
    <FormInput id="profile-savings" name="savings" type="number" min="0" step="0.01" label="Current savings" defaultValue={profile?.current_savings || 0} required />
    <FormInput id="profile-target" name="target" type="number" min="0" step="0.01" label="Initial savings target" defaultValue={profile?.initial_savings_target || 0} required />
    <div className="flex flex-col justify-end md:col-span-2"><ActionMessage state={action.state} /><div className="mt-4 flex justify-end"><PrimaryButton className="sm:w-auto" type="submit" disabled={action.state.loading}>{action.state.loading ? "Saving..." : "Save Financial Profile"}</PrimaryButton></div></div>
  </form>;
}

export default function ProfileSettingsModal({ onClose }: { onClose: () => void }) {
  const [tab, setTab] = useState<"account" | "financial">("account"); const { profile } = useUser();
  const tabClass = (active: boolean) => `flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm font-semibold transition ${active ? "bg-blue-600 text-white shadow-sm" : "text-slate-600 hover:bg-white hover:text-slate-900"}`;
  return <Modal title="Profile Settings" onClose={onClose} wide><div className="-m-6 flex min-h-[34rem]">
    <aside className="w-48 shrink-0 border-r border-slate-200 bg-slate-50 p-4"><p className="mb-3 px-3 text-xs font-bold uppercase tracking-wider text-slate-400">Settings</p>
      <div className="space-y-1"><button type="button" onClick={() => setTab("account")} className={tabClass(tab === "account")}><UserRound size={18} />Account</button><button type="button" onClick={() => setTab("financial")} className={tabClass(tab === "financial")}><WalletCards size={18} />Financial Profile</button></div>
    </aside><div className="min-w-0 flex-1 p-7"><div className="mb-7 flex items-center gap-3"><span className="grid size-10 place-items-center rounded-xl bg-blue-50 text-blue-600">{tab === "account" ? <UserRound size={20} /> : <WalletCards size={20} />}</span><div><h3 className="font-semibold">{tab === "account" ? "Account settings" : "Financial details"}</h3><p className="text-sm text-slate-500">{tab === "account" ? "Manage your identity and sign-in details." : "Update your personal financial information."}</p></div></div>
      {tab === "account" ? <AccountTab /> : <FinancialTab key={profile?.id || "new"} profile={profile} />}</div>
  </div></Modal>;
}
