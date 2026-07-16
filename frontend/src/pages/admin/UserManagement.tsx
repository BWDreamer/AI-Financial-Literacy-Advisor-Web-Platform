import { FormEvent, ReactNode, useCallback, useEffect, useState } from "react";
import { Bookmark, Heart, Pencil, Plus, RefreshCw, Search, Target, Trash2, UserCircle, X } from "lucide-react";
import {
  AdminUser,
  deleteAdminUser,
  getAdminUsers,
  inviteAdminUser,
  updateAdminUser,
} from "../../api/admin";
import { avatarUrl } from "../../api/auth";
import FormInput from "../../components/FormInput";
import Modal from "../../components/Modal";
import { useUser } from "../../store/UserProvider";

type UserForm = {
  firstName: string;
  lastName: string;
  email: string;
  password: string;
};

const DEFAULT_PASSWORD = "11111111";
const emptyInviteForm = (): UserForm => ({ firstName: "", lastName: "", email: "", password: DEFAULT_PASSWORD });

function errorMessage(caught: unknown) {
  return caught instanceof Error ? caught.message : "Something went wrong. Please try again.";
}

function initials(user: AdminUser) {
  const first = user.first_name?.[0] ?? "";
  const last = user.last_name?.[0] ?? "";
  return `${first}${last}`.toUpperCase() || "U";
}

function fullName(user: AdminUser) {
  return [user.first_name, user.last_name].filter(Boolean).join(" ") || "Unnamed user";
}

function displayDate(value: string) {
  return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "2-digit", year: "numeric" })
    .format(new Date(value)).replace(/\//g, "-");
}

