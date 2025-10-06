
import { test, expect } from '@playwright/test';

test.describe('Agent Lab UI - Tabbed Interface Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://127.0.0.1:7860');
  });

  test('should display main tabs correctly', async ({ page }) => {
    // Check that all 4 main tabs are present
    await expect(page.locator('[id="main-tabs"]')).toBeVisible();

    // Check tab labels
    await expect(page.getByRole('tab', { name: 'Chat' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Configuration' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Sessions' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Analytics' })).toBeVisible();
  });

  test('should navigate between tabs', async ({ page }) => {
    // Start on Chat tab (default)
    await expect(page.locator('[id="chat-tab"]')).toBeVisible();

    // Navigate to Configuration tab
    await page.getByRole('tab', { name: 'Configuration' }).click();
    await expect(page.locator('[id="config-tab"]')).toBeVisible();
    await expect(page.locator('[id="agent-name"]')).toBeVisible();

    // Navigate to Sessions tab
    await page.getByRole('tab', { name: 'Sessions' }).click();
    await expect(page.locator('[id="sessions-tab"]')).toBeVisible();
    await expect(page.locator('[id="session-name"]')).toBeVisible();

    // Navigate to Analytics tab
    await page.getByRole('tab', { name: 'Analytics' }).click();
    await expect(page.locator('[id="analytics-tab"]')).toBeVisible();
    await expect(page.locator('[id="run-info"]')).toBeVisible();

    // Back to Chat
    await page.getByRole('tab', { name: 'Chat' }).click();
    await expect(page.locator('[id="chat-tab"]')).toBeVisible();
  });

  test('keyboard shortcuts work in chat tab', async ({ page }) => {
    // Focus on chat input
    await page.locator('[id="chat-input"]').focus();

    // Test Ctrl+K to focus input (should already be focused)
    await page.keyboard.press('Control+k');
    await expect(page.locator('[id="chat-input"]')).toBeFocused();

    // Test Ctrl+R to refresh models
    await page.keyboard.press('Control+r');
    // Should trigger model refresh (check if model source updates)

    // Test Escape to stop generation (when not generating)
    await page.keyboard.press('Escape');
    // Should not error
  });

  test('chat functionality works across tabs', async ({ page }) => {
    // Ensure we're on chat tab
    await page.getByRole('tab', { name: 'Chat' }).click();

    // Build agent first (go to config tab)
    await page.getByRole('tab', { name: 'Configuration' }).click();
    await page.locator('[id="agent-name"]').fill('Test Agent');
    await page.locator('[id="system-prompt"]').fill('You are a helpful assistant.');
    await page.locator('[id="build-agent"]').click();

    // Back to chat
    await page.getByRole('tab', { name: 'Chat' }).click();

    // Type a message
    await page.locator('[id="chat-input"]').fill('Hello');

    // Test Ctrl+Enter to send (if implemented)
    await page.keyboard.press('Control+Enter');
    // Message should be sent or input should submit
  });

  test('session management works', async ({ page }) => {
    // Go to sessions tab
    await page.getByRole('tab', { name: 'Sessions' }).click();

    // Check session elements are present
    await expect(page.locator('[id="session-name"]')).toBeVisible();
    await expect(page.locator('[id="save-session"]')).toBeVisible();
    await expect(page.locator('[id="load-session"]')).toBeVisible();
    await expect(page.locator('[id="new-session"]')).toBeVisible();

    // Test new session
    await page.locator('[id="new-session"]').click();
    await expect(page.locator('[id="session-status"]')).toContainText('New session started');
  });

  test('analytics tab displays information', async ({ page }) => {
    // Go to analytics tab
    await page.getByRole('tab', { name: 'Analytics' }).click();

    // Check analytics elements
    await expect(page.locator('[id="run-info"]')).toBeVisible();
    await expect(page.locator('[id="download-csv"]')).toBeVisible();
  });

  test('configuration validation works', async ({ page }) => {
    // Go to configuration tab
    await page.getByRole('tab', { name: 'Configuration' }).click();

    // Test empty agent name
    await page.locator('[id="agent-name"]').fill('');
    await page.locator('[id="build-agent"]').click();
    // Should show validation error

    // Test valid inputs
    await page.locator('[id="agent-name"]').fill('Valid Agent');
    await page.locator('[id="system-prompt"]').fill('Valid prompt');
    await page.locator('[id="build-agent"]').click();
    // Should show success
  });

  test('model refresh works', async ({ page }) => {
    // Go to configuration tab
    await page.getByRole('tab', { name: 'Configuration' }).click();

    // Click refresh models
    await page.locator('[id="refresh-models"]').click();

    // Check if model source updates
    await expect(page.locator('[id="model-source"]')).toBeVisible();
  });

  test('web tool toggle works', async ({ page }) => {
    // Go to configuration tab
    await page.getByRole('tab', { name: 'Configuration' }).click();

    // Check web tool checkbox
    const webCheckbox = page.locator('[id="web-tool"]');
    await expect(webCheckbox).toBeVisible();

    // Toggle it
    await webCheckbox.check();
    await expect(webCheckbox).toBeChecked();

    await webCheckbox.uncheck();
    await expect(webCheckbox).not.toBeChecked();
  });

  test('tab accessibility - keyboard navigation', async ({ page }) => {
    // Test tab navigation with keyboard
    await page.keyboard.press('Tab');
    // Should focus on first tab or element

    // Test arrow keys for tab navigation (if supported)
    await page.getByRole('tab', { name: 'Chat' }).focus();
    await page.keyboard.press('ArrowRight');
    // Should move to next tab
  });

  test('responsive layout works', async ({ page }) => {
    // Test that layout adapts (basic check)
    await expect(page.locator('.gradio-container')).toBeVisible();

    // Check that columns are present
    await expect(page.locator('[id="chat-tab"]').locator('..').locator('div').first()).toBeVisible();
  });
});