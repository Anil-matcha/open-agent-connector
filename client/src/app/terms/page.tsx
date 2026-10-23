import React from "react";
import Link from "next/link";
import { FileText, ArrowLeft, Shield } from "lucide-react";

export const metadata = {
  title: "Terms of Service - ConnectorHub",
  description: "ConnectorHub Terms of Service and API usage guidelines.",
};

export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 font-sans selection:bg-zinc-200">
      <div className="max-w-4xl mx-auto px-6 py-12">
        {/* Navigation Back */}
        <Link
          href="/providers"
          className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-900 mb-8 transition-colors"
        >
          <ArrowLeft size={14} />
          Back to Platform
        </Link>

        {/* Header */}
        <div className="border-b border-zinc-200 pb-8 mb-8">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-zinc-100 border border-zinc-200 text-zinc-700 text-xs font-medium mb-3">
            <FileText size={14} />
            Service Terms & Agreement
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-zinc-900">Terms of Service</h1>
          <p className="mt-2 text-sm text-zinc-600">
            Last Updated: October 2026 • Effective Date: October 2026
          </p>
        </div>

        {/* Content Body */}
        <div className="prose prose-zinc max-w-none text-sm leading-relaxed space-y-8 text-zinc-700">
          <section>
            <h2 className="text-lg font-semibold text-zinc-900 mb-2">1. Acceptance of Terms</h2>
            <p>
              By accessing or using ConnectorHub (&quot;the Service&quot;), operated by SuparAgent, you agree to be bound
              by these Terms of Service. If you do not agree to all terms and conditions, you may not access or use the
              Service.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-zinc-900 mb-2">2. Description of the Service</h2>
            <p>
              ConnectorHub is a developer platform and API gateway enabling AI agents, applications, and workflows to
              connect and interact with third-party software services (such as Google Workspace, GitHub, Slack, and other
              API providers) through secure, authenticated connections.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-zinc-900 mb-2">3. Third-Party Integrations & Accounts</h2>
            <p className="mb-2">
              When connecting third-party services to ConnectorHub:
            </p>
            <ul className="list-disc pl-5 space-y-1 text-zinc-600">
              <li>
                You confirm that you possess the necessary administrative rights, authority, and permissions to connect
                the account.
              </li>
              <li>
                You agree to comply with all applicable terms of service and developer policies of the integrated
                providers (including the Google APIs Terms of Service and Google API Services User Data Policy).
              </li>
              <li>
                You acknowledge that ConnectorHub acts solely as an intermediary gateway; third-party service availability
                is governed by the respective providers.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-zinc-900 mb-2">4. Acceptable Use Policy</h2>
            <p className="mb-2">You agree not to use ConnectorHub to:</p>
            <ul className="list-disc pl-5 space-y-1 text-zinc-600">
              <li>Violate any local, national, or international laws or regulations.</li>
              <li>Circumvent rate limits, access controls, or security guards established by upstream providers.</li>
              <li>Transmit malicious software, unauthorized spam, or execute destructive denial-of-service operations.</li>
              <li>Exfiltrate or abuse user data outside the bounds of authorized agent execution.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-zinc-900 mb-2">5. Security & Credential Protection</h2>
            <p>
              We implement industry-grade security measures including AES-256-GCM encryption at rest, hop-by-hop SSRF
              protection, and TLS in transit. You are responsible for safeguarding your master access tokens, admin
              credentials, and preventing unauthorized delegation to third parties.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-zinc-900 mb-2">6. Limitation of Liability & Disclaimers</h2>
            <p>
              The Service is provided on an &quot;AS IS&quot; and &quot;AS AVAILABLE&quot; basis. In no event shall SuparAgent
              or ConnectorHub be liable for indirect, incidental, punitive, or consequential damages arising from upstream
              API downtime, revoked third-party credentials, or loss of access.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-zinc-900 mb-2">7. Termination & Account Deletion</h2>
            <p>
              You may terminate your use of the Service at any time by deleting your connections and access tokens in
              ConnectorHub. Upon deletion, all stored encrypted tokens and associated connection metadata are permanently
              expunged from our active database.
            </p>
          </section>

          <section className="border-t border-zinc-200 pt-6">
            <h2 className="text-lg font-semibold text-zinc-900 mb-2">8. Contact & Legal Inquiries</h2>
            <p>
              For legal inquiries, terms questions, or compliance documentation, please reach out to our legal team:
            </p>
            <p className="mt-2 font-mono text-xs text-zinc-800">
              Email: <strong>legal@suparagent.ai</strong> • Support: <strong>support@suparagent.ai</strong>
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
