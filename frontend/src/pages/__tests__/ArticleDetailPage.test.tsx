import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ArticleDetailPage from "../ArticleDetailPage";
import {
  getArticle,
  incrementArticleViews,
  likeArticle,
  saveArticle,
  unlikeArticle,
  unsaveArticle,
  type ArticleDetail,
} from "../../api/articles";
import { ApiError } from "../../api/client";

jest.mock("../../api/client", () => ({
  API_ORIGIN: "http://localhost:8000",
  ApiError: class ApiError extends Error {
    constructor(message: string, public status: number) {
      super(message);
    }
  },
}));

jest.mock("../../api/articles", () => ({
  getArticle: jest.fn(),
  incrementArticleViews: jest.fn(),
  likeArticle: jest.fn(),
  unlikeArticle: jest.fn(),
  saveArticle: jest.fn(),
  unsaveArticle: jest.fn(),
}));

let currentUser = {
  id: 1,
  username: "User",
  email: "user@example.com",
  avatar_url: null,
  role: "user",
};

jest.mock("../../store/UserProvider", () => ({
  useUser: () => ({ user: currentUser }),
}));

jest.mock("../../components/knowledge/ArticleContentRenderer", () => ({
  __esModule: true,
  default: () => <div>Rendered article content</div>,
}));

const mockedGetArticle = jest.mocked(getArticle);
const mockedIncrementArticleViews = jest.mocked(incrementArticleViews);
const mockedLikeArticle = jest.mocked(likeArticle);
const mockedUnlikeArticle = jest.mocked(unlikeArticle);
const mockedSaveArticle = jest.mocked(saveArticle);
const mockedUnsaveArticle = jest.mocked(unsaveArticle);

const article: ArticleDetail = {
  id: "budgeting-basics",
  title: "Budgeting Basics",
  summary: "A practical guide to budget planning.",
  coverImageUrl: null,
  authorName: "FinanceAI Learning Team",
  sourceName: "Knowledge Base",
  category: "Budgeting",
  publishedAt: "2026-07-02T00:00:00Z",
  views: 100,
  likes: 10,
  saves: 5,
  likedByMe: false,
  savedByMe: false,
  contentBlocks: [{ type: "paragraph", text: "Article body." }],
};

function renderPage(path = "/knowledge-hub/budgeting-basics") {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/knowledge-hub" element={<div>Knowledge hub index</div>} />
        <Route path="/knowledge-hub/:articleId" element={<ArticleDetailPage />} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  currentUser = {
    id: 1,
    username: "User",
    email: "user@example.com",
    avatar_url: null,
    role: "user",
  };
  mockedGetArticle.mockResolvedValue(article);
  mockedIncrementArticleViews.mockResolvedValue({
    articleId: "budgeting-basics",
    views: 101,
  });
  mockedLikeArticle.mockResolvedValue({
    articleId: "budgeting-basics",
    liked: true,
    likes: 11,
  });
  mockedUnlikeArticle.mockResolvedValue({
    articleId: "budgeting-basics",
    liked: false,
    likes: 10,
  });
  mockedSaveArticle.mockResolvedValue({
    articleId: "budgeting-basics",
    saved: true,
    saves: 6,
  });
  mockedUnsaveArticle.mockResolvedValue({
    articleId: "budgeting-basics",
    saved: false,
    saves: 5,
  });
});

test("loads article details and increments views for a regular user", async () => {
  renderPage();

  expect(await screen.findByRole("heading", { name: "Budgeting Basics" })).toBeInTheDocument();
  expect(screen.getByText("Rendered article content")).toBeInTheDocument();
  await waitFor(() => expect(mockedIncrementArticleViews).toHaveBeenCalledWith("budgeting-basics"));
  expect(await screen.findByText(/Views 101/i)).toBeInTheDocument();
});

test("does not increment views for an admin reader", async () => {
  currentUser = {
    id: 2,
    username: "Admin",
    email: "admin@example.com",
    avatar_url: null,
    role: "admin",
  };

  renderPage();

  expect(await screen.findByRole("heading", { name: "Budgeting Basics" })).toBeInTheDocument();
  expect(mockedIncrementArticleViews).not.toHaveBeenCalled();
});

test("toggles like and save actions from the detail page", async () => {
  const user = userEvent.setup();
  renderPage();

  await screen.findByRole("heading", { name: "Budgeting Basics" });
  await user.click(screen.getByRole("button", { name: /likes 10/i }));
  await waitFor(() => expect(mockedLikeArticle).toHaveBeenCalledWith("budgeting-basics"));
  expect(screen.getByRole("button", { name: /likes 11/i })).toHaveAttribute("aria-pressed", "true");

  await user.click(screen.getByRole("button", { name: /saves 5/i }));
  await waitFor(() => expect(mockedSaveArticle).toHaveBeenCalledWith("budgeting-basics"));
  expect(screen.getByRole("button", { name: /saves 6/i })).toHaveAttribute("aria-pressed", "true");
});

test("uses unlike and unsave when the article is already liked and saved", async () => {
  const user = userEvent.setup();
  mockedGetArticle.mockResolvedValueOnce({
    ...article,
    likedByMe: true,
    savedByMe: true,
  });
  renderPage();

  await screen.findByRole("heading", { name: "Budgeting Basics" });
  await user.click(screen.getByRole("button", { name: /likes 10/i }));
  await waitFor(() => expect(mockedUnlikeArticle).toHaveBeenCalledWith("budgeting-basics"));

  await user.click(screen.getByRole("button", { name: /saves 5/i }));
  await waitFor(() => expect(mockedUnsaveArticle).toHaveBeenCalledWith("budgeting-basics"));
});

test("redirects to the knowledge hub when the article is not found", async () => {
  mockedGetArticle.mockRejectedValueOnce(new ApiError("Article not found.", 404));

  renderPage();

  expect(await screen.findByText("Knowledge hub index")).toBeInTheDocument();
});
