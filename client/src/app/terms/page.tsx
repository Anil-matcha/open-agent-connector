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
  title: `Terms of Service - ${SERVICE_NAME}`,
  description: `Terms for using ${SERVICE_NAME}, operated by ${COMPANY}.`,
};

export default function TermsPage() {
  return (
    <LegalPage title="Terms of Service">
      <p>
        These terms govern your use of {SERVICE_NAME} ({SERVICE_URL}), operated by {COMPANY}{" "}
        (&quot;we&quot;, &quot;us&quot;). By using the service you agree to them. If you do not
        agree, do not use the service.
      </p>

      <Section heading="1. The service">
        <p>
          {SERVICE_NAME} lets you connect third-party accounts and allows AI agents and
          applications you authorize to discover and run actions against those accounts. We may
          change, suspend or discontinue features at any time.
        </p>
      </Section>

      <Section heading="2. Your account and credentials">
        <List
          items={[
            "You must have the right to connect every third-party account you add, and you are responsible for activity performed with your tokens and connections.",
            "Keep access tokens confidential. Revoke any token you believe is compromised.",
            "Grant agents only the permissions they need. Actions run with the access of the account you connected.",
          ]}
        />
      </Section>

      <Section heading="3. Third-party services">
        <p>
          Connected providers (for example Google, Microsoft, GitHub, Slack, Notion and Linear)
          are independent services governed by their own terms and policies, which you must follow.
          We are not responsible for third-party services, their availability, or changes to their
          APIs, and a provider may limit or revoke access at its discretion.
        </p>
      </Section>

      <Section heading="4. Acceptable use">
        <p>You agree not to:</p>
        <List
          items={[
            "break the law or violate a third party's rights or terms through the service;",
            "send spam or unsolicited bulk messages, or harass others;",
            "attempt to access data or accounts you are not authorized to use;",
            "probe, disrupt, overload or bypass the security or rate limits of the service;",
            "use the service to reach private or internal network resources, or to build a competing service from it by scraping or reverse engineering.",
          ]}
        />
        <p>We may suspend or terminate access that violates these terms or threatens the service.</p>
      </Section>

      <Section heading="5. Privacy">
        <p>
          Our{" "}
          <a className="underline" href="/privacy">
            Privacy Policy
          </a>{" "}
          explains how data is handled and forms part of these terms.
        </p>
      </Section>

      <Section heading="6. Availability and no warranty">
        <p>
          The service is provided &quot;as is&quot; and &quot;as available&quot;, without
          warranties of any kind, express or implied, including merchantability, fitness for a
          particular purpose and non-infringement. We do not guarantee that the service will be
          uninterrupted, error-free, or that every action will succeed against every provider.
        </p>
      </Section>

      <Section heading="7. Limitation of liability">
        <p>
          To the maximum extent permitted by law, {COMPANY} will not be liable for indirect,
          incidental, special, consequential or punitive damages, or for loss of data, profits or
          revenue, arising from your use of the service. Our total liability for any claim is
          limited to the amount you paid us for the service in the three months before the claim,
          or INR 1,000 if you paid nothing.
        </p>
      </Section>

      <Section heading="8. Termination">
        <p>
          You may stop using the service and delete your connections at any time. We may suspend or
          end your access at any time, including for breach of these terms.
        </p>
      </Section>

      <Section heading="9. Changes to these terms">
        <p>
          We may update these terms. Continued use after an update means you accept the revised
          terms.
        </p>
      </Section>

      <Section heading="10. Governing law">
        <p>
          These terms are governed by the laws of India. Courts in India have jurisdiction over
          disputes arising from them.
        </p>
      </Section>

      <Section heading="11. Contact">
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
