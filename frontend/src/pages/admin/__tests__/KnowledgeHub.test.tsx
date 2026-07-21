import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AdminKnowledgeHub from "../KnowledgeHub";
import {
  createAdminArticle,
  deleteAdminArticle,
  getPublishedAdminArticle,
  getPublishedAdminArticles,
  updateAdminArticle,
  uploadAdminArticleImage,
} from "../../../api/admin";
import type { Article, ArticleDetail } from "../../../api/articles";

let mockTipTapEditor: ReturnType<typeof createEditorMock>;

jest.mock("@tiptap/extension-image", () => ({ __esModule: true, default: { configure: jest.fn(() => ({})) } }));
jest.mock("@tiptap/extension-text-align", () => ({ __esModule: true, default: { configure: jest.fn(() => ({})) } }));
jest.mock("@tiptap/extension-underline", () => ({ __esModule: true, default: {} }));
jest.mock("@tiptap/starter-kit", () => ({ __esModule: true, default: {} }));
jest.mock("@tiptap/react", () => ({
  EditorContent: () => <div data-testid="editor-content" />,
  useEditor: jest.fn(() => mockTipTapEditor),
}));

jest.mock("../../../api/client", () => ({
  API_ORIGIN: "http://localhost:8000",
}));

jest.mock("../../../api/admin", () => ({
  getPublishedAdminArticles: jest.fn(),
  getPublishedAdminArticle: jest.fn(),
  createAdminArticle: jest.fn(),
  updateAdminArticle: jest.fn(),
  deleteAdminArticle: jest.fn(),
  uploadAdminArticleImage: jest.fn(),
}));

const mockedGetPublishedAdminArticles = jest.mocked(getPublishedAdminArticles);
const mockedGetPublishedAdminArticle = jest.mocked(getPublishedAdminArticle);
const mockedCreateAdminArticle = jest.mocked(createAdminArticle);
const mockedUpdateAdminArticle = jest.mocked(updateAdminArticle);
const mockedDeleteAdminArticle = jest.mocked(deleteAdminArticle);
const mockedUploadAdminArticleImage = jest.mocked(uploadAdminArticleImage);

function createEditorMock(
  doc = {
    type: "doc",
    content: [
      {
        type: "paragraph",
        content: [{ type: "text", text: "This is the article body." }],
      },
    ],
  },
) {
  const chainObject = {
    focus: jest.fn(),
    toggleBulletList: jest.fn(),
    toggleHeading: jest.fn(),
    updateAttributes: jest.fn(),
    toggleBold: jest.fn(),
    toggleItalic: jest.fn(),
    toggleUnderline: jest.fn(),
    setTextAlign: jest.fn(),
    setImage: jest.fn(),
    run: jest.fn(() => true),
  };

  Object.values(chainObject).forEach((method) => {
    if (method !== chainObject.run) {
      method.mockReturnValue(chainObject);
    }
  });

  return {
    chain: jest.fn(() => chainObject),
    getAttributes: jest.fn(() => ({})),
    getJSON: jest.fn(() => doc),
    isActive: jest.fn(() => false),
    chainObject,
  };
}

const articles: Article[] = [
  {
    id: "budgeting-article",
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
    id: "saving-article",
    title: "Saving Habits",
    summary: "Small habits that improve savings.",
    coverImageUrl: "/uploads/saving.png",
    authorName: "FinanceAI Learning Team",
    sourceName: "Knowledge Base",
    category: "Saving",
    publishedAt: "2026-07-04T00:00:00Z",
    views: 250,
    likes: 20,
    saves: 12,
  },
  {
    id: "tax-article",
    title: "Tax Time Checklist",
    summary: "Documents to prepare before tax time.",
    coverImageUrl: null,
    authorName: "FinanceAI Learning Team",
    sourceName: "Knowledge Base",
    category: "Tax",
    publishedAt: "2026-07-03T00:00:00Z",
    views: 50,
    likes: 30,
    saves: 2,
  },
];

const articleDetail = (article: Article): ArticleDetail => ({
  ...article,
  contentBlocks: {
    type: "doc",
    content: [
      {
        type: "paragraph",
        content: [{ type: "text", text: `${article.title} full article body.` }],
      },
    ],
  },
  likedByMe: false,
  savedByMe: false,
});

