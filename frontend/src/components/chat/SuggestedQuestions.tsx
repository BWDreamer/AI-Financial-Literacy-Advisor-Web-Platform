import { Sparkles } from "lucide-react";

type SuggestedQuestion = {
  id: string;
  question: string;
};

const SUGGESTION_COUNT = 3;
const SUGGESTION_STORAGE_KEY = "financeai-chat-suggested-question-ids";

export const australianFinancialRuleQuestions: SuggestedQuestion[] = [
  {
    id: "tax-brackets",
    question: "What are the latest Australian resident income tax brackets?",
  },
  {
    id: "medicare-levy",
    question: "Does the resident income tax table include the Medicare levy?",
  },
  {
    id: "marginal-tax-calculation",
    question: "How is Australian resident income tax calculated across marginal tax brackets?",
  },
  {
    id: "knowledge-years",
    question: "Which Australian tax rule years are available in the knowledge base?",
  },
  {
    id: "super-guarantee-rate",
    question: "What is the current employer super guarantee rate?",
  },
  {
    id: "super-qualifying-earnings",
    question: "What earnings are used to calculate employer super guarantee?",
  },
  {
    id: "payday-super",
    question: "When must employers pay super under Payday Super?",
  },
  {
    id: "concessional-cap",
    question: "What is the current concessional super contribution cap?",
  },
  {
    id: "concessional-cap-inclusions",
    question: "Which super contributions count towards the concessional contributions cap?",
  },
  {
    id: "non-concessional-cap",
    question: "What is the current non-concessional super contribution cap?",
  },
];

function shuffledQuestions() {
  const questions = [...australianFinancialRuleQuestions];
  for (let index = questions.length - 1; index > 0; index -= 1) {
    const randomIndex = Math.floor(Math.random() * (index + 1));
    [questions[index], questions[randomIndex]] = [
      questions[randomIndex],
      questions[index],
    ];
  }
  return questions;
}

function storedQuestionIds() {
  if (typeof window === "undefined") return new Set<string>();
  try {
    const storedValue = window.sessionStorage.getItem(SUGGESTION_STORAGE_KEY);
    const parsedValue = storedValue ? JSON.parse(storedValue) : [];
    return new Set<string>(Array.isArray(parsedValue) ? parsedValue : []);
  } catch {
    return new Set<string>();
  }
}

export function selectSuggestedQuestions() {
  const previousIds = storedQuestionIds();
  let selected = shuffledQuestions().slice(0, SUGGESTION_COUNT);

  if (
    previousIds.size === SUGGESTION_COUNT
    && selected.every((question) => previousIds.has(question.id))
  ) {
    const replacement = australianFinancialRuleQuestions.find(
      (question) => !previousIds.has(question.id),
    );
    if (replacement) selected = [replacement, ...selected.slice(1)];
  }

  return selected;
}

export function rememberSuggestedQuestions(questions: SuggestedQuestion[]) {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(
      SUGGESTION_STORAGE_KEY,
      JSON.stringify(questions.map((question) => question.id)),
    );
  } catch {
    // Random suggestions still work when browser storage is unavailable.
  }
}

export default function SuggestedQuestions({
  disabled,
  questions,
  onSelect,
}: {
  disabled: boolean;
  questions: SuggestedQuestion[];
  onSelect: (question: string) => void;
}) {
  return (
    <section aria-label="Suggested questions" className="mb-3">
      <div className="mb-2 flex items-center gap-2 px-1 text-sm font-bold text-slate-700">
        <Sparkles size={17} className="text-blue-600" aria-hidden="true" />
        <h2>You might want to ask</h2>
      </div>
      <div className="grid gap-2 lg:grid-cols-3">
        {questions.map((item) => (
          <button
            key={item.id}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(item.question)}
            className="min-h-16 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-left text-sm font-semibold leading-5 text-slate-700 shadow-sm transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-800 focus:outline-none focus:ring-4 focus:ring-blue-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {item.question}
          </button>
        ))}
      </div>
    </section>
  );
}
