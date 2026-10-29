---
description: Create a README from the repo's real files, with a fact report and a diff before any write
argument-hint: [path] [--depth minimal|standard|full] [--research] [--style fancy]
---
Use the `readme-keeper` skill in create mode on: $ARGUMENTS

Refuse if the target README already exists, and suggest `/readme-keeper:update`. Show the diff of the new file and stop. Write the file only after the user says yes. Never commit. Never run code from the target repo.