beforeEach(() => {
  jest.clearAllMocks();
  mockTipTapEditor = createEditorMock();
  mockedGetPublishedAdminArticles.mockResolvedValue({
    items: articles,
    page: 1,
    pageSize: 50,
    total: articles.length,
  });
  mockedGetPublishedAdminArticle.mockImplementation(async (id) => articleDetail(articles.find((article) => article.id === id) ?? articles[0]));
  mockedCreateAdminArticle.mockResolvedValue(articleDetail(articles[0]));
  mockedUpdateAdminArticle.mockResolvedValue(articleDetail(articles[1]));
  mockedDeleteAdminArticle.mockResolvedValue(undefined);
  mockedUploadAdminArticleImage.mockResolvedValue({ imageUrl: "/uploads/test-image.png" });
});

test("loads and displays published articles from the admin article API", async () => {
  render(<AdminKnowledgeHub />);

  expect(await screen.findByRole("heading", { name: /knowledge hub/i })).toBeInTheDocument();
  expect(await screen.findByText("Saving Habits")).toBeInTheDocument();
  expect(mockedGetPublishedAdminArticles).toHaveBeenCalledTimes(1);
  expect(screen.getByText("3 published")).toBeInTheDocument();
  expect(screen.getByText("Budgeting Basics")).toBeInTheDocument();
  expect(screen.getByText("Tax Time Checklist")).toBeInTheDocument();
});

test("filters articles by title search and category", async () => {
  const user = userEvent.setup();
  render(<AdminKnowledgeHub />);

  await screen.findByText("Budgeting Basics");
  await user.type(screen.getByLabelText(/search articles by title/i), "saving");

  expect(screen.queryByText("Budgeting Basics")).not.toBeInTheDocument();
  expect(screen.getByText("Saving Habits")).toBeInTheDocument();

  await user.clear(screen.getByLabelText(/search articles by title/i));
  await user.click(screen.getByRole("button", { name: /^tax$/i }));

  expect(screen.getByText("Tax Time Checklist")).toBeInTheDocument();
  expect(screen.queryByText("Saving Habits")).not.toBeInTheDocument();
});

test("sorts article rows by engagement fields", async () => {
  const user = userEvent.setup();
  render(<AdminKnowledgeHub />);

  await screen.findByText("Budgeting Basics");
  await user.selectOptions(screen.getByLabelText(/sort articles/i), "views-desc");

  const rows = screen.getAllByRole("article");
  expect(within(rows[0]).getByText("Saving Habits")).toBeInTheDocument();

  await user.selectOptions(screen.getByLabelText(/sort articles/i), "likes-desc");
  expect(within(screen.getAllByRole("article")[0]).getByText("Tax Time Checklist")).toBeInTheDocument();
});

test("deletes an article after confirmation", async () => {
  const user = userEvent.setup();
  render(<AdminKnowledgeHub />);

  await screen.findByText("Budgeting Basics");
  await user.click(screen.getAllByRole("button", { name: /delete/i })[0]);

  const dialog = screen.getByRole("dialog", { name: /delete article/i });
  expect(dialog).toHaveTextContent("Saving Habits");
  await user.click(within(dialog).getByRole("button", { name: /delete article/i }));

  await waitFor(() => expect(mockedDeleteAdminArticle).toHaveBeenCalledWith("saving-article"));
  await waitFor(() => expect(screen.queryByText("Saving Habits")).not.toBeInTheDocument());
});

