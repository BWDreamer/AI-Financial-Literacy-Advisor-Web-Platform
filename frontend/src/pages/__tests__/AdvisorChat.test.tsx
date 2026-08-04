import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import AdvisorChat from "../AdvisorChat";
import {
  addConversationMessage,
  createConversation,
  deleteConversation,
  getConversation,
  getConversations,
  sendAdvisorPdfMessage,
  streamAdvisorMessage,
} from "../../api/chat";

jest.mock("../../api/chat", () => ({
  addConversationMessage: jest.fn(),
  createConversation: jest.fn(),
  deleteConversation: jest.fn(),
  getConversation: jest.fn(),
  getConversations: jest.fn(),
  sendAdvisorPdfMessage: jest.fn(),
  streamAdvisorMessage: jest.fn(),
}));

jest.mock("../../store/UserProvider", () => ({
  useUser: () => ({
    user: {
      id: 1,
      username: "Lee",
      email: "lee@example.com",
      role: "user",
    },
  }),
}));

jest.mock("../../components/chat/SuggestedQuestions", () => ({
  __esModule: true,
  default: ({ onSelect, disabled }: { onSelect: (question: string) => void; disabled: boolean }) => (
    <button type="button" disabled={disabled} onClick={() => onSelect("What is budgeting?")}>
      Suggested budgeting question
    </button>
  ),
  rememberSuggestedQuestions: jest.fn(),
  selectSuggestedQuestions: jest.fn(() => ["What is budgeting?"]),
}));

const mockedGetConversations = jest.mocked(getConversations);
const mockedGetConversation = jest.mocked(getConversation);
const mockedCreateConversation = jest.mocked(createConversation);
const mockedSendAdvisorPdfMessage = jest.mocked(sendAdvisorPdfMessage);
const mockedStreamAdvisorMessage = jest.mocked(streamAdvisorMessage);
const mockedDeleteConversation = jest.mocked(deleteConversation);
const mockedAddConversationMessage = jest.mocked(addConversationMessage);

beforeAll(() => {
  Element.prototype.scrollIntoView = jest.fn();
});

function renderAdvisorChat(initialEntry: any = "/advisor-chat") {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <AdvisorChat />
    </MemoryRouter>
  );
}

const conversations = [
  {
    conversation_id: 1,
    title: "Budget chat",
    created_at: "2026-07-21T00:00:00Z",
    updated_at: "2026-07-21T00:00:00Z",
  },
];

const conversationDetail = {
  ...conversations[0],
  messages: [
    {
      id: 1,
      role: "user" as const,
      content: "What is budgeting?",
      created_at: "2026-07-21T00:00:00Z",
    },
    {
      id: 2,
      role: "assistant" as const,
      content: "Budgeting means planning your money.",
      created_at: "2026-07-21T00:00:01Z",
    },
  ],
};

beforeEach(() => {
  jest.clearAllMocks();
  mockedGetConversations.mockResolvedValue(conversations);
  mockedGetConversation.mockResolvedValue(conversationDetail);
  mockedCreateConversation.mockResolvedValue({
    conversation_id: 2,
    title: "New Conversation",
    created_at: "2026-07-22T00:00:00Z",
    updated_at: "2026-07-22T00:00:00Z",
  });
  mockedStreamAdvisorMessage.mockImplementation(async (_message, _conversationId, onDelta) => {
    onDelta("Educational response.");
    return {
      answer: "Educational response.",
      model: "test-model",
      memory_updated: false,
      memory_update_count: 0,
    };
  });
  mockedSendAdvisorPdfMessage.mockResolvedValue({
    answer: "Educational response.",
    model: "test-model",
    memory_updated: false,
    memory_update_count: 0,
    imported_records: [],
    low_confidence: false,
    extracted_text_characters: 128,
  });
  mockedDeleteConversation.mockResolvedValue(undefined);
  mockedAddConversationMessage.mockResolvedValue({
    id: 3,
    role: "assistant",
    content: "Goal planning prompt",
    created_at: "2026-07-22T00:00:00Z",
  });
});

