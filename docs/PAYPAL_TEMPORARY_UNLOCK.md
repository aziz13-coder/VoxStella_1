# PayPal Pending Activation

## Current policy

Vox Stella unlocks protected features only after the desktop app receives and
validates a signed license token from the license server. PayPal approval by
itself is not an entitlement, and there is no temporary or provisional premium
unlock.

If PayPal approves an in-app subscription while the public license service is
unreachable, the app may save the subscription ID as a pending activation. The
pending record exists only so the customer can finish verification later:

1. PayPal returns a subscription ID after checkout approval.
2. The desktop app asks the license server to verify the subscription.
3. When verification succeeds, the server creates or updates the license and
   returns a signed token bound to the device.
4. When the service is unreachable, the app stores a short-lived pending
   activation record. Protected features remain locked.
5. The customer can use **Finish PayPal activation** or **Verify Now** after the
   service is restored.
6. A successful retry replaces the pending record with the signed token. An
   expired pending record is removed and never becomes a backend session.

Server-side rejection—such as an inactive subscription, an unexpected plan, or
invalid PayPal data—is not stored as pending. Manually entered PayPal purchase
IDs must also be verified online before activation.

## Security boundary

- The license server, not the PayPal browser callback, decides entitlement.
- Pending activation status is always reported as inactive.
- Pending activation never creates a local backend session token.
- The desktop IPC response does not reveal the canonical license key returned
  by older server versions.
- Signed durable tokens remain in Electron secure storage. The renderer receives
  only a short-lived, device-bound local session with an opaque identifier.

## Operations

For the current local-server and Cloudflare-tunnel setup, public activation
requires both:

- `licensing_server\run-licensing-server.bat`
- `licensing_server\run_cloudflared.bat`

The local admin may remain available at
`http://127.0.0.1:8787/admin/login` while the tunnel is down, but activation
through `https://license.voxstella.app` will not work. After service is restored,
the customer should open Settings and select **Finish PayPal activation** or
**Verify Now**.
