# The Ark API

## Mail configuration
The auth lifecycle now supports transactional verification and password-reset email.

### Local setup
A local `.env` file has been added at `apps/api/.env`.

Current default behavior:
- `EMAIL_DELIVERY_MODE=debug`
- messages are captured in `apps/api/state/email_outbox.json`
- tokens are still exposed in API responses for local development

### Turn on real outbound SMTP
1. Open `apps/api/.env`
2. Set `SMTP_PASSWORD` to the mailbox/app password for `ron@chapmanandassociates.com`
3. Change `EMAIL_DELIVERY_MODE` from `debug` to `smtp` (or `auto`)
4. Restart the API process

### Current SMTP preset
The local config is prefilled for Google Workspace / Gmail SMTP:
- host: `smtp.gmail.com`
- port: `587`
- username: `ron@chapmanandassociates.com`
- TLS enabled

### Delivery modes
- `debug`: write email payloads to `state/email_outbox.json`
- `smtp`: send through SMTP, falling back to debug outbox if delivery fails
- `auto`: use SMTP when configured, otherwise use debug outbox
- `disabled`: suppress delivery entirely
