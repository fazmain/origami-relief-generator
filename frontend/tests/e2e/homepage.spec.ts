import { expect, test } from "@playwright/test";

test.describe("Homepage — static render", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("page loads without errors", async ({ page }) => {
    await expect(page).not.toHaveTitle(/error/i);
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));
    await page.waitForLoadState("networkidle");
    expect(errors).toHaveLength(0);
  });

  test("shows app header", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /origami relief generator/i })).toBeVisible();
  });

  test("shows upload file input", async ({ page }) => {
    await expect(page.locator('input[type="file"]')).toBeVisible();
  });

  test("width and height inputs have valid default mm values", async ({ page }) => {
    const inputs = page.locator('input[type="number"]');
    const width = Number(await inputs.nth(0).inputValue());
    const height = Number(await inputs.nth(1).inputValue());
    expect(width).toBeGreaterThan(0);
    expect(width).toBeLessThan(10000); // sanity: not pixel values from a full-res image
    expect(height).toBeGreaterThan(0);
    expect(height).toBeLessThan(10000);
  });

  test("shows resolution mode radio buttons", async ({ page }) => {
    await expect(page.getByText("Piece Count")).toBeVisible();
    await expect(page.getByText("Box Size")).toBeVisible();
  });

  test("shows algorithm radio buttons", async ({ page }) => {
    await expect(page.getByText("Depth Estimation")).toBeVisible();
    await expect(page.getByText("Luminance")).toBeVisible();
  });

  test("shows generate button", async ({ page }) => {
    await expect(page.getByRole("button", { name: /generate/i })).toBeVisible();
  });

  test("shows awaiting input placeholder when no grid data", async ({ page }) => {
    await expect(page.getByText(/awaiting input/i)).toBeVisible();
  });

  test("submitting without file shows error message", async ({ page }) => {
    await page.getByRole("button", { name: /generate/i }).click();
    await expect(page.getByText(/please select an image/i)).toBeVisible();
  });

  test("switching to box size mode shows box size input", async ({ page }) => {
    await page.getByLabel("Box Size").check();
    await expect(page.getByText(/min box size/i)).toBeVisible();
  });

  test("switching to count mode shows target pieces input", async ({ page }) => {
    // Start in count mode (default), switch away, switch back
    await page.getByLabel("Box Size").check();
    await page.getByLabel("Piece Count").check();
    await expect(page.getByText(/target pieces/i)).toBeVisible();
  });
});
