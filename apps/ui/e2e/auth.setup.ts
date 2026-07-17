import { test as setup, expect, request } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const authFile = path.join(__dirname, '.auth/user.json');

const E2E_EMAIL = 'e2e_test@terra.os';
const E2E_PASS = 'E2eTest123!';

setup('authenticate', async ({ page }) => {
  // Ensure .auth directory exists
  const authDir = path.dirname(authFile);
  if (!fs.existsSync(authDir)) {
    fs.mkdirSync(authDir, { recursive: true });
  }

  // Reuse existing auth state if the file was created in the last 10 minutes
  if (fs.existsSync(authFile)) {
    const stat = fs.statSync(authFile);
    const ageMs = Date.now() - stat.mtimeMs;
    if (ageMs < 10 * 60 * 1000) {
      console.log('[auth.setup] Reusing existing auth state (age:', Math.round(ageMs / 1000), 's)');
      return; // skip — file is fresh enough
    }
  }

  // Obtain token via API (with retry on rate limit)
  const apiContext = await request.newContext();
  let loginData: { access_token: string; refresh_token: string; user: object } | null = null;

  for (let attempt = 0; attempt < 3; attempt++) {
    const loginRes = await apiContext.post('http://localhost:3000/api/v2/auth/login', {
      data: { email: E2E_EMAIL, password: E2E_PASS },
      headers: { 'Content-Type': 'application/json' },
    });

    if (loginRes.ok()) {
      loginData = await loginRes.json() as typeof loginData;
      break;
    }

    const body = await loginRes.text();
    console.log(`[auth.setup] Attempt ${attempt + 1} failed: ${body}`);

    if (body.includes('Rate limit') || loginRes.status() === 429) {
      // Wait 65 seconds for the rate limit window to reset
      console.log('[auth.setup] Rate limited — waiting 65s...');
      await new Promise((r) => setTimeout(r, 65_000));
    } else {
      throw new Error(`Login failed: ${loginRes.status()} ${body}`);
    }
  }

  if (!loginData) {
    throw new Error('Could not obtain auth token after 3 attempts');
  }

  const { access_token, refresh_token, user } = loginData;

  // Open the app and inject auth into Zustand localStorage
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');

  await page.evaluate(({ token, refreshTok, usr }) => {
    const storeData = {
      state: {
        user: usr,
        accessToken: token,
        refreshToken: refreshTok,
      },
      version: 0,
    };
    localStorage.setItem('terra-auth', JSON.stringify(storeData));
    localStorage.setItem('terra-onboarding-dismissed', 'true');
    localStorage.setItem('onboarding-complete', 'true');
  }, { token: access_token, refreshTok: refresh_token, usr: user });

  // Reload to trigger Zustand hydration with injected auth
  await page.reload();
  await expect(
    page.locator('[aria-label="Zwiń menu"], [aria-label="Rozwiń menu"]').first()
  ).toBeVisible({ timeout: 20_000 });

  // Save signed-in state (localStorage included)
  await page.context().storageState({ path: authFile });
});
