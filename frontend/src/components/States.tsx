export function LoadingState({
  label = "Cargando",
  fullPage = false,
}: {
  label?: string;
  fullPage?: boolean;
}) {
  return (
    <div className={fullPage ? "state state--page" : "state"} role="status">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({
  title = "No hay registros",
  detail = "Los datos que cumplan los criterios aparecerán aquí.",
}: {
  title?: string;
  detail?: string;
}) {
  return (
    <div className="empty-state">
      <span className="empty-state__mark" aria-hidden="true" />
      <strong>{title}</strong>
      <p>{detail}</p>
    </div>
  );
}

export function Feedback({
  message,
  tone = "info",
  onClose,
}: {
  message: string;
  tone?: "success" | "error" | "info";
  onClose?: () => void;
}) {
  if (!message) return null;
  return (
    <div className={`feedback feedback--${tone}`} role={tone === "error" ? "alert" : "status"}>
      <span>{message}</span>
      {onClose ? (
        <button type="button" className="icon-button" onClick={onClose} aria-label="Cerrar mensaje">
          ×
        </button>
      ) : null}
    </div>
  );
}
