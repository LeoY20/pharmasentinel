-- PharmaSentinel Seed Data
-- Run this after schema.sql to populate initial data

-- ============================================================================
-- Seed: drugs table
-- The 10 monitored critical drugs with realistic initial stock values
-- ============================================================================

INSERT INTO drugs (name, type, stock_quantity, unit, price_per_unit, usage_rate_daily, criticality_rank, reorder_threshold_days)
VALUES
    ('Epinephrine', 'Anaphylaxis/Cardiac', 150, 'vials', 35.00, 8, 1, 14),
    ('Oxygen', 'Respiratory Support', 500, 'liters', 0.50, 120, 2, 7),
    ('Levofloxacin', 'Broad-Spectrum Antibiotic', 200, 'tablets', 12.00, 15, 3, 14),
    ('Propofol', 'Anesthetic', 80, 'vials', 45.00, 6, 4, 14),
    ('Penicillin', 'Antibiotic', 300, 'vials', 8.00, 20, 5, 14),
    ('IV Fluids', 'Hydration/Shock', 400, 'bags', 3.50, 50, 6, 14),
    ('Heparin', 'Anticoagulant', 120, 'vials', 28.00, 10, 7, 14),
    ('Insulin', 'Diabetes Management', 180, 'vials', 55.00, 12, 8, 14),
    ('Morphine', 'Analgesic/Pain', 100, 'vials', 18.00, 7, 9, 14),
    ('Vaccines', 'Immunization', 250, 'doses', 22.00, 5, 10, 21)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- Seed: suppliers table
-- Major US pharmaceutical distributors + nearby hospitals
-- ============================================================================

