import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AdvisorySettings from "../AdvisorySettings";
import { getAdvisorySettings, updateAdvisorySettings } from "../../../api/admin";

jest.mock("../../../api/admin", () => ({
  getAdvisorySettings: jest.fn(),
  updateAdvisorySettings: jest.fn(),
}));

const mockedGetAdvisorySettings = jest.mocked(getAdvisorySettings);
const mockedUpdateAdvisorySettings = jest.mocked(updateAdvisorySettings);

const apiSettings = {
  topics: [
    { name: "Budgeting" as const, enabled: true },
    { name: "Saving" as const, enabled: true },
    { name: "Tax" as const, enabled: false },
    { name: "Superannuation" as const, enabled: true },
    { name: "Investing" as const, enabled: false },
    { name: "Debt" as const, enabled: true },
  ],
};

beforeEach(() => {
  jest.clearAllMocks();
  mockedGetAdvisorySettings.mockResolvedValue(apiSettings);
  mockedUpdateAdvisorySettings.mockImplementation(async (topics) => ({ topics }));
});

test("loads advisory topic controls from the API", async () => {
  render(<AdvisorySettings />);

  expect(await screen.findByRole("heading", { name: /advisory settings/i })).toBeInTheDocument();
  await waitFor(() => expect(screen.queryByText("Loading")).not.toBeInTheDocument());
  expect(mockedGetAdvisorySettings).toHaveBeenCalledTimes(1);

  expect(screen.getAllByText("Budgeting").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Saving").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Tax").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Superannuation").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Investing").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Debt").length).toBeGreaterThan(0);

  expect(screen.getByText("4")).toBeInTheDocument();
  expect(screen.getAllByText("Enabled").length).toBeGreaterThan(0);
  expect(screen.getByText("2")).toBeInTheDocument();
  expect(screen.getAllByText("Disabled").length).toBeGreaterThan(0);
});

test("toggles a topic and saves the changed settings", async () => {
  const user = userEvent.setup();
  render(<AdvisorySettings />);

  await waitFor(() => expect(screen.queryByText("Loading")).not.toBeInTheDocument());
  const topicControls = screen.getByText("Topic Controls").closest("section");
  expect(topicControls).not.toBeNull();
  const taxRow = within(topicControls as HTMLElement).getByText("Tax").closest("div");
  expect(taxRow).not.toBeNull();

  await user.click(within(taxRow as HTMLElement).getByRole("button", { name: /disabled/i }));
  await user.click(screen.getByRole("button", { name: /save settings/i }));

  await waitFor(() => {
    expect(mockedUpdateAdvisorySettings).toHaveBeenCalledWith(
      expect.arrayContaining([{ name: "Tax", enabled: true }])
    );
  });
  expect(await screen.findByRole("status")).toHaveTextContent("Advisory settings saved.");
});

test("resets advisory settings to the default topic configuration", async () => {
  const user = userEvent.setup();
  render(<AdvisorySettings />);

  await waitFor(() => expect(screen.queryByText("Loading")).not.toBeInTheDocument());
  await user.click(screen.getByRole("button", { name: /reset defaults/i }));

  await waitFor(() => {
    expect(mockedUpdateAdvisorySettings).toHaveBeenCalledWith(
      expect.arrayContaining([
        { name: "Budgeting", enabled: true },
        { name: "Investing", enabled: false },
        { name: "Debt", enabled: true },
      ])
    );
  });
});

test("shows a loading error and retries successfully", async () => {
  mockedGetAdvisorySettings
    .mockRejectedValueOnce(new Error("Unable to load advisory settings."))
    .mockResolvedValueOnce(apiSettings);
  const user = userEvent.setup();
  render(<AdvisorySettings />);

  expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load advisory settings.");
  await user.click(screen.getByRole("button", { name: /try again/i }));

  await waitFor(() => expect(screen.queryByText("Loading")).not.toBeInTheDocument());
  expect(screen.getAllByText("Budgeting").length).toBeGreaterThan(0);
  expect(mockedGetAdvisorySettings).toHaveBeenCalledTimes(2);
});

test("shows an error when saving advisory settings fails", async () => {
  mockedUpdateAdvisorySettings.mockRejectedValueOnce(new Error("Save failed."));
  const user = userEvent.setup();
  render(<AdvisorySettings />);

  await waitFor(() => expect(screen.queryByText("Loading")).not.toBeInTheDocument());
  await user.click(screen.getByRole("button", { name: /save settings/i }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Save failed.");
  expect(screen.getByRole("button", { name: /save settings/i })).toBeEnabled();
});

test("shows an error when resetting advisory settings fails", async () => {
  mockedUpdateAdvisorySettings.mockRejectedValueOnce(new Error("Reset failed."));
  const user = userEvent.setup();
  render(<AdvisorySettings />);

  await waitFor(() => expect(screen.queryByText("Loading")).not.toBeInTheDocument());
  await user.click(screen.getByRole("button", { name: /reset defaults/i }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Reset failed.");
  expect(screen.getByRole("button", { name: /reset defaults/i })).toBeEnabled();
});
