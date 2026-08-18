# Pi RPC Extension UI Responses

Source: <https://pi.dev/docs/latest/rpc>

Pi extensions can request interaction through the RPC extension UI sub-protocol. A dialog request is emitted on stdout as `extension_ui_request`; the RPC client sends an `extension_ui_response` on stdin.

## Selecting an action

For a `select` request, respond with the option string and the request's matching `id`:

```json
{"type":"extension_ui_response","id":"uuid-1","value":"Allow"}
```

For example, an extension can ask whether to allow a dangerous command:

```json
{
  "type": "extension_ui_request",
  "id": "uuid-1",
  "method": "select",
  "title": "Allow dangerous command?",
  "options": ["Allow", "Block"],
  "timeout": 10000
}
```

The response's `id` must exactly match the request `id`. The supplied `value` should be one of the offered option strings.

## Confirming an action

For a `confirm` request, respond with a boolean:

```json
{"type":"extension_ui_response","id":"uuid-2","confirmed":true}
```

Use `false` to decline.

## Cancelling

Any dialog request can be dismissed with:

```json
{"type":"extension_ui_response","id":"uuid-3","cancelled":true}
```

The extension receives `undefined` for `select`, `input`, and `editor`; it receives `false` for `confirm`.

## Scope

Only dialog methods require a response:

- `select`
- `confirm`
- `input`
- `editor`

Fire-and-forget methods, including `notify`, `setStatus`, `setWidget`, `setTitle`, and `set_editor_text`, emit UI requests but do not expect a response.

If a dialog request contains `timeout`, Pi resolves it automatically with its default result when the timeout expires.
