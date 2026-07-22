import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import KnowledgeHub from "../KnowledgeHub";
import {
  getArticleCategories,
  getArticles,
  getFeaturedArticles,
  getLikedArticleIds,
  getRecommendedArticles,
  getSavedArticleIds,
  likeArticle,
  saveArticle,
  type Article,
} from "../../api/articles";

jest.mock("../../api/client", () => ({
  API_ORIGIN: "http://localhost:8000",
  ApiError: class ApiError extends Error {
    constructor(message: string, public status: number) {
      super(message);
    }
  },
}));

jest.mock("../../api/articles", () => ({
  getArticles: jest.fn(),
  getFeaturedArticles: jest.fn(),
  getRecommendedArticles: jest.fn(),
  getArticleCategories: jest.fn(),
  getLikedArticleIds: jest.fn(),
  getSavedArticleIds: jest.fn(),
  likeArticle: jest.fn(),
  unlikeArticle: jest.fn(),
  saveArticle: jest.fn(),
  unsaveArticle: jest.fn(),
}));

const mockedGetArticles = jest.mocked(getArticles);
const mockedGetFeaturedArticles = jest.mocked(getFeaturedArticles);
const mockedGetRecommendedArticles = jest.mocked(getRecommendedArticles);
const mockedGetArticleCategories = jest.mocked(getArticleCategories);
const mockedGetLikedArticleIds = jest.mocked(getLikedArticleIds);
const mockedGetSavedArticleIds = jest.mocked(getSavedArticleIds);
const mockedLikeArticle = jest.mocked(likeArticle);
const mockedSaveArticle = jest.mocked(saveArticle);

const articles: Article[] = [
  {
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
  },
  {
    id: "saving-habits",
    title: "Saving Habits",
    summary: "Small habits that improve savings.",
    coverImageUrl: null,
    authorName: "FinanceAI Learning Team",
    sourceName: "Knowledge Base",
    category: "Saving",
    publishedAt: "2026-07-04T00:00:00Z",
    views: 250,
    likes: 20,
    saves: 12,
  },
];

function renderPage() {
  render(
    <MemoryRouter>
      <KnowledgeHub />
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  mockedGetArticles.mockResolvedValue({
    items: articles,
    page: 1,
    pageSize: 50,
    total: articles.length,
  });
  mockedGetRecommendedArticles.mockResolvedValue([articles[1]]);
  mockedGetFeaturedArticles.mockResolvedValue([articles[0]]);
  mockedGetArticleCategories.mockResolvedValue(["Budgeting", "Saving"]);
  mockedGetLikedArticleIds.mockResolvedValue({ articleIds: ["budgeting-basics"] });
  mockedGetSavedArticleIds.mockResolvedValue({ articleIds: ["saving-habits"] });
  mockedLikeArticle.mockResolvedValue({
    articleId: "saving-habits",
    liked: true,
    likes: 21,
  });
  mockedSaveArticle.mockResolvedValue({
    articleId: "budgeting-basics",
    saved: true,
    saves: 6,
  });
});

test("loads recommended articles, categories and the article list", async () => {
  renderPage();

  expect(await screen.findByText("Budgeting Basics")).toBeInTheDocument();
  expect(screen.getAllByText("Saving Habits").length).toBeGreaterThan(0);
  expect(mockedGetRecommendedArticles).toHaveBeenCalledWith(5);
  expect(mockedGetArticleCategories).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("button", { name: "Budgeting" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Saving" })).toBeInTheDocument();
});

test("searches, filters and sorts articles through the article API", async () => {
  const user = userEvent.setup();
  renderPage();

  await screen.findByText("Budgeting Basics");
  await user.type(screen.getByPlaceholderText(/search articles/i), "tax");
  await waitFor(() => {
    expect(mockedGetArticles).toHaveBeenLastCalledWith(
      expect.objectContaining({ keyword: "tax" })
    );
  });

  await user.click(screen.getByRole("button", { name: "Saving" }));
  await waitFor(() => {
    expect(mockedGetArticles).toHaveBeenLastCalledWith(
      expect.objectContaining({ category: "Saving" })
    );
  });

  await user.click(screen.getByRole("button", { name: /sort by/i }));
  await user.click(screen.getByRole("button", { name: /most liked/i }));
  await waitFor(() => {
    expect(mockedGetArticles).toHaveBeenLastCalledWith(
      expect.objectContaining({ sortBy: "most_liked" })
    );
  });
});

test("shows liked and saved personal article tabs", async () => {
  const user = userEvent.setup();
  renderPage();

  await screen.findByText("Budgeting Basics");
  await user.click(screen.getByRole("button", { name: /^saved$/i }));

  let listCards = screen.getAllByRole("article");
  expect(listCards).toHaveLength(1);
  expect(within(listCards[0]).getByText("Saving Habits")).toBeInTheDocument();
  expect(within(listCards[0]).queryByText("Budgeting Basics")).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /^liked$/i }));
  listCards = screen.getAllByRole("article");
  expect(listCards).toHaveLength(1);
  expect(within(listCards[0]).getByText("Budgeting Basics")).toBeInTheDocument();
  expect(within(listCards[0]).queryByText("Saving Habits")).not.toBeInTheDocument();
});

test("updates like and save state from article card actions", async () => {
  const user = userEvent.setup();
  renderPage();

  await screen.findByText("Budgeting Basics");
  const cards = screen.getAllByRole("article");
  const budgetingCard = cards.find((card) => within(card).queryByText("Budgeting Basics"));
  const savingCard = cards.find((card) => within(card).queryByText("Saving Habits"));
  expect(budgetingCard).not.toBeNull();
  expect(savingCard).not.toBeNull();

  await user.click(within(savingCard as HTMLElement).getByRole("button", { name: "20" }));
  await waitFor(() => expect(mockedLikeArticle).toHaveBeenCalledWith("saving-habits"));
  expect(within(savingCard as HTMLElement).getByRole("button", { name: "21" })).toBeInTheDocument();

  await user.click(within(budgetingCard as HTMLElement).getByRole("button", { name: "5" }));
  await waitFor(() => expect(mockedSaveArticle).toHaveBeenCalledWith("budgeting-basics"));
  expect(within(budgetingCard as HTMLElement).getByRole("button", { name: "6" })).toBeInTheDocument();
});

test("shows an error when the article list cannot load", async () => {
  mockedGetArticles.mockRejectedValueOnce(new Error("Unable to load articles."));

  renderPage();

  expect(await screen.findByText("Unable to load articles.")).toBeInTheDocument();
  expect(screen.queryByText("Budgeting Basics")).not.toBeInTheDocument();
});
