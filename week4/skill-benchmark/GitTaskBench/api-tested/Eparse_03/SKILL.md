---
name: eparse_03-workflow
description: Inspect the task input, run the repository operation, and validate the submission.
---

# Eparse_03 workflow

Run this command in the terminal. It executes the three ordered stages.

```sh
python -B /workspace/skill/scripts/run_workflow.py Eparse_03 excel.py /workspace/input /workspace/output
```

If it reports validated, the expected submission is ready. End the task. If a stage fails, read its reported error and resolve it before submitting.
