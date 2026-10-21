# v0.8.0

#!/usr/bin/env python3
import csv
import plistlib
import subprocess
from lxml import etree
import sys
import argparse
from copy import deepcopy
import re
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout

# DEBUG konfigurieren: False = normaler Modus, True = verbose Debug-Modus
DEBUG_MODE = False


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, text):
        for stream in self.streams:
            stream.write(text)
        return len(text)

    def flush(self):
        for stream in self.streams:
            stream.flush()


def get_text_ns(el, name):
    """Namespace-robust: local-name() ohne namespaces."""
    xpath = f".//*[local-name()='{name}']"
    children = el.xpath(xpath)
    return (children[0].text or '').strip() if children else ''


def detect_structure(*roots):
    for root in roots:
        if root.xpath(".//*[local-name()='item']"):
            return 'items', 'item'
        if root.xpath(".//*[local-name()='speaker']"):
            return 'speakers', 'speaker'
    return 'empty', None


def make_key(root, block, block_type):
    if block_type == 'item':
        title = get_text_ns(block, 'title')
        first = get_text_ns(block, 'firstName')
        last = get_text_ns(block, 'lastName')
        parts = [p for p in [title, first, last] if p]
    else:  # speaker
        first = get_text_ns(block, 'firstName')
        last = get_text_ns(block, 'lastName')
        parts = [p for p in [first, last] if p]
    return '::'.join(parts) if parts else None


def has_unique_ids(root, block_type):
    return any(get_text_ns(block, 'uniqueId') for block in root.xpath(f".//*[local-name()='{block_type}']"))


def blocks_by_unique_id(root, block_type, debug=False):
    """Sammelt Blöcke anhand ihrer eindeutigen IDs."""
    blocks = {}
    if debug:
        print(f"\n📂 {block_type.title()}s anhand von uniqueId sammeln...")
    for i, block in enumerate(root.xpath(f".//*[local-name()='{block_type}']"), 1):
        unique_id = get_text_ns(block, 'uniqueId')
        if unique_id:
            blocks[unique_id] = block
            if debug:
                print(f"  {i:2d}. '{unique_id}'")
        elif debug:
            print(f"  {i:2d}. [ohne uniqueId]")
    return blocks


def blocks_by_key(root, block_type, debug=False):
    """Zeigt alle gefundenen Blöcke, optional mit Ausgabe."""
    blocks = {}
    if debug:
        print(f"\n📂 {block_type.title()}s sammeln...")
    for i, block in enumerate(root.xpath(f".//*[local-name()='{block_type}']"), 1):
        key = make_key(root, block, block_type)
        if key:
            blocks[key] = block
            if debug:
                print(f"  {i:2d}. '{key}'")
        else:
            if debug:
                print(f"  {i:2d}. [ohne Key]")
    return blocks


def elements_equal(block1, block2, block_type, debug=False):
    """Vergleicht Felder mit Diff-Details."""
    if block_type == 'item':
        fields = ['title', 'firstName', 'lastName', 'speakers']
    else:
        fields = ['name', 'firstName', 'lastName']
    
    for f in fields:
        v1 = get_text_ns(block1, f)
        v2 = get_text_ns(block2, f)
        if v1 != v2:
            if debug:
                print(f"     ❌ '{f}': '{v1}' → '{v2}'")
            return False
    if debug:
        print("     ✅ Alle Felder identisch")
    return True


def unique_id_fields_equal(block1, block2, debug=False):
    """Vergleicht im uniqueId-Modus die fachlich relevanten Änderungsfelder."""
    for field in ['title', 'firstName', 'lastName', 'speakers']:
        value1 = get_text_ns(block1, field)
        value2 = get_text_ns(block2, field)
        if value1 != value2:
            if debug:
                print(f"     ❌ '{field}': '{value1}' → '{value2}'")
            return False
    if debug:
        print("     ✅ Titel, Speaker und Sprecher identisch")
    return True


