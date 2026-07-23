import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { loginAccount, resetPassword, sendPasswordResetVerificationCode } from "../api/auth";
import AuthLayout from "../components/AuthLayout";
import FormInput from "../components/FormInput";
import Modal from "../components/Modal";
import PasswordChecklist, { isStrongPassword } from "../components/PasswordChecklist";
import PasswordInput from "../components/PasswordInput";
import PrimaryButton from "../components/PrimaryButton";
import { useUser } from "../store/UserProvider";
import { setToken } from "../store/tokenService";

function useLoginForm() {
  const navigate = useNavigate(); const { user, refreshUser, refreshProfile } = useUser();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setError("");
    setLoading(true);
    try {
      const result = await loginAccount(String(form.get("email")), String(form.get("password")));
      setToken(result.access_token);
      const currentUser = await refreshUser();
      if (currentUser.role === "admin") {
        navigate("/admin", { replace: true });
      } else {
        await refreshProfile();
        navigate("/home", { replace: true });
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to sign in. Please try again.");
    } finally {
      setLoading(false);
    }
  }
  return { user, error, loading, handleSubmit };
}

export default function Login() {
  const { user, error, loading, handleSubmit } = useLoginForm();
  const [forgotOpen, setForgotOpen] = useState(false);
  if (user) return <Navigate to={user.role === "admin" ? "/admin" : "/home"} replace />;
  return (
    <AuthLayout activeTab="login" title="Welcome back" subtitle="Sign in to continue to your financial dashboard.">
      <form className="space-y-5" onSubmit={handleSubmit}>
        {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">{error}</p>}
        <FormInput id="login-email" label="Email address" name="email" type="email" autoComplete="email" placeholder="you@example.com" required />
        <PasswordInput id="login-password" label="Password" name="password" autoComplete="current-password" placeholder="Enter your password" required />
        <button type="button" onClick={() => setForgotOpen(true)} className="text-sm font-semibold text-blue-600 hover:text-blue-700">Forgot password?</button>
        <PrimaryButton type="submit" disabled={loading}>{loading ? "Signing in..." : "Sign In"}</PrimaryButton>
      </form>
      {forgotOpen && <ForgotPasswordModal onClose={() => setForgotOpen(false)} />}
    </AuthLayout>
  );
}

function useForgotPassword(onClose: () => void) {
  const [email, setEmail] = useState(""); const [password, setPassword] = useState("");
  const [sent, setSent] = useState(false); const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false); const [message, setMessage] = useState(""); const [error, setError] = useState("");
  async function sendCode() {
    setError(""); setMessage(""); setSending(true);
    try { await sendPasswordResetVerificationCode(email.trim()); setSent(true); setMessage("A verification code was sent to your email."); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to send verification code."); }
    finally { setSending(false); }
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget); setError(""); setLoading(true);
    if (password !== form.get("confirm")) { setError("Passwords do not match."); setLoading(false); return; }
    try { await resetPassword(email.trim(), String(form.get("code")), password); setMessage("Password updated. Please sign in with your new password."); setTimeout(onClose, 900); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to reset password."); }
    finally { setLoading(false); }
  }
  return { email, setEmail, password, setPassword, sent, loading, sending, message, error, sendCode, submit };
}

function ForgotPasswordModal({ onClose }: { onClose: () => void }) {
  const form = useForgotPassword(onClose);
  return <Modal title="Reset Password" onClose={onClose}><form onSubmit={form.submit} className="grid gap-4">
    <p className="text-sm text-slate-500">Enter your account email, then use the verification code to set a new password.</p>
    <FormInput id="reset-email" label="Email address" type="email" value={form.email} onChange={(event) => { form.setEmail(event.target.value); }} required />
    <button type="button" onClick={() => void form.sendCode()} disabled={form.sending || !form.email.trim()} className="h-12 rounded-xl border border-blue-300 px-4 text-sm font-semibold text-blue-700 hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50">{form.sending ? "Sending..." : form.sent ? "Resend code" : "Send verification code"}</button>
    <FormInput id="reset-code" name="code" label="Verification code" inputMode="numeric" pattern="[0-9]{6}" minLength={6} maxLength={6} autoComplete="one-time-code" required />
    <PasswordInput id="reset-password" label="New password" autoComplete="new-password" value={form.password} onChange={(event) => form.setPassword(event.target.value)} minLength={10} required />
    <PasswordChecklist password={form.password} />
    <PasswordInput id="reset-confirm" name="confirm" label="Confirm new password" autoComplete="new-password" minLength={10} required />
    {form.error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{form.error}</p>}{form.message && <p className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{form.message}</p>}
    <div className="flex justify-end gap-3"><button type="button" onClick={onClose} className="rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50">Cancel</button><PrimaryButton className="w-auto" disabled={form.loading || !form.sent || !isStrongPassword(form.password)}>{form.loading ? "Saving..." : "Reset Password"}</PrimaryButton></div>
  </form></Modal>;
}
