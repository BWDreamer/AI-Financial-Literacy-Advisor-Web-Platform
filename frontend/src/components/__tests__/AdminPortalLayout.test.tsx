import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import AdminPortalLayout from "../AdminPortalLayout";

const clearUser = jest.fn();

jest.mock("../../api/auth", () => ({
  avatarUrl: jest.fn(() => null),
}));

jest.mock("../../store/UserProvider", () => ({
  useUser: () => ({
    user: {
      id: 1,
      username: "Admin",
      email: "admin@example.com",
      avatar_url: null,
      role: "admin",
    },
    clearUser,
  }),
}));

function renderLayout() {
  render(
    <MemoryRouter initialEntries={["/admin/dashboard"]}>
      <Routes>
        <Route path="/admin" element={<AdminPortalLayout />}>
          <Route path="dashboard" element={<div>Dashboard content</div>} />
        </Route>
        <Route path="/login" element={<div>Login page</div>} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  clearUser.mockClear();
});

test("renders the admin sidebar navigation and signed-in admin profile", () => {
  renderLayout();

  expect(screen.getByText("FinAI Advisor")).toBeInTheDocument();
  expect(screen.getByText("Admin Console")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /dashboard/i })).toHaveAttribute("href", "/admin/dashboard");
  expect(screen.getByRole("link", { name: /user management/i })).toHaveAttribute("href", "/admin/users");
  expect(screen.getByRole("link", { name: /advisory settings/i })).toHaveAttribute("href", "/admin/settings");
  expect(screen.getByRole("link", { name: /knowledge hub/i })).toHaveAttribute("href", "/admin/knowledge");
  expect(screen.getByText("Admin")).toBeInTheDocument();
  expect(screen.getByText("admin@example.com")).toBeInTheDocument();
});

test("clears the user and returns to login when logging out", async () => {
  const user = userEvent.setup();
  renderLayout();

  await user.click(screen.getByRole("button", { name: /admin admin@example.com/i }));
  await user.click(screen.getByRole("button", { name: /log out/i }));

  expect(clearUser).toHaveBeenCalledTimes(1);
  await waitFor(() => expect(screen.getByText("Login page")).toBeInTheDocument());
});
