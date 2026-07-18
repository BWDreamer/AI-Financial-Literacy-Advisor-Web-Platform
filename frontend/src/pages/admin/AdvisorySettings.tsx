import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { RefreshCw, RotateCcw, Save, ShieldCheck } from "lucide-react";
import {
  getAdvisorySettings,
  updateAdvisorySettings,
  type AdvisorySettings as AdvisorySettingsData,
} from "../../api/admin";

const defaultSettings: AdvisorySettingsData = {
  topics: [
    { name: "Budgeting", enabled: true },
    { name: "Saving", enabled: true },
    { name: "Tax", enabled: true },
    { name: "Superannuation", enabled: true },
    { name: "Investing", enabled: false },
    { name: "Debt", enabled: true },
  ],
};

export default function AdvisorySettings() {
  const [settings, setSettings] = useState<AdvisorySettingsData>(defaultSettings);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [pageError, setPageError] = useState("");
  const [savedMessage, setSavedMessage] = useState("");

  const loadSettings = useCallback(async () => {
    setLoading(true);
    setPageError("");
    try {
      const data = await getAdvisorySettings();
      setSettings(data);
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Unable to load advisory settings.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSettings();
  }, [loadSettings]);

  const summary = useMemo(() => {
    const enabledTopics = settings.topics.filter((topic) => topic.enabled);
    return {
      enabledCount: enabledTopics.length,
      disabledCount: settings.topics.length - enabledTopics.length,
      enabledTopics,
    };
  }, [settings]);

  function updateTopic(index: number, enabled: boolean) {
    setSettings((current) => ({
      ...current,
      topics: current.topics.map((topic, topicIndex) =>
        topicIndex === index ? { ...topic, enabled } : topic
      ),
    }));
    setSavedMessage("");
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setPageError("");
    try {
      const data = await updateAdvisorySettings(settings.topics);
      setSettings(data);
      setSavedMessage("Advisory settings saved.");
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Unable to save advisory settings.");
    } finally {
      setSaving(false);
    }
  }

  async function resetSettings() {
    setSaving(true);
    setPageError("");
    try {
      const data = await updateAdvisorySettings(defaultSettings.topics);
      setSettings(data);
      setSavedMessage("Advisory settings reset to defaults.");
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Unable to reset advisory settings.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="p-5 sm:p-8 lg:p-12">
      <header>
        <p className="text-sm font-bold uppercase tracking-wide text-violet-600">Administration</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">
          Advisory Settings
        </h1>
      </header>

      {savedMessage && (
        <div
          role="status"
          className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-700"
        >
          {savedMessage}
        </div>
      )}

      {pageError && (
        <div
          role="alert"
          className="mt-6 flex flex-col gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 sm:flex-row sm:items-center sm:justify-between"
        >
          <span>{pageError}</span>
          <button type="button" onClick={() => void loadSettings()} className="inline-flex items-center gap-2 font-semibold">
            <RefreshCw size={16} /> Try Again
          </button>
        </div>
      )}

      <form onSubmit={submit} className="mt-8 grid gap-7 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-3">
            <span className="grid size-11 place-items-center rounded-xl bg-blue-50 text-blue-600">
              <ShieldCheck size={20} />
            </span>
            <div>
              <h2 className="text-xl font-bold text-slate-950">Topic Controls</h2>
              <p className="mt-1 text-sm text-slate-500">
                Choose which advisory topics are available to users.
              </p>
            </div>
          </div>

          <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200">
            <div className="grid grid-cols-[minmax(0,1fr)_130px] bg-slate-50 px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
              <span>Topic</span>
              <span>Status</span>
            </div>
            <div className="divide-y divide-slate-200">
              {settings.topics.map((topic, index) => (
                <div
                  key={topic.name}
                  className="grid grid-cols-[minmax(0,1fr)_130px] items-center gap-4 px-4 py-4"
                >
                  <p className="font-semibold text-slate-950">{topic.name}</p>
                  <button
                    type="button"
                    onClick={() => updateTopic(index, !topic.enabled)}
                    disabled={loading || saving}
                    className={`w-fit rounded-full px-3 py-1 text-xs font-bold transition ${
                      topic.enabled
                        ? "bg-emerald-50 text-emerald-700"
                        : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {loading ? "Loading" : topic.enabled ? "Enabled" : "Disabled"}
                  </button>
                </div>
              ))}
            </div>
          </div>
        </section>

        <aside className="space-y-6">
          <section className="sticky top-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-bold text-slate-950">Summary Preview</h2>
            <div className="mt-5 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-xl bg-emerald-50 px-3 py-3 text-center">
                  <p className="text-2xl font-bold text-emerald-700">{summary.enabledCount}</p>
                  <p className="text-xs font-semibold text-emerald-700">Enabled</p>
                </div>
                <div className="rounded-xl bg-slate-100 px-3 py-3 text-center">
                  <p className="text-2xl font-bold text-slate-600">{summary.disabledCount}</p>
                  <p className="text-xs font-semibold text-slate-500">Disabled</p>
                </div>
              </div>

              <div>
                <p className="mb-2 text-sm font-semibold text-slate-600">Enabled topics</p>
                <div className="flex flex-wrap gap-2">
                  {summary.enabledTopics.map((topic) => (
                    <span
                      key={topic.name}
                      className="rounded-full bg-violet-50 px-3 py-1 text-xs font-semibold text-violet-700"
                    >
                      {topic.name}
                    </span>
                  ))}
                  {summary.enabledTopics.length === 0 && (
                    <span className="text-sm text-slate-500">No topics enabled.</span>
                  )}
                </div>
              </div>
            </div>

            <div className="mt-7 grid gap-3">
              <button
                type="submit"
                disabled={loading || saving}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Save size={17} /> {saving ? "Saving..." : "Save Settings"}
              </button>
              <button
                type="button"
                onClick={() => void resetSettings()}
                disabled={loading || saving}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <RotateCcw size={17} /> Reset Defaults
              </button>
            </div>
          </section>
        </aside>
      </form>
    </section>
  );
}
