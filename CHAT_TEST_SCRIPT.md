# Chatbot manual test script

Copy-paste these into the chat widget in order, after restarting `mcp-server`
and `ai-server`. Written to catch the tool-confusion / lost-history bugs
found on 2026-09-15 (see `KNOWN_ISSUES.md` #3 and `IMPROVEMENT_SUGGESTIONS.md`).

1. What's the cheapest product in the Dairy & Eggs category?
   - Expect: one named product + its price, plain sentence, no JSON.

2. Is that one in stock?
   - Expect: correctly says yes/no about that same product (not a re-dump of the category list).

3. How many do you have left, exactly?
   - Expect: the stock count for that one product, not a summed total across the category.

4. What's in your Beverages category?
   - Expect: a clean formatted list (regression check — this one already worked before).

5. Going back to that dairy product — what was its price again?
   - Expect: correctly recalls the dairy product's price, not "no dairy products in the current category."
