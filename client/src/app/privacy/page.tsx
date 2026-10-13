import type { Metadata } from "next";
import {
  LegalPage,
  Section,
  List,
  COMPANY,
  CONTACT_EMAIL,
  SERVICE_NAME,
  SERVICE_URL,
} from "@/components/legal/LegalPage";

export const metadata: Metadata = {
  title: `Privacy Policy - ${SERVICE_NAME}`,
  description: `How ${COMPANY} handles data in ${SERVICE_NAME}.`,
};

export default function PrivacyPage() {
  return (
    <LegalPage title="Privacy Policy">
      <p>
        {SERVICE_NAME} ({SERVICE_URL}) is an integration gateway that lets AI agents and
        applications connect to third-party apps and run actions on a user&apos;s behalf. It is
        operated by {COMPANY} (&quot;we&quot;, &quot;us&quot;). This policy explains what data
        the service handles and how we protect it.
      </p>

      <Section heading="1. Information we handle">
        <List
          items={[
            <>
              <strong>Connected-account credentials.</strong> When you connect a third-party
              account (for example Google, Microsoft, GitHub, Slack, Notion or Linear), we receive
              OAuth access and refresh tokens, or API keys you provide, for that account.
            </>,
            <>
              <strong>Connection metadata.</strong> The provider name, a connection name you
              choose, basic account identity information returned by the provider (such as a
              username or email address) and connection status.
            </>,
            <>
              <strong>Action activity.</strong> When an agent runs an action, we keep a run record:
              action name, status, timing, which token made the call, and bounded, redacted
              summaries of the input and output.
            </>,
            <>
              <strong>Access tokens for this service.</strong> Only a one-way hash of each runtime
              token is stored, plus its name, permissions and last-used time.
            </>,
            <>
              <strong>Technical logs.</strong> Our web server records IP address, request path,
              user agent and timestamps for security and troubleshooting.
            </>,
          ]}
        />
      </Section>

      <Section heading="2. How we use it">
        <p>
          We use this information only to provide the service: to authorize connections, refresh
          expired tokens, execute the actions you or your agents request, show you activity
          history, and keep the service secure and reliable. We do not sell personal data, and we
          do not use it for advertising.
        </p>
      </Section>

      <Section heading="3. Data obtained from Google APIs">
        <p>
          {SERVICE_NAME}&apos;s use and transfer to any other app of information received from
          Google APIs will adhere to the{" "}
          <a
            className="underline"
            href="https://developers.google.com/terms/api-services-user-data-policy"
          >
            Google API Services User Data Policy
          </a>
          , including the Limited Use requirements. In particular, we use Google user data only to
          provide or improve user-facing features the user requested; we do not transfer it to
          others except as needed to provide those features, to comply with law, or as part of a
          merger or sale with notice; we do not use it for serving advertisements; and we do not
          allow humans to read it unless you give consent for specific data, it is necessary for
          security or abuse investigation, or the law requires it.
        </p>
      </Section>

      <Section heading="4. Security">
        <List
          items={[
            "Provider credentials are encrypted at rest with AES-256-GCM. The encryption key is stored separately from the database.",
            "All traffic to the service uses HTTPS.",
            "Tokens and secrets are not returned in API responses or written to run logs.",
            "Outbound requests are restricted to public internet destinations.",
            "No system is perfectly secure, and we cannot guarantee absolute security.",
          ]}
        />
      </Section>

      <Section heading="5. Sharing and service providers">
        <p>
          We share data with a third-party provider only when you or your agent asks an action to
          run against that provider&apos;s API, and then only what the action needs. The service is
          hosted on Amazon Web Services. We may disclose information if required by law or to
          protect the rights, safety or security of users or the service.
        </p>
      </Section>

      <Section heading="6. Retention and deletion">
        <p>
          Connection credentials are kept while a connection is active. You can disconnect or
          delete a connection at any time, which removes its stored credentials. You can also
          revoke our access from the third-party provider&apos;s own account settings. To request
          deletion of other data we hold about you, email{" "}
          <a className="underline" href={`mailto:${CONTACT_EMAIL}`}>
            {CONTACT_EMAIL}
          </a>
          . Backups and security logs may persist for a limited period before they are overwritten.
        </p>
      </Section>

      <Section heading="7. Your choices and rights">
        <p>
          You may request access to, correction of, or deletion of your personal data, and you may
          withdraw consent to a connection at any time. Contact us at the address below and we
          will respond as required by applicable law.
        </p>
      </Section>

      <Section heading="8. Children">
        <p>The service is not directed to children under 18, and we do not knowingly collect their data.</p>
      </Section>

      <Section heading="9. Changes">
        <p>
          We may update this policy. The date at the top shows the latest revision, and material
          changes will be reflected on this page.
        </p>
      </Section>

      <Section heading="10. Contact">
        <p>
          {COMPANY}
          <br />
          Email:{" "}
          <a className="underline" href={`mailto:${CONTACT_EMAIL}`}>
            {CONTACT_EMAIL}
          </a>
        </p>
      </Section>
    </LegalPage>
  );
}
