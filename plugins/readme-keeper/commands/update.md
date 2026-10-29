---
description: Refresh the marked regions of an existing README from the repo and show a diff
argument-hint: [path] [--style fancy]
---
Use the `readme-keeper` skill in update mode on: $ARGUMENTS

Never edit text outside readme-keeper markers. For an unmarked README, propose markers and do not add them without approval. Show the diff and stop. Write the file only after the user says yes. Never commit. Never run code from the target repo.
