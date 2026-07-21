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
    "src/components/AdminPortalLayout.tsx",
    "src/config/adminNavigation.ts",
    "src/api/admin.ts",
    "!src/**/*.d.ts",
    "!src/**/*.test.{ts,tsx}",
  ],
  coverageDirectory: "coverage",
};
