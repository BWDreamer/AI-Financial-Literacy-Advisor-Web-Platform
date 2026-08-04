import {
  createAdminArticle,
  deleteAdminArticle,
  deleteAdminUser,
  getAdminArticle,
  getAdminArticles,
  getAdminUser,
  getAdminUsers,
  getAdvisorySettings,
  inviteAdminUser,
  updateAdminArticle,
  updateAdminUser,
  updateAdvisorySettings,
  uploadAdminArticleImage,
} from "../admin";
import { apiGet, apiRequest } from "../client";

jest.mock("../client", () => ({
  apiGet: jest.fn(),
  apiRequest: jest.fn(),
}));

const mockedApiGet = jest.mocked(apiGet);
const mockedApiRequest = jest.mocked(apiRequest);

beforeEach(() => {
  jest.clearAllMocks();
  mockedApiGet.mockResolvedValue({});
  mockedApiRequest.mockResolvedValue({});
});

test("gets and updates advisory settings through admin-only endpoints", async () => {
  const topics = [
    { name: "Budgeting" as const, enabled: true },
    { name: "Investing" as const, enabled: false },
  ];

  await getAdvisorySettings();
  expect(mockedApiGet).toHaveBeenCalledWith("/admin/advisory-settings", true);

  await updateAdvisorySettings(topics);
  expect(mockedApiRequest).toHaveBeenCalledWith("/admin/advisory-settings", {
    method: "PATCH",
    authenticated: true,
    body: JSON.stringify({ topics }),
  });
});

test("uses the expected admin user management endpoints", async () => {
  const createRequest = {
    first_name: "Jane",
    last_name: "Smith",
    email: "jane@example.com",
    password: "11111111",
  };
  const updateRequest = {
    first_name: "Janet",
    last_name: "Smith",
    email: "janet@example.com",
  };

  await getAdminUsers();
  expect(mockedApiGet).toHaveBeenCalledWith("/admin/users", true);

  await getAdminUser(7);
  expect(mockedApiGet).toHaveBeenCalledWith("/admin/users/7", true);

  await inviteAdminUser(createRequest);
  expect(mockedApiRequest).toHaveBeenCalledWith("/admin/users", {
    method: "POST",
    authenticated: true,
    body: JSON.stringify(createRequest),
  });

  await updateAdminUser(7, updateRequest);
  expect(mockedApiRequest).toHaveBeenCalledWith("/admin/users/7", {
    method: "PATCH",
    authenticated: true,
    body: JSON.stringify(updateRequest),
  });

  await deleteAdminUser(7);
  expect(mockedApiRequest).toHaveBeenCalledWith("/admin/users/7", {
    method: "DELETE",
    authenticated: true,
  });
});

test("uses admin article endpoints that include all workflow states", async () => {
  await getAdminArticles({ status: "draft", page: 2, pageSize: 25 });
  expect(mockedApiRequest).toHaveBeenCalledWith("/admin/articles?status=draft&page=2&page_size=25", {
    authenticated: true,
  });

  await getAdminArticle("budgeting-basics");
  expect(mockedApiRequest).toHaveBeenCalledWith("/admin/articles/budgeting-basics", {
    authenticated: true,
  });
});

test("uses admin article endpoints for create, update and delete", async () => {
  const articleRequest = {
    id: "tax-checklist",
    title: "Tax Checklist",
    summary: "Prepare early for tax time.",
    coverImageUrl: null,
    authorName: "FinanceAI Learning Team",
    sourceName: "Knowledge Base",
    category: "Tax",
    status: "published" as const,
    publishedAt: "2026-07-19T00:00:00Z",
    contentBlocks: {
      type: "doc",
      content: [{ type: "paragraph", content: [{ type: "text", text: "Keep your receipts organised." }] }],
    },
  };

  await createAdminArticle(articleRequest);
  expect(mockedApiRequest).toHaveBeenCalledWith("/admin/articles", {
    method: "POST",
    authenticated: true,
    body: JSON.stringify(articleRequest),
  });

  await updateAdminArticle("tax-checklist", articleRequest);
  expect(mockedApiRequest).toHaveBeenCalledWith("/admin/articles/tax-checklist", {
    method: "PUT",
    authenticated: true,
    body: JSON.stringify(articleRequest),
  });

  await deleteAdminArticle("tax-checklist");
  expect(mockedApiRequest).toHaveBeenCalledWith("/admin/articles/tax-checklist", {
    method: "DELETE",
    authenticated: true,
  });
});

test("uploads article images as form data", async () => {
  const file = new File(["image"], "cover.png", { type: "image/png" });

  await uploadAdminArticleImage(file);

  expect(mockedApiRequest).toHaveBeenCalledWith("/admin/articles/images", {
    method: "POST",
    authenticated: true,
    body: expect.any(FormData),
  });
  const body = mockedApiRequest.mock.calls[0][1]?.body as FormData;
  expect(body.get("file")).toBe(file);
});
