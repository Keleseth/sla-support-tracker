CREATE OR REPLACE FUNCTION insert_events(valid_events_json jsonb, rejected_events_json jsonb)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    event_element         jsonb;
    incoming              events;
    stored                events;
    received_count        integer := jsonb_array_length(valid_events_json)
                                     + jsonb_array_length(rejected_events_json);
    inserted_count        integer := 0;
    duplicates_count      integer := 0;
    errors                jsonb;
    conflict_description  CONSTANT text :=
        'event_id уже существует с другими данными, сохранена первая версия';
BEGIN
    INSERT INTO rejected_events (event_id, conversation_id, issue_code, description, payload)
    SELECT rejected.event_id, rejected.conversation_id, rejected.issue_code,
           rejected.description, COALESCE(rejected.payload, 'null'::jsonb)
    FROM jsonb_to_recordset(rejected_events_json) AS rejected(
        event_id text, conversation_id text, issue_code text, description text, payload jsonb
    )
    ON CONFLICT (issue_code, md5(payload::text)) DO NOTHING;

    SELECT COALESCE(jsonb_agg(jsonb_build_object(
               'item_index', rejected.item_index,
               'event_id', rejected.event_id,
               'issue_code', rejected.issue_code,
               'description', rejected.description
           )), '[]'::jsonb)
    INTO errors
    FROM jsonb_to_recordset(rejected_events_json) AS rejected(
        item_index integer, event_id text, issue_code text, description text
    );

    FOR event_element IN
        SELECT element
        FROM jsonb_array_elements(valid_events_json) AS element
        ORDER BY (element ->> 'item_index')::integer
    LOOP
        incoming := jsonb_populate_record(NULL::events, event_element);

        INSERT INTO events SELECT incoming.*
        ON CONFLICT (event_id) DO NOTHING;

        IF FOUND THEN
            inserted_count := inserted_count + 1;
        ELSE
            SELECT * INTO stored FROM events WHERE events.event_id = incoming.event_id;

            IF stored IS NOT DISTINCT FROM incoming THEN
                duplicates_count := duplicates_count + 1;
            ELSE
                errors := errors || jsonb_build_object(
                    'item_index', (event_element ->> 'item_index')::integer,
                    'event_id', incoming.event_id,
                    'issue_code', 'event_id_conflict',
                    'description', conflict_description
                );

                INSERT INTO rejected_events (event_id, conversation_id, issue_code, description, payload)
                VALUES (incoming.event_id, incoming.conversation_id, 'event_id_conflict',
                        conflict_description, event_element - 'item_index')
                ON CONFLICT (issue_code, md5(payload::text)) DO NOTHING;
            END IF;
        END IF;
    END LOOP;

    RETURN jsonb_build_object(
        'received', received_count,
        'inserted', inserted_count,
        'duplicates', duplicates_count,
        'rejected', jsonb_array_length(errors),
        'errors', (
            SELECT COALESCE(jsonb_agg(error_item ORDER BY (error_item ->> 'item_index')::integer),
                            '[]'::jsonb)
            FROM jsonb_array_elements(errors) AS error_item
        )
    );
END;
$$;
