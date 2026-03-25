# Gemini Migration Guide

This document explains all the changes made directly to switch the CrewAI system from a local **Ollama** infrastructure completely toward using **Google Gemini 2.5 Flash**.

## What Changed?

1. **Configuration Defaults**:
   - Updates were made inside `config/settings.py` so that if no environment values are loaded, it naturally attempts to use **Gemini (`gemini-2.5-flash`)** rather than **Ollama** or OpenAI.
   - We specifically mapped the literal `"gemini"` provider to check for `GEMINI_API_KEY` and inject `gemini/{LLM_MODEL}` into the LLM initialization string so `litellm` intercepts it seamlessly.

2. **Environment Variables**:
   - `LLM_PROVIDER` in `.env` and `.env.example` has been set to defaults of `gemini` rather than something else.
   - Your `.env` and `.env.example` have been structured so `GEMINI_API_KEY` is prominently displayed waiting for your input.

3. **Scripts & Checks**:
   - `check_ollama.py` was **DELETED**, as the system no longer tries probing localhost for Llama weights.
   - `check_setup.py` was **ADDED** replacing our validation step to instead verify `GEMINI_API_KEY` presence.
   - `setup.py` no longer executes long multi-GB pulls of local models, simply verifying your `GEMINI_API_KEY`.

4. **Makefile Updates**:
   - Added reference updates so running `make check` evaluates Google API connectivity correctly through `check_setup.py`.

5. **Documentation Overhaul**:
   - Handled `README.md` and `MODELS.md` to cleanly present Gemini capabilities and usage.

---

## What To Do Next

1. Head to [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) and generate a new key if you don't already have one.
2. Open the `.env` file in the root directory.
3. Replace the placeholder value for `GEMINI_API_KEY` so it looks like this:
   ```bash
   GEMINI_API_KEY=AIzaSy...your-real-key-goes-here
   ```
4. Run:
   ```bash
   python check_setup.py
   # Or "make check"
   ```

You are all set. The system is entirely wired up for Gemini!
