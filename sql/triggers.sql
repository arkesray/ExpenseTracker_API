-- Postgres triggers to keep `events` aggregates in sync
-- Usage: psql -h <host> -U <user> -d <db> -f sql/triggers.sql

-- 1) Transactions trigger: keeps `events.transaction_count` and `events.total_amount`
CREATE OR REPLACE FUNCTION transactions_update_event_totals()
RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    -- new transaction added
    UPDATE events SET transaction_count = COALESCE(transaction_count,0) + 1 WHERE id = NEW.event_id;
    IF NEW.is_expense THEN
      UPDATE events SET total_amount = COALESCE(total_amount,0) + NEW.amount WHERE id = NEW.event_id;
    END IF;
    RETURN NEW;

  ELSIF TG_OP = 'DELETE' THEN
    -- transaction removed
    UPDATE events SET transaction_count = GREATEST(COALESCE(transaction_count,0) - 1, 0) WHERE id = OLD.event_id;
    IF OLD.is_expense THEN
      UPDATE events SET total_amount = COALESCE(total_amount,0) - OLD.amount WHERE id = OLD.event_id;
    END IF;
    RETURN OLD;
  END IF;
END;
$$ LANGUAGE plpgsql VOLATILE;

DROP TRIGGER IF EXISTS trg_transactions_update_event_totals ON transactions;
CREATE TRIGGER trg_transactions_update_event_totals
AFTER INSERT OR UPDATE OR DELETE ON transactions
FOR EACH ROW EXECUTE FUNCTION transactions_update_event_totals();


-- 2) Event members trigger: keeps `events.member_count`
CREATE OR REPLACE FUNCTION event_members_update_member_count()
RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    UPDATE events SET member_count = COALESCE(member_count,0) + 1 WHERE id = NEW.event_id;
    RETURN NEW;
  ELSIF TG_OP = 'DELETE' THEN
    UPDATE events SET member_count = GREATEST(COALESCE(member_count,0) - 1, 0) WHERE id = OLD.event_id;
    RETURN OLD;
  END IF;
END;
$$ LANGUAGE plpgsql VOLATILE;

DROP TRIGGER IF EXISTS trg_event_members_update_member_count ON event_members;
CREATE TRIGGER trg_event_members_update_member_count
AFTER INSERT OR DELETE ON event_members
FOR EACH ROW EXECUTE FUNCTION event_members_update_member_count();


-- 3) TransactionShares: ensure `total_amount` reflects the parent transaction's `amount`
CREATE OR REPLACE FUNCTION transaction_shares_set_total_amount()
RETURNS trigger AS $$
DECLARE
  v_amount NUMERIC;
BEGIN
  IF NEW.transaction_id IS NULL THEN
    RETURN NEW;
  END IF;
  SELECT amount INTO v_amount FROM transactions WHERE id = NEW.transaction_id;
  IF v_amount IS NOT NULL THEN
    NEW.total_amount := v_amount;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql VOLATILE;

DROP TRIGGER IF EXISTS trg_transaction_shares_set_total ON transaction_shares;
CREATE TRIGGER trg_transaction_shares_set_total
BEFORE INSERT OR UPDATE ON transaction_shares
FOR EACH ROW EXECUTE FUNCTION transaction_shares_set_total_amount();


-- Helpful checks to detect drift (run occasionally):
-- SELECT e.id, e.total_amount AS stored, COALESCE(SUM(t.amount) FILTER (WHERE t.is_expense),0) AS expected
-- FROM events e LEFT JOIN transactions t ON t.event_id = e.id
-- GROUP BY e.id HAVING e.total_amount <> COALESCE(SUM(t.amount) FILTER (WHERE t.is_expense),0);

-- Notes:
-- - These are Postgres PL/pgSQL triggers; adapt if you use a different RDBMS.
-- - After installing triggers, remove or disable SQLAlchemy listeners that update the same aggregates to avoid double updates.
-- - Apply this file with: psql -h <host> -U <user> -d <db> -f sql/triggers.sql


