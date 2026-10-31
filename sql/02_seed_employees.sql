INSERT INTO employees (author_id, full_name, department) VALUES
    ('care-001', 'Анна Тестовая', 'care'),
    ('care-002', 'Борис Тестовый', 'care'),
    ('sales-001', 'Виктор Тестовый', 'sales')
ON CONFLICT (author_id) DO NOTHING;
