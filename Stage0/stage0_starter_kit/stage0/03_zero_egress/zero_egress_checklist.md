# Stage 0 — Zero-Egress Verification

Gate this satisfies (Stage table, row 0): "static/dynamic network analysis for
zero data egress" -> "Gate: zero egress confirmed."

**Read this first — the original version of this checklist tested the wrong
thing.** It checked for "zero requests, full stop," but the paper's Section
3.1 doesn't actually claim that: it claims zero *raw data* egress except one
narrow, consented exception at Tier 3. Those are different claims, and
testing the wrong one would either produce a false "fail" the day someone
correctly triggers Tier 3 in testing, or quietly let real behavioral data
leak through inside what looks like a legitimate Tier 3 call.

## The architecture decision that resolves this — make it now, before you build

The paper's current wording ("only a pre-formatted alert") is ambiguous
about *how* that alert leaves the device. There are two ways to build Tier
2/3 delivery, and they lead to two different testable claims:

- **Option 1 — Sentinel sends it directly** (an in-app network/API call to
  place the call or send the message). Now "zero egress" genuinely has an
  exception, and verification has to inspect the *content* of that one
  request every time it fires, not just count requests.
- **Option 2 — Sentinel hands off via OS intent** (`Intent.ACTION_DIAL` for
  the Tele MANAS/emergency call, `Intent.ACTION_SENDTO` or a WhatsApp share
  intent for the pre-designated-contact message) and a human taps send/call
  in the *system* dialer or messaging app. Sentinel's own process never
  touches the network, ever, at any tier — the receiving app does, using
  its own already-encrypted transport (WhatsApp's E2E, the carrier's voice
  channel), not a channel Sentinel built. "A human places the call, not
  Sentinel" — already the paper's own stated principle for the call path —
  extends cleanly to "a human sends the message, not Sentinel" for text.

**Recommendation: build Option 2.** It's both the stronger claim (literally
zero network permission requested, not "zero except one audited exception")
and the simpler one to verify (Option A below works exactly as originally
written, with no content-inspection step needed). It also resolves a loose
word in the paper worth tightening either way: "encrypted context message"
currently reads as if Sentinel does its own cryptography, when handing off
to WhatsApp's share intent gets you transport encryption for free, from a
channel a reviewer can name and trust rather than a custom scheme you'd
have to justify.

If Option 1 turns out to be necessary for some reason not yet identified,
Option A's pass criterion below needs one more line: capture the payload of
any Tier 2/3-triggered request and confirm it contains only the pre-approved
template + minimal routing metadata (contact name, tier label, phone
number) — never raw sensor data, EMA transcript text, or conversation
history. Content, not just count.

## Option A — dynamic check with mitmproxy (do this one; ~30 min setup)

1. Install mitmproxy on your dev machine: `pip install mitmproxy`
2. Run `mitmweb` (opens a local proxy + web UI at localhost:8081)
3. On the Android emulator or a real test device connected via `adb`, set the
   Wi-Fi proxy to your machine's IP : 8080, and install mitmproxy's CA cert
   on the device (mitmproxy serves it at `mitm.it` once the proxy is active)
   so HTTPS traffic can be inspected, not just blocked.
4. Install and run the Sentinel stub app. Exercise every screen: the EMA
   check-in, a Tier 1/2 nudge, **and deliberately trigger a Tier 3 event**
   using the "Critical" test path — don't just test the quiet-state app,
   test the one moment traffic would be most justified if it were going to
   appear at all.
5. Watch the mitmweb traffic log for the *entire session*, Tier 3 included.
   - **Pass (if built as Option 2 above)**: zero requests originate from
     Sentinel's package, including during and after the Tier 3 trigger —
     the dialer/WhatsApp intent fires and *those* apps generate traffic
     under *their own* package, which is expected and fine to see in the
     proxy log; Sentinel's own package should show nothing.
   - **Pass (if built as Option 1)**: zero requests outside the single Tier
     3 moment, and that request's body contains only the approved template
     fields — check this every time you re-test, not once.
   - Requests from the OS or other background apps are expected noise —
     filter by package name (`adb shell dumpsys netstats detail` also shows
     per-UID bytes if you want a second, non-proxy confirmation).

