import { RuntimeProvider } from "./assistantRuntime";
import { ChatThread } from "./components/ChatThread";

const warningBannerText =
  import.meta.env.VITE_WARNING_BANNER_TEXT?.trim() ?? "";

export function App() {
  const chatPanelClassName = [
    "chat-panel",
    warningBannerText ? "chat-panel-with-banner" : ""
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <RuntimeProvider>
      <main className="app-shell">
        <section
          className={chatPanelClassName}
          aria-label="Papyri assistant chat"
        >
          <header className="chat-header">
            <div>
              <h1>Papyri Assistant</h1>
              <p>assistant-ui frontend with a LangChain backend</p>
            </div>
            <span className="status-pill">Local</span>
          </header>
          {warningBannerText && (
            <div className="warning-banner" role="alert">
              {warningBannerText}
            </div>
          )}
          <ChatThread />
        </section>
      </main>
    </RuntimeProvider>
  );
}
