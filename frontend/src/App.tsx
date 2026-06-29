import { RuntimeProvider } from "./assistantRuntime";
import { ChatThread } from "./components/ChatThread";

export function App() {
  return (
    <RuntimeProvider>
      <main className="app-shell">
        <section className="chat-panel" aria-label="Papyri assistant chat">
          <header className="chat-header">
            <div>
              <h1>Papyri Assistant</h1>
              <p>assistant-ui frontend with a LangChain backend</p>
            </div>
            <span className="status-pill">Local</span>
          </header>
          <ChatThread />
        </section>
      </main>
    </RuntimeProvider>
  );
}
