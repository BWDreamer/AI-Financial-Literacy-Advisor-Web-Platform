import { useState } from "react";
import type { InputHTMLAttributes } from "react";
import { Eye, EyeOff } from "lucide-react";

type PasswordInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & {
  label: string;
};

export default function PasswordInput({ id, label, ...props }: PasswordInputProps) {
  const [visible, setVisible] = useState(false);
  return <label className="block" htmlFor={id}><span className="mb-2 block text-sm font-medium text-slate-700">{label}</span>
    <span className="relative block"><input id={id} type={visible ? "text" : "password"} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 pr-12 text-sm outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-100" {...props} />
      <button type="button" onClick={() => setVisible((value) => !value)} className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700" aria-label={visible ? "Hide password" : "Show password"}>
        {visible ? <EyeOff size={18} /> : <Eye size={18} />}
      </button></span></label>;
}
