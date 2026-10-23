import React from "react";
import Link from "next/link";
import { ShieldCheck, Lock, ArrowLeft, ExternalLink, Trash2, EyeOff } from "lucide-react";

export const metadata = {
  title: "Privacy Policy - ConnectorHub",
  description: "ConnectorHub Privacy Policy and Google API Services User Data Policy Compliance.",
};

export default function PrivacyPolicyPage() {
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
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-medium mb-3">
            <ShieldCheck size={14} />
            Privacy & Security First
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-zinc-900">Privacy Policy</h1>
          <p className="mt-2 text-sm text-zinc-600">
            Last Updated: October 2026 • Effective Date: October 2026
          </p>
        </div>

        {/* Content Body */}
        <div className="prose prose-zinc max-w-none text-sm leading-relaxed space-y-8 text-zinc-700">
          {/* Section: Overview */}
          <section>
            <h2 className="text-lg font-semibold text-zinc-900 mb-2">1. Overview</h2>
            <p>
              ConnectorHub (&quot;we&quot;, &quot;our&quot;, or &quot;us&quot;), operated by SuparAgent, is an integration
              gateway that enables authorized AI agents and developers to connect safely to external APIs and tools.
              This Privacy Policy explains how we collect, store, handle, and protect your information when you connect
              third-party services (including Google Workspace, Microsoft 365, GitHub, Slack, and other supported tools)
              to ConnectorHub.
            </p>
          </section>

          {/* Section: Mandatory Google Limited Use Disclosure */}
          <section className="p-6 rounded-xl bg-blue-50/70 border border-blue-200 text-blue-950">
            <div className="flex items-start gap-3">
              <Lock className="text-blue-600 mt-0.5 shrink-0" size={20} />
              <div>
                <h2 className="text-base font-semibold text-blue-900 mb-2">
                  Google API Services User Data Policy (Limited Use Disclosure)
                </h2>
                <p className="text-blue-900 leading-relaxed font-medium mb-3">
                  ConnectorHub&apos;s use and transfer to any other app of information received from Google APIs will
                  adhere to the{" "}
                  <a
                    href="https://developers.google.com/terms/api-services-user-data-policy"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline text-blue-800 hover:text-blue-950 inline-flex items-center gap-0.5"
                  >
                    Google API Services User Data Policy
                    <ExternalLink size={12} />
                  </a>
                  , including the Limited Use requirements.
                </p>
                <ul className="list-disc pl-5 space-y-1.5 text-xs text-blue-800">
                  <li>
                    <strong>Purpose-Specific Access:</strong> Google Workspace user data (Gmail, Google Drive, Google
                    Sheets, Google Calendar) is accessed exclusively to execute explicit, user-initiated actions requested
                    by your configured AI agents or workflows.
                  </li>
                  <li>
                    <strong>No Advertising or Sale:</strong> We never sell Google user data, transfer it to data brokers,
                    or use it for serving advertisements.
                  </li>
                  <li>
                    <strong>No Generalized AI Training:</strong> Information received through Google Workspace APIs is
                    never used to train generalized machine learning or artificial intelligence models without your
                    explicit affirmative consent.
                  </li>
                  <li>
                    <strong>Human Access Restrictions:</strong> Human employees or contractors do not read or view your
                    Google Workspace data unless you have given explicit permission for troubleshooting, it is necessary
                    for security investigations, or required by law.
                  </li>
                </ul>
              </div>
            </div>
          </section>

          {/* Section: Information We Access and Process */}
          <section>
            <h2 className="text-lg font-semibold text-zinc-900 mb-2">2. Information We Access and Process</h2>
            <p className="mb-3">
              When you connect an account to ConnectorHub, we access only the scopes and data strictly necessary to fulfill
              the actions you authorize:
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 rounded-lg border border-zinc-200 bg-white">
                <h3 className="font-semibold text-zinc-900 mb-1">OAuth Credentials & Tokens</h3>
                <p className="text-xs text-zinc-600">
                  Access tokens and refresh tokens granted during the OAuth handshake. All tokens are encrypted at rest
                  using industry-standard AES-256-GCM.
                </p>
              </div>
              <div className="p-4 rounded-lg border border-zinc-200 bg-white">
                <h3 className="font-semibold text-zinc-900 mb-1">Live Action Data</h3>
                <p className="text-xs text-zinc-600">
                  Data retrieved dynamically upon action execution (e.g., email threads, spreadsheet rows, calendar
                  events, drive files). Data is proxied in-memory and not permanently harvested.
                </p>
              </div>
            </div>
          </section>

          {/* Section: How Data is Stored & Encrypted */}
          <section>
            <h2 className="text-lg font-semibold text-zinc-900 mb-2">3. Data Security & Storage</h2>
            <p className="mb-2">We apply robust enterprise security standards to protect your data:</p>
            <ul className="list-disc pl-5 space-y-1 text-zinc-600">
              <li>
                <strong>AES-256-GCM Encryption:</strong> All sensitive credentials, OAuth tokens, and secrets are
                encrypted at rest with per-record authentication tags.
              </li>
              <li>
                <strong>Multi-Tenant Isolation:</strong> Connections and execution contexts are strictly segmented by
                tenant ID and cryptographically partitioned.
              </li>
              <li>
                <strong>SSRF Protection & Address Pinning:</strong> Outbound API calls pass through guarded transports
                preventing internal network egress and DNS rebinding attacks.
              </li>
              <li>
                <strong>TLS 1.3 in Transit:</strong> All communications between your browser, our servers, and upstream
                API endpoints are encrypted with TLS 1.3.
              </li>
            </ul>
          </section>

          {/* Section: User Rights, Revocation & Deletion */}
          <section>
            <h2 className="text-lg font-semibold text-zinc-900 mb-2">4. Your Control, Revocation, and Deletion</h2>
            <p className="mb-3">You maintain complete, real-time control over your connections and data:</p>
            <div className="p-4 rounded-lg border border-zinc-200 bg-white space-y-3">
              <div className="flex items-start gap-2.5">
                <Trash2 size={16} className="text-rose-600 mt-0.5 shrink-0" />
                <div>
                  <h4 className="font-medium text-zinc-900 text-xs">Disconnecting in ConnectorHub</h4>
                  <p className="text-xs text-zinc-600">
                    You can delete any connection at any time directly from the Connections page. Deleting a connection
                    immediately and permanently purges its encrypted access tokens and refresh tokens from our database.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-2.5">
                <EyeOff size={16} className="text-zinc-600 mt-0.5 shrink-0" />
                <div>
                  <h4 className="font-medium text-zinc-900 text-xs">Revoking Access via Provider Settings</h4>
                  <p className="text-xs text-zinc-600">
                    You can unilaterally revoke ConnectorHub&apos;s authorization at any time directly from your provider&apos;s
                    security dashboard (e.g.,{" "}
                    <a
                      href="https://myaccount.google.com/permissions"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline text-zinc-800"
                    >
                      Google Account Third-Party Permissions
                    </a>
                    ).
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Section: Contact */}
          <section className="border-t border-zinc-200 pt-6">
            <h2 className="text-lg font-semibold text-zinc-900 mb-2">5. Contact Information</h2>
            <p>
              If you have any questions, privacy requests, or security inquiries regarding this policy or ConnectorHub,
              please contact our security team at:
            </p>
            <p className="mt-2 font-mono text-xs text-zinc-800">
              Email: <strong>privacy@suparagent.ai</strong> • Support: <strong>support@suparagent.ai</strong>
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
