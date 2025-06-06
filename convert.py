import xml.etree.ElementTree as ET
import ast
from xml.dom import minidom

def parse_domain_prefix_tree(domain, operator):
    def parse(it):
        token = next(it)
        if token in ('&', '|'):
            op = 'and' if token == '&' else 'or'
            left = parse(it)
            right = parse(it)
            return f"({left} {op} {right})"
        elif isinstance(token, tuple) and len(token) == 3:
            field, oper, value = token
            return f"{field} {operator.get(oper, oper)} {repr(value)}"
        else:
            return str(token)
    return parse(iter(domain))

def convert_to_17_format(domain, operator):
    if isinstance(domain, list):
        try:
            if domain and domain[0] in ('&', '|'):
                return parse_domain_prefix_tree(domain, operator)
            elif all(isinstance(item, tuple) and len(item) == 3 for item in domain):
                return " and ".join(
                    f"{f} {operator.get(o, o)} {repr(v)}" for f, o, v in domain
                )
            elif isinstance(domain[0], tuple):
                f, o, v = domain[0]
                return f"{f} {operator.get(o, o)} {repr(v)}"
        except Exception as e:
            return f"<parse_error: {e}>"
    elif isinstance(domain, tuple) and len(domain) == 3:
        f, o, v = domain
        return f"{f} {operator.get(o, o)} {repr(v)}"
    elif isinstance(domain, bool):
        return str(domain).lower()
    return str(domain)

def convert_xml_string(xml_str):
    operator = {
        '=': '==', '>=': '>=', '<=': '<=', '>': '>', '<': '<',
        'in': 'in', 'not in': 'not in', '!=': '!=', '<>': '!='
    }

    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError as e:
        return f"<!-- XML parse error: {e} -->"

    elements_to_add = []

    for parent in root.iter():
        if 'attrs' in parent.attrib:
            try:
                raw = parent.attrib['attrs']
                attrs = ast.literal_eval(raw)
                for key in attrs:
                    expr = convert_to_17_format(attrs[key], operator)
                    parent.set(key, expr)
                del parent.attrib['attrs']
            except Exception as e:
                parent.set('attrs_error', str(e))

        for i, child in enumerate(list(parent)):
            if child.tag == "attribute" and child.attrib.get("name") == "attrs":
                try:
                    raw = child.text
                    attrs = ast.literal_eval(raw)
                    for key, val in attrs.items():
                        new_elem = ET.Element("attribute")
                        new_elem.set("name", key)
                        new_elem.text = convert_to_17_format(val, operator)
                        elements_to_add.append((parent, i, new_elem))
                    parent.remove(child)
                except Exception as e:
                    child.tag = "attribute_error"
                    child.set("error", str(e))

    for parent, index, new_elem in elements_to_add:
        parent.insert(index, new_elem)

    for elem in root.iter():
        if 'states' in elem.attrib:
            states = [f"'{s.strip()}'" for s in elem.attrib['states'].split(',')]
            expr = f"state not in [{', '.join(states)}]"

            has_invisible_tag = any(
                child.tag == 'attribute' and child.attrib.get('name') == 'invisible'
                for child in list(elem)
            )

            if 'invisible' in elem.attrib:
                elem.set('invisible', f"{elem.attrib['invisible']} or {expr}")
            elif not has_invisible_tag:
                elem.set('invisible', expr)

            del elem.attrib['states']

    raw_str = ET.tostring(root, encoding='utf-8')
    reparsed = minidom.parseString(raw_str)
    pretty = reparsed.toprettyxml(indent="    ")

    clean_lines = [
        line for line in pretty.split('\n')
        if line.strip() and not line.strip().startswith('<?xml')
    ]
    return '\n'.join(clean_lines)
