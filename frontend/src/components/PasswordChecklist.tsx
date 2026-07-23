type PasswordChecklistProps = {
  password: string;
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

export default function PasswordChecklist({ password }: PasswordChecklistProps) {
  return (
    <div className="grid grid-cols-1 gap-3 rounded-2xl bg-slate-50 p-4 text-sm sm:grid-cols-2">
      {getPasswordRules(password).map((rule) => (
        <div key={rule.label} className="flex items-center gap-3 text-slate-600">
          <span className={`size-4 rounded-full border ${rule.valid ? "border-blue-600 bg-blue-600" : "border-slate-300"}`} />
          <span className={rule.valid ? "font-medium text-slate-900" : ""}>{rule.label}</span>
        </div>
      ))}
    </div>
  );
}
