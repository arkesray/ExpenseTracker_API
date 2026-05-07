-- Backfill / Repair queries (run once after creating the triggers)
-- Recompute total_amount from transactions (only expense rows)
UPDATE events
SET total_amount = COALESCE((
    SELECT COALESCE(SUM(t.amount),0)
    FROM transactions t
    WHERE t.event_id = events.id AND t.is_expense = TRUE
), 0);

-- Recompute transaction_count
UPDATE events
SET transaction_count = COALESCE((
    SELECT COUNT(*) FROM transactions t WHERE t.event_id = events.id
), 0);

-- Recompute member_count
UPDATE events
SET member_count = COALESCE((
    SELECT COUNT(*) FROM event_members em WHERE em.event_id = events.id
), 0);

-- Backfill transaction_shares.total_amount from transactions
UPDATE transaction_shares
SET total_amount = t.amount
FROM transactions t
WHERE transaction_shares.transaction_id = t.id;