INSERT INTO suppliers (name, drug_name, location, lead_time_days, price_per_unit, reliability_score, is_nearby_hospital, active)
VALUES
    -- National Distributors
    ('McKesson Corporation', 'Epinephrine', 'National (US)', 1, 33.00, 0.98, FALSE, TRUE),
    ('McKesson Corporation', 'Propofol', 'National (US)', 1, 43.00, 0.98, FALSE, TRUE),
    ('McKesson Corporation', 'Levofloxacin', 'National (US)', 1, 11.50, 0.98, FALSE, TRUE),
    ('McKesson Corporation', 'Penicillin', 'National (US)', 1, 7.50, 0.98, FALSE, TRUE),
    ('McKesson Corporation', 'IV Fluids', 'National (US)', 1, 3.25, 0.98, FALSE, TRUE),
    ('McKesson Corporation', 'Heparin', 'National (US)', 1, 27.00, 0.98, FALSE, TRUE),
    ('McKesson Corporation', 'Insulin', 'National (US)', 1, 53.00, 0.98, FALSE, TRUE),
    ('McKesson Corporation', 'Morphine', 'National (US)', 1, 17.00, 0.98, FALSE, TRUE),

    ('Cardinal Health', 'Epinephrine', 'National (US)', 1, 34.00, 0.97, FALSE, TRUE),
    ('Cardinal Health', 'Propofol', 'National (US)', 1, 44.00, 0.97, FALSE, TRUE),
    ('Cardinal Health', 'Oxygen', 'National (US)', 1, 0.48, 0.97, FALSE, TRUE),
    ('Cardinal Health', 'Levofloxacin', 'National (US)', 1, 11.75, 0.97, FALSE, TRUE),
    ('Cardinal Health', 'IV Fluids', 'National (US)', 1, 3.30, 0.97, FALSE, TRUE),

    ('AmerisourceBergen', 'Penicillin', 'National (US)', 1, 7.75, 0.96, FALSE, TRUE),
    ('AmerisourceBergen', 'Heparin', 'National (US)', 1, 27.50, 0.96, FALSE, TRUE),
    ('AmerisourceBergen', 'Insulin', 'National (US)', 1, 54.00, 0.96, FALSE, TRUE),
    ('AmerisourceBergen', 'Morphine', 'National (US)', 1, 17.50, 0.96, FALSE, TRUE),
    ('AmerisourceBergen', 'Vaccines', 'National (US)', 1, 21.50, 0.96, FALSE, TRUE),

    -- Regional Distributors
    ('Morris & Dickson', 'Epinephrine', 'Southeast US', 2, 34.50, 0.95, FALSE, TRUE),
    ('Morris & Dickson', 'Propofol', 'Southeast US', 2, 44.50, 0.95, FALSE, TRUE),
    ('Morris & Dickson', 'IV Fluids', 'Southeast US', 2, 3.40, 0.95, FALSE, TRUE),

    ('Henry Schein', 'Levofloxacin', 'National (US)', 2, 12.00, 0.94, FALSE, TRUE),
    ('Henry Schein', 'Penicillin', 'National (US)', 2, 8.00, 0.94, FALSE, TRUE),
    ('Henry Schein', 'Vaccines', 'National (US)', 2, 22.00, 0.94, FALSE, TRUE),

    -- Manufacturers (Direct)
    ('Pfizer (Direct)', 'Vaccines', 'Global', 5, 20.00, 0.99, FALSE, TRUE),
    ('Pfizer (Direct)', 'Penicillin', 'Global', 5, 7.00, 0.99, FALSE, TRUE),

    ('Teva Pharmaceuticals', 'Epinephrine', 'Global', 7, 32.00, 0.93, FALSE, TRUE),
    ('Teva Pharmaceuticals', 'Morphine', 'Global', 7, 16.50, 0.93, FALSE, TRUE),

    ('Fresenius Kabi', 'Propofol', 'Global', 5, 42.00, 0.95, FALSE, TRUE),
    ('Fresenius Kabi', 'IV Fluids', 'Global', 5, 3.00, 0.95, FALSE, TRUE),
    ('Fresenius Kabi', 'Heparin', 'Global', 5, 26.00, 0.95, FALSE, TRUE),

    ('Baxter International', 'IV Fluids', 'Global', 3, 3.20, 0.96, FALSE, TRUE),
    ('Baxter International', 'Heparin', 'Global', 3, 26.50, 0.96, FALSE, TRUE),
    ('Baxter International', 'Morphine', 'Global', 3, 17.25, 0.96, FALSE, TRUE),

    -- Nearby Hospitals (Pittsburgh area)
    ('Pittsburgh General Hospital', 'Epinephrine', 'Pittsburgh, PA', 0, 35.00, 0.90, TRUE, TRUE),
    ('Pittsburgh General Hospital', 'Oxygen', 'Pittsburgh, PA', 0, 0.50, 0.90, TRUE, TRUE),
    ('Pittsburgh General Hospital', 'IV Fluids', 'Pittsburgh, PA', 0, 3.50, 0.90, TRUE, TRUE),

    ('UPMC Mercy', 'Propofol', 'Pittsburgh, PA', 0, 45.00, 0.92, TRUE, TRUE),
    ('UPMC Mercy', 'Heparin', 'Pittsburgh, PA', 0, 28.00, 0.92, TRUE, TRUE),
    ('UPMC Mercy', 'Morphine', 'Pittsburgh, PA', 0, 18.00, 0.92, TRUE, TRUE),

    ('Allegheny General Hospital', 'Levofloxacin', 'Pittsburgh, PA', 0, 12.00, 0.91, TRUE, TRUE),
    ('Allegheny General Hospital', 'Penicillin', 'Pittsburgh, PA', 0, 8.00, 0.91, TRUE, TRUE),
    ('Allegheny General Hospital', 'Insulin', 'Pittsburgh, PA', 0, 55.00, 0.91, TRUE, TRUE)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- Seed: substitutes table
-- Pre-populate with hard-coded medically validated substitution mappings
-- ============================================================================

