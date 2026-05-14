#!/usr/bin/env python3
"""
Print the next Demand Gen targeting split as a config-only scaffold.

This script does not call the Google Ads API. It keeps future Demand Gen tests
separated by audience signal so we can create them intentionally after Search
cleanup has enough readback.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DemandGenSegment:
    name: str
    objective: str
    optimized_targeting: bool
    search_terms: tuple[str, ...]
    url_signals: tuple[str, ...] = ()
    notes: str = ""


SEGMENTS = (
    DemandGenSegment(
        name="High-intent billing searches",
        objective="Retain Search-like intent while testing visual/self-selection creative.",
        optimized_targeting=False,
        search_terms=(
            "therapist billing service",
            "therapy billing services",
            "mental health billing services",
            "behavioral health billing company",
            "billing service for therapists",
            "outsourced billing for therapists",
            "private practice billing service",
            "insurance billing for therapists",
            "medicaid billing for therapists",
            "claims billing for therapists",
        ),
        notes="Use this as the cleanest non-Search prospecting test.",
    ),
    DemandGenSegment(
        name="Payer pain",
        objective="Test payer/program language from the new Search expansion.",
        optimized_targeting=False,
        search_terms=(
            "bcchp billing",
            "healthchoice illinois billing",
            "careSource behavioral health billing",
            "buckeye therapist billing",
            "ihcp billing",
            "hoosier healthwise billing",
            "turquoise care billing",
            "turquoise claims billing help",
        ),
        url_signals=(
            "https://www.bcbsil.com/bcchp",
            "https://medicaid.ohio.gov/",
            "https://www.in.gov/medicaid/",
            "https://www.hca.nm.gov/turquoise-care-health-plans/",
        ),
        notes="Keep payer and EHR signals separate so reporting can tell us what works.",
    ),
    DemandGenSegment(
        name="EHR billing pain",
        objective="Reach practices showing EHR-adjacent billing-help intent.",
        optimized_targeting=False,
        search_terms=(
            "SimplePractice billing help",
            "SimplePractice insurance billing help",
            "TherapyNotes billing help",
            "TherapyNotes insurance billing",
            "Sessions Health billing help",
            "EHR billing cleanup",
            "therapy EHR claims help",
            "claim denials SimplePractice",
            "SimplePractice Medicaid billing",
        ),
        url_signals=(
            "https://www.simplepractice.com/",
            "https://www.therapynotes.com/",
            "https://www.sessionshealth.com/",
            "https://www.availity.com/",
            "https://www.caqh.org/",
        ),
        notes="Do not include generic EHR/software shopping terms in this narrow test.",
    ),
    DemandGenSegment(
        name="Practice operator",
        objective="Prospect for therapist owners, billers, and group-practice operators.",
        optimized_targeting=False,
        search_terms=(
            "practice manager",
            "private practice owner",
            "therapy group practice",
            "behavioral health practice billing",
            "medical office manager",
            "credentialing specialist",
            "therapy practice revenue cycle",
            "payer paperwork therapy practice",
        ),
        notes="Creative should force self-selection instead of relying on the audience alone.",
    ),
    DemandGenSegment(
        name="Retargeting",
        objective="Follow up with high-fit visitors and ad engagers.",
        optimized_targeting=False,
        search_terms=(),
        notes="Use site visitors, Search visitors, lead-form openers, video viewers, and qualified-but-unbooked leads.",
    ),
    DemandGenSegment(
        name="Scaled Demand Gen",
        objective="Only use after qualified-conversion signals are strong enough to scale.",
        optimized_targeting=True,
        search_terms=(
            "therapist billing service",
            "medicaid billing for therapists",
            "SimplePractice billing help",
            "private practice therapist billing",
        ),
        notes="Separate campaign/ad group so optimized targeting does not blur learning tests.",
    ),
)


def print_markdown() -> None:
    print("# Demand Gen Targeting Scaffold")
    print()
    print("Config-only. No Google Ads objects are created by this script.")
    print()
    for segment in SEGMENTS:
        optimized = "on" if segment.optimized_targeting else "off"
        print(f"## {segment.name}")
        print(f"- Objective: {segment.objective}")
        print(f"- Optimized targeting: {optimized}")
        if segment.search_terms:
            print("- Search-term signals:")
            for term in segment.search_terms:
                print(f"  - {term}")
        if segment.url_signals:
            print("- URL signals:")
            for url in segment.url_signals:
                print(f"  - {url}")
        if segment.notes:
            print(f"- Notes: {segment.notes}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    if args.json:
        print(json.dumps([asdict(segment) for segment in SEGMENTS], indent=2))
    else:
        print_markdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