test("loads conversations and opens the latest conversation", async () => {
  renderAdvisorChat();

  expect(screen.getByText("Loading conversations...")).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: /advisor chat/i })).toBeInTheDocument();
  expect(screen.getByText("What is budgeting?")).toBeInTheDocument();
  const assistantReply = screen
    .getByText(/Budgeting means planning your money/i)
    .closest("article");
  expect(assistantReply).toHaveClass(
    "w-full",
    "bg-transparent",
    "lg:w-fit",
    "lg:max-w-[61.8%]",
    "lg:rounded-2xl",
    "lg:bg-white",
    "lg:p-4",
    "lg:shadow-sm",
  );
  expect(assistantReply).not.toHaveAttribute("style");
  expect(mockedGetConversations).toHaveBeenCalledTimes(1);
  expect(mockedGetConversation).toHaveBeenCalledWith(1);
});

test("shows the empty welcome when there are no saved conversations", async () => {
  mockedGetConversations.mockResolvedValueOnce([]);
  renderAdvisorChat();

  expect(await screen.findByText(/how can i help/i)).toBeInTheDocument();
  expect(screen.getByText(/Lee/)).toBeInTheDocument();
});

test("sends a suggested question in the active conversation and refreshes it", async () => {
  const user = userEvent.setup();
  renderAdvisorChat();

  await screen.findByText("What is budgeting?");
  await user.click(screen.getByRole("button", { name: /suggested budgeting question/i }));

  await waitFor(() => expect(mockedStreamAdvisorMessage).toHaveBeenCalledWith(
    "What is budgeting?",
    1,
    expect.any(Function),
    undefined,
    undefined,
    expect.any(AbortSignal),
  ));
  await waitFor(() => expect(mockedGetConversation).toHaveBeenCalledTimes(2));
  expect(screen.queryByText("Memory updated")).not.toBeInTheDocument();
});

test("shows a dismissible notice after memory is updated", async () => {
  mockedStreamAdvisorMessage.mockImplementationOnce(
    async (_message, _conversationId, onDelta) => {
      onDelta("I have updated your details.");
      return {
        answer: "I have updated your details.",
        model: "test-model",
        memory_updated: true,
        memory_update_count: 2,
      };
    },
  );
  const user = userEvent.setup();
  renderAdvisorChat();

  await screen.findByText("What is budgeting?");
  await user.click(
    screen.getByRole("button", { name: /suggested budgeting question/i }),
  );

  expect(await screen.findByText("Memory updated")).toBeInTheDocument();
  expect(
    screen.getByText("2 details saved to your memories."),
  ).toBeInTheDocument();

  await user.click(
    screen.getByRole("button", { name: /dismiss memory update/i }),
  );
  expect(screen.queryByText("Memory updated")).not.toBeInTheDocument();
});

test("creates a conversation before sending from an empty chat", async () => {
  mockedGetConversations.mockResolvedValueOnce([]);
  const user = userEvent.setup();
  renderAdvisorChat();

  await screen.findByText(/how can i help/i);
  await user.type(screen.getByPlaceholderText(/ask anything about personal finance/i), "Explain superannuation");
  await user.click(screen.getByTitle("Send message"));

  await waitFor(() => expect(mockedCreateConversation).toHaveBeenCalledTimes(1));
  await waitFor(() => expect(mockedStreamAdvisorMessage).toHaveBeenCalledWith(
    "Explain superannuation",
    2,
    expect.any(Function),
    undefined,
    undefined,
    expect.any(AbortSignal),
  ));
});

test("shows an error and removes the thinking message when sending fails", async () => {
  mockedStreamAdvisorMessage.mockRejectedValueOnce(new Error("Unable to send your message."));
  const user = userEvent.setup();
  renderAdvisorChat();

  await screen.findByText("What is budgeting?");
  await user.type(screen.getByPlaceholderText(/ask anything about personal finance/i), "Explain investing");
  await user.click(screen.getByTitle("Send message"));

  expect(await screen.findByText("Unable to send your message.")).toBeInTheDocument();
  await waitFor(() => expect(screen.queryByText("Thinking...")).not.toBeInTheDocument());
  await waitFor(() => expect(mockedGetConversation).toHaveBeenCalledTimes(2));
});

