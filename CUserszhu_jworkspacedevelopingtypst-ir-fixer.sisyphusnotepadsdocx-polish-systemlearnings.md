
## 2025-04-22 - extract_section_map implemented
- Added  to 
- Algorithm: scan paragraphs for markers via , match / pairs by block_id using stack
- ,  (exclusive)
- Tables detected by iterating  and matching table elements between marker paragraphs
- Edge cases handled: unmatched starts (skipped with warning), unmatched ends (skipped with warning), empty blocks (recorded)
- 5 new TDD tests added: two blocks, nested sections, empty block, malformed missing irend, block with table
- All 17/17 tests in  pass, full suite 389/389 pass
- Type check () and lint () pass cleanly
- Key finding:  root has no , so imports from  use direct path (not )
- Key finding:  always creates end markers — for malformed tests, build DOCX manually
