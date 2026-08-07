import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import ArticleList from "../ArticleList";
import type { Article } from "../../../api/articles";

jest.mock("../../../api/client", () => ({
  API_ORIGIN: "http://localhost:8000",
}));

const article: Article = {
  id: "budgeting-basics",
  title: "Budgeting Basics",
  summary: "A short guide to planning spending.",
  coverImageUrl: "/uploads/budget.png",
  authorName: "FinanceAI",
  sourceName: "Knowledge Base",
  publishedAt: "2026-07-02T00:00:00Z",
  category: "Budgeting",
  views: 1200,
  likes: 25,
  saves: 10,
};

function renderList(props: Partial<Parameters<typeof ArticleList>[0]> = {}) {
  const onToggleLike = jest.fn();
  const onToggleSave = jest.fn();
  render(
    <MemoryRouter>
      <ArticleList
        articles={[article]}
        likedArticleIds={new Set()}
        savedArticleIds={new Set()}
        onToggleLike={onToggleLike}
        onToggleSave={onToggleSave}
        {...props}
      />
    </MemoryRouter>,
  );
  return { onToggleLike, onToggleSave };
}

test("renders a custom empty article list message", () => {
  renderList({
    articles: [],
    emptyTitle: "No saved articles yet",
    emptyDescription: "Save an article to read it later.",
  });

  expect(screen.getByText("No saved articles yet")).toBeInTheDocument();
  expect(screen.getByText("Save an article to read it later.")).toBeInTheDocument();
});

test("renders article cards and forwards like and save actions", async () => {
  const user = userEvent.setup();
  const { onToggleLike, onToggleSave } = renderList({
    likedArticleIds: new Set([article.id]),
    savedArticleIds: new Set([article.id]),
  });

  expect(screen.getByRole("link", { name: "Budgeting Basics" })).toHaveAttribute(
    "href",
    "/knowledge-hub/budgeting-basics",
  );
  expect(screen.getByRole("img", { name: "Budgeting Basics" })).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "25" }));
  await user.click(screen.getByRole("button", { name: "10" }));

  expect(onToggleLike).toHaveBeenCalledWith(article);
  expect(onToggleSave).toHaveBeenCalledWith(article);
});