def get_blocks(root, block_type, use_unique_ids, debug=False):
    if use_unique_ids:
        return blocks_by_unique_id(root, block_type, debug=debug)
    return blocks_by_key(root, block_type, debug=debug)


def find_input_files(input_dir):
    return sorted(
        path for path in Path(input_dir).iterdir()
        if path.is_file() and path.suffix.lower() == '.xml'
    )


def filename_version(path):
    match = re.match(
        r"^(?P<base>.+)\((?P<timestamp>\d{4}_\d{2}_\d{2}-\d{2}_\d{2})\)$",
        Path(path).stem,
    )
    if not match:
        return None
    return match.group('base'), match.group('timestamp')


def find_input_pairs(input_dir):
    xml_files = find_input_files(input_dir)
    if not xml_files:
        print("❌ Im Ordner Input wurden keine XML-Dateien gefunden.")
        sys.exit(1)

    groups = {}
    for path in xml_files:
        filename_info = filename_version(path)
        if filename_info is None:
            print(f"❌ Dateiname enthält keinen Zeitstempel im erwarteten Format: {path.name}")
            print("   Erwartet wird ein Suffix wie '(2026_10_21-11_28)'.")
            sys.exit(1)
        base, timestamp = filename_info
        groups.setdefault(base, []).append((timestamp, path))

    pairs = []
    for base, versions in sorted(groups.items()):
        if len(versions) != 2:
            print(f"❌ Für '{base}' müssen genau zwei XML-Dateien vorhanden sein.")
            print(f"   Gefunden: {len(versions)}")
            sys.exit(1)
        versions.sort(key=lambda version: version[0])
        if versions[0][0] == versions[1][0]:
            print(f"❌ Die Zeitstempel für '{base}' müssen unterschiedlich sein.")
            sys.exit(1)
        pairs.append((versions[0][1], versions[1][1]))
    return pairs


def validate_input_files(old_path, new_path):
    old_file = Path(old_path).resolve()
    new_file = Path(new_path).resolve()
    if old_file == new_file:
        print("❌ ALT und NEU müssen unterschiedliche Dateien sein.")
        sys.exit(1)
    if not old_file.is_file() or not new_file.is_file():
        print("❌ Die angegebenen XML-Dateien müssen existieren.")
        sys.exit(1)
    if old_file.suffix.lower() != '.xml' or new_file.suffix.lower() != '.xml':
        print("❌ Es können nur XML-Dateien verglichen werden.")
        sys.exit(1)
    old_version = filename_version(old_file)
    new_version = filename_version(new_file)
    if (old_version is None) != (new_version is None):
        print("❌ Beide Dateinamen müssen entweder einen Zeitstempel enthalten oder keinen.")
        sys.exit(1)
    if old_version and new_version and old_version[0] != new_version[0]:
        print("❌ Die Dateinamen gehören nicht zur selben XML-Dateigruppe.")
        sys.exit(1)


def order_input_files(old_path, new_path):
    old_file = Path(old_path).resolve()
    new_file = Path(new_path).resolve()
    old_version = filename_version(old_file)
    new_version = filename_version(new_file)
    if old_version and new_version:
        if old_version[1] == new_version[1]:
            print("❌ Die Zeitstempel der beiden XML-Dateien sind identisch.")
            sys.exit(1)
        if old_version[1] > new_version[1]:
            return str(new_file), str(old_file)
        return str(old_file), str(new_file)

    old_stat = old_file.stat()
    new_stat = new_file.stat()
    old_creation_time = getattr(old_stat, 'st_birthtime', old_stat.st_ctime)
    new_creation_time = getattr(new_stat, 'st_birthtime', new_stat.st_ctime)

    if old_creation_time == new_creation_time:
        print("❌ Die Erstellzeiten der beiden XML-Dateien sind identisch.")
        print("   ALTE und NEUE Datei können nicht automatisch bestimmt werden.")
        sys.exit(1)

    if old_creation_time > new_creation_time:
        return str(new_file), str(old_file)
    return str(old_file), str(new_file)


