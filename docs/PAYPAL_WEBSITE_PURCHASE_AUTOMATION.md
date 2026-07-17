# PayPal Website Purchase Automation

## Current Website Purchase Points

The generated website currently exposes two PayPal purchase paths:

- Website monthly subscription: `P-4L214935JK8549417NIAB5KY` at `$35 / month`
- Website one-time license: PayPal hosted checkout `BME4R68MWV2VA` at `$250`

The app's in-app Astro Clock offer remains separate:

- In-app monthly subscription: `P-83N24493LW950963HNIIXO7Q` at `$25 / month`

## How Website Purchases Link To The Desktop App

The desktop app cannot automatically know that a website buyer and a desktop install are the same person unless the user provides a shared identifier.

The supported identifier is the PayPal purchase ID:

- For the `$35 / month` website subscription, the user enters the PayPal subscription ID, usually starting with `I-`.
- For the `$250` one-time checkout, the user enters the PayPal transaction/capture ID from the PayPal receipt.

In the desktop app:

1. Open Settings.
2. Go to License and Activation.
3. Paste the PayPal website purchase ID.
4. Press Activate PayPal purchase.

The app sends that ID to the existing license server. The server verifies it with PayPal, creates or updates a normal row in the existing `licenses` table, activates the current device, and returns the same signed license token used by manual licenses.

## Server Requirements

Automatic website purchase activation requires the existing license server to be reachable publicly:

- Local server: `licensing_server\run-licensing-server.bat`
- Cloudflare tunnel: `licensing_server\run_cloudflared.bat`
- Public endpoint: `https://license.voxstella.app`

If the tunnel is closed, the admin page may still work locally, but public PayPal activation and PayPal webhooks cannot reach the server.

## PayPal Webhook Events

Configure the PayPal webhook URL as:

`https://license.voxstella.app/paypal/webhook`

Subscribe to these events:

- `BILLING.SUBSCRIPTION.ACTIVATED`
- `BILLING.SUBSCRIPTION.CANCELLED`
- `BILLING.SUBSCRIPTION.SUSPENDED`
- `BILLING.SUBSCRIPTION.EXPIRED`
- `BILLING.SUBSCRIPTION.PAYMENT.FAILED`
- `PAYMENT.SALE.COMPLETED`
- `PAYMENT.CAPTURE.COMPLETED`
- `PAYMENT.CAPTURE.REFUNDED`
- `PAYMENT.CAPTURE.REVERSED`
- `PAYMENT.CAPTURE.DENIED`

## Existing Licenses

Older manually created license keys still use `/license/activate`, `/license/refresh`, and `/license/verify`.

PayPal automation is additive: it creates licenses in the same table and returns the same signed token format. It does not replace or invalidate old manual keys.
