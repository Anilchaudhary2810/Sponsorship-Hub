# SponsorHub -> SponsorPitch-Level Scale Plan (India)

## 1) Target Positioning
SponsorHub should position itself as an India-first sponsorship operating system:
- One workflow for sponsors, organizers, and creators
- Trust-first execution (KYC, approvals, payments, audits)
- Measurable outcomes (closed deals, ROI, repeat partnerships)

## 2) Current Strengths You Already Have
- Multi-role marketplace and deal state transitions
- Proposal approvals, negotiations, and revenue milestones
- Trust profile and admin KYC review flow
- Reporting snapshots and exports
- Collaboration and lifecycle nudge modules

## 3) Gaps Before "Real" SponsorPitch-Level Product

### A. Simulated or partially real modules
1. Integrations are simulated payload responses, not real provider API/OAuth calls
   - `backend/routers/integrations.py:145`
2. Billing upgrades are marked `simulated` (plan changes occur without real payment capture)
   - `backend/routers/billing.py:143`
3. Payments use a development mock order fallback if gateway credentials are missing
   - `backend/routers/payments.py:63`
4. KYC input is URL-based document metadata only (no real upload/storage pipeline)
   - `backend/schemas.py:409`

### B. Inconvenient UX / ops friction
1. ScaleOps requires manual IDs in UI flows (approver user id, member user id, resource id)
   - `frontend/src/pages/ScaleOpsPage.jsx:648`
   - `frontend/src/pages/ScaleOpsPage.jsx:861`
   - `frontend/src/pages/ScaleOpsPage.jsx:891`
2. No built-in matching engine for sponsor-event-creator fit
   - `docs/project_context.txt:3`
3. Plan limits are defined but not enforced in create flows
   - `backend/routers/billing.py:10` (definitions used for usage/display only)

### C. Over-features for early stage (should be staged)
1. Too many advanced modules exposed before core activation loop is optimized
2. Internal power tools in one heavy page (`ScaleOpsPage`) can overwhelm regular users
3. Multiple integration provider options are visible even though only export-style paths are truly functional

## 4) Product Focus Model (What to prioritize)
Use one north-star loop:
1. User signs up
2. User publishes opportunity
3. User sends/receives first deal
4. Deal reaches payment + signature + close
5. User sees proof/report and starts next deal

Every feature should improve this loop's speed, trust, or conversion.

## 5) Execution Roadmap

## Phase 0 (Week 0-2): Reliability and Launch Safety
- Fix payment amount capture before order creation (`DealCreate` flow)
- Remove insecure client-supplied identity fields from create payloads
- Enforce plan limits in event/campaign/deal create routes
- Add password-strength validation to reset-password path
- Keep landing page + signup + first-deal flow extremely clear

Exit criteria:
- First deal can complete from proposal -> payment -> signature -> close in production config.

## Phase 1 (Week 3-6): Real Money and Trust
- Integrate real Razorpay subscription or checkout for plan upgrades
- Keep webhook verification strict across environments
- Build KYC file upload pipeline (S3/Cloudinary), not only URL input
- Add audit trail views for support/admin resolution

Exit criteria:
- Paid upgrade actually charges users.
- KYC submissions contain verifiable uploaded files.

## Phase 2 (Week 7-12): Growth Engine for India
- Public discovery pages for events/campaigns (SEO + shareability)
- Role-based onboarding checklist to first deal
- City-focused launch playbook (Bengaluru -> Mumbai -> Delhi NCR)
- Campus/event committee partnerships + agency pilot cohort

Exit criteria:
- Measurable activation lift and repeat deal creation from early cohorts.

## Phase 3 (Month 4-6): SponsorPitch-Level Capability
- Matching/recommendation engine v1 (budget, niche, location, audience fit)
- Real integrations: pick 1-2 first (Slack + HubSpot) and execute deeply
- Contract/PDF and GST-friendly invoice workflow
- Workspace collaboration via email invite flow (remove ID-based UX)

Exit criteria:
- Teams can run repeatable sponsor pipelines with minimal manual coordination.

## Phase 4 (Month 7-12): Scale and Defensibility
- Mobile-first ops experience or PWA
- Partner scoring and trust reputation improvements
- Performance and observability for higher traffic and ops load
- Enterprise controls for agencies and large sponsors

## 6) Suggested GTM in India
1. Beachhead: college fests + startup events (high sponsorship turnover)
2. Second wedge: creator agencies and influencer campaign managers
3. Sponsor acquisition: city brand partners + category-led outreach (fintech, edtech, D2C)
4. Pricing: free for discovery, paid for advanced execution + team + reporting

## 7) KPI Dashboard to Track Weekly
- Activation: signup -> first opportunity published (% and median hours)
- Conversion: opportunities -> first deal created -> first closed deal
- Trust: % of KYC approved profiles, dispute rate, payment success rate
- Revenue: paid conversion rate, MRR, expansion revenue
- Retention: 30-day active teams, repeat deal rate, sponsor repeat rate

## 8) What To Defer (until core loop is strong)
- Broad multi-provider integration matrix
- Deep enterprise customizations
- Too many parallel workflow modules in primary user navigation

Rule: if a feature does not improve first-deal conversion, trust, or repeat usage, defer it.