def default_delta_path(old_path, new_path):
    output_dir = Path(__file__).resolve().parent / 'Output'
    delta_name = f"{Path(old_path).stem}__{Path(new_path).stem}__delta.xml"
    return str(output_dir / delta_name)


def default_log_path(new_path):
    output_dir = Path(__file__).resolve().parent / 'Output'
    return output_dir / f"Log_{Path(new_path).stem}.txt"


def local_name(tag):
    return etree.QName(tag).localname


def add_csv_value(row, key, value):
    if key not in row:
        row[key] = value
        return

    suffix = 2
    candidate = f"{key}_{suffix}"
    while candidate in row:
        suffix += 1
        candidate = f"{key}_{suffix}"
    row[candidate] = value


def flatten_element(element, prefix=''):
    row = {}
    for name, value in element.attrib.items():
        add_csv_value(row, f"{prefix}@{local_name(name)}", value)

    children = list(element)
    text = (element.text or '').strip()
    if text and not children:
        add_csv_value(row, prefix or local_name(element.tag), text)

    for child in children:
        child_name = local_name(child.tag)
        child_prefix = f"{prefix}.{child_name}" if prefix else child_name
        for key, value in flatten_element(child, child_prefix).items():
            add_csv_value(row, key, value)
    return row


def repeated_children(parent):
    children = list(parent)
    for child in children:
        same_tag = [
            candidate for candidate in children
            if local_name(candidate.tag) == local_name(child.tag)
        ]
        if len(same_tag) > 1:
            return same_tag
    return []


def find_csv_records(root):
    records = repeated_children(root)
    if records:
        return records

    for parent in root.iter():
        records = repeated_children(parent)
        if records:
            return records

    children = list(root)
    return children or [root]


