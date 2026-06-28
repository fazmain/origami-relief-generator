import { expect, Page, test } from "@playwright/test";
import path from "path";

const TEST_IMAGE = path.join(__dirname, "fixtures", "test-image.png");

const MOCK_PROCESS_RESPONSE = {
  grid: [
    {
      id: "C0",
      color: "#a3b2c1",
      height_mm: 25.0,
      exterior_coords: [
        [7.5, 0], [3.75, 6.495], [-3.75, 6.495],
        [-7.5, 0], [-3.75, -6.495], [3.75, -6.495],
      ],
      top_vertices_z: [25.0, 25.0, 25.0, 25.0, 25.0, 25.0],
      is_cluster: false,
      box_size_mm: 15.0,
    },
  ],
  metadata: { num_cols: 1, num_rows: 1, box_size_mm: 15.0, R: 7.5 },
};

async function mockBackend(page: Page) {
  await page.route("**/api/process", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_PROCESS_RESPONSE),
    })
  );

  await page.route("**/api/pdf", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/pdf",
      body: Buffer.from("%PDF-1.4\n%%EOF"),
    })
  );

  await page.route("**/api/pdf_poster", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/pdf",
      body: Buffer.from("%PDF-1.4\n%%EOF"),
    })
  );
}

test.describe("Upload & Generate Flow (mocked backend)", () => {
  test.beforeEach(async ({ page }) => {
    await mockBackend(page);
    await page.goto("/");
  });

  test("after successful process shows result metadata", async ({ page }) => {
    await page.locator('input[type="file"]').setInputFiles(TEST_IMAGE);
    await page.getByRole("button", { name: /generate/i }).click();

    await expect(page.getByText(/result metadata/i)).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/columns/i)).toBeVisible();
  });

  test("after successful process shows download buttons", async ({ page }) => {
    await page.locator('input[type="file"]').setInputFiles(TEST_IMAGE);
    await page.getByRole("button", { name: /generate/i }).click();

    await expect(page.getByRole("button", { name: /download pdf blueprint/i })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("button", { name: /poster/i })).toBeVisible();
  });

  test("after successful process shows 3D viewer controls", async ({ page }) => {
    await page.locator('input[type="file"]').setInputFiles(TEST_IMAGE);
    await page.getByRole("button", { name: /generate/i }).click();

    await expect(page.getByText(/explode view/i)).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/sun azimuth/i)).toBeVisible();
    await expect(page.getByText(/sun elevation/i)).toBeVisible();
  });

  test("3D canvas renders after processing", async ({ page }) => {
    await page.locator('input[type="file"]').setInputFiles(TEST_IMAGE);
    await page.getByRole("button", { name: /generate/i }).click();

    await expect(page.locator("canvas")).toBeVisible({ timeout: 15_000 });
  });

  test("shows loading state while processing", async ({ page }) => {
    // Delay the mock response so we can catch the loading state
    await page.route("**/api/process", async (route) => {
      await new Promise((r) => setTimeout(r, 500));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_PROCESS_RESPONSE),
      });
    });

    await page.locator('input[type="file"]').setInputFiles(TEST_IMAGE);
    await page.getByRole("button", { name: /generate/i }).click();

    await expect(page.getByRole("button", { name: /processing/i })).toBeVisible();
    await expect(page.getByText(/result metadata/i)).toBeVisible({ timeout: 10_000 });
  });

  test("shows error message on API failure", async ({ page }) => {
    await page.route("**/api/process", (route) =>
      route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "fail" }) })
    );

    await page.locator('input[type="file"]').setInputFiles(TEST_IMAGE);
    await page.getByRole("button", { name: /generate/i }).click();

    await expect(page.getByText(/error/i)).toBeVisible({ timeout: 10_000 });
  });

  test("width field does not get overwritten with pixel values after file upload", async ({ page }) => {
    const widthBefore = await page.locator('input[type="number"]').nth(0).inputValue();

    await page.locator('input[type="file"]').setInputFiles(TEST_IMAGE);
    await page.waitForTimeout(200); // let onload fire

    const widthAfter = await page.locator('input[type="number"]').nth(0).inputValue();
    // Width (mm) should not have been changed to image pixel width (50px)
    expect(widthAfter).toBe(widthBefore);
    // Definitely should not be 50 (the test image pixel width)
    expect(Number(widthAfter)).not.toBe(50);
  });
});

test.describe("Upload Flow — no backend (offline validation)", () => {
  test("error shown when no file selected", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /generate/i }).click();
    await expect(page.getByText(/please select an image/i)).toBeVisible();
  });
});