function displayDateTime(value: string | null) {
  if (!value) return "Never";
  return new Intl.DateTimeFormat("en-AU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function displayRole(role: string | null | undefined) {
  return role ? role.charAt(0).toUpperCase() + role.slice(1) : "User";
}

function UserAvatar({ user, size = "size-14" }: { user: AdminUser; size?: string }) {
  const src = avatarUrl(user.avatar_url ?? null);
  if (src) return <img src={src} alt={`${fullName(user)} avatar`} className={`${size} rounded-full object-cover ring-4 ring-violet-50`} />;
  return <span className={`grid ${size} place-items-center rounded-full bg-violet-600 font-bold text-white ring-4 ring-violet-50`}>{initials(user)}</span>;
}

function ReadOnlyInfo({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl bg-slate-100 px-4 py-3">
    <span className="block text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</span>
    <span className="mt-1 block font-semibold text-slate-900">{value}</span>
  </div>;
}

function DetailStat({ icon, label, value }: { icon: ReactNode; label: string; value: number }) {
  return <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
    <div className="flex items-center gap-3 text-sm font-semibold text-slate-500">{icon}<span>{label}</span></div>
    <p className="mt-3 text-2xl font-bold text-slate-950">{value.toLocaleString()}</p>
  </div>;
}

function UserFields({ form, setForm, includePassword }: { form: UserForm; setForm: (form: UserForm) => void; includePassword: boolean }) {
  return <div className="space-y-5">
    <div className="grid gap-5 sm:grid-cols-2">
      <FormInput id="first-name" label="First Name" value={form.firstName} maxLength={50} required onChange={(event) => setForm({ ...form, firstName: event.target.value })} />
      <FormInput id="last-name" label="Last Name" value={form.lastName} maxLength={50} required onChange={(event) => setForm({ ...form, lastName: event.target.value })} />
    </div>
    <FormInput id="email" label="Email Address" type="email" value={form.email} required onChange={(event) => setForm({ ...form, email: event.target.value })} />
    {includePassword && <FormInput id="password" label="Password" type="text" value={form.password} minLength={6} maxLength={72} required onChange={(event) => setForm({ ...form, password: event.target.value })} />}
  </div>;
}

function FormActions({ submitLabel, onCancel, disabled }: { submitLabel: string; onCancel: () => void; disabled: boolean }) {
  return <div className="mt-7 grid gap-3 sm:grid-cols-2">
    <button type="submit" disabled={disabled} className="rounded-xl bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60">{disabled ? "Saving..." : submitLabel}</button>
    <button type="button" onClick={onCancel} disabled={disabled} className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-900 transition hover:bg-slate-50 disabled:opacity-60">Cancel</button>
  </div>;
}

export default function UserManagement() {
  const { user: currentUser } = useUser();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [emailSearch, setEmailSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState("");
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteForm, setInviteForm] = useState<UserForm>(emptyInviteForm);
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null);
  const [editForm, setEditForm] = useState<UserForm>(emptyInviteForm);
  const [detailUser, setDetailUser] = useState<AdminUser | null>(null);
  const [deletingUser, setDeletingUser] = useState<AdminUser | null>(null);
  const normalizedSearch = emailSearch.trim().toLowerCase();
  const visibleUsers = users.filter((user) =>
    user.id !== currentUser?.id && user.email.toLowerCase().includes(normalizedSearch)
  );

  const loadUsers = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true);
    try {
      setUsers(await getAdminUsers());
      setPageError("");
    } catch (caught) {
      setPageError(errorMessage(caught));
    } finally {
      if (showLoading) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadUsers(true);
    const interval = window.setInterval(() => void loadUsers(), 60_000);
    return () => window.clearInterval(interval);
  }, [loadUsers]);

  function openInvite() {
    setInviteForm(emptyInviteForm());
    setFormError("");
    setInviteOpen(true);
  }

  async function submitInvite(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true); setFormError("");
    try {
      const created = await inviteAdminUser({ first_name: inviteForm.firstName.trim(), last_name: inviteForm.lastName.trim(), email: inviteForm.email.trim().toLowerCase(), password: inviteForm.password });
      setUsers((current) => [...current, created].sort((a, b) => a.id - b.id));
      setInviteOpen(false);
    } catch (caught) {
      setFormError(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }

  function openEdit(user: AdminUser) {
    setEditingUser(user);
    setEditForm({ firstName: user.first_name ?? "", lastName: user.last_name ?? "", email: user.email, password: DEFAULT_PASSWORD });
    setFormError("");
  }

  async function submitEdit(event: FormEvent) {
    event.preventDefault();
    if (!editingUser) return;
    setSubmitting(true); setFormError("");
    try {
      const request = {
        first_name: editForm.firstName.trim(),
        last_name: editForm.lastName.trim(),
        email: editForm.email.trim().toLowerCase(),
      };
      const updated = await updateAdminUser(editingUser.id, request);
      setUsers((current) => current.map((user) => user.id === updated.id ? updated : user));
      setEditingUser(null);
    } catch (caught) {
      setFormError(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }

  async function confirmDelete() {
    if (!deletingUser) return;
    setSubmitting(true); setFormError("");
    try {
      await deleteAdminUser(deletingUser.id);
      setUsers((current) => current.filter((user) => user.id !== deletingUser.id));
      setDeletingUser(null);
    } catch (caught) {
      setFormError(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }

  return <section className="p-5 sm:p-8 lg:p-12">
    <header className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
      <div><p className="text-sm font-bold uppercase tracking-wide text-violet-600">Administration</p><h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">User Management</h1></div>
      <button type="button" onClick={openInvite} className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-950 px-6 py-3.5 font-semibold text-white transition hover:bg-slate-800"><Plus size={20} /> Invite User</button>
    </header>

    {pageError && <div role="alert" className="mt-6 flex flex-col gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 sm:flex-row sm:items-center sm:justify-between"><span>{pageError}</span><button type="button" onClick={() => void loadUsers(true)} className="inline-flex items-center gap-2 font-semibold"><RefreshCw size={16} /> Try Again</button></div>}

    <div className="mt-6 max-w-xl">
      <label htmlFor="user-email-search" className="mb-2 block text-sm font-semibold text-slate-700">Search users by email</label>
      <div className="relative">
        <Search size={19} aria-hidden="true" className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
        <input id="user-email-search" type="search" value={emailSearch} onChange={(event) => setEmailSearch(event.target.value)} placeholder="Enter an email address" className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-11 pr-11 text-sm outline-none transition placeholder:text-slate-400 focus:border-violet-500 focus:ring-4 focus:ring-violet-100" />
        {emailSearch && <button type="button" onClick={() => setEmailSearch("")} aria-label="Clear email search" className="absolute right-2 top-1/2 grid size-8 -translate-y-1/2 place-items-center rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-700"><X size={17} /></button>}
      </div>
    </div>

    <div className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"><div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left">
      <thead className="border-b border-slate-200 bg-slate-50/70 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-6 py-5">User ID</th><th className="px-6 py-5">Name</th><th className="px-6 py-5">Email</th><th className="px-6 py-5">Joined</th><th className="px-6 py-5">Status</th><th className="px-6 py-5">Actions</th></tr></thead>
      <tbody className="divide-y divide-slate-200">
        {loading && <tr><td colSpan={6} className="px-6 py-16 text-center text-slate-500">Loading users...</td></tr>}
        {!loading && visibleUsers.map((user) => <tr key={user.id} className="transition hover:bg-slate-50/70">
          <td className="px-6 py-6"><span className="rounded-lg bg-slate-100 px-3 py-2 font-mono text-sm text-slate-600">{user.user_id}</span></td>
          <td className="px-6 py-6"><div className="flex items-center gap-3"><span className="grid size-11 place-items-center rounded-full bg-violet-600 text-sm font-bold text-white">{initials(user)}</span><span className="font-semibold text-slate-950">{fullName(user)}</span></div></td>
          <td className="px-6 py-6 text-slate-600">{user.email}</td><td className="px-6 py-6 text-slate-600">{displayDate(user.created_at)}</td>
          <td className="px-6 py-6"><span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${user.is_online ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>{user.is_online ? "Online" : "Offline"}</span></td>
          <td className="px-6 py-6"><div className="flex items-center gap-5 whitespace-nowrap"><button type="button" onClick={() => openEdit(user)} className="inline-flex items-center gap-1.5 font-semibold text-indigo-600 hover:text-indigo-800"><Pencil size={17} /> Edit</button><button type="button" onClick={() => { setDeletingUser(user); setFormError(""); }} className="inline-flex items-center gap-1.5 font-semibold text-red-500 hover:text-red-700"><Trash2 size={17} /> Delete</button></div></td>
        </tr>)}
        {!loading && visibleUsers.length === 0 && !pageError && <tr><td colSpan={6} className="px-6 py-16 text-center text-slate-500">{normalizedSearch ? "No users match this email search." : "No users have been added yet."}</td></tr>}
      </tbody>
    </table></div></div>

    {inviteOpen && <Modal title="Invite User" wide onClose={() => !submitting && setInviteOpen(false)}><form onSubmit={submitInvite}>{formError && <p role="alert" className="mb-5 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{formError}</p>}<UserFields form={inviteForm} setForm={setInviteForm} includePassword /><p className="mt-2 text-xs text-slate-500">The default password is 11111111.</p><FormActions submitLabel="Add User" onCancel={() => setInviteOpen(false)} disabled={submitting} /></form></Modal>}
    {editingUser && (
      <Modal title="Edit User" wide onClose={() => !submitting && setEditingUser(null)}>
        <form onSubmit={submitEdit}>
          {formError && <p role="alert" className="mb-5 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{formError}</p>}
          <div className="mb-5 grid gap-4 sm:grid-cols-2">
            <ReadOnlyInfo label="User ID" value={editingUser.user_id} />
            <ReadOnlyInfo label="Role" value={displayRole(editingUser.role)} />
          </div>
          <UserFields form={editForm} setForm={setEditForm} includePassword={false} />
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <ReadOnlyInfo label="Joined" value={displayDate(editingUser.created_at)} />
            <ReadOnlyInfo label="Last Active" value={displayDateTime(editingUser.last_seen_at)} />
          </div>
          <button type="button" onClick={() => setDetailUser(editingUser)} className="mt-5 inline-flex items-center gap-2 rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50">
            <UserCircle size={18} /> View Details
          </button>
          <FormActions submitLabel="Save Changes" onCancel={() => setEditingUser(null)} disabled={submitting} />
        </form>
      </Modal>
    )}
    {detailUser && (
      <Modal title="User Details" onClose={() => setDetailUser(null)}>
        <div className="flex items-center gap-4">
          <UserAvatar user={detailUser} size="size-16" />
          <div className="min-w-0">
            <h3 className="truncate text-xl font-bold text-slate-950">{fullName(detailUser)}</h3>
            <p className="truncate text-sm text-slate-500">{detailUser.email}</p>
          </div>
        </div>
        <div className="mt-6">
          <ReadOnlyInfo label="Region" value={detailUser.region || "Not provided"} />
        </div>
        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          <DetailStat icon={<Target size={19} className="text-indigo-500" />} label="Goals" value={detailUser.goals_count} />
          <DetailStat icon={<Heart size={19} className="text-red-500" />} label="Liked Articles" value={detailUser.liked_articles_count} />
          <DetailStat icon={<Bookmark size={19} className="text-violet-500" />} label="Saved Articles" value={detailUser.saved_articles_count} />
        </div>
      </Modal>
    )}
    {deletingUser && <Modal title="Delete User" onClose={() => !submitting && setDeletingUser(null)}>{formError && <p role="alert" className="mb-5 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{formError}</p>}<p className="text-sm leading-6 text-slate-600">Are you sure you want to delete <strong className="text-slate-900">{fullName(deletingUser)}</strong>? This action cannot be undone.</p><div className="mt-7 grid gap-3 sm:grid-cols-2"><button type="button" disabled={submitting} onClick={() => void confirmDelete()} className="rounded-xl bg-red-600 px-5 py-3 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-60">{submitting ? "Deleting..." : "Delete User"}</button><button type="button" disabled={submitting} onClick={() => setDeletingUser(null)} className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold hover:bg-slate-50 disabled:opacity-60">Cancel</button></div></Modal>}
  </section>;
}
