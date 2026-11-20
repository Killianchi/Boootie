# App Store Connect: privacy setup for boootie

Answers below match the policy at https://boootie.com/privacy. Data flow: screenshots and actions
(taps, swipes, typed text) pass through boootie's relay on Cloudflare, which forwards them in
memory without storing or logging them. boootie stores a random phone id, SHA-256 hashes of the
phone's key and link, and the registration date. Cloudflare request logs record time, path and
status; the path includes the phone id and link secret. If any of this changes, update both the
policy and these answers before submitting.

## URLs (App Information page)

| Field | Value |
|---|---|
| Privacy Policy URL | https://boootie.com/privacy |
| Support URL | https://boootie.com/support |
| Marketing URL (optional) | https://boootie.com |

## App Privacy questionnaire ("nutrition label")

**Do you or your third-party partners collect data from this app?** Yes.

Apple counts data as "collected" when it leaves the device and is kept longer than needed to
serve the request in real time. Data the user sends to their own AI provider through the app
still has to be declared, because the app transmits it.

| Data type (Apple's category) | Collected? | Linked to the user? | Used for tracking? | Purpose |
|---|---|---|---|---|
| User Content → Photos or Videos (screenshots, forwarded to the user's AI provider, which keeps them) | Yes | No | No | App Functionality |
| User Content → Other User Content (text the assistant types on the phone) | Yes | No | No | App Functionality |
| Identifiers → Device ID (random phone id, stored with hashed keys) | Yes | No | No | App Functionality |
| Contact Info, Location, Financial Info, Browsing History, Contacts, Health, Audio, Diagnostics | No | | | |

- **Tracking:** No. boootie does not link data with third-party data for advertising and does
  not share it with data brokers, so the app does **not** need the App Tracking Transparency
  prompt.
- **Pre-order payments:** they happen on boootie.com through Stripe, not in the app, so they are
  not part of the app's label. If you later sell inside the app, add Financial Info and
  Contact Info (Name, Email).
- **Account:** if the app ever has user accounts, Apple requires an in-app way to delete the
  account (guideline 5.1.1(v)). Today deletion is by email, as the policy says.

## Things that must stay true for the policy to be accurate

- The phone sends a screenshot only when the assistant asks, and only while casting.
- The relay never writes screenshots or typed text to storage or logs.
- Only hashes of the phone's key and link are stored.
- Link to https://boootie.com/privacy from inside the app (settings or onboarding).
- Recommended: move the link secret out of the request path (for example into a header), so
  Cloudflare's request logs no longer contain it in plain text. Then update the "Request logs"
  paragraph in the policy.

## Before submitting

1. Make sure the contact mailbox in `site.config.json` receives mail.
2. Re-read the policy against how the finished app actually behaves.
3. Have it reviewed by a Swiss lawyer or privacy advisor; this draft is not legal advice.
