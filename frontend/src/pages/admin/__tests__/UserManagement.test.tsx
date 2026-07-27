import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import UserManagement from "../UserManagement";
import { deleteAdminUser, getAdminUsers, inviteAdminUser, updateAdminUser } from "../../../api/admin";

jest.mock("../../../api/admin", () => ({
  getAdminUsers: jest.fn(),
  inviteAdminUser: jest.fn(),
  updateAdminUser: jest.fn(),
  deleteAdminUser: jest.fn(),
}));

jest.mock("../../../api/auth", () => ({
  avatarUrl: jest.fn(() => null),
}));

jest.mock("../../../store/UserProvider", () => ({
  useUser: () => ({
    user: {
      id: 1,
      email: "admin@example.com",
      role: "admin",
    },
  }),
}));

const mockedGetAdminUsers = jest.mocked(getAdminUsers);
const mockedInviteAdminUser = jest.mocked(inviteAdminUser);
const mockedUpdateAdminUser = jest.mocked(updateAdminUser);
const mockedDeleteAdminUser = jest.mocked(deleteAdminUser);

const adminUser = {
  id: 1,
  user_id: "USR-0001",
  first_name: "Admin",
  last_name: null,
  email: "admin@example.com",
  avatar_url: null,
  role: "admin",
  region: null,
  created_at: "2026-07-01T00:00:00Z",
  is_online: true,
  last_seen_at: "2026-07-18T00:00:00Z",
  goals_count: 0,
  liked_articles_count: 0,
  saved_articles_count: 0,
};

const regularUsers = [
  {
    id: 2,
    user_id: "USR-0002",
    first_name: "Mike",
    last_name: "Green",
    email: "mike@example.com",
    avatar_url: null,
    role: "user",
    region: "Australia",
    created_at: "2026-07-16T00:00:00Z",
    is_online: true,
    last_seen_at: "2026-07-18T00:00:00Z",
    goals_count: 1,
    liked_articles_count: 2,
    saved_articles_count: 3,
  },
  {
    id: 3,
    user_id: "USR-0003",
    first_name: "Jane",
    last_name: "Smith",
    email: "jane@example.com",
    avatar_url: null,
    role: "user",
    region: null,
    created_at: "2026-06-12T00:00:00Z",
    is_online: false,
    last_seen_at: null,
    goals_count: 0,
    liked_articles_count: 0,
    saved_articles_count: 0,
  },
];

beforeEach(() => {
  jest.clearAllMocks();
  mockedGetAdminUsers.mockResolvedValue([adminUser, ...regularUsers]);
  mockedInviteAdminUser.mockResolvedValue({
    ...regularUsers[0],
    id: 4,
    user_id: "USR-0004",
    first_name: "Test",
    last_name: "User",
    email: "test@example.com",
    created_at: "2026-07-18T00:00:00Z",
    is_online: false,
    role: "user",
    avatar_url: null,
    region: null,
    last_seen_at: null,
    goals_count: 0,
    liked_articles_count: 0,
    saved_articles_count: 0,
  });
  mockedUpdateAdminUser.mockResolvedValue({
    ...regularUsers[0],
    first_name: "Michael",
    email: "michael@example.com",
  });
  mockedDeleteAdminUser.mockResolvedValue(undefined);
});

test("loads normal users and keeps the current admin out of the user table", async () => {
  render(<UserManagement />);

  expect(await screen.findByText("mike@example.com")).toBeInTheDocument();
  expect(screen.getByText("jane@example.com")).toBeInTheDocument();
  expect(screen.queryByText("admin@example.com")).not.toBeInTheDocument();
});

test("filters users by email search", async () => {
  const user = userEvent.setup();
  render(<UserManagement />);

  await screen.findByText("mike@example.com");
  await user.type(screen.getByLabelText(/search users by email/i), "jane");

  expect(screen.queryByText("mike@example.com")).not.toBeInTheDocument();
  expect(screen.getByText("jane@example.com")).toBeInTheDocument();
});

test("opens invite user form with default password and submits a new user", async () => {
  const user = userEvent.setup();
  render(<UserManagement />);

  await screen.findByText("mike@example.com");
  await user.click(screen.getByRole("button", { name: /invite user/i }));

  const dialog = screen.getByRole("dialog", { name: /invite user/i });
  expect(dialog).toBeInTheDocument();
  expect(screen.getByLabelText(/^password$/i)).toHaveValue("11111111");

  await user.type(screen.getByLabelText(/first name/i), "Test");
  await user.type(screen.getByLabelText(/last name/i), "User");
  await user.type(screen.getByLabelText(/email address/i), "test@example.com");
  await user.click(screen.getByRole("button", { name: /add user/i }));

  await waitFor(() => {
    expect(mockedInviteAdminUser).toHaveBeenCalledWith({
      first_name: "Test",
      last_name: "User",
      email: "test@example.com",
      password: "11111111",
    });
  });
  expect(await screen.findByRole("status")).toHaveTextContent("User test@example.com was invited successfully.");
});

