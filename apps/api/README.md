# The Ark API

## Mail configuration
The auth lifecycle now supports transactional verification and password-reset email.

### Local setup
A local `.env` file has been added at `apps/api/.env`.

Current default behavior:
- `EMAIL_DELIVERY_MODE=debug`
- messages are captured in `apps/api/state/email_outbox.json`
- tokens are still exposed in API responses for local development

### Turn on Resend API delivery
1. Verify your sending domain in Resend
2. Create a Resend API key
3. Open `apps/api/.env`
4. Set:
   - `EMAIL_DELIVERY_MODE=api` (or `auto`)
   - `EMAIL_PROVIDER=resend`
   - `RESEND_API_KEY=<your resend api key>`
   - `EMAIL_FROM_ADDRESS=support@arkastrology.app`
   - `EMAIL_SUPPORT_ADDRESS=support@arkastrology.app`
5. Restart the API process

### Turn on real outbound SMTP
1. Open `apps/api/.env`
2. Set `SMTP_PASSWORD` to the mailbox/app password for `ron@chapmanandassociates.com`
3. Change `EMAIL_DELIVERY_MODE` from `debug` to `smtp` (or `auto`)
4. Restart the API process

### Current SMTP preset
The local example config is prefilled for Google Workspace / Gmail SMTP:
- host: `smtp.gmail.com`
- port: `587`
- username: `ron@chapmanandassociates.com`
- TLS enabled

### Delivery modes
- `debug`: write email payloads to `state/email_outbox.json`
- `api`: send through a supported email API provider such as Resend, falling back to debug outbox if delivery fails
- `smtp`: send through SMTP, falling back to debug outbox if delivery fails
- `auto`: prefer API delivery when `EMAIL_PROVIDER` is configured, otherwise use SMTP when configured, otherwise use debug outbox
- `disabled`: suppress delivery entirely
