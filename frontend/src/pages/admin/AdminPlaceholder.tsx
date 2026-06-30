type AdminPlaceholderProps = {
  title: string;
};

export default function AdminPlaceholder({ title }: AdminPlaceholderProps) {
  return (
    <section className="p-6 sm:p-10 lg:p-12">
      <p className="text-sm font-bold uppercase tracking-wide text-violet-600">Administration</p>
      <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">{title}</h1>
      <div className="mt-8 rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
        This section will be implemented in a later stage.
      </div>
    </section>
  );
}
