import { Icon } from "@/lib/icons";

export function Toast({
  message,
  kind = "success",
}: {
  message: string;
  kind?: "success" | "error";
}) {
  return (
    <div className={`toast ${kind === "error" ? "error" : ""}`}>
      <span className="t-ic">
        <Icon name={kind === "error" ? "close" : "check"} size={12} strokeWidth={2.6} />
      </span>
      {message}
    </div>
  );
}
