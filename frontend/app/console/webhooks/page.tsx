import { PlaceholderPage } from "@/components/console/PlaceholderPage";
export default function Page() {
  return <PlaceholderPage title="Webhooks" subtitle="Manage event subscriptions, endpoint health, signing posture, and retry status." items={["Endpoint registration and subscription matrix", "Delivery history with response codes", "Retry/dead-letter placeholders", "Signing secret rotate workflow placeholder"]} />;
}
