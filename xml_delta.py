# v0.5.0

#!/usr/bin/env python3
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


def find_input_files(input_dir):
    xml_files = sorted(
        path for path in Path(input_dir).iterdir()
        if path.is_file() and path.suffix.lower() == '.xml'
    )

    if len(xml_files) != 2:
        print("❌ Im Ordner Input müssen sich exakt 2 XML-Dateien befinden.")
        print(f"   Gefunden: {len(xml_files)}")
        sys.exit(1)
    return xml_files


def validate_input_files(old_path, new_path):
    input_dir = Path(old_path).resolve().parent
    xml_files = find_input_files(input_dir)

    selected_files = {Path(old_path).resolve(), Path(new_path).resolve()}
    if selected_files != set(xml_files):
        print("❌ Es müssen genau die beiden XML-Dateien aus dem Ordner Input verwendet werden.")
        sys.exit(1)


def order_input_files(old_path, new_path):
    old_file = Path(old_path).resolve()
    new_file = Path(new_path).resolve()
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


def main():
    parser = argparse.ArgumentParser(description='XML-Delta v1.3')
    parser.add_argument('old', nargs='?', help='XML-Datei (optional, Standard: Input-Ordner)')
    parser.add_argument('new', nargs='?', help='XML-Datei (optional, Standard: Input-Ordner)')
    parser.add_argument('delta', nargs='?', help='Delta XML (optional, Standard: Output-Ordner)')
    parser.add_argument('--dry-run', action='store_true', help='Nur Preview')
    parser.add_argument('--debug', action='store_true', default=DEBUG_MODE, help='Verbose Debug-Modus')
    args = parser.parse_args()
    debug = args.debug

    if any(path is None for path in (args.old, args.new, args.delta)) and any(path is not None for path in (args.old, args.new, args.delta)):
        parser.error('old, new und delta müssen gemeinsam angegeben werden oder vollständig entfallen')

    if args.old is None:
        input_files = find_input_files(Path(__file__).resolve().parent / 'Input')
        args.old, args.new = (str(path) for path in input_files)
        args.delta = None

    validate_input_files(args.old, args.new)
    args.old, args.new = order_input_files(args.old, args.new)
    if args.delta is None:
        args.delta = default_delta_path(args.old, args.new)

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

    # Blöcke sammeln
    old_blocks = blocks_by_key(old_root, block_type, debug=debug) if block_type else {}
    new_blocks = blocks_by_key(new_root, block_type, debug=debug) if block_type else {}

    if debug:
        print(f"\n📊 XML-Vergleich:\nAltes XML: {len(old_blocks)} Einträge\nNeues XML: {len(new_blocks)} Einträge")

    # Delta zählen
    delta_count = 0
    for key in new_blocks:
        old_block = old_blocks.get(key)
        if old_block is None:
            delta_count += 1
        else:
            changed = not elements_equal(old_block, new_blocks[key], block_type, debug=False)
            if changed:
                delta_count += 1

    print(f"\n📦 DELTA: {delta_count} Einträge")

    # Delta bauen (Root mit Namespaces von new_root)
    delta_root = etree.Element(new_root.tag, attrib=dict(new_root.attrib), nsmap=new_root.nsmap)

    print(f"\n🔍 Delta-Berechnung...")

    for key in new_blocks:
        old_block = old_blocks.get(key)
        if old_block is None:
            if debug:
                print(f"\n--- Key '{key}' ---")
                print("  ➕ NEU!")
            else:
                print(f"➕ NEU: '{key}'")
            delta_root.append(deepcopy(new_blocks[key]))
        else:
            changed = not elements_equal(old_block, new_blocks[key], block_type, debug=debug)
            if changed:
                if debug:
                    print("  ✏️  GÄNDERT!")
                else:
                    print(f"✏️ GEÄNDERT: '{key}'")
                delta_root.append(deepcopy(new_blocks[key]))

    # Gelöschte
    deleted = set(old_blocks.keys()) - set(new_blocks.keys())
    if deleted:
        print(f"\n🗑️  GELÖSCHT ({len(deleted)}):")
        for d in sorted(deleted):
            print(f"  - '{d}'")
    else:
        print(f"\nℹ️  Keine Löschungen")

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
        if debug:
            print(f"\n✅ '{args.delta}' geschrieben ({delta_count} Einträge)")
if __name__ == '__main__':
    output_dir = Path(__file__).resolve().parent / 'Output'
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / 'xml_delta.txt'

    with log_path.open('w', encoding='utf-8') as log_file:
        stdout_tee = Tee(sys.stdout, log_file)
        stderr_tee = Tee(sys.stderr, log_file)
        with redirect_stdout(stdout_tee), redirect_stderr(stderr_tee):
            main()