test("shows validation when publishing an incomplete article", async () => {
  mockTipTapEditor = createEditorMock({ type: "doc", content: [{ type: "paragraph" }] });
  const user = userEvent.setup();
  render(<AdminKnowledgeHub />);

  await screen.findByText("Budgeting Basics");
  await user.click(screen.getByRole("button", { name: /new article/i }));
  await user.click(screen.getByRole("button", { name: /publish article/i }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Please complete the title, excerpt and article body before saving.");
  expect(mockedCreateAdminArticle).not.toHaveBeenCalled();
});

test("publishes a new article with form values and editor content", async () => {
  const editorDoc = {
    type: "doc",
    content: [
      {
        type: "paragraph",
        content: [{ type: "text", text: "Tax planning article body." }],
      },
    ],
  };
  mockTipTapEditor = createEditorMock(editorDoc);
  const user = userEvent.setup();
  render(<AdminKnowledgeHub />);

  await screen.findByText("Budgeting Basics");
  await user.click(screen.getByRole("button", { name: /new article/i }));
  await user.type(screen.getByLabelText(/^title$/i), "Tax Planning Tips");
  await user.type(screen.getByLabelText(/excerpt/i), "A short tax summary.");
  await user.selectOptions(screen.getByLabelText(/^category$/i), "Tax");
  await user.click(screen.getByRole("button", { name: /publish article/i }));

  await waitFor(() => expect(mockedCreateAdminArticle).toHaveBeenCalledTimes(1));
  expect(mockedCreateAdminArticle).toHaveBeenCalledWith(expect.objectContaining({
    id: expect.stringMatching(/^tax-planning-tips-/),
    title: "Tax Planning Tips",
    summary: "A short tax summary.",
    category: "Tax",
    sourceName: "Knowledge Base",
    authorName: "FinanceAI Learning Team",
    status: "published",
    publishedAt: expect.any(String),
    contentBlocks: editorDoc,
  }));
});

test("loads article details and saves edited article changes", async () => {
  const user = userEvent.setup();
  render(<AdminKnowledgeHub />);

  await screen.findByText("Saving Habits");
  await user.click(screen.getAllByRole("button", { name: /edit/i })[0]);

  expect(await screen.findByRole("button", { name: /save changes/i })).toBeInTheDocument();
  expect(mockedGetPublishedAdminArticle).toHaveBeenCalledWith("saving-article");

  const titleInput = screen.getByLabelText(/^title$/i);
  await user.clear(titleInput);
  await user.type(titleInput, "Updated Saving Habits");
  await user.click(screen.getByRole("button", { name: /save changes/i }));

  await waitFor(() => expect(mockedUpdateAdminArticle).toHaveBeenCalledWith(
    "saving-article",
    expect.objectContaining({
      title: "Updated Saving Habits",
      summary: "Small habits that improve savings.",
      category: "Saving",
    }),
  ));
});

test("uploads cover images and inline article images", async () => {
  const user = userEvent.setup();
  render(<AdminKnowledgeHub />);

  await screen.findByText("Budgeting Basics");
  await user.click(screen.getByRole("button", { name: /new article/i }));

  const [inlineInput, coverInput] = Array.from(document.querySelectorAll<HTMLInputElement>('input[type="file"]'));
  const cover = new File(["cover"], "cover.png", { type: "image/png" });
  const inline = new File(["inline"], "inline.png", { type: "image/png" });

  await user.upload(coverInput, cover);
  expect(mockedUploadAdminArticleImage).toHaveBeenCalledWith(cover);
  expect(await screen.findByAltText("Cover preview")).toHaveAttribute("src", "http://localhost:8000/uploads/test-image.png");

  await user.upload(inlineInput, inline);
  await waitFor(() => expect(mockedUploadAdminArticleImage).toHaveBeenCalledWith(inline));
  expect(mockTipTapEditor.chainObject.setImage).toHaveBeenCalledWith({
    src: "http://localhost:8000/uploads/test-image.png",
    alt: "Article image",
  });
});

test("shows an error if article details cannot be loaded for editing", async () => {
  mockedGetPublishedAdminArticle.mockRejectedValueOnce(new Error("Unable to load article details."));
  const user = userEvent.setup();
  render(<AdminKnowledgeHub />);

  await screen.findByText("Saving Habits");
  await user.click(screen.getAllByRole("button", { name: /edit/i })[0]);

  expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load article details.");
  expect(screen.queryByRole("button", { name: /save changes/i })).not.toBeInTheDocument();
});

test("keeps the delete dialog open and reports an error when deletion fails", async () => {
  mockedDeleteAdminArticle.mockRejectedValueOnce(new Error("Delete failed."));
  const user = userEvent.setup();
  render(<AdminKnowledgeHub />);

  await screen.findByText("Saving Habits");
  await user.click(screen.getAllByRole("button", { name: /delete/i })[0]);
  await user.click(within(screen.getByRole("dialog", { name: /delete article/i })).getByRole("button", { name: /delete article/i }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Delete failed.");
  expect(screen.getByRole("dialog", { name: /delete article/i })).toBeInTheDocument();
});

test("shows a list loading error and retries successfully", async () => {
  mockedGetPublishedAdminArticles.mockRejectedValueOnce(new Error("Unable to load articles."));
  const user = userEvent.setup();
  render(<AdminKnowledgeHub />);

  expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load articles.");
  expect(screen.queryByText("Saving Habits")).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /try again/i }));

  expect(await screen.findByText("Saving Habits")).toBeInTheDocument();
  expect(mockedGetPublishedAdminArticles).toHaveBeenCalledTimes(2);
});

test("shows the empty state when search filters out every article", async () => {
  const user = userEvent.setup();
  render(<AdminKnowledgeHub />);

  await screen.findByText("Budgeting Basics");
  await user.type(screen.getByLabelText(/search articles by title/i), "does not exist");

  expect(screen.getByText("No published articles match the current filters.")).toBeInTheDocument();
  expect(screen.queryByText("Budgeting Basics")).not.toBeInTheDocument();
});

test("shows the empty state when the article API returns no items", async () => {
  mockedGetPublishedAdminArticles.mockResolvedValueOnce({
    items: [],
    page: 1,
    pageSize: 50,
    total: 0,
  });

  render(<AdminKnowledgeHub />);

  expect(screen.getByText("0 published")).toBeInTheDocument();
  expect(await screen.findByText("No published articles match the current filters.")).toBeInTheDocument();
});

test("closes the delete dialog without deleting when cancelled", async () => {
  const user = userEvent.setup();
  render(<AdminKnowledgeHub />);

  await screen.findByText("Saving Habits");
  await user.click(screen.getAllByRole("button", { name: /delete/i })[0]);

  expect(screen.getByRole("dialog", { name: /delete article/i })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /^cancel$/i }));

  await waitFor(() => expect(screen.queryByRole("dialog", { name: /delete article/i })).not.toBeInTheDocument());
  expect(mockedDeleteAdminArticle).not.toHaveBeenCalled();
});

