# Table Detection Experiment

## Purpose

This experiment investigates how tables appear in a DOCX file's document order, how they relate to surrounding paragraphs, and whether table content can be accessed reliably via `python-docx`.

## Examination Results

The examine script analyzed the document successfully. Key findings:

- **Separate counts**: 3 paragraphs and 1 table were found as distinct top-level elements.
- **Document order via `iter_inner_content()`**: The mixed sequence of paragraphs and tables was preserved correctly:
  1. Paragraph: "Paragraph before table unique ..."
  2. Paragraph: "Table One Caption Unique Q1..."
  3. Table: 3 rows, 2 cols
  4. Paragraph: "Paragraph after table unique P..."
- **Cell content access**: All 6 cells were readable with exact text retrieval:
  - Row 0: headers "Col A Uniq1...", "Col B Uniq2..."
  - Row 1: "Cell 1-1 Unique X1...", "Cell 1-2 Unique Y1..."
  - Row 2: "Cell 2-1 Unique X2...", "Cell 2-2 Unique Y2..."

## Testing Results

The test script failed with a `KeyError: 'type'`:

```
expected_tables = [node for node in expected['children'] if node['type'] == 'TypstTable']
KeyError: 'type'
```

This error indicates that the serialized expected JSON file does not include a `type` field for IR nodes. The test logic assumed a Pydantic JSON serialization format that includes `type`, but the actual output omitted it. This is a serialization format mismatch, not a DOCX parsing failure.

## Findings

- **`iter_inner_content()` correctly interleaves paragraphs and tables**: This confirms that `python-docx` preserves document order when iterating over mixed content.
- **Tables are distinct block-level elements**: They are separate from paragraphs and can be counted and accessed independently.
- **Cell text retrieval works perfectly**: Every cell's text was extracted exactly.
- **JSON serialization issue**: The expected JSON lacks `type` fields, causing any script that tries to filter by `node['type']` to fail. This affects table, figure, and equation tests equally.

## Recommendations for Phase 2

1. **Use `iter_inner_content()` for document-order mapping**. It is the correct way to walk a DOCX body when both paragraphs and tables are present.
2. **Treat tables as first-class block nodes**: They can be mapped directly to `TypstTable` IR nodes.
3. **Fix the expected JSON serialization** to include a `type` field (or `discriminator` field) for each node, or update test scripts to identify nodes by other properties (e.g., presence of `data` and `headers` for tables).
4. **Capture captions carefully**: In this pandoc-generated document, the caption appears as a paragraph immediately before the table, not attached to it. Phase 2 mapping should look for adjacent "Table Caption" or "Caption" style paragraphs to associate captions with tables.
