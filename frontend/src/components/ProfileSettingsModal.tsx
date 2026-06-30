import { FormEvent, useState } from "react";
import { Camera, Trash2, UserRound, WalletCards } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { avatarUrl, deleteAccount, updateEmail, updatePassword, updateUsername, uploadAvatar } from "../api/auth";
import { FinancialProfile, saveFinancialProfile } from "../api/profile";
import { useUser } from "../store/UserProvider";
import FormInput from "./FormInput";
import Modal from "./Modal";
import PasswordInput from "./PasswordInput";
import PrimaryButton from "./PrimaryButton";

type ActionState = { loading: boolean; error: string; success: string };
type Tab = "account" | "security";

const countries = ["Australia", "China", "India", "Indonesia", "Malaysia", "New Zealand", "Singapore", "United Kingdom", "United States", "Other"];
const inputClass = "w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100";

function useAction() {
  const [state, setState] = useState<ActionState>({ loading: false, error: "", success: "" });
  async function run(action: () => Promise<unknown>, success: string) {
    setState({ loading: true, error: "", success: "" });
    try { await action(); setState({ loading: false, error: "", success }); return true; }
    catch (caught) {
      const error = caught instanceof Error ? caught.message : "Unable to save your changes.";
      setState({ loading: false, error, success: "" }); return false;
    }
  }
  return { state, run, setState };
}

function ActionMessage({ state }: { state: ActionState }) {
  if (state.error) return <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{state.error}</p>;
  if (state.success) return <p role="status" className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-700">{state.success}</p>;
  return null;
}

function CurrentAvatar({ large = false }: { large?: boolean }) {
  const { user } = useUser(); const src = avatarUrl(user?.avatar_url || null);
  const size = large ? "size-20" : "size-12";
  if (src) return <img src={src} alt="Current avatar" className={`${size} rounded-full object-cover ring-4 ring-white shadow-lg`} />;
  return <span className={`${size} grid place-items-center rounded-full bg-blue-50 text-blue-600 ring-4 ring-white shadow-lg`}><UserRound size={large ? 42 : 24} /></span>;
}

function SettingsHero() {
  const { user } = useUser();
  return <section className="flex items-center gap-5 px-2 pb-4 pt-5"><CurrentAvatar large /><div><h3 className="text-2xl font-bold text-slate-900">{user?.username || "FinanceAI User"}</h3><p className="mt-1 text-sm text-slate-500">{user?.email}</p></div></section>;
}

function SettingsTabs({ tab, setTab, onClose }: { tab: Tab; setTab: (tab: Tab) => void; onClose: () => void }) {
  const tabs: { id: Tab; label: string }[] = [{ id: "account", label: "Account" }, { id: "security", label: "Security" }];
  return <div className="relative flex border-b border-slate-200 pr-14">{tabs.map((item) => <button key={item.id} type="button" onClick={() => setTab(item.id)} className={`px-6 py-3.5 text-sm font-bold transition ${tab === item.id ? "border-b-2 border-blue-600 text-blue-700" : "text-slate-500 hover:text-slate-900"}`}>{item.label}</button>)}<button type="button" onClick={onClose} aria-label="Close settings" className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-800"><X size={22} /></button></div>;
}

function SettingsCard({ title, children }: { title: string; children: ReactNode }) {
  return <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white"><h4 className="bg-slate-50 px-5 py-3 text-base font-bold text-slate-700">{title}</h4>{children}</section>;
}

function SettingRow({ icon, title, detail, children }: { icon: ReactNode; title: string; detail?: string; children: ReactNode }) {
  return <div className="grid gap-4 border-t border-slate-200 px-5 py-4 first:border-t-0 lg:grid-cols-[minmax(0,1fr)_minmax(20rem,1.2fr)]"><div className="flex min-w-0 items-center gap-4"><span className="grid size-10 shrink-0 place-items-center rounded-full bg-slate-100 text-slate-400">{icon}</span><div className="min-w-0"><p className="font-semibold text-slate-900">{title}</p>{detail && <p className="mt-1 truncate text-sm text-slate-500">{detail}</p>}</div></div><div className="min-w-0">{children}</div></div>;
}

function RegionSelect({ value }: { value: string }) {
  return <select name="region" defaultValue={value} className={inputClass} required>{countries.map((country) => <option key={country} value={country}>{country}</option>)}</select>;
}

