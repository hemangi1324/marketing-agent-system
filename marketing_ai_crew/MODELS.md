# 🖥️ Which Gemini Model Should You Use?

This project is configured to use Google Gemini API by default. You can change the model used by altering your `.env` file.

---

## Model Selection

| Model Name       | Cost Profile       | Best For |
|------------------|--------------------|----------|
| `gemini-2.5-flash` | 💸 Cost effective  | Highly rapid iterations, structured content tasks, general use |
| `gemini-1.5-pro`   | 💰 Premium         | Highly complex reasoning, massive context parsing, logic flow |

---

## How to Switch Model

Just edit one line in `.env`:

```bash
# Current (default value)
LLM_MODEL=gemini-2.5-flash

# Switch to heavy reasoning
LLM_MODEL=gemini-1.5-pro
```

No code changes are needed. Just restart any running agent.
