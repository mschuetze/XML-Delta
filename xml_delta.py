# v0.4.0

#!/usr/bin/env python3
from lxml import etree
import sys
import argparse


def get_text(el, name):
    """Extrahiert Text aus Child-Element, stripped."""
    child = el.find(name)
    return (child.text or '').strip() if child is not None else ''


def make_key(item):
    """Erstellt eindeutigen Key aus title + firstName + lastName."""
    title = get_text(item, 'title')
    first = get_text(item, 'firstName')
    last = get_text(item, 'lastName')
    key_parts = [p for p in [title, first, last] if p]  # Leere überspringen
    return '::'.join(key_parts) if key_parts else None


def items_by_key(root):
    """Sammelt alle <item> nach Key in Dict."""
    items = {}
    for item in root.iterfind('.//item'):
        key = make_key(item)
        if key:
            items[key] = item
    return items


def elements_equal_simple(item1, item2):
    """Vergleicht relevante Felder: title, firstName, lastName, speakers."""
    fields = ['title', 'firstName', 'lastName', 'speakers']
    for field in fields:
        if get_text(item1, field) != get_text(item2, field):
            return False
    return True


def main():
    parser_cli = argparse.ArgumentParser(
        description='Delta für einfache <result><item>…</item>…</result>-Struktur v1.0',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiel:
  %(prog)s old.xml new.xml delta.xml
  %(prog)s old.xml new.xml delta.xml --dry-run
        """
    )
    parser_cli.add_argument('old', help='Alte XML-Datei (old.xml)')
    parser_cli.add_argument('new', help='Neue XML-Datei (new.xml)')
    parser_cli.add_argument('delta', help='Ausgabe Delta XML (delta.xml)')
    parser_cli.add_argument('--dry-run', action='store_true', help='Nur simulieren, nichts speichern')
    args = parser_cli.parse_args()

    # XML laden
    try:
        parser = etree.XMLParser(strip_cdata=False, recover=False, encoding='UTF-8')
        old_tree = etree.parse(args.old, parser)
        new_tree = etree.parse(args.new, parser)
        old_root, new_root = old_tree.getroot(), new_tree.getroot()
    except etree.XMLSyntaxError as e:
        print(f"❌ XML-Syntaxfehler: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"❌ Datei nicht gefunden: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Lese-Fehler: {e}", file=sys.stderr)
        sys.exit(1)

    # Items sammeln
    old_items = items_by_key(old_root)
    new_items = items_by_key(new_root)

    print(f"📊 Gefunden: {len(old_items)} alt, {len(new_items)} neu")

    # Delta-Root erstellen (gleiche Struktur wie new)
    delta_root = etree.Element(new_root.tag, attrib=dict(new_root.attrib))

    # Delta-Blöcke: nur geändert/neu
    delta_count = 0
    for key, new_item in new_items.items():
        old_item = old_items.get(key)
        if not old_item or not elements_equal_simple(old_item, new_item):
            delta_root.append(new_item)
            delta_count += 1

    print(f"📦 Delta: {delta_count} geändert/neu ({len(new_items) - delta_count} unverändert)")

    if delta_count == 0:
        print("ℹ️  Keine Änderungen erkannt")

    # Formatieren und ausgeben
    etree.indent(delta_root, space="  ")
    delta_tree = etree.ElementTree(delta_root)

    if args.dry_run:
        output = etree.tostring(
            delta_tree, pretty_print=True, encoding='unicode',
            xml_declaration=True, with_tail=False
        )
        print(output)
        print("\n✅ Dry-Run abgeschlossen (kein Speichern)")
    else:
        delta_tree.write(
            args.delta, encoding='UTF-8', xml_declaration=True,
            pretty_print=True
        )
        print(f"✅ Delta gespeichert: {args.delta}")


if __name__ == '__main__':
    main()