function AvatarEditor() {
  const { refreshUser } = useUser(); const action = useAction();
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const file = new FormData(event.currentTarget).get("avatar");
    if (!(file instanceof File) || !file.size) return;
    await action.run(async () => { await uploadAvatar(file); await refreshUser(); }, "Avatar updated successfully.");
  }
  return <form onSubmit={submit} className="space-y-2"><div className="flex flex-wrap items-center gap-4"><CurrentAvatar /><input id="avatar-file" name="avatar" type="file" accept="image/jpeg,image/png,image/webp" required className="sr-only" /><label htmlFor="avatar-file" className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"><Camera size={18} />Choose Image</label><PrimaryButton className="w-auto py-2.5" disabled={action.state.loading}>{action.state.loading ? "Uploading..." : "Upload"}</PrimaryButton></div><ActionMessage state={action.state} /></form>;
}

function AccountDetailsForm() {
  const { user, profile, refreshUser, refreshProfile } = useUser(); const action = useAction();
  const [settings, setSettings] = useState<ExtendedAccountSettings | null>(null);
  useEffect(() => { void getExtendedAccountSettings(String(user?.id || "")).then(setSettings); }, [user?.id]);
  async function save(form: FormData) {
    const firstName = String(form.get("firstName")); const lastName = String(form.get("lastName")); const region = String(form.get("region"));
    await saveExtendedAccountSettings({ firstName, lastName, dateOfBirth: String(form.get("dob")), age: String(form.get("age")), mobile: String(form.get("mobile")), region }, String(user?.id || ""));
    await updateUsername(`${firstName} ${lastName}`.trim() || user?.username || user?.email || "FinanceAI User");
    await saveFinancialProfile({ region, monthly_income: profile?.monthly_income || 0, fixed_expenses: profile?.fixed_expenses || 0, current_savings: profile?.current_savings || 0, initial_savings_target: profile?.initial_savings_target || 0 });
    await Promise.all([refreshUser(), refreshProfile()]);
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); await action.run(() => save(new FormData(event.currentTarget)), "Account details saved successfully.");
  }
  return <form onSubmit={submit} className="space-y-5"><AvatarEditor /><div className="grid gap-x-6 gap-y-4 sm:grid-cols-2"><FormInput id="first-name" name="firstName" label="First Name" defaultValue={settings?.firstName || ""} /><FormInput id="last-name" name="lastName" label="Last Name" defaultValue={settings?.lastName || ""} /><FormInput id="date-of-birth" name="dob" type="date" label="Date of Birth" defaultValue={settings?.dateOfBirth || ""} /><FormInput id="age" name="age" type="number" min="0" max="130" label="Age" defaultValue={settings?.age || ""} /><label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">Region</span><RegionSelect value={settings?.region || profile?.region || "Australia"} /></label><FormInput id="mobile" name="mobile" type="tel" label="Mobile" defaultValue={settings?.mobile || ""} /></div><div className="flex items-center justify-end gap-4 pt-2"><ActionMessage state={action.state} /><PrimaryButton className="w-auto py-2.5" disabled={action.state.loading}>{action.state.loading ? "Saving..." : "Save Account"}</PrimaryButton></div></form>;
}

function EmailUpdateModal({ onClose }: { onClose: () => void }) {
  const { user, refreshUser } = useUser(); const action = useAction();
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    await action.run(async () => { await updateEmail(String(form.get("newEmail")), String(form.get("password"))); await refreshUser(); }, "Email updated successfully.");
  }
  return <Modal title="Update Email" onClose={onClose}><form onSubmit={submit} className="grid gap-4"><FormInput id="current-email" name="currentEmail" type="email" label="Current Email" value={user?.email || ""} readOnly /><FormInput id="new-email" name="newEmail" type="email" label="New Email" required /><PasswordInput id="email-password" name="password" label="Current Password" autoComplete="current-password" required /><ActionMessage state={action.state} /><div className="flex justify-end gap-3"><button type="button" onClick={onClose} className="rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50">Cancel</button><PrimaryButton className="w-auto" disabled={action.state.loading}>{action.state.loading ? "Saving..." : "Update Email"}</PrimaryButton></div></form></Modal>;
}

function PasswordUpdateModal({ onClose }: { onClose: () => void }) {
  const action = useAction();
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const element = event.currentTarget; const form = new FormData(element);
    if (form.get("next") !== form.get("confirm")) { action.setState({ loading: false, error: "New password and confirmation do not match.", success: "" }); return; }
    const saved = await action.run(() => updatePassword(String(form.get("current")), String(form.get("next"))), "Password updated successfully.");
    if (saved) element.reset();
  }
  return <Modal title="Change Password" onClose={onClose}><form onSubmit={submit} className="grid gap-4"><PasswordInput id="security-current" name="current" label="Current Password" autoComplete="current-password" required /><PasswordInput id="security-next" name="next" label="New Password" autoComplete="new-password" minLength={8} required /><PasswordInput id="security-confirm" name="confirm" label="Confirm New Password" autoComplete="new-password" minLength={8} required /><ActionMessage state={action.state} /><div className="flex justify-end gap-3"><button type="button" onClick={onClose} className="rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50">Cancel</button><PrimaryButton className="w-auto" disabled={action.state.loading}>{action.state.loading ? "Saving..." : "Change Password"}</PrimaryButton></div></form></Modal>;
}

