import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import UserPortalLayout from "../UserPortalLayout";
import {
  archiveGoal,
  getGoalNotifications,
  readGoalNotification,
} from "../../api/goals";

const clearUser = jest.fn();
const refreshUser = jest.fn();
let userState: {
  user: {
    id: number;
    username: string;
    email: string;
    avatar_url: string | null;
    role: string;
    onboarding_completed: boolean;
  } | null;
  loading: boolean;
  error: string;
} = {
  user: {
    id: 1,
    username: "Regular User",
    email: "user@example.com",
    avatar_url: null,
    role: "user",
    onboarding_completed: true,
  },
  loading: false,
  error: "",
};

jest.mock("../../api/auth", () => ({
  avatarUrl: jest.fn(() => null),
}));

jest.mock("../../api/goals", () => ({
  archiveGoal: jest.fn(),
  getGoalNotifications: jest.fn(() => Promise.resolve([])),
  readGoalNotification: jest.fn(),
}));

jest.mock("../../store/UserProvider", () => ({
  useUser: () => ({
    ...userState,
    refreshUser,
    clearUser,
  }),
}));

jest.mock("../OnboardingOverlay", () => ({
  __esModule: true,
  default: () => <div>Onboarding overlay</div>,
}));

jest.mock("../ProfileSettingsModal", () => ({
  __esModule: true,
  default: ({ onClose }: { onClose: () => void }) => (
    <div role="dialog" aria-label="Profile Settings">
      <button type="button" onClick={onClose}>Close profile settings</button>
    </div>
  ),
}));

function renderLayout(initialPath = "/home") {
  render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/" element={<UserPortalLayout />}>
          <Route path="home" element={<div>Home content</div>} />
        </Route>
        <Route path="/login" element={<div>Login page</div>} />
      </Routes>
    </MemoryRouter>
  );
}

const mockedGetGoalNotifications = jest.mocked(getGoalNotifications);
const mockedArchiveGoal = jest.mocked(archiveGoal);
const mockedReadGoalNotification = jest.mocked(readGoalNotification);

beforeEach(() => {
  jest.clearAllMocks();
  mockedGetGoalNotifications.mockResolvedValue([]);
  mockedArchiveGoal.mockResolvedValue(undefined);
  mockedReadGoalNotification.mockResolvedValue(undefined);
  userState = {
    user: {
      id: 1,
      username: "Regular User",
      email: "user@example.com",
      avatar_url: null,
      role: "user",
      onboarding_completed: true,
    },
    loading: false,
    error: "",
  };
});

test("renders user navigation and signed-in profile", async () => {
  renderLayout();

  await waitFor(() => expect(mockedGetGoalNotifications).toHaveBeenCalledTimes(1));
  expect(screen.getByText("FinanceAI")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /home page/i })).toHaveAttribute("href", "/home");
  expect(screen.getByRole("link", { name: /advisor chat/i })).toHaveAttribute("href", "/advisor-chat");
  expect(screen.getByRole("link", { name: /my goals/i })).toHaveAttribute("href", "/goals");
  expect(screen.getByRole("link", { name: /knowledge hub/i })).toHaveAttribute("href", "/knowledge-hub");
  expect(screen.getByText("Regular User")).toBeInTheDocument();
  expect(screen.getByText("user@example.com")).toBeInTheDocument();
});

test("clears the user and returns to login when logging out", async () => {
  const user = userEvent.setup();
  renderLayout();

  await waitFor(() => expect(mockedGetGoalNotifications).toHaveBeenCalledTimes(1));
  await user.click(screen.getByRole("button", { name: /regular user user@example.com/i }));
  await user.click(screen.getByRole("button", { name: /log out/i }));

  expect(clearUser).toHaveBeenCalledTimes(1);
  await waitFor(() => expect(screen.getByText("Login page")).toBeInTheDocument());
});

test("redirects to login when no user is available", async () => {
  userState = { user: null, loading: false, error: "" };

  renderLayout();

  expect(await screen.findByText("Login page")).toBeInTheDocument();
});

test("shows onboarding for incomplete regular users", async () => {
  userState.user = {
    ...userState.user!,
    onboarding_completed: false,
  };

  renderLayout();

  await waitFor(() => expect(mockedGetGoalNotifications).toHaveBeenCalledTimes(1));
  expect(screen.getByText("Onboarding overlay")).toBeInTheDocument();
});

test("shows goal notifications and confirms a completed goal", async () => {
  mockedGetGoalNotifications
    .mockResolvedValueOnce([
      {
        id: 11,
        goal_id: 7,
        title: "Emergency Fund completed",
        message: "You reached your emergency fund target.",
        notification_type: "goal_completed",
        read: false,
        created_at: "2026-07-22T00:00:00Z",
      },
    ])
    .mockResolvedValueOnce([]);
  const user = userEvent.setup();

  renderLayout();

  await user.click(await screen.findByRole("button", { name: /goal notifications/i }));

  expect(screen.getByText("Emergency Fund completed")).toBeInTheDocument();
  expect(screen.getByText("You reached your emergency fund target.")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /confirm completed/i }));

  await waitFor(() => expect(mockedArchiveGoal).toHaveBeenCalledWith(7));
  expect(mockedReadGoalNotification).toHaveBeenCalledWith(11);
  await waitFor(() => expect(mockedGetGoalNotifications).toHaveBeenCalledTimes(2));
});
