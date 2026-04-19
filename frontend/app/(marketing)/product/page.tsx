import { MarketingPage } from "@/components/marketing/MarketingPage";
export default function Page() {
  return <MarketingPage title="Product" subtitle="A unified control plane for agent identities, approvals, policies, and runtime trust decisions." bullets={["Agent onboarding with blueprint-based approvals", "Centralized authorization decisions with policy context", "Audit trails and webhooks for downstream systems", "Lifecycle actions: suspend, rotate, expire, revoke"]} />;
}
