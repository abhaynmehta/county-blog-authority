import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App.jsx";
import { api, sortIssues, scoreBand } from "./api.js";

vi.mock("./api.js", async () => {
  const actual = await vi.importActual("./api.js");
  return {
    ...actual,
    api: {
      projects: vi.fn(),
      audit: vi.fn(),
      health: vi.fn(),
      corpus: vi.fn(),
      history: vi.fn(),
    },
  };
});

const AUDIT = {
  slug: "t",
  score: 35,
  publishable: false,
  word_count: 120,
  gates: [
    { gate: "Factual Accuracy", status: "FAIL", details: "1 factual issue" },
    { gate: "Technical SEO Eligibility", status: "PASS", details: "SEO basics pass" },
  ],
  issues: [
    {
      issue_id: "A-1", severity: "medium", owner: "ROI", category: "meta_title",
      summary: "Meta title too long", quoted_text: null, verified_fact: null,
      recommended_action: "Shorten it", acceptance_test: "Title is 30-60 chars",
    },
    {
      issue_id: "A-2", severity: "critical", owner: "ROI", category: "factual_error",
      summary: "Center Court placed in Noida", quoted_text: "Center Court in Noida",
      verified_fact: "The Center Court is in Gurugram, Haryana",
      recommended_action: "Correct the location", acceptance_test: "Described as Gurugram",
    },
  ],
  counts: { critical: 1, high: 0, medium: 1, low: 0, info: 0 },
};

const PROJECTS = {
  projects: [{
    name: "The Center Court", slug: "center_court", city: "Gurugram",
    sector: "88-A", rera_authority: "HARERA",
    configurations: [{ type: "3 BHK", carpet_area_sqft: 888, super_area_sqft: 1565 }],
    prohibited: ["Describing this project as being in Noida"],
  }],
  prohibited_wording: [],
};

const HEALTH = {
  status: "ok", engine_version: "0.1.0", projects_loaded: 5,
  claims_loaded: 10, registry_errors: [],
  storage: { durable: true, warning: null },
};

const CORPUS = {
  summary: { total: 87, publishable: 42, avg_score: 67.9, critical_docs: 24 },
  documents: [],
};

const HISTORY = { runs: 0, message: "No audit history yet." };

beforeEach(() => {
  vi.clearAllMocks();
  api.projects.mockResolvedValue(PROJECTS);
  api.audit.mockResolvedValue(AUDIT);
  api.health.mockResolvedValue(HEALTH);
  api.corpus.mockResolvedValue(CORPUS);
  api.history.mockResolvedValue(HISTORY);
});

async function goToAuditTab() {
  const user = userEvent.setup();
  render(<App />);
  const auditTab = await screen.findByRole("tab", { name: /audit a draft/i });
  await user.click(auditTab);
  return user;
}

describe("helpers", () => {
  it("sorts issues worst first", () => {
    const sorted = sortIssues(AUDIT.issues);
    expect(sorted[0].severity).toBe("critical");
  });

  it("does not mutate the input array", () => {
    const input = [...AUDIT.issues];
    sortIssues(input);
    expect(input[0].issue_id).toBe("A-1");
  });

  it.each([[95, "good"], [70, "fair"], [20, "poor"], [null, "unknown"]])(
    "bands score %s as %s", (score, band) => {
      expect(scoreBand(score)).toBe(band);
    });
});

describe("dashboard", () => {
  it("shows the dashboard by default", async () => {
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
  });

  it("shows system status when health loads", async () => {
    render(<App />);
    expect(await screen.findByText("5 projects loaded")).toBeInTheDocument();
  });
});

describe("audit flow", () => {
  it("disables the button until there is content", async () => {
    await goToAuditTab();
    expect(screen.getByRole("button", { name: /run audit/i })).toBeDisabled();
  });

  it("enables the button once content is typed", async () => {
    const user = await goToAuditTab();
    await user.type(screen.getByLabelText(/draft content/i), "Some copy");
    expect(screen.getByRole("button", { name: /run audit/i })).toBeEnabled();
  });

  it("shows the score and publishable state after auditing", async () => {
    const user = await goToAuditTab();
    await user.type(screen.getByLabelText(/draft content/i), "Some copy");
    await user.click(screen.getByRole("button", { name: /run audit/i }));

    expect(await screen.findByText("35")).toBeInTheDocument();
    expect(screen.getByText(/blocked/i)).toBeInTheDocument();
  });

  it("renders critical issues before medium ones", async () => {
    const user = await goToAuditTab();
    await user.type(screen.getByLabelText(/draft content/i), "Some copy");
    await user.click(screen.getByRole("button", { name: /run audit/i }));

    await screen.findByText(/Center Court placed in Noida/);
    const headings = screen.getAllByRole("heading", { level: 4 });
    const issueHeadings = headings.filter(h =>
      h.textContent.includes("Center Court") || h.textContent.includes("Meta title")
    );
    expect(issueHeadings[0]).toHaveTextContent(/Center Court placed in Noida/);
  });

  it("shows the quoted text and the verified fact", async () => {
    const user = await goToAuditTab();
    await user.type(screen.getByLabelText(/draft content/i), "Some copy");
    await user.click(screen.getByRole("button", { name: /run audit/i }));

    expect(await screen.findByText("Center Court in Noida")).toBeInTheDocument();
    expect(screen.getByText(/is in Gurugram, Haryana/)).toBeInTheDocument();
  });

  it("shows every gate with its status", async () => {
    const user = await goToAuditTab();
    await user.type(screen.getByLabelText(/draft content/i), "Some copy");
    await user.click(screen.getByRole("button", { name: /run audit/i }));

    await screen.findByText("Factual Accuracy");
    expect(screen.getByText("FAIL")).toBeInTheDocument();
    expect(screen.getByText("PASS")).toBeInTheDocument();
  });

  it("surfaces an API error to the user instead of failing silently", async () => {
    api.audit.mockRejectedValue(new Error("content exceeds 200000 characters"));
    const user = await goToAuditTab();
    await user.type(screen.getByLabelText(/draft content/i), "Some copy");
    await user.click(screen.getByRole("button", { name: /run audit/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/exceeds 200000/);
  });

  it("still renders when the projects call fails", async () => {
    api.projects.mockRejectedValue(new Error("offline"));
    render(<App />);
    expect(await screen.findByRole("heading", { name: /county group/i }))
      .toBeInTheDocument();
  });
});

describe("project reference", () => {
  it("lists projects from the registry", async () => {
    await goToAuditTab();
    expect(await screen.findByText("The Center Court")).toBeInTheDocument();
  });

  it("reveals verified figures when a project is expanded", async () => {
    const user = await goToAuditTab();
    await user.click(await screen.findByRole("button", { name: /The Center Court/ }));

    expect(screen.getByText("888")).toBeInTheDocument();
    expect(screen.getByText(/being in Noida/)).toBeInTheDocument();
  });

  it("collapses an expanded project when clicked again", async () => {
    const user = await goToAuditTab();
    const toggle = await screen.findByRole("button", { name: /The Center Court/ });
    await user.click(toggle);
    await user.click(toggle);
    await waitFor(() => expect(screen.queryByText("888")).not.toBeInTheDocument());
  });
});
