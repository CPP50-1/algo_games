# Submitting your bot

This doubles as a real rehearsal of the branch → pull request → review →
merge workflow, using your own competitive bot as the reason to actually do
it properly.

## Steps

1. Clone this repo and create a branch named after you:

   ```bash
   git checkout -b bot/<your-first-name>
   ```

2. Check `docs/` for the game that's currently active (e.g. `docs/tron.md`,
   `docs/delivery.md`) -- it tells you which folder your file goes in, what
   state your `decide()` receives, and what to return. Add exactly one file:
   `<that-game's-bots-folder>/<your-first-name>.py`, containing one class
   that subclasses `Bot` (see the README's "Writing a bot" section for the
   parts that are the same for every game).

3. Commit and push your branch, then open a pull request against `develop`.

4. A GitHub Action will automatically smoke-test your bot -- it just checks
   that your file imports cleanly and `decide()` runs without crashing or
   timing out on a dummy board. It does **not** judge strategy. A green
   check means "safe to include in the tournament," not "good code."

5. Once your PR is merged, your bot is in. You can keep pushing updates to
   your branch and opening new PRs right up until the deadline the trainer
   sets.

## Rules

- One file, one `Bot` subclass, in the correct folder for the active game. A
  file with zero or several subclasses will fail the CI check.
- Don't touch anyone else's file. If your PR modifies a bot file that isn't
  yours, it won't be merged.
- Don't modify anything outside your game's bots folder (engine code, other
  people's bots, the CI workflow, other games' folders). If you think
  something in the engine itself needs fixing, flag it to the trainer rather
  than changing it in your PR.

## If the CI check fails

Read the annotation on your PR -- it names the exact problem (import error,
no `Bot` subclass found, timeout, etc.). Fix it and push again; the check
re-runs automatically on every push to your branch.
