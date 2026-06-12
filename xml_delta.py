# v0.4.2

#!/usr/bin/env python3
from lxml import etree
import sys
import argparse

# DEBUG konfigurieren: False = normaler Modus, True = verbose Debug-Modus
DEBUG_MODE = False


def get_text_ns(el, name):
    """Namespace-robust: local-name() ohne namespaces."""
    xpath = f".//*[local-name()='{name}']"
    children = el.xpath(xpath)
    return (children[0].text or '').strip() if children else ''


def detect_structure(root):
    if root.xpath(".//item"):
        return 'items', 'item'
    elif root.xpath(".//speaker"):
        return 'speakers', 'speaker'
    raise ValueError("Unbekannte Struktur")


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
    for i, block in enumerate(root.xpath(f".//{block_type}"), 1):
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


def main():
    parser = argparse.ArgumentParser(description='XML-Delta v1.3')
    parser.add_argument('old', help='Alte XML')
    parser.add_argument('new', help='Neue XML')
    parser.add_argument('delta', help='Delta XML')
    parser.add_argument('--dry-run', action='store_true', help='Nur Preview')
    parser.add_argument('--debug', action='store_true', default=DEBUG_MODE, help='Verbose Debug-Modus')
    args = parser.parse_args()
    debug = args.debug

    # Laden
    try:
        parser_xml = etree.XMLParser(strip_cdata=False, recover=False)
        old_root = etree.parse(args.old, parser_xml).getroot()
        new_root = etree.parse(args.new, parser_xml).getroot()
    except Exception as e:
        print(f"❌ Lade-Fehler: {e}")
        sys.exit(1)

    # Typ erkennen
    block_type = detect_structure(old_root)[1]

    # Blöcke sammeln
    old_blocks = blocks_by_key(old_root, block_type, debug=debug)
    new_blocks = blocks_by_key(new_root, block_type, debug=debug)

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

    # Delta bauen
    delta_root = etree.Element(new_root.tag, attrib=dict(new_root.attrib))

    print(f"\n🔍 Delta-Berechnung...")

    for key in new_blocks:
        old_block = old_blocks.get(key)
        if old_block is None:
            if debug:
                print(f"\n--- Key '{key}' ---")
                print("  ➕ NEU!")
            else:
                print(f"➕ NEU: '{key}'")
            delta_root.append(new_blocks[key])
            # delta_count already gezählt
        else:
            changed = not elements_equal(old_block, new_blocks[key], block_type, debug=debug)
            if changed:
                if debug:
                    print("  ✏️  GÄNDERT!")
                else:
                    print(f"✏️ GEÄNDERT: '{key}'")
                delta_root.append(new_blocks[key])
                # delta_count already gezählt

    # Gelöschte
    deleted = set(old_blocks.keys()) - set(new_blocks.keys())
    if deleted:
        print(f"\n🗑️  GELÖSCHT ({len(deleted)}):")
        for d in sorted(deleted):
            print(f"  - '{d}'")
    else:
        print(f"\nℹ️  Keine Löschungen")

    # Ausgabe
    etree.indent(delta_root, space="  ")
    delta_tree = etree.ElementTree(delta_root)

    if args.dry_run:
        print(f"\n{'='*50}")
        print("DELTA-PREVIEW:")
        print(etree.tostring(delta_tree, pretty_print=True, encoding='unicode', xml_declaration=True))
    else:
        delta_tree.write(args.delta, encoding='UTF-8', xml_declaration=True, pretty_print=True)
        if debug:
            print(f"\n✅ '{args.delta}' geschrieben ({delta_count} Einträge)")
if __name__ == '__main__':
    main()
