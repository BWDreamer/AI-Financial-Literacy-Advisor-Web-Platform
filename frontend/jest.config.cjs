/** @type {import('jest').Config} */
module.exports = {
  preset: "ts-jest",
  testEnvironment: "jsdom",
  setupFiles: ["<rootDir>/src/testPolyfills.ts"],
  setupFilesAfterEnv: ["<rootDir>/src/setupTests.ts"],
  testMatch: ["<rootDir>/src/**/*.test.ts?(x)"],
  moduleNameMapper: {
    "\\.(css|less|sass|scss)$": "identity-obj-proxy",
  },
  collectCoverageFrom: [
    "src/pages/admin/**/*.{ts,tsx}",
    "src/pages/ArticleDetailPage.tsx",
    "src/pages/AdvisorChat.tsx",
    "src/pages/HomePage.tsx",
    "src/pages/KnowledgeHub.tsx",
    "src/pages/MyGoals.tsx",
    "src/components/AdminPortalLayout.tsx",
    "src/components/UserPortalLayout.tsx",
    "src/components/knowledge/ArticleCard.tsx",
    "src/components/knowledge/ArticleList.tsx",
    "src/config/adminNavigation.ts",
    "src/api/admin.ts",
    "!src/**/*.d.ts",
    "!src/**/*.test.{ts,tsx}",
  ],
  coverageDirectory: "coverage",
};