test("edits a normal user's basic profile fields", async () => {
  const user = userEvent.setup();
  render(<UserManagement />);

  await screen.findByText("mike@example.com");
  await user.click(screen.getAllByRole("button", { name: /edit/i })[0]);

  const dialog = screen.getByRole("dialog", { name: /edit user/i });
  expect(dialog).toHaveTextContent("USR-0002");
  expect(dialog).toHaveTextContent("Role");
  expect(dialog).toHaveTextContent("User");
  expect(dialog).toHaveTextContent("Last Active");

  const firstNameInput = screen.getByLabelText(/first name/i);
  const emailInput = screen.getByLabelText(/email address/i);
  await user.clear(firstNameInput);
  await user.type(firstNameInput, "Michael");
  await user.clear(emailInput);
  await user.type(emailInput, "michael@example.com");
  await user.click(screen.getByRole("button", { name: /save changes/i }));

  await waitFor(() => {
    expect(mockedUpdateAdminUser).toHaveBeenCalledWith(2, {
      first_name: "Michael",
      last_name: "Green",
      email: "michael@example.com",
    });
  });
});

test("opens user details from the edit dialog", async () => {
  const user = userEvent.setup();
  render(<UserManagement />);

  await screen.findByText("mike@example.com");
  await user.click(screen.getAllByRole("button", { name: /edit/i })[0]);
  await user.click(screen.getByRole("button", { name: /view details/i }));

  expect(screen.getByRole("heading", { name: /user details/i })).toBeInTheDocument();
  expect(screen.getAllByText("Mike Green").length).toBeGreaterThan(0);
  expect(screen.getByText("Australia")).toBeInTheDocument();
  expect(screen.getByText("Goals")).toBeInTheDocument();
  expect(screen.getByText("Liked Articles")).toBeInTheDocument();
  expect(screen.getByText("Saved Articles")).toBeInTheDocument();
});

test("deletes a normal user after confirmation", async () => {
  const user = userEvent.setup();
  render(<UserManagement />);

  await screen.findByText("jane@example.com");
  await user.click(screen.getAllByRole("button", { name: /delete/i })[1]);

  const dialog = screen.getByRole("dialog", { name: /delete user/i });
  expect(dialog).toHaveTextContent("Jane Smith");
  await user.click(screen.getByRole("button", { name: /delete user/i }));

  await waitFor(() => {
    expect(mockedDeleteAdminUser).toHaveBeenCalledWith(3);
  });
  await waitFor(() => expect(screen.queryByText("jane@example.com")).not.toBeInTheDocument());
});

test("shows a loading error and retries the user list request", async () => {
  mockedGetAdminUsers
    .mockRejectedValueOnce(new Error("Unable to load users."))
    .mockResolvedValueOnce([adminUser, ...regularUsers]);
  const user = userEvent.setup();
  render(<UserManagement />);

  expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load users.");
  expect(screen.queryByText("mike@example.com")).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /try again/i }));

  expect(await screen.findByText("mike@example.com")).toBeInTheDocument();
  expect(mockedGetAdminUsers).toHaveBeenCalledTimes(2);
});

test("keeps the invite dialog open and reports an error when inviting fails", async () => {
  mockedInviteAdminUser.mockRejectedValueOnce(new Error("Email already exists."));
  const user = userEvent.setup();
  render(<UserManagement />);

  await screen.findByText("mike@example.com");
  await user.click(screen.getByRole("button", { name: /invite user/i }));
  await user.type(screen.getByLabelText(/first name/i), "Test");
  await user.type(screen.getByLabelText(/last name/i), "User");
  await user.type(screen.getByLabelText(/email address/i), "test@example.com");
  await user.click(screen.getByRole("button", { name: /add user/i }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Email already exists.");
  expect(screen.getByRole("dialog", { name: /invite user/i })).toBeInTheDocument();
});

test("keeps the edit dialog open and reports an error when updating fails", async () => {
  mockedUpdateAdminUser.mockRejectedValueOnce(new Error("Update failed."));
  const user = userEvent.setup();
  render(<UserManagement />);

  await screen.findByText("mike@example.com");
  await user.click(screen.getAllByRole("button", { name: /edit/i })[0]);
  await user.click(screen.getByRole("button", { name: /save changes/i }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Update failed.");
  expect(screen.getByRole("dialog", { name: /edit user/i })).toBeInTheDocument();
});

test("keeps the delete dialog open and reports an error when deletion fails", async () => {
  mockedDeleteAdminUser.mockRejectedValueOnce(new Error("Delete failed."));
  const user = userEvent.setup();
  render(<UserManagement />);

  await screen.findByText("jane@example.com");
  await user.click(screen.getAllByRole("button", { name: /delete/i })[1]);
  await user.click(screen.getByRole("button", { name: /delete user/i }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Delete failed.");
  expect(screen.getByRole("dialog", { name: /delete user/i })).toBeInTheDocument();
});

test("closes the delete dialog without deleting when cancelled", async () => {
  const user = userEvent.setup();
  render(<UserManagement />);

  await screen.findByText("jane@example.com");
  await user.click(screen.getAllByRole("button", { name: /delete/i })[1]);

  expect(screen.getByRole("dialog", { name: /delete user/i })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /^cancel$/i }));

  await waitFor(() => expect(screen.queryByRole("dialog", { name: /delete user/i })).not.toBeInTheDocument());
  expect(mockedDeleteAdminUser).not.toHaveBeenCalled();
});
