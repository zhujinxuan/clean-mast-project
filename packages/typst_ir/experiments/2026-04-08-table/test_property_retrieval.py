"""
Test table property retrieval.

Questions:
- Can we retrieve table dimensions correctly?
- Can we determine table position in document order?
- Can we access cell content?
"""
import json

from docx import Document
from docx.table import Table

with open("input.json") as f:
    expected = json.load(f)

doc = Document("output/table.docx")

print("=== Test 1: Table Position in Document Order ===")
expected_tables = [node for node in expected['children'] if node['type'] == 'TypstTable']
actual_positions = []

for i, content in enumerate(doc.iter_inner_content()):
    if isinstance(content, Table):
        actual_positions.append(i)

print(f"Expected tables: {len(expected_tables)}")
print(f"Found tables at positions: {actual_positions}")
assert len(expected_tables) == len(actual_positions), "Table count mismatch"

print("\n=== Test 2: Table Dimensions ===")
for i, (expected_table, table) in enumerate(zip(expected_tables, doc.tables)):
    expected_rows = len(expected_table['data']) + 1  # +1 for header
    expected_cols = len(expected_table['headers'])
    actual_rows = len(table.rows)
    actual_cols = len(table.columns)
    
    print(f"Table {i}:")
    print(f"  Expected: {expected_rows} rows x {expected_cols} cols")
    print(f"  Actual: {actual_rows} rows x {actual_cols} cols")
    assert expected_rows == actual_rows, f"Row count mismatch in table {i}"
    assert expected_cols == actual_cols, f"Column count mismatch in table {i}"

print("\n✓ All tests passed")