function DeleteAccountModal({ onClose }: { onClose: () => void }) {
  const { user, clearUser } = useUser(); const navigate = useNavigate(); const action = useAction();
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const password = String(new FormData(event.currentTarget).get("password"));
    const deleted = await action.run(() => deleteAccount(password), "Account deleted successfully.");
    if (deleted) { clearExtendedAccountSettings(String(user?.id || "")); clearUser(); navigate("/login", { replace: true }); }
  }
  return <Modal title="Delete Account" onClose={onClose}><form onSubmit={submit} className="space-y-6"><div className="rounded-3xl bg-emerald-50 p-6 text-slate-800"><h3 className="text-center text-xl font-bold">Are You Sure You Want To Delete Your Account?</h3><p className="mt-5 text-sm leading-6">This action will permanently delete all of your data, and you will not be able to recover it. Please keep the following in mind before proceeding:</p><ul className="mt-4 list-disc space-y-3 pl-6 text-sm"><li>All your expenses, income and associated transactions will be eliminated.</li><li>You will not be able to access your account or related information.</li><li>This action cannot be undone.</li></ul></div><p className="text-center font-bold text-slate-900">Please Enter Your Password To Confirm Deletion Of Your Account.</p><PasswordInput id="delete-password" name="password" label="Current Password" autoComplete="current-password" required /><ActionMessage state={action.state} /><div className="flex justify-end gap-3"><button type="button" onClick={onClose} className="rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50">Cancel</button><button type="submit" disabled={action.state.loading} className="rounded-xl bg-red-600 px-4 py-3 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-60">{action.state.loading ? "Deleting..." : "Yes, Delete Account"}</button></div></form></Modal>;
}

function DeleteSection() {
  const [open, setOpen] = useState(false);
  return <SettingsCard title="Delete Account"><div className="flex items-start justify-between gap-4 px-5 py-5"><div className="flex items-start gap-4"><span className="grid size-11 place-items-center rounded-full bg-red-50 text-red-600"><Trash2 size={20} /></span><div><p className="font-semibold text-red-900">Delete your account</p><p className="mt-1 max-w-xl text-sm text-red-700">This permanently removes your account access and user data. You will need your current password to continue.</p></div></div><button type="button" onClick={() => setOpen(true)} className="shrink-0 rounded-xl bg-red-600 px-4 py-3 text-sm font-semibold text-white hover:bg-red-700">Delete Account</button></div>{open && <DeleteAccountModal onClose={() => setOpen(false)} />}</SettingsCard>;
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

function SecurityActionRow({ icon, title, detail, action, onClick }: { icon: ReactNode; title: string; detail?: string; action: string; onClick: () => void }) {
  return <div className="flex items-center justify-between gap-4 border-t border-slate-200 px-5 py-5 first:border-t-0"><div className="flex min-w-0 items-center gap-4"><span className="grid size-11 shrink-0 place-items-center rounded-full bg-slate-100 text-slate-400">{icon}</span><div className="min-w-0"><p className="font-semibold text-slate-900">{title}</p>{detail && <p className="mt-1 truncate text-sm text-slate-500">{detail}</p>}</div></div><button type="button" onClick={onClick} className="shrink-0 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-600 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700">{action}</button></div>;
}

function SecurityTab() {
  const { user } = useUser(); const [modal, setModal] = useState<"email" | "password" | null>(null);
  return <div className="space-y-6"><SettingsCard title="Security settings"><SecurityActionRow icon={<Mail size={20} />} title="Log in email" detail={user?.email} action="Update Email" onClick={() => setModal("email")} /><SecurityActionRow icon={<LockKeyhole size={20} />} title="Password" action="Change Password" onClick={() => setModal("password")} /></SettingsCard><DeleteSection />{modal === "email" && <EmailUpdateModal onClose={() => setModal(null)} />}{modal === "password" && <PasswordUpdateModal onClose={() => setModal(null)} />}</div>;
}

export default function ProfileSettingsModal({ onClose }: { onClose: () => void }) {
  const [tab, setTab] = useState<Tab>("account");
  return <Modal title="Settings" onClose={onClose} wide hideHeader><SettingsTabs tab={tab} setTab={setTab} onClose={onClose} /><SettingsHero />{tab === "account" ? <AccountTab /> : <SecurityTab />}</Modal>;
}
