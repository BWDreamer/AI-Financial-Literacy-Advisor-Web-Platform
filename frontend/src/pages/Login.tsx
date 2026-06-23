import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { loginAccount } from "../api/auth";
import AuthLayout from "../components/AuthLayout";
import FormInput from "../components/FormInput";
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
      await Promise.all([refreshUser(), refreshProfile()]);
      navigate("/home");
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
  if (user) return <Navigate to="/home" replace />;
  return (
    <AuthLayout activeTab="login" title="Welcome back" subtitle="Sign in to continue to your financial dashboard.">
      <form className="space-y-5" onSubmit={handleSubmit}>
        {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">{error}</p>}
        <FormInput id="login-email" label="Email address" name="email" type="email" autoComplete="email" placeholder="you@example.com" required />
        <FormInput id="login-password" label="Password" name="password" type="password" autoComplete="current-password" placeholder="Enter your password" required />
        <PrimaryButton type="submit" disabled={loading}>{loading ? "Signing in..." : "Sign In"}</PrimaryButton>
      </form>
    </AuthLayout>
  );
}
