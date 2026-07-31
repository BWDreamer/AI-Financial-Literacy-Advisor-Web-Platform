type PasswordChecklistProps = {
  password: string;
  variant?: "default" | "glass";
};

export function getPasswordRules(password: string) {
  return [
    { label: "Lowercase characters", valid: /[a-z]/.test(password) },
    { label: "Uppercase characters", valid: /[A-Z]/.test(password) },
    { label: "Numbers", valid: /\d/.test(password) },
    { label: "At least 10 characters", valid: password.length >= 10 },
  ];
}

export function isStrongPassword(password: string) {
  return getPasswordRules(password).every((rule) => rule.valid);
}

export default function PasswordChecklist({ password, variant = "default" }: PasswordChecklistProps) {
  const isGlass = variant === "glass";

  return (
    <div className={`grid grid-cols-1 gap-3 rounded-2xl p-4 text-sm sm:grid-cols-2 ${isGlass ? "border border-white/15 bg-white/10" : "bg-slate-50"}`}>
      {getPasswordRules(password).map((rule) => (
        <div key={rule.label} className={`flex items-center gap-3 ${isGlass ? "text-white/75" : "text-slate-600"}`}>
          <span className={`size-4 rounded-full border ${rule.valid ? "border-blue-300 bg-blue-400" : isGlass ? "border-white/35" : "border-slate-300"}`} />
          <span className={rule.valid ? isGlass ? "font-medium text-white" : "font-medium text-slate-900" : ""}>{rule.label}</span>
        </div>
      ))}
    </div>
  );
}
