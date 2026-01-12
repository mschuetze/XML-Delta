# v0.2.0

#!/usr/bin/env python3
from lxml import etree
import sys
import argparse

def elements_equal(el1, el2):
    if el1.tag != el2.tag: return False
    if sorted(el1.attrib.items()) != sorted(el2.attrib.items()): return False
    if len(el1) != len(el2): return False
    text1 = el1.text or ''
    text2 = el2.text or ''
    if text1 != text2: return False
    tail1 = el1.tail or ''
    tail2 = el2.tail or ''
    if tail1 != tail2: return False
    for c1, c2 in zip(el1, el2):
        if not elements_equal(c1, c2): return False
    return True

def get_key(el, key_fields):
    key_parts = []
    for field in key_fields:
        child = el.find(field)
        if child is not None:
            val = (child.text or el.tail or '').strip()
            key_parts.append(val)
    return '_'.join(key_parts)

if __name__ == '__main__':
    parser_cli = argparse.ArgumentParser(description='XML-Delta mit Container-Struktur.')
    parser_cli.add_argument('old', help='Alte XML')
    parser_cli.add_argument('new', help='Neue XML')
    parser_cli.add_argument('delta', help='Delta XML')
    args = parser_cli.parse_args()

    parser = etree.XMLParser(strip_cdata=False)
    old_tree = etree.parse(args.old, parser)
    new_tree = etree.parse(args.new, parser)
    old_root, new_root = old_tree.getroot(), new_tree.getroot()

    # 🔥 DEINE KOMPLETTE STRUKTUR
    CONTAINERS = {
        'speakers': 'speaker',
        'sessions': 'session',
        'tracks': 'track',
        'qualifications': 'qualification',
        'sessionTypes': 'sessiontype',  # Passe an, falls plural
        'sponsor-types': 'sponsor-type',  # Passe an
        'sponsors': 'sponsor',  # Passe an
    }

    KEY_FIELDS = {
        'speaker': ['_id'],
        'session': ['_id'],
        'track': ['_id'],
        'qualification': ['_id'],
        'sessiontype': ['_id'],  # Für sessionTypes Container
        'sponsor-type': ['_id'],  # Für sponsor-types
        'sponsor': ['_id'],  # Für sponsors
        'conference': ['_id'],
    }

    # Blöcke sammeln
    def collect_blocks(root, block_type, key_field):
        return {get_key(t, key_field): t for t in root.findall(f'.//{block_type}')
                if get_key(t, key_field)}

    old_blocks = {}
    new_blocks = {}
    for block_type, key_field in KEY_FIELDS.items():
        old_blocks[block_type] = collect_blocks(old_root, block_type, key_field)
        new_blocks[block_type] = collect_blocks(new_root, block_type, key_field)

    # 🔥 Delta mit CONTAINER-STRUKTUR bauen
    delta_root = etree.Element(new_root.tag, attrib=dict(new_root.attrib))

    # Normale Container: Nur geänderte/neue Kinder
    for container_tag, child_tag in CONTAINERS.items():
        container = etree.SubElement(delta_root, container_tag)
        delta_children = 0
        for key, new_child in new_blocks.get(child_tag, {}).items():
            old_child = old_blocks.get(child_tag, {}).get(key)
            if not old_child or not elements_equal(old_child, new_child):
                container.append(new_child)
                delta_children += 1
        print(f"📦 {container_tag}: {delta_children} geändert/neu")
        if delta_children == 0:
            delta_root.remove(container)  # Leeren entfernen

    ALWAYS_INCLUDE = ['qualifications', 'sessionTypes', 'sponsor-types', 'sponsors']
    for container_tag in ALWAYS_INCLUDE:
        child_tag = CONTAINERS[container_tag]
        container = etree.SubElement(delta_root, container_tag)
        count = 0
        for new_child in new_blocks.get(child_tag, {}).values():
            container.append(new_child)
            count += 1
        print(f"🔒 {container_tag}: {count} (immer vollständig)")

    # 🔗 Speaker-Dependencies für Sessions sicherstellen
    required_speakers = set()
    for session in new_blocks.get('session', {}).values():
        speaker_refs = session.findall(".//speakers/speaker/speakerId")
        for ref in speaker_refs:
            speaker_id = (ref.text or '').strip()
            if speaker_id:
                required_speakers.add(speaker_id)

    speakers_container = delta_root.find('speakers')
    if speakers_container is None:
        speakers_container = etree.SubElement(delta_root, 'speakers')

    added_deps = 0
    for speaker_id, speaker_el in new_blocks.get('speaker', {}).items():
        if speaker_id in required_speakers and speaker_el not in speakers_container:
            speakers_container.append(speaker_el)
            added_deps += 1

    if added_deps > 0:
        print(f"🔗 {added_deps} Speaker für Session-References hinzugefügt")


    # Direkt unter Root (conference)
    if 'conference' in KEY_FIELDS:
        for key, new_conf in new_blocks['conference'].items():
            old_conf = old_blocks['conference'].get(key)
            if not old_conf or not elements_equal(old_conf, new_conf):
                delta_root.append(new_conf)

    # Formatierung
    etree.indent(delta_root, space="  ")
    tree = etree.ElementTree(delta_root)
    tree.write(args.delta, encoding='UTF-8', xml_declaration=True)
    print(f"✅ Delta erzeugt: {args.delta}")