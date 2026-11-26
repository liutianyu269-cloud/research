---
name: pdfplumber-extraction
description: Extract first-page text, tables, or email addresses from a text-layer PDF with pdfplumber.
---

Run the workflow with the requested extraction mode. For text, read the page's
text layer. For tables, preserve the order of pages, tables, rows and cells.
For email addresses, extract from the text layer and keep first occurrence order.
A failed read or a missing expected table is an error.
