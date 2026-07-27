import { adminNavigation } from "../adminNavigation";

test("defines the four admin navigation pages", () => {
  expect(adminNavigation).toHaveLength(1);
  expect(adminNavigation[0].label).toBe("Administration");
  expect(adminNavigation[0].items.map((item) => ({ label: item.label, to: item.to }))).toEqual([
    { label: "Dashboard", to: "/admin/dashboard" },
    { label: "User Management", to: "/admin/users" },
    { label: "Advisory Settings", to: "/admin/settings" },
    { label: "Knowledge Hub", to: "/admin/knowledge" },
  ]);
});
