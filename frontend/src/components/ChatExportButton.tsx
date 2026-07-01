import {
  useAui,
  useAuiState,
  type ExportedMessageRepository,
  type ThreadMessage
} from "@assistant-ui/react";

type ExportableMessagePart = ThreadMessage["content"][number];

function exportRepositoryToMessages(
  repository: ExportedMessageRepository
): ThreadMessage[] {
  if (!repository.headId) {
    return repository.messages.map((item) => item.message);
  }

  const messagesById = new Map(
    repository.messages
      .filter((item) => item.message.id)
      .map((item) => [item.message.id as string, item])
  );
  const orderedMessages: ThreadMessage[] = [];
  const seenIds = new Set<string>();
  let currentId: string | null = repository.headId;

  while (currentId) {
    if (seenIds.has(currentId)) {
      return repository.messages.map((item) => item.message);
    }

    const currentItem = messagesById.get(currentId);
    if (!currentItem) {
      return repository.messages.map((item) => item.message);
    }

    seenIds.add(currentId);
    orderedMessages.push(currentItem.message);
    currentId = currentItem.parentId;
  }

  return orderedMessages.reverse();
}

function titleCaseRole(role: ThreadMessage["role"]) {
  return role.charAt(0).toUpperCase() + role.slice(1);
}

function formatMessagePart(part: ExportableMessagePart): string {
  if (part.type === "text") {
    return part.text ?? "";
  }

  if (part.type === "reasoning") {
    const reasoningText = part.text?.trim();

    return reasoningText ? `### Reasoning\n\n${reasoningText}` : "";
  }

  if ("text" in part && typeof part.text === "string") {
    return part.text;
  }

  return `\`\`\`json\n${JSON.stringify(part, null, 2)}\n\`\`\``;
}

function messagesToMarkdown(messages: ThreadMessage[]) {
  const exportedAt = new Date();
  const sections = messages
    .map((message) => {
      const content = message.content
        ?.map(formatMessagePart)
        .map((part) => part.trim())
        .filter(Boolean)
        .join("\n\n");

      if (!content) {
        return "";
      }

      return `## ${titleCaseRole(message.role)}\n\n${content}`;
    })
    .filter(Boolean);

  return [
    "# Papyri Assistant Chat",
    "",
    `Exported: ${exportedAt.toLocaleString()}`,
    "",
    ...sections
  ]
    .join("\n")
    .trimEnd()
    .concat("\n");
}

function downloadMarkdown(markdown: string) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const blob = new Blob([markdown], {
    type: "text/markdown;charset=utf-8"
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");

  anchor.href = url;
  anchor.download = `papyri-chat-${timestamp}.md`;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function ChatExportButton() {
  const aui = useAui();
  const isThreadEmpty = useAuiState((state) => state.thread.isEmpty);

  const handleExport = () => {
    const repository = aui.thread().export();
    const markdown = messagesToMarkdown(exportRepositoryToMessages(repository));

    downloadMarkdown(markdown);
  };

  return (
    <button
      aria-label="Export chat history"
      className="export-button"
      disabled={isThreadEmpty}
      onClick={handleExport}
      title="Export chat history"
      type="button"
    >
      <svg
        aria-hidden="true"
        fill="none"
        height="20"
        viewBox="0 0 24 24"
        width="20"
      >
        <path
          d="M12 3v11m0 0 4-4m-4 4-4-4M5 17v3h14v-3"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2"
        />
      </svg>
    </button>
  );
}
