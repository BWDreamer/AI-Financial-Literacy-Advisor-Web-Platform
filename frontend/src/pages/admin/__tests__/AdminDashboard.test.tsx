import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AdminDashboard from "../AdminDashboard";
import { getAdminArticles, getAdminUsers } from "../../../api/admin";

jest.mock("../../../api/admin", () => ({
  getAdminUsers: jest.fn(),
  getAdminArticles: jest.fn(),
}));

const mockedGetAdminUsers = jest.mocked(getAdminUsers);
const mockedGetAdminArticles = jest.mocked(getAdminArticles);

const users = [
  {
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
  },
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

const articles = [
  {
    id: "budgeting-1",
    title: "Budgeting basics",
    summary: "Simple budget guide",
    coverImageUrl: null,
    authorName: "FinanceAI Learning Team",
    sourceName: "Knowledge Base",
    category: "Budgeting",
    publishedAt: "2026-07-02T00:00:00Z",
    views: 100,
    likes: 12,
    saves: 8,
    status: "published" as const,
    updatedAt: "2026-07-02T00:00:00Z",
  },
  {
    id: "saving-1",
    title: "Saving habits",
    summary: "Small savings add up",
    coverImageUrl: null,
    authorName: "FinanceAI Learning Team",
    sourceName: "Knowledge Base",
    category: "Saving",
    publishedAt: "2026-07-03T00:00:00Z",
    views: 250,
    likes: 30,
    saves: 15,
    status: "published" as const,
    updatedAt: "2026-07-03T00:00:00Z",
  },
];

beforeEach(() => {
  jest.clearAllMocks();
  mockedGetAdminUsers.mockResolvedValue(users);
  mockedGetAdminArticles.mockResolvedValue({
    items: articles,
    page: 1,
    pageSize: 50,
    total: articles.length,
  });
});

test("renders dashboard metrics and quick actions from admin API data", async () => {
  render(
    <MemoryRouter>
      <AdminDashboard />
    </MemoryRouter>
  );

  expect(await screen.findByRole("heading", { name: /dashboard/i })).toBeInTheDocument();
  expect(mockedGetAdminUsers).toHaveBeenCalledTimes(1);
  expect(mockedGetAdminArticles).toHaveBeenCalledWith({ status: "published" });

  expect(screen.getByText("Total Users")).toBeInTheDocument();
  expect(screen.getByText("Published Articles")).toBeInTheDocument();
  expect(screen.getByText("Platform Activity")).toBeInTheDocument();
  expect(screen.getByText("New Users by Month")).toBeInTheDocument();
  expect(screen.getByText("Content Engagement by Category")).toBeInTheDocument();
  expect(screen.getByText("Quick Actions")).toBeInTheDocument();
  expect(screen.getByText("Invite or manage users")).toBeInTheDocument();
  expect(screen.getByText("Create a new article")).toBeInTheDocument();
  expect(screen.getByText("Configure advisory topics")).toBeInTheDocument();
  expect((await screen.findAllByText("Saving habits")).length).toBeGreaterThan(0);
});
