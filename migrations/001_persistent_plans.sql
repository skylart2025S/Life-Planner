CREATE TABLE lp_plans (
    user_id text NOT NULL CHECK (length(user_id) > 0),
    plan_id text NOT NULL CHECK (length(plan_id) > 0),
    revision bigint NOT NULL DEFAULT 0 CHECK (revision >= 0),
    PRIMARY KEY (user_id, plan_id)
);

CREATE TABLE lp_items (
    user_id text NOT NULL,
    plan_id text NOT NULL,
    item_id text NOT NULL CHECK (length(item_id) > 0),
    title text NOT NULL,
    kind text NOT NULL,
    start_at timestamptz NOT NULL,
    end_at timestamptz NOT NULL CHECK (end_at > start_at),
    linked_to text,
    fixed boolean NOT NULL DEFAULT false,
    PRIMARY KEY (user_id, plan_id, item_id),
    FOREIGN KEY (user_id, plan_id) REFERENCES lp_plans (user_id, plan_id),
    FOREIGN KEY (user_id, plan_id, linked_to)
        REFERENCES lp_items (user_id, plan_id, item_id) DEFERRABLE INITIALLY DEFERRED,
    CHECK (linked_to IS NULL OR linked_to <> item_id)
);
CREATE INDEX lp_items_start ON lp_items (user_id, plan_id, start_at);

CREATE TABLE lp_proposals (
    user_id text NOT NULL,
    plan_id text NOT NULL,
    proposal_id text NOT NULL,
    base_revision bigint NOT NULL CHECK (base_revision >= 0),
    changes jsonb NOT NULL CHECK (jsonb_typeof(changes) = 'array'),
    explanation text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, plan_id, proposal_id),
    FOREIGN KEY (user_id, plan_id) REFERENCES lp_plans (user_id, plan_id)
);

CREATE TABLE lp_changes (
    user_id text NOT NULL,
    plan_id text NOT NULL,
    proposal_id text NOT NULL,
    applied_revision bigint NOT NULL CHECK (applied_revision > 0),
    changes jsonb NOT NULL CHECK (jsonb_typeof(changes) = 'array'),
    idempotency_key text NOT NULL CHECK (length(idempotency_key) > 0),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, plan_id, proposal_id),
    UNIQUE (user_id, plan_id, applied_revision),
    UNIQUE (user_id, plan_id, proposal_id, applied_revision),
    FOREIGN KEY (user_id, plan_id, proposal_id)
        REFERENCES lp_proposals (user_id, plan_id, proposal_id)
);

CREATE TABLE lp_receipts (
    user_id text NOT NULL,
    plan_id text NOT NULL,
    idempotency_key text NOT NULL CHECK (length(idempotency_key) > 0),
    proposal_id text NOT NULL,
    applied_revision bigint NOT NULL,
    PRIMARY KEY (user_id, plan_id, idempotency_key),
    FOREIGN KEY (user_id, plan_id, proposal_id, applied_revision)
        REFERENCES lp_changes (user_id, plan_id, proposal_id, applied_revision)
);

CREATE TABLE lp_outbox (
    user_id text NOT NULL,
    plan_id text NOT NULL,
    proposal_id text NOT NULL,
    event_id text NOT NULL UNIQUE,
    event_type text NOT NULL,
    payload jsonb NOT NULL,
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'delivered', 'failed')),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, plan_id, proposal_id),
    FOREIGN KEY (user_id, plan_id, proposal_id)
        REFERENCES lp_changes (user_id, plan_id, proposal_id)
);

CREATE FUNCTION lp_reject_history_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Planner history is immutable';
END;
$$;
CREATE TRIGGER lp_changes_immutable BEFORE UPDATE OR DELETE ON lp_changes
    FOR EACH ROW EXECUTE FUNCTION lp_reject_history_mutation();
CREATE TRIGGER lp_receipts_immutable BEFORE UPDATE OR DELETE ON lp_receipts
    FOR EACH ROW EXECUTE FUNCTION lp_reject_history_mutation();
CREATE TRIGGER lp_proposals_immutable BEFORE UPDATE OR DELETE ON lp_proposals
    FOR EACH ROW EXECUTE FUNCTION lp_reject_history_mutation();
