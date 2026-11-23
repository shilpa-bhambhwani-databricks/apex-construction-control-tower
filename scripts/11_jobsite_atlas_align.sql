UPDATE jobsite_lookahead SET info_ok = false, info_detail = 'RFI-0387 open 26 days (embed plates, L2 grid B)', info_owner = 'Architect / EOR', info_needed_by = 'Today'
WHERE project_id = 'P-1001' AND seq = 1
;;
UPDATE jobsite_lookahead SET info_ok = false, info_detail = 'RFI-0391 open 23 days (duct bank vs. footing F-12)', info_owner = 'MEP engineer', info_needed_by = 'Today'
WHERE project_id = 'P-1001' AND seq = 2
;;
UPDATE jobsite_lookahead SET info_ok = true, info_detail = 'No open RFIs', info_owner = NULL, info_needed_by = NULL
WHERE project_id = 'P-1001' AND seq = 3
;;
UPDATE jobsite_lookahead SET ready = (info_ok AND approvals_ok AND materials_ok AND float_ok) WHERE project_id = 'P-1001'
;;
SELECT seq, activity, ready, info_detail, approvals_detail, materials_detail, float_detail FROM jobsite_lookahead WHERE project_id = 'P-1001' ORDER BY seq