test("sends uploaded PDF files through the PDF advisor endpoint", async () => {
  const user = userEvent.setup();
  const { container } = renderAdvisorChat();
  const pdf = new File(["statement"], "statement.pdf", {
    type: "application/pdf",
  });

  await screen.findByText("What is budgeting?");
  const input = container.querySelector("input[type='file']") as HTMLInputElement;
  await user.upload(input, pdf);
  await user.type(
    screen.getByPlaceholderText(/ask anything about personal finance/i),
    "Review this statement",
  );
  await user.click(screen.getByTitle("Send message"));

  await waitFor(() => expect(mockedSendAdvisorPdfMessage).toHaveBeenCalledWith(
    "Review this statement",
    1,
    [pdf],
    expect.any(AbortSignal),
  ));
  expect(mockedStreamAdvisorMessage).not.toHaveBeenCalled();
  await waitFor(() => expect(mockedGetConversation).toHaveBeenCalledTimes(2));
});

test("removes an uploaded PDF before sending", async () => {
  const user = userEvent.setup();
  const { container } = renderAdvisorChat();
  const pdf = new File(["statement"], "statement.pdf", {
    type: "application/pdf",
  });

  await screen.findByText("What is budgeting?");
  const input = container.querySelector("input[type='file']") as HTMLInputElement;
  await user.upload(input, pdf);

  expect(screen.getByText("statement.pdf")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /delete statement.pdf/i }));

  expect(screen.queryByText("statement.pdf")).not.toBeInTheDocument();
  await user.type(
    screen.getByPlaceholderText(/ask anything about personal finance/i),
    "Review this statement",
  );
  await user.click(screen.getByTitle("Send message"));

  await waitFor(() => expect(mockedStreamAdvisorMessage).toHaveBeenCalledWith(
    "Review this statement",
    1,
    expect.any(Function),
    undefined,
    undefined,
    expect.any(AbortSignal),
  ));
  expect(mockedSendAdvisorPdfMessage).not.toHaveBeenCalled();
});

test("removes the last uploaded PDF with backspace when the message is empty", async () => {
  const user = userEvent.setup();
  const { container } = renderAdvisorChat();
  const pdf = new File(["statement"], "statement.pdf", {
    type: "application/pdf",
  });

  await screen.findByText("What is budgeting?");
  const input = container.querySelector("input[type='file']") as HTMLInputElement;
  await user.upload(input, pdf);

  expect(screen.getByText("statement.pdf")).toBeInTheDocument();
  const composer = screen.getByPlaceholderText(/ask anything about personal finance/i);
  await user.click(composer);
  await user.keyboard("{Backspace}");

  expect(screen.queryByText("statement.pdf")).not.toBeInTheDocument();
});

test("shows a memory update notice after a PDF import updates memories", async () => {
  mockedSendAdvisorPdfMessage.mockResolvedValueOnce({
    answer: "I saved details from this document.",
    model: "test-model",
    memory_updated: true,
    memory_update_count: 0,
    imported_records: [],
    low_confidence: false,
    extracted_text_characters: 128,
  });
  const user = userEvent.setup();
  const { container } = renderAdvisorChat();
  const pdf = new File(["statement"], "statement.pdf", {
    type: "application/pdf",
  });

  await screen.findByText("What is budgeting?");
  const input = container.querySelector("input[type='file']") as HTMLInputElement;
  await user.upload(input, pdf);
  await user.click(screen.getByTitle("Send message"));

  expect(await screen.findByText("Memory updated")).toBeInTheDocument();
  expect(screen.getByText("1 detail saved to your memories.")).toBeInTheDocument();
});

test("renders streamed advisor deltas while a response is pending", async () => {
  let resolveStream: ((value: {
    answer: string;
    model: string;
    memory_updated: boolean;
    memory_update_count: number;
  }) => void) | undefined;
  mockedStreamAdvisorMessage.mockImplementationOnce(async (_message, _conversationId, onDelta) => {
    onDelta("First ");
    onDelta("second");
    return new Promise((resolve) => {
      resolveStream = resolve;
    });
  });
  const user = userEvent.setup();
  renderAdvisorChat();

  await screen.findByText("What is budgeting?");
  await user.type(screen.getByPlaceholderText(/ask anything about personal finance/i), "Explain cash flow");
  await user.click(screen.getByTitle("Send message"));

  const streamingReply = (await screen.findByText("First second"))
    .closest("article");
  expect(streamingReply).toHaveClass(
    "w-full",
    "bg-transparent",
    "lg:max-w-[61.8%]",
  );
  expect(streamingReply).not.toHaveAttribute("style");

  resolveStream?.({
    answer: "First second",
    model: "test-model",
    memory_updated: false,
    memory_update_count: 0,
  });
  await waitFor(() => expect(mockedGetConversation).toHaveBeenCalledTimes(2));
});