test("returns from the new article editor without creating an article", async () => {
  const user = userEvent.setup();
  render(<AdminKnowledgeHub />);

  await screen.findByText("Budgeting Basics");
  await user.click(screen.getByRole("button", { name: /new article/i }));
  expect(screen.getByRole("button", { name: /publish article/i })).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /back to knowledge hub/i }));

  expect(await screen.findByRole("button", { name: /new article/i })).toBeInTheDocument();
  expect(mockedCreateAdminArticle).not.toHaveBeenCalled();
});

test("removes an existing cover image from the editor", async () => {
  const user = userEvent.setup();
  render(<AdminKnowledgeHub />);

  await screen.findByText("Saving Habits");
  await user.click(screen.getAllByRole("button", { name: /edit/i })[0]);

  expect(await screen.findByAltText("Cover preview")).toHaveAttribute("src", "http://localhost:8000/uploads/saving.png");
  await user.click(screen.getByRole("button", { name: /remove cover/i }));

  expect(screen.queryByAltText("Cover preview")).not.toBeInTheDocument();
  expect(screen.getByText("Click to upload cover image")).toBeInTheDocument();
});

test("runs rich text toolbar commands", async () => {
  const user = userEvent.setup();
  render(<AdminKnowledgeHub />);

  await screen.findByText("Budgeting Basics");
  await user.click(screen.getByRole("button", { name: /new article/i }));

  await user.click(screen.getByRole("button", { name: /^h1$/i }));
  expect(mockTipTapEditor.chainObject.toggleHeading).toHaveBeenCalledWith({ level: 1 });

  await user.click(screen.getByRole("button", { name: /bold/i }));
  expect(mockTipTapEditor.chainObject.toggleBold).toHaveBeenCalled();

  await user.click(screen.getByRole("button", { name: /align center/i }));
  expect(mockTipTapEditor.chainObject.setTextAlign).toHaveBeenCalledWith("center");

  await user.selectOptions(screen.getByLabelText(/font size/i), "1.35rem");
  expect(mockTipTapEditor.chainObject.updateAttributes).toHaveBeenCalledWith("paragraph", { fontSize: "1.35rem" });

  await user.selectOptions(screen.getByLabelText(/line spacing/i), "2");
  expect(mockTipTapEditor.chainObject.updateAttributes).toHaveBeenCalledWith("paragraph", { lineHeight: "2" });
});

test("shows an upload error when cover upload fails", async () => {
  mockedUploadAdminArticleImage.mockRejectedValueOnce(new Error("Upload failed."));
  const user = userEvent.setup();
  render(<AdminKnowledgeHub />);

  await screen.findByText("Budgeting Basics");
  await user.click(screen.getByRole("button", { name: /new article/i }));

  const [, coverInput] = Array.from(document.querySelectorAll<HTMLInputElement>('input[type="file"]'));
  await user.upload(coverInput, new File(["cover"], "cover.png", { type: "image/png" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Upload failed.");
  expect(screen.queryByAltText("Cover preview")).not.toBeInTheDocument();
});
