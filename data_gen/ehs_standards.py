"""Brand-neutral EHS field standards (synthetic company standard + OSHA 29 CFR 1926 references) for Jobsite Intelligence.
Output: data_gen/out_docs/ehs/EHS_Field_Standards.pdf   Run: .venv/bin/python -I data_gen/ehs_standards.py

Company-standard requirements are SYNTHETIC and labeled as such. OSHA references cite 29 CFR 1926 sections;
verify against eCFR before any customer-facing use (https://www.ecfr.gov/current/title-29/subtitle-B/chapter-XVII/part-1926).
"""
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location("documents", Path(__file__).parent / "documents.py")
docs = importlib.util.module_from_spec(spec); spec.loader.exec_module(docs)  # reuse the Doc PDF class

SECTIONS = [
    ("EHS-07 Excavation and Trenching",
     ["OSHA reference: 29 CFR 1926 Subpart P. Excavations 5 feet or deeper require a protective system (sloping, benching, shoring, or shielding) unless in stable rock (1926.652(a)(1)). "
      "A competent person inspects excavations daily before work starts and after rain or other hazard-increasing events (1926.651(k)). "
      "Trenches 4 feet or deeper need a safe means of egress within 25 feet of lateral travel (1926.651(c)(2)). Keep spoil at least 2 feet from the edge (1926.651(j)(2)).",
      "Company standard (synthetic): an Excavation Permit signed by the superintendent is required for any excavation deeper than 4 feet; locate and mark utilities 72 hours before digging; "
      "barricade open excavations at end of shift."]),
    ("EHS-11 Fall Protection and Leading Edges",
     ["OSHA reference: general construction fall protection applies at 6 feet (1926.501(b)(1)). In steel erection (Subpart R), fall protection applies at 15 feet above a lower level, "
      "with specific provisions for connectors and controlled decking zones (1926.760).",
      "Company standard (synthetic): 100% tie-off at 6 feet on all work, including steel erection, unless a written exception is approved by the EHS manager. "
      "Leading-edge decking requires a pre-task plan reviewed at the morning huddle and a designated monitor when first-year workers are on the crew. "
      "Two near-misses on the same hazard within 14 days trigger a stand-down and a toolbox talk."]),
    ("EHS-14 Cranes, Rigging, and Critical Lifts",
     ["OSHA reference: 29 CFR 1926 Subpart CC (Cranes and Derricks in Construction) covers assembly/disassembly, power-line safety, inspections, signal persons, and qualified riggers.",
      "Company standard (synthetic): a Critical Lift Plan is required for any lift over 75% of rated capacity, any tandem lift, or any lift over occupied areas; "
      "the lift supervisor confirms wind is below the manufacturer's limit and stops lifts when sustained wind exceeds 20 mph or gusts exceed 30 mph; "
      "a pre-lift meeting covers rigging, exclusion zone, signal person, and communication."]),
    ("EHS-18 Electrical Work and Energization",
     ["OSHA reference: 29 CFR 1926 Subpart K (Electrical). NFPA 70E governs energized electrical work, including the energized electrical work permit and arc-flash PPE.",
      "Company standard (synthetic): no energized work without an approved Energized Work Permit; first energization of switchgear requires a written energization plan, "
      "lockout/tagout verification, and an exclusion zone; only qualified persons enter the arc-flash boundary."]),
    ("EHS-21 Hot Work",
     ["OSHA reference: 29 CFR 1926 Subpart J (Welding and Cutting).",
      "Company standard (synthetic): hot work permit required in all buildings; fire watch during hot work and for 60 minutes after; extinguisher within 25 feet; "
      "in occupied buildings coordinate with the owner's facilities team before the permit is issued."]),
    ("EHS-25 Occupied Buildings and Public Protection",
     ["Company standard (synthetic): in occupied hospitals follow the owner's Infection Control Risk Assessment (ICRA) class for barriers and negative air; "
      "on occupied campuses and airports maintain physical separation of public routes and coordinate deliveries outside peak hours."]),
    ("EHS-30 Toolbox Talks",
     ["Company standard (synthetic): every crew holds a toolbox talk before high-risk work. A toolbox talk covers: the hazard, the controls and required permit, "
      "lessons from recent near-misses on this job, conditions today (weather), how new workers are paired with experienced leads, and every worker's authority to stop work."]),
]


def main():
    out = Path(__file__).parent / "out_docs" / "ehs"
    out.mkdir(parents=True, exist_ok=True)
    d = docs.Doc("Contractor EHS Field Standards (synthetic excerpts)", "EHS Field Standards Rev. 2026-1")
    d.title_block(["EHS Field Standards - Excerpts", "Synthetic company standard for demonstration. OSHA references cite 29 CFR 1926.", "Revision 2026-1"])
    for title, paras in SECTIONS:
        d.hd(title)
        for p in paras:
            d.para(p)
    d.output(str(out / "EHS_Field_Standards.pdf")); print("pdf  EHS_Field_Standards.pdf", len(SECTIONS), "sections")


if __name__ == "__main__":
    main()
