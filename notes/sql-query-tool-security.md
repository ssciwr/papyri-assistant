# Securing SQL submitted to an agent tool

_Scope: a LangChain/Deep Agents tool that receives SQL from an LLM or another web service and executes it against PostgreSQL. The SQL must be treated as untrusted code, even when the caller is an internal service._

## Recommended boundary

Do **not** make arbitrary SQL the normal service-to-service API. Prefer a typed, versioned query contract (for example `report_id`, approved filters, sort enum, page size) and have the database service construct the query with bound parameters. Parameter binding keeps data separate from SQL, while identifiers and sort directions must come from code or an explicit allow-list; escaping and keyword deny-lists are not adequate protections. [OWASP SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html) · [OWASP Input Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)

If free-form SQL is a required product feature, put one server-owned **query gateway** between the agent/MCP tool and the database:

```text
authenticated caller + user/tenant context
  -> query gateway: parse -> authorize AST -> bound values -> resource checks
  -> least-privilege read-only DB role / views / RLS
  -> bounded result + audit event
```

Authenticate the calling service over TLS (mTLS is appropriate for highly privileged services) and make an authorization decision on every request. For bearer tokens, validate the signature and at least issuer, audience, expiry, and not-before claims; derive the requested tenant and permissions from that verified identity, never from model-provided SQL or request fields. [OWASP REST Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html) · [OWASP Web Service Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Web_Service_Security_Cheat_Sheet.html)

## Gateway policy: parse and authorize structure, not text

Use a parser for the exact database dialect and reject a parse failure or more than one statement. Apply a positive policy to the parsed AST, then execute a newly rendered/parameterized query; regex checks, stripping semicolons, and an LLM “query checker” are not an authorization boundary.

For an initial read-only tool, reject every construct except a narrow `SELECT` subset. In particular reject DML/DDL, `COPY`, `CALL`, `DO`, transaction and session commands, data-modifying CTEs, `SELECT INTO`, locking clauses such as `FOR UPDATE`, unapproved functions/operators, unqualified names, and access to system schemas. Check nested subqueries and CTE bodies too. “Starts with SELECT” is insufficient: a CTE can contain writes and selectable functions can have effects or costly execution.

Allow only an explicit set of schema-qualified views (preferably) or tables and columns for each verified principal/capability. Also bound joins, nesting, page size and requested columns; inject/enforce a server maximum result limit through the AST rather than concatenating SQL. Bind all literal values through the driver. Return a small, typed result set and do not expose raw database errors to the caller.

This AST policy is an application design recommendation; it reduces accidental or surprising queries but does **not** replace database authorization. The database role remains the final containment boundary.

## PostgreSQL containment

Use a distinct non-owner, non-superuser agent role with only `CONNECT`, schema `USAGE`, and `SELECT` on the approved views/tables—no `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `CREATE`, role-management, `BYPASSRLS`, or broadly granted function execution. PostgreSQL grants object privileges per role, and a role without `BYPASSRLS` remains subject to row-security policies. [PostgreSQL `GRANT`](https://www.postgresql.org/docs/current/sql-grant.html) · [PostgreSQL role attributes](https://www.postgresql.org/docs/current/role-attributes.html) · [PostgreSQL row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)

Expose curated views that omit sensitive fields, and enforce tenant isolation with row-level security where applicable. Fix the role's `search_path` to trusted schemas and revoke `CREATE` on any schema searched by the role; PostgreSQL documents the risk of writable schemas masking objects. [PostgreSQL schemas and privileges](https://www.postgresql.org/docs/current/ddl-schemas.html) · [PostgreSQL `CREATE FUNCTION` security guidance](https://www.postgresql.org/docs/current/sql-createfunction.html)

Execute each tool call in a read-only transaction and configure short, role- or session-specific `statement_timeout` and `lock_timeout`; consider a connection limit and an idle-in-transaction timeout. PostgreSQL supports transaction read-only mode and these timeout controls. [PostgreSQL `SET TRANSACTION`](https://www.postgresql.org/docs/current/sql-set-transaction.html) · [PostgreSQL client connection defaults](https://www.postgresql.org/docs/current/runtime-config-client.html) · [PostgreSQL `CREATE ROLE`](https://www.postgresql.org/docs/current/sql-createrole.html)

## Deep Agents integration

Make the SQL tool call a structured request (for example `query`, `params`, and a server-derived authorization context) and perform the gateway checks inside the tool implementation, before its database driver call. A system prompt, a query-checking LLM, or schema descriptions can improve correctness but cannot authorize execution. LangChain's SQL tutorial itself calls out the inherent risk and says the database permissions should be scoped as narrowly as possible. [LangChain: Build a SQL agent](https://docs.langchain.com/oss/python/langchain/sql-agent)

Use `wrap_tool_call` middleware as an additional interception point for logging, deny/allow enforcement, and controlled failures; Deep Agents accepts custom middleware. Put this security middleware before non-critical middleware, but keep the tool/gateway check mandatory so a configuration error cannot bypass it. For high-impact or policy-ambiguous calls, configure Human-in-the-Loop approval and ensure the graph has durable checkpointing. [LangChain custom middleware](https://docs.langchain.com/oss/python/langchain/middleware/custom) · [Deep Agents customization](https://docs.langchain.com/oss/python/deepagents/customization) · [LangChain Human-in-the-Loop](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)

Finally, cap tool calls per run, log the authenticated subject, policy version, normalized query fingerprint, authorization decision, timeout, row count, and correlation ID (redacting parameter values). This supports incident review without making sensitive query data a new exposure. [Deep Agents: going to production](https://docs.langchain.com/oss/python/deepagents/going-to-production)

## Minimum viable rollout

1. Start with a read-only role over a small set of tenant-safe views, short timeouts, a result cap, and audited structured query templates.
2. Add a dialect-aware AST allow-list only if free-form analytical SQL is genuinely required.
3. Require human approval for any future write path; implement writes as separate, narrow business-operation tools rather than widening the SQL policy.
