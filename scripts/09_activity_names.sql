UPDATE schedule_activities SET activity_name = CASE trade
  WHEN 'Concrete' THEN element_at(array('Slab-on-grade pour', 'Elevated deck pour', 'Pile cap concrete', 'Grade beam pour', 'Shear wall pour'), CAST(abs(hash(activity_id)) % 5 AS INT) + 1)
  WHEN 'Steel erection' THEN element_at(array('Steel erection L2', 'Steel erection L3', 'Metal decking L4', 'Roof steel', 'Moment frame connections'), CAST(abs(hash(activity_id)) % 5 AS INT) + 1)
  WHEN 'Electrical' THEN element_at(array('Duct bank trenching', 'Switchgear set', 'Feeder pulls', 'Panel rough-in', 'Generator pads'), CAST(abs(hash(activity_id)) % 5 AS INT) + 1)
  WHEN 'Mechanical' THEN element_at(array('Chiller set', 'Ductwork rough-in', 'Chilled water piping', 'AHU set'), CAST(abs(hash(activity_id)) % 4 AS INT) + 1)
  WHEN 'Sitework' THEN element_at(array('Mass excavation', 'Underground utilities', 'Site paving', 'Storm drainage'), CAST(abs(hash(activity_id)) % 4 AS INT) + 1)
  ELSE element_at(array('Framing and drywall', 'Ceilings', 'Doors and hardware', 'Finishes'), CAST(abs(hash(activity_id)) % 4 AS INT) + 1) END
;;
MERGE INTO schedule_activities s USING (
  SELECT r.activity_id, x.name, x.start, x.flt FROM rfis r JOIN (VALUES
    ('RFI-0387', 'Steel erection L2 (grid B)', DATE'2026-11-16', 0),
    ('RFI-0391', 'Duct bank trenching - north yard', DATE'2026-11-11', 2),
    ('RFI-0352', 'Pile caps PC-14 to PC-22', DATE'2026-11-13', 4)) AS x(rfi_id, name, start, flt) ON r.rfi_id = x.rfi_id AND r.project_id = 'P-1001'
) u ON s.activity_id = u.activity_id
WHEN MATCHED THEN UPDATE SET activity_name = u.name, planned_start = u.start, planned_finish = u.start + INTERVAL 10 DAYS, total_float_days = u.flt, critical_flag = true, actual_start = NULL
;;
SELECT r.rfi_id, s.activity_name, s.planned_start, s.total_float_days, s.critical_flag FROM rfis r JOIN schedule_activities s ON s.activity_id = r.activity_id
WHERE r.rfi_id IN ('RFI-0387', 'RFI-0391', 'RFI-0352') AND r.project_id = 'P-1001'
