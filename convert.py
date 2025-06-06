import xml.etree.ElementTree as ET
import ast
from xml.dom import minidom

def convert_to_17_format(domain, operator):
    if isinstance(domain, bool):
        return str(domain).lower()
    elif isinstance(domain, list):
        if len(domain) == 0:
            return ''
        if len(domain) == 1 and isinstance(domain[0], tuple):
            field, oper, value = domain[0]
            value = f"'{value}'" if isinstance(value, str) else value
            return f"{field} {operator.get(oper, oper)} {value}"
        elif all(isinstance(i, tuple) and len(i) == 3 for i in domain):
            return " and ".join(
                f"{f} {operator.get(o, o)} {repr(v)}" for f, o, v in domain
            )
        else:
            # handle &, |, &
            stack = []
            i = 0
            while i < len(domain):
                if domain[i] in ('&', '|'):
                    op = 'and' if domain[i] == '&' else 'or'
                    left = domain[i + 1]
                    right = domain[i + 2]
                    left_expr = convert_to_17_format([left], operator)
                    right_expr = convert_to_17_format([right], operator)
                    stack.append(f"({left_expr} {op} {right_expr})")
                    i += 3
                else:
                    i += 1
            return " and ".join(stack)
    return str(domain)

def convert_xml_odoo17(xml_str):
    return _convert_xml_core(xml_str, version="17")

def convert_xml_odoo18(xml_str):
    return _convert_xml_core(xml_str, version="18")

def _convert_xml_core(xml_str, version="17"):
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
        # Inline attrs
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

        # <attribute name="attrs">
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

    # states
    for elem in root.iter():
        if 'states' in elem.attrib:
            states = [f"'{s.strip()}'" for s in elem.attrib['states'].split(',')]
            expr = f"state not in [{', '.join(states)}]"
            if 'invisible' in elem.attrib:
                elem.set('invisible', f"{elem.attrib['invisible']} or {expr}")
            else:
                elem.set('invisible', expr)
            del elem.attrib['states']

    # Odoo 18-specific
    if version == "18":
        for elem in root.iter():
            if elem.tag == "tree":
                elem.tag = "list"
            if elem.tag == "list" and elem.attrib.get("editable") == "1":
                elem.set("editable", "bottom")

    # Pretty print (no <?xml version)
    raw_str = ET.tostring(root, encoding='utf-8')
    reparsed = minidom.parseString(raw_str)
    pretty = reparsed.toprettyxml(indent="    ")
    clean_lines = [line for line in pretty.split('\n') if line.strip() and not line.strip().startswith('<?xml')]
    return '\n'.join(clean_lines)
