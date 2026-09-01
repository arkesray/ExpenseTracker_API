-- SQL script to delete an entire event along with all its related transactions, shares, and memberships.
-- Replace :event_id with the ID of the event you want to delete.

BEGIN;

-- 1. Delete all transaction shares associated with transactions in this event first (to respect RESTRICT on TransactionShare -> Transaction)
DELETE FROM transaction_shares
WHERE transaction_id IN (
    SELECT id FROM transactions WHERE event_id = :event_id
);

-- 2. Delete all transactions for this event (to respect RESTRICT on Transaction -> Event)
DELETE FROM transactions 
WHERE event_id = :event_id;

-- 3. Remove all members from the event (to respect RESTRICT on EventMembership -> Event)
DELETE FROM event_members 
WHERE event_id = :event_id;

-- 4. Finally, delete the event itself
DELETE FROM events 
WHERE id = :event_id;

COMMIT;