## Option B — static check (do this too, it's cheap and catches a different class of bug)

1. Confirm the `AndroidManifest.xml` does **not** declare the `INTERNET`
   permission at all. With Option 2 above, this isn't a stretch goal
   anymore — it's the actual achievable target, since intent handoffs don't
   require the calling app to hold the permission the receiving app uses.
   No permission = no sockets, full stop, and it's the single strongest
   claim available ("the OS structurally prevents it," not "we chose not
   to" or "we audited the one time it happens").
2. If `INTERNET` genuinely can't be avoided, grep the compiled APK for host
   strings instead of trusting the manifest:
   ```
   apktool d app-release.apk -o decoded
   grep -rEo "https?://[a-zA-Z0-9./?=_-]+" decoded/ | sort -u
   ```
   Every URL that shows up needs a one-line justification. Anything you can't
   justify is a bug, not a finding to explain away.
3. Run `./gradlew :app:dependencies` and skim for any SDK known to phone
   home by default (analytics/crash-reporting SDKs are the usual culprit —
   several popular ones do this even when you never call them directly).
   A model-update channel is not a justification for this permission
   either — Play Store app updates don't require the app's own runtime
   `INTERNET` permission; the Store handles distribution at the OS level.

## Scaling to Stage 1, 2, and 3 — what changes, honestly

**The mitmproxy approach above does not scale past Stage 0.** It requires
installing a debug CA certificate on the test device — reasonable for your
own dev phone or an emulator, not something you can ask a Stage 1 beta
cohort to do to their personal phones. What scales instead:

- **Automate Option B in CI.** Make the apktool/grep check (and a manifest
  permission check) run on every release build, failing the build if a new
  network endpoint or the `INTERNET` permission appears without an explicit
  sign-off. One verified APK, distributed to the whole beta cohort, is a
  stronger and more scalable claim than re-running a manual proxy check per
  user — you're verifying the artifact everyone runs, once, rigorously,
  instead of sampling behavior across devices you don't control.

- **There's a real tension in Stage 1's own method column worth resolving
  explicitly, not discovering during the beta.** The Stage table's Stage 1
  row calls for "real-world false-alarm rate" and "retention... tracked" —
  both of which require *some* signal to leave individual devices and
  aggregate somewhere a researcher can look at it. That's in direct tension
  with the zero-egress claim Stage 0 just spent this much effort confirming.
  Don't let that surface for the first time when a beta tester or a reviewer
  asks "wait, how do you know the false-alarm rate if nothing left the
  phone?" Resolve it now, in the paper: the clean answer is a distinct,
  separately-consented **beta telemetry mode** — off by default, describing
  explicitly to Stage 1 participants what minimal, aggregate, non-behavioral
  signal (e.g., "a Tier 2/3 alert fired" as a boolean count, not the content
  or the sensor data behind it) leaves the device and why — kept clearly
  apart from the zero-knowledge production posture the paper argues for
  everywhere else. That's a real design decision this project hasn't stated
  yet, and Stage 1 is where it stops being deferrable.

- **Stage 0's verification artifacts become Stage 2/3's documentation, not
  throwaway checks.** IRB review (required starting Stage 2, per the Stage
  table) will ask for exactly this kind of static/dynamic network evidence
  as part of a data-protection protocol. Keep dated, reproducible output
  from every Option A/B run — that's not extra work now, it's Stage 2's
  paperwork already done in advance.

## Writing this up for the paper

Section 5.1 currently says privacy claims are "treated as a Stage 0
validation target ... not an assumption embedded in the architecture
diagram." Once both checks above pass, that sentence gets to change from a
promise to a result. If you build Option 2 (recommended): "Static analysis
confirmed the application declares no INTERNET permission; dynamic analysis
across a full session, including a deliberately triggered Tier 3 event,
confirmed zero outbound requests originating from the application at any
tier." That's a strictly stronger sentence than what the paper currently
supports — worth the architecture decision above to earn it.
