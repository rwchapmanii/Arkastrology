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

## Grounded chat configuration

The Ask feature can now answer from the current reading plus the traditional source documents loaded into the repo.

### Deterministic fallback

If no OpenAI key is configured, grounded chat still works, but it uses a local deterministic synthesis path. That keeps answers source-bound, but they will sound flatter and more repetitive.

### Turn on higher-reasoning grounded chat

1. Open `apps/api/.env`
2. Set:
   - `OPENAI_API_KEY=<your api key>`
   - optional: `OPENAI_CHAT_MODEL=gpt-5.5`
   - optional: `OPENAI_REASONING_EFFORT=high`
3. Restart or redeploy the API

With those env vars present, The Ark will retrieve grounded source passages locally and then ask the model to synthesize a more articulate astrologer-style answer from that context.

## Core reading LLM synthesis

The main natal, synastry, and daily-horoscope prose can also be synthesized by a cheaper OpenAI model while keeping the chart engine and traditional alignment document as the source of truth.

### How it works

- the chart engine still computes placements, transits, profections, topic judgments, and constraints locally
- The Ark then sends that structured evidence plus the traditional alignment document to an OpenAI model
- the model rewrites only the final prose layer; it does not replace the astrology calculation layer
- if the model is unavailable, the API falls back to the deterministic reading engine automatically

### Recommended low-cost setup

1. Open `apps/api/.env`
2. Set:
   - `OPENAI_API_KEY=<your api key>`
   - optional: `OPENAI_READING_MODEL=gpt-5-mini`
   - optional: `OPENAI_READING_REASONING_EFFORT=low`
   - optional: `OPENAI_READING_TIMEOUT_SECONDS=45`
3. Restart or redeploy the API