INSERT INTO substitutes (drug_name, substitute_name, equivalence_notes, preference_rank)
VALUES
    -- Epinephrine substitutes
    ('Epinephrine', 'Norepinephrine', 'For cardiac use only (NOT anaphylaxis). Similar vasopressor effects.', 1),
    ('Epinephrine', 'Vasopressin', 'Second-line for cardiac arrest. Different mechanism but can support BP.', 2),

    -- Propofol substitutes
    ('Propofol', 'Etomidate', 'Shorter duration. Good for rapid sequence intubation. Less hypotension.', 1),
    ('Propofol', 'Ketamine', 'Useful for hemodynamically unstable patients. Maintains BP. Different side effect profile.', 2),
    ('Propofol', 'Midazolam', 'Slower onset. Benzodiazepine class. Useful for sedation but not ideal for induction.', 3),

    -- Penicillin substitutes
    ('Penicillin', 'Amoxicillin', 'Similar spectrum, oral or IV. Well tolerated. First choice substitute.', 1),
    ('Penicillin', 'Cephalexin', 'First-generation cephalosporin. Check for penicillin allergy cross-reactivity (~10%).', 2),
    ('Penicillin', 'Azithromycin', 'Macrolide. Use if penicillin allergy confirmed. Different spectrum.', 3),

    -- Levofloxacin substitutes
    ('Levofloxacin', 'Moxifloxacin', 'Same fluoroquinolone class. Similar spectrum with better anaerobic coverage.', 1),
    ('Levofloxacin', 'Ciprofloxacin', 'Same fluoroquinolone class. Better for UTIs and GI infections.', 2),
    ('Levofloxacin', 'Doxycycline', 'Tetracycline class. Different mechanism. Broad spectrum alternative.', 3),

    -- Heparin substitutes
    ('Heparin', 'Enoxaparin', 'Low molecular weight heparin (LMWH). More predictable dosing. Preferred by many.', 1),
    ('Heparin', 'Fondaparinux', 'Synthetic factor Xa inhibitor. Use for HIT patients. No cross-reactivity.', 2),
    ('Heparin', 'Warfarin', 'Oral anticoagulant. Slower onset (days). Requires INR monitoring. For chronic use.', 3),

    -- Insulin substitutes
    ('Insulin', 'Insulin Lispro', 'Rapid-acting analog (Humalog). Onset 15 min. For meal coverage.', 1),
    ('Insulin', 'Insulin Glargine', 'Long-acting basal insulin (Lantus). For basal coverage, not acute DKA.', 2),

    -- Morphine substitutes
    ('Morphine', 'Hydromorphone', '5-7x more potent than morphine. Dilaudid. Adjust dose carefully. Less nausea.', 1),
    ('Morphine', 'Fentanyl', '50-100x more potent. Rapid onset. Use in ICU settings. Careful dosing required.', 2),
    ('Morphine', 'Oxycodone', 'Oral option. ~1.5x potency of morphine. For moderate to severe pain.', 3),

    -- IV Fluids substitutes
    ('IV Fluids', 'Lactated Ringers', 'Better for large-volume resuscitation. Contains electrolytes. Preferred for trauma.', 1),
    ('IV Fluids', 'Normal Saline', '0.9% NaCl. Standard isotonic crystalloid. Universal for most indications.', 2),
    ('IV Fluids', 'D5W', '5% dextrose in water. For specific indications (hypoglycemia, maintenance). Not for resuscitation.', 3)
ON CONFLICT (drug_name, substitute_name) DO NOTHING;

-- ============================================================================
-- Seed: surgery_schedule table
-- Upcoming surgeries with drug requirements
-- ============================================================================