def set_finder_tag(csv_path, has_entries):
    if sys.platform != 'darwin':
        return None

    attribute = 'com.apple.metadata:_kMDItemUserTags'
    tag_name = 'XML-Delta: Einträge' if has_entries else 'XML-Delta: leer'
    color = 2 if has_entries else 6
    path = str(csv_path)
    attributes = subprocess.run(
        ['xattr', path],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    if attribute in attributes:
        encoded_tags = subprocess.run(
            ['xattr', '-p', '-x', attribute, path],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        existing_tags = plistlib.loads(bytes.fromhex(encoded_tags))
        if not isinstance(existing_tags, list) or not all(isinstance(tag, str) for tag in existing_tags):
            raise ValueError(f"Ungültige Finder-Tags auf '{csv_path}'.")
    else:
        existing_tags = []

    tags = [
        tag for tag in existing_tags
        if tag.split('\n', 1)[0] not in {'XML-Delta: Einträge', 'XML-Delta: leer'}
    ]
    tags.append(f"{tag_name}\n{color}")
    subprocess.run(
        ['xattr', '-w', '-x', attribute, plistlib.dumps(tags, fmt=plistlib.FMT_BINARY).hex(), path],
        check=True,
        capture_output=True,
        text=True,
    )
    return tag_name


def convert_xml_to_csv(source_path, has_entries):
    source = Path(source_path)
    root = etree.parse(str(source)).getroot()
    rows = [flatten_element(record) for record in find_csv_records(root)] if has_entries else []

    fieldnames = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    destination = source.with_name(f"{source.stem}_UTF-16.csv")
    with destination.open('w', encoding='utf-16', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction='ignore')
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)
    return destination


def comparison_heading(old_path):
    base = filename_version(old_path)
    name = base[0] if base else Path(old_path).stem
    name = name.casefold()
    for keyword, heading in (
        ('sessions', 'Sessions'),
        ('keynotes', 'Keynotes'),
        ('workshops', 'Workshops'),
        ('speaker', 'Speaker'),
    ):
        if keyword in name:
            return heading
    return name


def run_logged_comparisons(comparisons, debug, dry_run, log_path):
    with log_path.open('w', encoding='utf-8') as log_file:
        stdout_tee = Tee(sys.stdout, log_file)
        stderr_tee = Tee(sys.stderr, log_file)
        with redirect_stdout(stdout_tee), redirect_stderr(stderr_tee):
            for old_path, new_path, delta_path in comparisons:
                args = argparse.Namespace(
                    old=old_path,
                    new=new_path,
                    delta=delta_path,
                    dry_run=dry_run,
                )
                heading = comparison_heading(old_path)
                print(f"\n{'=' * 70}")
                print(f"{heading.upper():^70}")
                print(f"{'=' * 70}")
                print(f"Vergleich: {Path(old_path).name} → {Path(new_path).name}")
                run_comparison(args, debug)


def run_comparison(args, debug):
    # Laden
    try:
        parser_xml = etree.XMLParser(strip_cdata=False, recover=False)
        old_root = etree.parse(args.old, parser_xml).getroot()
        new_root = etree.parse(args.new, parser_xml).getroot()
    except Exception as e:
        print(f"❌ Lade-Fehler: {e}")
        sys.exit(1)

    # Typ erkennen
    block_type = detect_structure(old_root, new_root)[1]

    use_unique_ids = bool(
        block_type
        and has_unique_ids(old_root, block_type)
        and has_unique_ids(new_root, block_type)
    )

    # Blöcke sammeln
    old_blocks = get_blocks(old_root, block_type, use_unique_ids, debug=debug) if block_type else {}
    new_blocks = get_blocks(new_root, block_type, use_unique_ids, debug=debug) if block_type else {}

    if debug:
        print(f"\n📊 XML-Vergleich:\nAltes XML: {len(old_blocks)} Einträge\nNeues XML: {len(new_blocks)} Einträge")
    if use_unique_ids:
        print("\nℹ️  uniqueId in beiden XML erkannt: Abgleich über eindeutige IDs")
    else:
        print("\nℹ️  uniqueId nicht in beiden XML erkannt: bisheriger Abgleich")

    # Delta zählen
    delta_count = 0
    for key in new_blocks:
        old_block = old_blocks.get(key)
        if old_block is None:
            delta_count += 1
        else:
            changed = not (
                unique_id_fields_equal(old_block, new_blocks[key], debug=False)
                if use_unique_ids
                else elements_equal(old_block, new_blocks[key], block_type, debug=False)
            )
            if changed:
                delta_count += 1

    print(f"\n📦 DELTA: {delta_count} Einträge")

    # Delta bauen (Root mit Namespaces von new_root)
    delta_root = etree.Element(new_root.tag, attrib=dict(new_root.attrib), nsmap=new_root.nsmap)

    print(f"\n🔍 Delta-Berechnung...")

    new_entries = []
    update_entries = []
    unchanged_entries = []

    for key in new_blocks:
        old_block = old_blocks.get(key)
        if old_block is None:
            new_entries.append(key)
            delta_root.append(deepcopy(new_blocks[key]))
        else:
            changed = not (
                unique_id_fields_equal(old_block, new_blocks[key], debug=False)
                if use_unique_ids
                else elements_equal(old_block, new_blocks[key], block_type, debug=False)
            )
            if changed:
                update_entries.append(key)
                delta_root.append(deepcopy(new_blocks[key]))
            else:
                unchanged_entries.append(key)

    # Gelöschte
    deleted = sorted(set(old_blocks.keys()) - set(new_blocks.keys()))

    print("\n✅ NEU:")
    for key in new_entries:
        print(f"  - '{key}'")
    if not new_entries:
        print("  Keine Einträge")

    print("\n✏️ UPDATES:")
    for key in update_entries:
        print(f"  - '{key}'")
    if not update_entries:
        print("  Keine Einträge")

    print("\n🗑️ GELÖSCHT:")
    for key in deleted:
        print(f"  - '{key}'")
    if not deleted:
        print("  Keine Einträge")

    print("\nℹ️ UNVERÄNDERT:")
    for key in unchanged_entries:
        print(f"  - '{key}'")
    if not unchanged_entries:
        print("  Keine Einträge")

    # Ausgabe: minified, mit Namespaces erhalten und XML-Deklaration in doppelten Anführungszeichen
    # Erzeuge Bytes, passe ggf. Deklaration an, und schreibe dann als UTF-8 Text
    xml_bytes = etree.tostring(delta_root, pretty_print=False, xml_declaration=True, encoding='UTF-8')
    xml_text = xml_bytes.decode('utf-8')
    xml_text = re.sub(r"<\?xml version=['\"]1.0['\"] encoding=['\"]UTF-8['\"]\?>",
                      "<?xml version=\"1.0\" encoding=\"UTF-8\"?>", xml_text)

    if args.dry_run:
        print(f"\n{'='*50}")
        print("DELTA-PREVIEW:")
        print(xml_text)
    else:
        with open(args.delta, 'w', encoding='utf-8') as fh:
            fh.write(xml_text)
        has_entries = len(delta_root) > 0
        csv_path = convert_xml_to_csv(args.delta, has_entries)
        print(f"\n📄 CSV erstellt: '{csv_path}'")
        try:
            finder_tag = set_finder_tag(csv_path, has_entries)
        except (OSError, subprocess.CalledProcessError, plistlib.InvalidFileException, ValueError) as error:
            details = error.stderr.strip() if isinstance(error, subprocess.CalledProcessError) and error.stderr else str(error)
            print(f"⚠️ Finder-Farbe konnte nicht gesetzt werden: {details}")
        else:
            if finder_tag:
                print(f"🏷️ Finder-Tag: {finder_tag}")
        if debug:
            print(f"\n✅ '{args.delta}' geschrieben ({delta_count} Einträge)")


def main():
    parser = argparse.ArgumentParser(description='XML-Delta v1.3')
    parser.add_argument('old', nargs='?', help='XML-Datei (optional, Standard: Input-Ordner)')
    parser.add_argument('new', nargs='?', help='XML-Datei (optional, Standard: Input-Ordner)')
    parser.add_argument('delta', nargs='?', help='Delta XML (optional, Standard: Output-Ordner)')
    parser.add_argument('--dry-run', action='store_true', help='Nur Preview')
    parser.add_argument('--debug', action='store_true', default=DEBUG_MODE, help='Verbose Debug-Modus')
    args = parser.parse_args()

    if any(path is None for path in (args.old, args.new, args.delta)) and any(path is not None for path in (args.old, args.new, args.delta)):
        parser.error('old, new und delta müssen gemeinsam angegeben werden oder vollständig entfallen')

    output_dir = Path(__file__).resolve().parent / 'Output'
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.old is None:
        input_dir = Path(__file__).resolve().parent / 'Input'
        pairs = find_input_pairs(input_dir)
        comparisons = []
        for old_path, new_path in pairs:
            old_path, new_path = order_input_files(old_path, new_path)
            comparisons.append((
                str(old_path),
                str(new_path),
                default_delta_path(old_path, new_path),
            ))
        newest_input = max(
            (new_path for _, new_path, _ in comparisons),
            key=lambda path: filename_version(path)[1],
        )
        log_path = output_dir / f"Log_Batch_{Path(newest_input).stem}.txt"
    else:
        validate_input_files(args.old, args.new)
        args.old, args.new = order_input_files(args.old, args.new)
        if args.delta is None:
            args.delta = default_delta_path(args.old, args.new)
        comparisons = [(args.old, args.new, args.delta)]
        log_path = default_log_path(args.new)

    run_logged_comparisons(comparisons, args.debug, args.dry_run, log_path)


if __name__ == '__main__':
    main()
