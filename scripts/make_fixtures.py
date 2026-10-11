"""Generate SYNTHETIC test words and clocks. Never align real media with this script."""

import json
from pathlib import Path

QUOTE = (
    "We shall fight on the beaches, we shall fight on the landing grounds, "
    "we shall fight in the fields and in the streets, we shall fight in the hills; "
    "we shall never surrender."
)


def record(
    version,
    title,
    passages,
    *,
    asset=None,
    event=None,
    rights="approved",
    availability="online",
    flags=None,
    metadata=None,
    event_date=None,
    untimed="",
):
    words = []
    coverage = []
    for start, text, language, confidence in passages:
        for position, word in enumerate(text.split()):
            words.append(
                dict(
                    word_id=f"w{len(words):04d}",
                    text=word,
                    start_ms=start + position * 650,
                    end_ms=start + position * 650 + 550,
                    language=language,
                    confidence=confidence,
                )
            )
        coverage.append(dict(start_ms=start, end_ms=words[-1]["end_ms"]))
    duration = max((w["end_ms"] for w in words), default=10000) + 10000
    return dict(
        schema_version="1",
        event_id=event or "event-" + version,
        asset_id=asset or "asset-" + version,
        recording_version_id=version,
        transcript_revision_id="tr-" + version + "-1",
        title=title,
        event_date=event_date,
        recording_date=None,
        custody_reference="DEMO-SHELF-" + version,
        duration_ms=duration,
        rights_class=rights,
        availability_state=availability,
        source_kind="synthetic_fixture",
        source_reference="data/PROVENANCE.md#" + version,
        coverage=coverage,
        words=words,
        untimed_text=untimed,
        source_metadata=metadata or [],
        quality_flags=flags or [],
    )


records = [
    record(
        "churchill-full",
        "We Shall Fight on the Beaches — synthetic reading fixture",
        [
            (
                5000,
                "The catalogue introduction describes a wartime address after an evacuation. "
                "This introduction is original synthetic fixture prose and is not a "
                "historical quotation.",
                "en",
                0.99,
            ),
            (120000, QUOTE, "en", 0.99),
            (
                180000,
                "This test commentary describes the archive registration process and the "
                "preservation of a physical carrier. Operators record the shelf reference "
                "before delivery.",
                "en",
                0.99,
            ),
        ],
        asset="asset-churchill",
        event="churchill-1940-06-04",
        event_date="1940-06-04",
    ),
    record(
        "churchill-edit",
        "We Shall Fight on the Beaches — synthetic edited fixture",
        [(18000, QUOTE, "en", 0.99)],
        asset="asset-churchill",
        event="churchill-1940-06-04",
        event_date="1940-06-04",
        availability="offline",
    ),
    record(
        "orchard",
        "Orchard oral history — synthetic",
        [
            (
                4000,
                "The gardeners planted apple trees beside the river. Each spring they checked "
                "the soil and pruned damaged branches. Rainfall helped the roots grow "
                "through summer. "
                "The harvest supplied fresh fruit to the village market and local schools.",
                "en",
                0.98,
            )
        ],
    ),
    record(
        "flood",
        "Flood evacuation account — synthetic partial transcript",
        [
            (
                10000,
                "Rising water entered the houses during the night. Volunteers carried families "
                "to higher ground in small boats. The community centre provided dry "
                "blankets and warm "
                "meals while residents waited for the river to fall.",
                "en",
                0.61,
            ),
            (
                95000,
                "The damaged bridge reopened after engineers inspected the stone supports. "
                "Residents returned to repair their homes.",
                "en",
                0.68,
            ),
        ],
        flags=["poor_audio_simulated", "metadata_conflict"],
        metadata=[
            dict(field="event_date", value="1952", source="synthetic ledger A"),
            dict(field="event_date", value="1953", source="synthetic ledger B"),
        ],
        untimed="Unaligned note: a later radio appeal mentioned emergency accommodation.",
    ),
    record(
        "railway",
        "Steam railway interview — synthetic offline",
        [
            (
                6000,
                "The steam locomotive pulled passenger carriages across the valley. Workers "
                "shovelled coal into the firebox and watched the pressure gauge. The "
                "station master "
                "announced departures while families waited on the platform for the morning train.",
                "en",
                0.97,
            )
        ],
        availability="offline",
    ),
    record(
        "restricted",
        "Closed meeting — synthetic restricted",
        [
            (
                3000,
                "Operation Marigold discussed confidential shelter locations and private "
                "evacuation "
                "routes. The committee kept the register sealed and limited access to "
                "approved staff.",
                "en",
                0.98,
            )
        ],
        rights="restricted",
    ),
    record(
        "unknown-rights",
        "Unresolved rights — synthetic",
        [
            (
                3000,
                "Project Azurestone describes an unpublished botanical expedition into "
                "the northern "
                "forest. The collection has no confirmed rights clearance.",
                "en",
                0.99,
            )
        ],
        rights="unknown",
    ),
    record(
        "french",
        "Community library opening — synthetic mixed language",
        [
            (
                2000,
                "La bibliothèque municipale ouvre ses portes aux enfants. Les lecteurs peuvent "
                "emprunter des livres et découvrir les histoires de leur quartier.",
                "fr",
                0.95,
            ),
            (
                25000,
                "The town library welcomes children and offers books about the local community.",
                "en",
                0.95,
            ),
        ],
    ),
    record(
        "untimed",
        "Unaligned catalogue transcript — synthetic",
        [],
        untimed="A brass band performed beside the harbour on a summer afternoon.",
    ),
]

if __name__ == "__main__":
    Path("data/sample/recordings.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + "\n"
    )