test("deletes a conversation from the history sidebar", async () => {
  const user = userEvent.setup();
  renderAdvisorChat();

  await screen.findByText("What is budgeting?");
  await user.click(screen.getByLabelText(/toggle conversation history/i));
  await user.click(screen.getAllByRole("button", { name: /delete budget chat/i })[0]);

  await waitFor(() => expect(mockedDeleteConversation).toHaveBeenCalledWith(1));
  await waitFor(() => expect(mockedGetConversations).toHaveBeenCalledTimes(2));
});

test("selects another conversation from the history sidebar", async () => {
  const user = userEvent.setup();
  const taxConversation = {
    conversation_id: 4,
    title: "Tax chat",
    created_at: "2026-07-23T00:00:00Z",
    updated_at: "2026-07-23T00:00:00Z",
  };
  mockedGetConversations.mockResolvedValueOnce([conversations[0], taxConversation]);
  mockedGetConversation.mockImplementation(async (id) => (
    id === 4
      ? {
        ...taxConversation,
        messages: [
          {
            id: 10,
            role: "user",
            content: "Can you explain tax deductions?",
            created_at: "2026-07-23T00:00:00Z",
          },
          {
            id: 11,
            role: "assistant",
            content: "Tax deductions reduce taxable income.",
            created_at: "2026-07-23T00:00:01Z",
          },
        ],
      }
      : conversationDetail
  ));

  renderAdvisorChat();

  await screen.findByText("Tax deductions reduce taxable income.");
  await user.click(screen.getByLabelText(/toggle conversation history/i));
  await user.click(screen.getAllByTitle("Budget chat")[0]);

  await waitFor(() => expect(mockedGetConversation).toHaveBeenCalledWith(1));
  expect(await screen.findByText(/Budgeting means planning your money/i)).toBeInTheDocument();
});

test("shows an error when selecting a conversation fails", async () => {
  const user = userEvent.setup();
  mockedGetConversation
    .mockResolvedValueOnce(conversationDetail)
    .mockRejectedValueOnce(new Error("Unable to load this conversation."));

  renderAdvisorChat();

  await screen.findByText("What is budgeting?");
  await user.click(screen.getByLabelText(/toggle conversation history/i));
  await user.click(screen.getAllByTitle("Budget chat")[0]);

  expect(await screen.findByText("Unable to load this conversation.")).toBeInTheDocument();
});

test("starts a new conversation from the history sidebar", async () => {
  const user = userEvent.setup();
  renderAdvisorChat();

  await screen.findByText("What is budgeting?");
  await user.click(screen.getByLabelText(/toggle conversation history/i));
  await user.click(screen.getAllByRole("button", { name: /new conversation/i })[0]);

  expect(await screen.findByText(/how can i help/i)).toBeInTheDocument();
  expect(screen.queryByText(/Budgeting means planning your money/i)).not.toBeInTheDocument();
});

test("shows an error when deleting a conversation fails", async () => {
  mockedDeleteConversation.mockRejectedValueOnce(new Error("Unable to delete conversation."));
  const user = userEvent.setup();
  renderAdvisorChat();

  await screen.findByText("What is budgeting?");
  await user.click(screen.getByLabelText(/toggle conversation history/i));
  await user.click(screen.getAllByRole("button", { name: /delete budget chat/i })[0]);

  expect(await screen.findByText("Unable to delete conversation.")).toBeInTheDocument();
  expect(mockedGetConversations).toHaveBeenCalledTimes(1);
});

test("starts goal planning by appending an assistant prompt", async () => {
  const user = userEvent.setup();
  renderAdvisorChat();

  await screen.findByText("What is budgeting?");
  await user.click(screen.getByRole("button", { name: /set a goal/i }));

  await waitFor(() => expect(mockedAddConversationMessage).toHaveBeenCalledWith(
    1,
    "assistant",
    expect.any(String),
  ));
});

