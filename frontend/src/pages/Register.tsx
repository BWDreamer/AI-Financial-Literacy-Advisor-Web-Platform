import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { register } from "../api/client";
import AuthLayout from "../components/AuthLayout";
import FormInput from "../components/FormInput";
import PrimaryButton from "../components/PrimaryButton";

function RegisterFields({ error, loading }: { error: string; loading: boolean }) {
  return <>
    {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">{error}</p>}
    <FormInput id="register-email" label="Email address" name="email" type="email" autoComplete="email" placeholder="you@example.com" required />
    <FormInput id="register-password" label="Password" name="password" type="password" autoComplete="new-password" minLength={8} maxLength={72} placeholder="At least 8 characters" required />
    <FormInput id="confirm-password" label="Confirm password" name="confirmPassword" type="password" autoComplete="new-password" placeholder="Re-enter your password" required />
    <PrimaryButton type="submit" disabled={loading}>{loading ? "Creating account..." : "Create Account"}</PrimaryButton>
  </>;
}

export default function Register() {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password"));
    if (password !== form.get("confirmPassword")) return setError("Passwords do not match.");
    setError("");
    setLoading(true);
    try {
      await register(String(form.get("email")), password);
      navigate("/dashboard");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to create your account. Please try again.");
    } finally {
      setLoading(false);
    }
  }
  return (
    <AuthLayout activeTab="register" title="Create your account" subtitle="Start building healthier financial habits today.">
      <form className="space-y-5" onSubmit={handleSubmit}>
        <RegisterFields error={error} loading={loading} />
      </form>
    </AuthLayout>
  );
}
