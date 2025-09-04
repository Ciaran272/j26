import json
import re
import sys
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path


def to_katakana(s: str) -> str:
    if not s:
        return s
    out = []
    for ch in s:
        if 'ぁ' <= ch <= 'ゖ':
            out.append(chr(ord(ch) + 0x60))
        else:
            out.append(ch)
    return ''.join(out)


def parse_xml(path: str) -> ET.Element:
    if path.endswith('.gz'):
        with gzip.open(path, 'rb') as f:
            return ET.fromstring(f.read())
    else:
        return ET.parse(path).getroot()


def convert_jmdict(src_xml: str, out_json: str) -> None:
    print(f'[JMdict] converting -> {out_json}')
    root = parse_xml(src_xml)
    ns = {}
    out: dict[str, list[str]] = {}
    for entry in root.findall('entry', ns):
        kanjis = [e.text for e in entry.findall('k_ele/keb', ns)]
        readings = [to_katakana(e.text or '') for e in entry.findall('r_ele/reb', ns)]
        readings = [r for r in readings if r]
        if not readings:
            continue
        uniq_readings = list(dict.fromkeys(readings))
        keys = (kanjis or []) + ([] if kanjis else readings)
        for k in keys:
            if not k:
                continue
            L = out.setdefault(k, [])
            for r in uniq_readings:
                if r not in L:
                    L.append(r)
    Path(out_json).write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    print(f'[JMdict] done: {len(out)} entries')


def convert_kanjidic2(src_xml: str, out_json: str) -> None:
    print(f'[KANJIDIC2] converting -> {out_json}')
    root = parse_xml(src_xml)
    out: dict[str, list[str]] = {}
    for ch in root.findall('character'):
        literal = ch.findtext('literal')
        if not literal:
            continue
        # KANJIDIC2 uses snake_case: reading_meaning/rmgroup
        rgroup = ch.find('reading_meaning/rmgroup')
        if rgroup is None:
            continue
        rs: list[str] = []
        for r in rgroup.findall('reading'):
            typ = r.attrib.get('r_type', '')
            val = (r.text or '').strip()
            if not val:
                continue
            if typ == 'ja_on':
                rs.append(val)  # カタカナ
            elif typ == 'ja_kun':
                v = re.sub(r'[・.]', '', val.split('-')[0])  # 去分隔与送り仮名标记
                rs.append(to_katakana(v))
        if rs:
            out[literal] = list(dict.fromkeys(rs))
    Path(out_json).write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    print(f'[KANJIDIC2] done: {len(out)} characters')


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python convert_dicts.py JMdict_e[.gz] kanjidic2.xml[.gz]')
        sys.exit(1)
    jmdict_src = sys.argv[1]
    kanji_src = sys.argv[2]
    convert_jmdict(jmdict_src, 'jmdict_readings.json')
    convert_kanjidic2(kanji_src, 'kanjidic2_readings.json')
    print('All done.')


