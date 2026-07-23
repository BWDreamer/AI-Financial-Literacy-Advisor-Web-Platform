import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import {
  loginAccount,
  registerAccount,
  sendRegistrationVerificationCode,
} from "../api/auth";
import AuthLayout from "../components/AuthLayout";
import FormInput from "../components/FormInput";
import PasswordChecklist, { isStrongPassword } from "../components/PasswordChecklist";
import PasswordInput from "../components/PasswordInput";
import PrimaryButton from "../components/PrimaryButton";
import { useUser } from "../store/UserProvider";
import { setToken } from "../store/tokenService";

type RegisterFieldsProps = {
  email: string;
  error: string;
  info: string;
  loading: boolean;
  sendingCode: boolean;
  codeSent: boolean;
  password: string;
  onEmailChange: (email: string) => void;
  onPasswordChange: (password: string) => void;
  onSendCode: () => void;
};

function RegisterFields({
  email,
  error,
  info,
  loading,
  sendingCode,
  codeSent,
  password,
  onEmailChange,
  onPasswordChange,
  onSendCode,
}: RegisterFieldsProps) {
  const passwordValid = isStrongPassword(password);
  return <>
    {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">{error}</p>}
    {info && <p className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700" role="status">{info}</p>}
    <FormInput id="register-username" label="Username" name="username" minLength={2} maxLength={50} autoComplete="username" placeholder="Choose a username" required />
    <FormInput
      id="register-email"
      label="Email address"
      name="email"
      type="email"
      autoComplete="email"
      placeholder="you@example.com"
      value={email}
      onChange={(event) => onEmailChange(event.target.value)}
      required
    />
    <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
      <FormInput
        id="register-verification-code"
        label="Email verification code"
        name="verificationCode"
        inputMode="numeric"
        pattern="[0-9]{6}"
        minLength={6}
        maxLength={6}
        autoComplete="one-time-code"
        placeholder="6-digit code"
        required
      />
      <button
        type="button"
        onClick={onSendCode}
        disabled={sendingCode || !email.trim()}
        className="h-12 rounded-xl border border-blue-300 px-4 text-sm font-semibold text-blue-700 transition hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {sendingCode ? "Sending..." : codeSent ? "Resend code" : "Send code"}
      </button>
    </div>
    <PasswordInput id="register-password" label="Password" name="password" autoComplete="new-password" minLength={10} maxLength={72} placeholder="At least 10 characters" value={password} onChange={(event) => onPasswordChange(event.target.value)} required />
    <PasswordChecklist password={password} />
    <PasswordInput id="confirm-password" label="Confirm password" name="confirmPassword" autoComplete="new-password" placeholder="Re-enter your password" required />
    <PrimaryButton type="submit" disabled={loading || !passwordValid}>{loading ? "Creating account..." : "Create Account"}</PrimaryButton>
  </>;
}

function useRegisterForm() {
  const navigate = useNavigate();
  const { user, refreshUser, refreshProfile } = useUser();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [loading, setLoading] = useState(false);
  const [sendingCode, setSendingCode] = useState(false);
  const [codeSent, setCodeSent] = useState(false);

  function changeEmail(value: string) {
    setEmail(value);
    setCodeSent(false);
    setInfo("");
  }

  async function sendCode() {
    setError("");
    setInfo("");
    setSendingCode(true);
    try {
      await sendRegistrationVerificationCode(email.trim());
      setCodeSent(true);
      setInfo("A verification code was sent to " + email.trim() + ".");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to send the verification code.");
    } finally {
      setSendingCode(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password"));
    if (password !== form.get("confirmPassword")) {
      setError("Passwords do not match.");
      return;
    }
    if (!isStrongPassword(password)) {
      setError("Password must include lowercase, uppercase, numbers, and at least 10 characters.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const normalizedEmail = email.trim();
      await registerAccount(
        normalizedEmail,
        String(form.get("username")),
        password,
        String(form.get("verificationCode")),
      );
      const result = await loginAccount(normalizedEmail, password);
      setToken(result.access_token);
      await Promise.all([refreshUser(), refreshProfile()]);
      navigate("/home");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to create your account. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return {
    user,
    email,
    password,
    error,
    info,
    loading,
    sendingCode,
    codeSent,
    changeEmail,
    setPassword,
    sendCode,
    handleSubmit,
  };
}

export default function Register() {
  const form = useRegisterForm();
  if (form.user) return <Navigate to="/home" replace />;
  return (
    <AuthLayout activeTab="register" title="Create your account" subtitle="Start building healthier financial habits today.">
      <form className="space-y-5" onSubmit={form.handleSubmit}>
        <RegisterFields
          email={form.email}
          error={form.error}
          info={form.info}
          loading={form.loading}
          sendingCode={form.sendingCode}
          codeSent={form.codeSent}
          password={form.password}
          onEmailChange={form.changeEmail}
          onPasswordChange={form.setPassword}
          onSendCode={() => void form.sendCode()}
        />
      </form>
    </AuthLayout>
  );
}
