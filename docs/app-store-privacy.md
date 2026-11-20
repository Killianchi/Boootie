# App Store Connect: privacy setup for boootie

Answers below match the policy at https://boootie.com/privacy. They assume the data flow
described there: screenshots and requests go straight from the phone to the AI provider the
user connects, and boootie runs no server that sees them. If that changes, update both the
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
| User Content → Photos or Videos (screenshots) | Yes | No | No | App Functionality |
| User Content → Audio Data (voice requests, if offered) | Yes | No | No | App Functionality |
| User Content → Other User Content (typed requests) | Yes | No | No | App Functionality |
| Identifiers → Device ID (device serial for pairing and updates) | Yes | No | No | App Functionality |
| Diagnostics → Crash Data, Performance Data (opt-in only) | Yes | No | No | App Functionality |
| Contact Info, Location, Financial Info, Browsing History, Contacts, Health | No | | | |

- **Tracking:** No. boootie does not link data with third-party data for advertising and does
  not share it with data brokers, so the app does **not** need the App Tracking Transparency
  prompt.
- **Pre-order payments:** they happen on boootie.com through Stripe, not in the app, so they are
  not part of the app's label. If you later sell inside the app, add Financial Info and
  Contact Info (Name, Email).
- **Account:** if the app ever has user accounts, Apple requires an in-app way to delete the
  account (guideline 5.1.1(v)). The policy already promises *Settings → Delete my data*.

## Things the app itself must do to match the policy

- Ask for screen and microphone access with clear permission text (Info.plist usage strings),
  for example: "boootie uses the microphone so you can say what you want it to do."
- Only capture the screen while a task the user started is running, and show that a task is
  running with a way to stop it.
- Store AI access keys in the iOS Keychain.
- Offer *Settings → Delete my data* that clears task history and disconnects the AI provider.
- Ship diagnostics off by default, with an opt-in switch.
- Link to https://boootie.com/privacy from inside the app (Settings or onboarding).

## Before submitting

1. Fill in `legalName`, `legalAddress` and `contactEmail` in `site.config.json`, make sure the
   mailbox receives mail, then rebuild and deploy. The pages show placeholders until then.
2. Re-read the policy against how the finished app actually behaves.
3. Have it reviewed by a Swiss lawyer or privacy advisor; this draft is not legal advice.