test("selects a goal category after starting goal planning", async () => {
  const planningConversation = {
    ...conversationDetail,
    messages: [
      ...conversationDetail.messages,
      {
        id: 12,
        role: "assistant" as const,
        content: "What goal would you like to set today?\n\n[Financial goal planning mode: choose_category]",
        created_at: "2026-07-23T00:00:00Z",
      },
    ],
  };
  mockedGetConversation
    .mockResolvedValueOnce(conversationDetail)
    .mockResolvedValue(planningConversation);
  const user = userEvent.setup();
  renderAdvisorChat();

  await screen.findByText("What is budgeting?");
  await user.click(screen.getByRole("button", { name: /set a goal/i }));

  expect(await screen.findByRole("button", { name: /emergency fund/i })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /emergency fund/i }));

  await waitFor(() => expect(mockedAddConversationMessage).toHaveBeenLastCalledWith(
    1,
    "assistant",
    expect.stringContaining("What Emergency Fund goal would you like to set?"),
  ));
});

test("shows an error when starting goal planning fails", async () => {
  mockedAddConversationMessage.mockRejectedValueOnce(
    new Error("Unable to start goal planning."),
  );
  const user = userEvent.setup();
  renderAdvisorChat();

  await screen.findByText("What is budgeting?");
  await user.click(screen.getByRole("button", { name: /set a goal/i }));

  expect(await screen.findByText("Unable to start goal planning.")).toBeInTheDocument();
});

test("starts a goal review from route state and sends the goal id to the advisor", async () => {
  const goalReview = {
    kind: "goal_review" as const,
    version: 1 as const,
    goal_id: 7,
    name: "Emergency Fund",
    category: "Emergency Fund",
    target_amount: 10000,
    current_amount: 2500,
    monthly_contribution: 500,
    target_date: "2027-07-01",
    priority: "High",
    status: "on_track" as const,
    progress_percentage: 25,
  };

  renderAdvisorChat({
    pathname: "/advisor-chat",
    state: {
      mode: "goal-review",
      requestId: "advisor-chat-goal-review-test",
      goal: goalReview,
    },
  });

  await waitFor(() => expect(mockedCreateConversation).toHaveBeenCalledWith(
    "Goal review: Emergency Fund",
  ));
  await waitFor(() => expect(mockedStreamAdvisorMessage).toHaveBeenCalledWith(
    expect.stringContaining("Please review this existing financial goal"),
    2,
    expect.any(Function),
    undefined,
    7,
    expect.any(AbortSignal),
  ));
  await waitFor(() => expect(mockedGetConversation).toHaveBeenCalledWith(2));
});

test("shows an error when goal review cannot be completed", async () => {
  mockedStreamAdvisorMessage.mockRejectedValueOnce(new Error("Unable to review this goal."));
  const goalReview = {
    kind: "goal_review" as const,
    version: 1 as const,
    goal_id: 8,
    name: "Car Fund",
    category: "General Saving",
    target_amount: 12000,
    current_amount: 1000,
    monthly_contribution: 300,
    target_date: "2027-12-01",
    priority: "Medium",
    status: "behind" as const,
    progress_percentage: 8,
  };

  renderAdvisorChat({
    pathname: "/advisor-chat",
    state: {
      mode: "goal-review",
      requestId: "advisor-chat-goal-review-failure-test",
      goal: goalReview,
    },
  });

  expect(await screen.findByText("Unable to review this goal.")).toBeInTheDocument();
  await waitFor(() => expect(mockedGetConversation).toHaveBeenCalledWith(2));
});

test("sends PDF-only messages with the default extraction prompt", async () => {
  const user = userEvent.setup();
  const { container } = renderAdvisorChat();
  const pdf = new File(["statement"], "statement.pdf", {
    type: "application/pdf",
  });

  await screen.findByText("What is budgeting?");
  const input = container.querySelector("input[type='file']") as HTMLInputElement;
  await user.upload(input, pdf);
  await user.click(screen.getByTitle("Send message"));

  await waitFor(() => expect(mockedSendAdvisorPdfMessage).toHaveBeenCalledWith(
    "Extract financial information from the uploaded PDF.",
    1,
    [pdf],
    expect.any(AbortSignal),
  ));
  await waitFor(() => expect(mockedGetConversation).toHaveBeenCalledTimes(2));
});

test("shows an error when conversations cannot load", async () => {
  mockedGetConversations.mockRejectedValueOnce(new Error("Unable to load conversations."));

  renderAdvisorChat();

  expect(await screen.findByText("Unable to load conversations.")).toBeInTheDocument();
});
