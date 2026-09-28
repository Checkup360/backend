# Privacy Policy

> **STATUS: DRAFT — PENDING LEGAL REVIEW**
> **Document Type:** `PRIVACY_POLICY`
> **Version:** `1.0.0-draft`
> **Applicable Legal Framework:** Argentine Personal Data Protection Act (Law No. 25.326), Regulatory Decree 1558/2001, and guidelines of the Agency of Access to Public Information (AAIP).

---

## 1. Data Controller Information

- **Controller:** Checkup360 Platform Operator / Sponsoring Organization
- **Contact:** privacy@checkup360.com
- **Purpose of Processing:** Preventive health assessments, workplace wellness analytics, occupational risk calculation, and organizational health trends.

---

## 2. Categories of Data Collected

Checkup360 processes the following categories of data:

1. **Identifying & Contact Data:** First name, last name, email address, phone number, profile photo, and date of birth.
2. **Employment Data:** Organization membership, assigned department, organizational roles, and onboarding status.
3. **Sensitive Health Data (Law 25.326, Art. 2):**
   - **Anthropometric & Physical Metrics:** Biological sex, height, weight, waist circumference, neck circumference.
   - **Vital Signs & Laboratory Indicators:** Systolic/diastolic blood pressure, fasting glucose, total cholesterol, HDL cholesterol, triglycerides, prescribed medications (hypertension, statins, glucose-lowering drugs).
   - **Lifestyle & Behavioral Habits:** Physical activity, nutritional habits, smoking status, alcohol consumption patterns (AUDIT-C).
   - **Sleep & Musculoskeletal Symptoms:** Snoring, daytime fatigue, observed apnea, localized musculoskeletal pain (Nordic Questionnaire).
   - **Mental Health & Emotional Well-being:** Depressive symptoms (PHQ-9 items, including mood, interest, sleep trouble, appetite, psychomotor changes, and thoughts of self-harm), perceived stress (PSS-10).

---

## 3. Legal Basis for Processing

- **Explicit Consent (Law 25.326, Art. 5 & Art. 7):** Health data is classified as sensitive data and is processed exclusively upon your free, express, and informed consent.
- **Specific Purpose:** Data is collected solely for preventive health evaluation, calculating standardized epidemiological scores, and presenting indicators to you and authorized organizational administrators.

---

## 4. Dual Persistence & Data Storage

To ensure both real-time user experience and auditable clinical history:
1. **Current Health Snapshot (`member_health_data`):** Holds the most recent state of your biometric and clinical indicators.
2. **Historical Submissions Log (`assessment_submissions`):** Append-only audit record of each questionnaire submitted, with timestamp and the specific version under which consent was granted.
3. **Computed Risk Indicators (`risk_scores` & `member_overall_scores`):** Stored results including score values, risk levels, and attention flags.

---

## 5. Data Sharing & Visibility (Employer / Organization Admins)

- **Organization Admins:** Designated administrators of your Organization have access to your calculated wellness scores, risk levels, participation status, and granular questionnaire submissions.
- **Third-Party Service Providers:**
  - **Google LLC:** Authentication and identity confirmation via Google OAuth 2.0. Health data is never transmitted to Google.
  - **Email Delivery Services (e.g., Resend / SMTP):** Transmits transactional account invitations and password reset links.
  - **Calculation Engine:** An internal, stateless computing engine evaluates risk equations in-memory without persistent data storage.

---

## 6. International Data Transfers

Certain infrastructure and communication tools (e.g., Google OAuth, Resend email delivery) process data on servers located outside the Argentine Republic (principally in the United States). By consenting to this Policy, you expressly authorize such international transfers required for platform functionality under appropriate contractual safeguards.

---

## 7. Data Subject Rights (ARCO)

Under Law No. 25.326, you hold the following rights:
1. **Right of Access (Art. 14):** Request information regarding your personal and health data stored in the Platform.
2. **Right to Rectification & Update (Art. 16):** Update or correct inaccurate or incomplete health and personal data directly via your profile or support.
3. **Right to Revoke Consent & Erasure (Art. 16):** You may revoke consent for any specific health questionnaire at any time. Revocation blocks future processing and data submissions for that form while retaining historical audit records in append-only storage for clinical traceability.

To exercise your statutory rights, contact: privacy@checkup360.com.

> The Agency of Access to Public Information (AAIP), in its capacity as regulatory authority under Law No. 25.326, has the power to attend to complaints and claims filed by data subjects whose rights are affected by non-compliance with data protection regulations.
