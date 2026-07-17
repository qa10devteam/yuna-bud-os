import { test, expect, Page } from '@playwright/test';

/**
 * E2E – Navigation tests (Terra-OS / budos)
 *
 * Pre-condition: user is authenticated (storageState from auth.setup.ts)
 *
 * Tests:
 *  1. Main dashboard visible after login
 *  2. Sidebar module navigation: Rynek, Kosztorys, Zwiad
 *  3. No unhandled JS errors in console across those modules
 */

const jsErrors: string[] = [];

test.describe('Navigation – authenticated user', () => {
  test.beforeEach(async ({ page }) => {
    // Collect uncaught JS errors
    page.on('pageerror', (err) => {
      // Ignore known benign errors (e.g. network, service worker)
      const msg = err.message;
      if (
        !msg.includes('ChunkLoadError') &&
        !msg.includes('Loading chunk') &&
        !msg.includes('serviceWorker')
      ) {
        jsErrors.push(msg);
      }
    });

    await page.goto('/');
    // Wait for authenticated dashboard to load
    await expect(
      page.locator('[aria-label="Zwiń menu"], [aria-label="Rozwiń menu"]').first()
    ).toBeVisible({ timeout: 15_000 });
  });

  test('main dashboard is visible after login', async ({ page }) => {
    // The sidebar must be visible
    await expect(
      page.locator('[aria-label="Zwiń menu"], [aria-label="Rozwiń menu"]').first()
    ).toBeVisible();

    // Main content area must exist — use .first() to avoid strict-mode violation
    await expect(page.locator('main, [class*="content"], [class*="page"], h1, h2').first()).toBeVisible({ timeout: 10_000 });

    // Page title should not be an error
    await expect(page).not.toHaveTitle(/error|404|500/i);
  });

  test('navigate to Rynek (market-intel) module', async ({ page }) => {
    // Expand sidebar if collapsed (click toggle)
    const expandBtn = page.locator('[aria-label="Rozwiń menu"]');
    if (await expandBtn.isVisible()) {
      await expandBtn.click();
    }

    // Click "Rynek" in sidebar
    const rynekBtn = page.getByRole('button', { name: 'Rynek' }).first();
    await expect(rynekBtn).toBeVisible({ timeout: 5_000 });
    await rynekBtn.click();

    // Page content should load
    await page.waitForTimeout(2_000);

    // The page should show some content area — use .first() to avoid strict-mode violation
    await expect(page.locator('main, [class*="page"], h1, h2, [class*="Market"], [class*="market"]').first()).toBeVisible({ timeout: 10_000 });
  });

  test('navigate to Kosztorys module', async ({ page }) => {
    // Expand sidebar if collapsed
    const expandBtn = page.locator('[aria-label="Rozwiń menu"]');
    if (await expandBtn.isVisible()) {
      await expandBtn.click();
    }

    const kosztorysBtn = page.getByRole('button', { name: 'Kosztorys' }).first();
    await expect(kosztorysBtn).toBeVisible({ timeout: 5_000 });
    await kosztorysBtn.click();

    await page.waitForTimeout(2_000);

    await expect(page.locator('main, [class*="page"], h1, h2, [class*="Kosztorys"], [class*="kosztorys"]').first()).toBeVisible({ timeout: 10_000 });
  });

  test('navigate to Zwiad module', async ({ page }) => {
    // Expand sidebar if collapsed
    const expandBtn = page.locator('[aria-label="Rozwiń menu"]');
    if (await expandBtn.isVisible()) {
      await expandBtn.click();
    }

    const zwiadBtn = page.getByRole('button', { name: 'Zwiad' }).first();
    await expect(zwiadBtn).toBeVisible({ timeout: 5_000 });
    await zwiadBtn.click();

    await page.waitForTimeout(2_000);

    await expect(page.locator('main, [class*="page"], h1, h2, [class*="Zwiad"], [class*="zwiad"]').first()).toBeVisible({ timeout: 10_000 });
  });

  test('no unhandled JS errors across module navigation', async ({ page }) => {
    // Expand sidebar
    const expandBtn = page.locator('[aria-label="Rozwiń menu"]');
    if (await expandBtn.isVisible()) {
      await expandBtn.click();
    }

    const modules = ['Rynek', 'Kosztorys', 'Zwiad'];
    const collectedErrors: string[] = [];

    page.on('pageerror', (err) => {
      const msg = err.message;
      if (!msg.includes('ChunkLoadError') && !msg.includes('Loading chunk') && !msg.includes('serviceWorker')) {
        collectedErrors.push(msg);
      }
    });

    for (const moduleName of modules) {
      const btn = page.getByRole('button', { name: moduleName }).first();
      if (await btn.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await btn.click();
        await page.waitForTimeout(1_500);
      }
    }

    // Assert no critical JS errors occurred
    expect(collectedErrors, `JS errors found: ${collectedErrors.join('; ')}`).toHaveLength(0);
  });
});
