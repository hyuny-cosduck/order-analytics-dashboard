# Claude Code Permission Modes

**6 levels from most restrictive to most permissive:**

| Mode | Auto-Approves | Requires Approval |
|------|--------------|-------------------|
| **plan** | Reads only | Cannot edit/execute |
| **default** | Reads only | Edits, bash, network |
| **acceptEdits** | Reads + edits | Bash, network |
| **auto** | Everything (with classifier checks) | Blocked categories |
| **dontAsk** | Only pre-allowed tools | Auto-denies everything else |
| **bypassPermissions** | Everything | Nothing (except protected paths) |

**Protected paths always require approval:** `.git`, `.claude`, `.vscode`, `.idea`, `.husky`

**Fine-grained rules** (in settings):
```json
{
  "permissions": {
    "allow": ["Bash(npm run *)"],
    "ask": ["Bash(git push *)"],
    "deny": ["Bash(rm -rf *)"]
  }
}
```

**Precedence:** Deny > Ask > Allow

**Switching modes:** `--permission-mode <mode>` at startup or `Shift+Tab` during session
