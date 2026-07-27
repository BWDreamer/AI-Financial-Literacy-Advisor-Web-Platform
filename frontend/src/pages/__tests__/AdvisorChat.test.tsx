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
  sendAdvisorMessage,
  sendAdvisorPdfMessage,
} from "../../api/chat";

jest.mock("../../api/chat", () => ({
  addConversationMessage: jest.fn(),
  createConversation: jest.fn(),
  deleteConversation: jest.fn(),
  getConversation: jest.fn(),
  getConversations: jest.fn(),
  sendAdvisorMessage: jest.fn(),
  sendAdvisorPdfMessage: jest.fn(),
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
const mockedSendAdvisorMessage = jest.mocked(sendAdvisorMessage);
const mockedSendAdvisorPdfMessage = jest.mocked(sendAdvisorPdfMessage);
const mockedDeleteConversation = jest.mocked(deleteConversation);
const mockedAddConversationMessage = jest.mocked(addConversationMessage);

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
  mockedSendAdvisorMessage.mockResolvedValue({
    answer: "Educational response.",
    model: "test-model",
  });
  mockedSendAdvisorPdfMessage.mockResolvedValue({
    answer: "PDF response.",
    model: "test-model",
    imported_records: [],
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
  expect(screen.getByText(/Budgeting means planning your money/i)).toBeInTheDocument();
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

  await waitFor(() => expect(mockedSendAdvisorMessage).toHaveBeenCalledWith(
    "What is budgeting?",
    1,
  ));
  await waitFor(() => expect(mockedGetConversation).toHaveBeenCalledTimes(2));
});

test("creates a conversation before sending from an empty chat", async () => {
  mockedGetConversations.mockResolvedValueOnce([]);
  const user = userEvent.setup();
  renderAdvisorChat();

  await screen.findByText(/how can i help/i);
  await user.type(screen.getByPlaceholderText(/ask anything about personal finance/i), "Explain superannuation");
  await user.click(screen.getByTitle("Send message"));

  await waitFor(() => expect(mockedCreateConversation).toHaveBeenCalledTimes(1));
  await waitFor(() => expect(mockedSendAdvisorMessage).toHaveBeenCalledWith(
    "Explain superannuation",
    2,
  ));
});

test("shows an error and removes the thinking message when sending fails", async () => {
  mockedSendAdvisorMessage.mockRejectedValueOnce(new Error("Unable to send your message."));
  const user = userEvent.setup();
  renderAdvisorChat();

  await screen.findByText("What is budgeting?");
  await user.type(screen.getByPlaceholderText(/ask anything about personal finance/i), "Explain investing");
  await user.click(screen.getByTitle("Send message"));

  expect(await screen.findByText("Unable to send your message.")).toBeInTheDocument();
  await waitFor(() => expect(screen.queryByText("Thinking...")).not.toBeInTheDocument());
  expect(screen.getByText("Explain investing")).toBeInTheDocument();
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
  ));
  expect(mockedSendAdvisorMessage).not.toHaveBeenCalled();
  await waitFor(() => expect(mockedGetConversation).toHaveBeenCalledTimes(2));
});

test("deletes a conversation from the history sidebar", async () => {
  const user = userEvent.setup();
  renderAdvisorChat();

  await screen.findByText("What is budgeting?");
  await user.click(screen.getByLabelText(/toggle conversation history/i));
  await user.click(screen.getByText("Budget chat"));
  await user.click(screen.getByRole("button", { name: /delete budget chat/i }));

  await waitFor(() => expect(mockedDeleteConversation).toHaveBeenCalledWith(1));
  await waitFor(() => expect(mockedGetConversations).toHaveBeenCalledTimes(2));
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
  await waitFor(() => expect(mockedSendAdvisorMessage).toHaveBeenCalledWith(
    expect.stringContaining("Please review this existing financial goal"),
    2,
    undefined,
    7,
  ));
  await waitFor(() => expect(mockedGetConversation).toHaveBeenCalledWith(2));
});

test("shows an error when conversations cannot load", async () => {
  mockedGetConversations.mockRejectedValueOnce(new Error("Unable to load conversations."));

  renderAdvisorChat();

  expect(await screen.findByText("Unable to load conversations.")).toBeInTheDocument();
});