INSERT INTO surgery_schedule (surgery_type, scheduled_date, estimated_duration_hours, drugs_required, status)
VALUES
    (
        'Cardiac Bypass',
        CURRENT_DATE + INTERVAL '3 days',
        5.5,
        '[
            {"drug_name": "Heparin", "quantity": 10, "unit": "vials"},
            {"drug_name": "Propofol", "quantity": 3, "unit": "vials"},
            {"drug_name": "Morphine", "quantity": 5, "unit": "vials"},
            {"drug_name": "IV Fluids", "quantity": 8, "unit": "bags"}
        ]'::jsonb,
        'SCHEDULED'
    ),
    (
        'Appendectomy',
        CURRENT_DATE + INTERVAL '5 days',
        2.0,
        '[
            {"drug_name": "Propofol", "quantity": 2, "unit": "vials"},
            {"drug_name": "Levofloxacin", "quantity": 4, "unit": "tablets"},
            {"drug_name": "IV Fluids", "quantity": 4, "unit": "bags"},
            {"drug_name": "Morphine", "quantity": 2, "unit": "vials"}
        ]'::jsonb,
        'SCHEDULED'
    ),
    (
        'Hip Replacement',
        CURRENT_DATE + INTERVAL '7 days',
        3.5,
        '[
            {"drug_name": "Propofol", "quantity": 2, "unit": "vials"},
            {"drug_name": "Heparin", "quantity": 6, "unit": "vials"},
            {"drug_name": "Morphine", "quantity": 4, "unit": "vials"},
            {"drug_name": "IV Fluids", "quantity": 6, "unit": "bags"}
        ]'::jsonb,
        'SCHEDULED'
    ),
    (
        'Emergency Trauma',
        CURRENT_DATE + INTERVAL '1 day',
        4.0,
        '[
            {"drug_name": "Epinephrine", "quantity": 3, "unit": "vials"},
            {"drug_name": "IV Fluids", "quantity": 12, "unit": "bags"},
            {"drug_name": "Morphine", "quantity": 6, "unit": "vials"},
            {"drug_name": "Heparin", "quantity": 4, "unit": "vials"},
            {"drug_name": "Oxygen", "quantity": 200, "unit": "liters"}
        ]'::jsonb,
        'SCHEDULED'
    ),
    (
        'Tonsillectomy',
        CURRENT_DATE + INTERVAL '10 days',
        1.5,
        '[
            {"drug_name": "Propofol", "quantity": 1, "unit": "vials"},
            {"drug_name": "Penicillin", "quantity": 6, "unit": "vials"},
            {"drug_name": "Morphine", "quantity": 1, "unit": "vials"},
            {"drug_name": "IV Fluids", "quantity": 2, "unit": "bags"}
        ]'::jsonb,
        'SCHEDULED'
    ),
    (
        'Cesarean Section',
        CURRENT_DATE + INTERVAL '12 days',
        2.5,
        '[
            {"drug_name": "Propofol", "quantity": 2, "unit": "vials"},
            {"drug_name": "Morphine", "quantity": 3, "unit": "vials"},
            {"drug_name": "IV Fluids", "quantity": 6, "unit": "bags"},
            {"drug_name": "Penicillin", "quantity": 4, "unit": "vials"}
        ]'::jsonb,
        'SCHEDULED'
    ),
    (
        'Knee Arthroscopy',
        CURRENT_DATE + INTERVAL '15 days',
        2.0,
        '[
            {"drug_name": "Propofol", "quantity": 2, "unit": "vials"},
            {"drug_name": "Morphine", "quantity": 2, "unit": "vials"},
            {"drug_name": "IV Fluids", "quantity": 3, "unit": "bags"},
            {"drug_name": "Levofloxacin", "quantity": 3, "unit": "tablets"}
        ]'::jsonb,
        'SCHEDULED'
    ),
    (
        'Cholecystectomy',
        CURRENT_DATE + INTERVAL '18 days',
        3.0,
        '[
            {"drug_name": "Propofol", "quantity": 2, "unit": "vials"},
            {"drug_name": "Levofloxacin", "quantity": 5, "unit": "tablets"},
            {"drug_name": "Morphine", "quantity": 3, "unit": "vials"},
            {"drug_name": "IV Fluids", "quantity": 5, "unit": "bags"}
        ]'::jsonb,
        'SCHEDULED'
    ),
    (
        'Spinal Fusion',
        CURRENT_DATE + INTERVAL '21 days',
        6.0,
        '[
            {"drug_name": "Propofol", "quantity": 3, "unit": "vials"},
            {"drug_name": "Heparin", "quantity": 8, "unit": "vials"},
            {"drug_name": "Morphine", "quantity": 8, "unit": "vials"},
            {"drug_name": "IV Fluids", "quantity": 10, "unit": "bags"}
        ]'::jsonb,
        'SCHEDULED'
    ),
    (
        'Cataract Surgery',
        CURRENT_DATE + INTERVAL '25 days',
        1.0,
        '[
            {"drug_name": "Propofol", "quantity": 1, "unit": "vials"},
            {"drug_name": "IV Fluids", "quantity": 1, "unit": "bags"}
        ]'::jsonb,
        'SCHEDULED'
    )
ON CONFLICT DO NOTHING;
