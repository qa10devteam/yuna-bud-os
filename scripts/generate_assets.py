#!/usr/bin/env python3
"""
Generate Terra.OS branded SVG assets from JSON specifications.
Use with GPT-Image-2 generated images for icon/brand consistency.
"""
import json
import os
from pathlib import Path

def create_terra_logo_svg(output_path='terra_logo.svg'):
    """Create the Terra.OS logo SVG with shovel metaphor."""
    svg_data = {
        "width": 512,
        "height": 512,
        "background": "transparent",
        "shapes": [
            # Handle (green)
            {"type": "rect", "x": 240, "y": 100, "width": 32, "height": 200, "fill": "#00FF94", "rx": 16},
            # Shaft (blue)
            {"type": "rect", "x": 244, "y": 50, "width": 24, "height": 60, "fill": "#3B82F6", "rx": 12},
            # Blade (red)
            {"type": "path", "d": "M 160 50 L 256 20 L 352 50 L 256 80 Z", "fill": "#FF3300", "stroke": "#FF3300", "stroke-width": "3"},
            # Connection nodes
            {"type": "circle", "cx": 256, "cy": 100, "r": 12, "fill": "#00FF94"},
            {"type": "circle", "cx": 256, "cy": 50, "r": 8, "fill": "#3B82F6"},
            {"type": "circle", "cx": 256, "cy": 20, "r": 6, "fill": "#FF3300"},
        ]
    }
    
    import xml.etree.ElementTree as ET
    w, h = svg_data['width'], svg_data['height']
    svg = ET.Element('svg', xmlns='http://www.w3.org/2000/svg', width=str(w), height=str(h), viewBox=f'0 0 {w} {h}')
    
    for shape in svg_data['shapes']:
        if shape['type'] == 'path':
            el = ET.SubElement(svg, 'path', d=shape['d'], fill=shape.get('fill','#fff'))
            if 'stroke' in shape:
                el.set('stroke', shape['stroke'])
                el.set('stroke-width', shape.get('stroke-width', '1'))
        elif shape['type'] == 'circle':
            ET.SubElement(svg, 'circle', cx=str(shape['cx']), cy=str(shape['cy']), r=str(shape['r']), fill=shape.get('fill', '#fff'))
        else:
            attrs = {k: str(v) for k, v in shape.items() if k != 'type'}
            ET.SubElement(svg, shape['type'], **attrs)
    
    tree = ET.ElementTree(svg)
    ET.indent(tree, '  ')
    tree.write(output_path, encoding='unicode', xml_declaration=True)
    return output_path

def create_module_icon_svg(module_name, output_path=None):
    """Create SVG icon for a Terra.OS module."""
    icons = {
        'zwiad': {'color': '#00FF94', 'icon': 'search'},
        'kosztorys': {'color': '#3B82F6', 'icon': 'calculator'},
        'silnik': {'color': '#FF3300', 'icon': 'warning'},
        'decyzja': {'color': '#A855F7', 'icon': 'layers'},
    }
    
    icon_data = icons.get(module_name, icons['zwiad'])
    color = icon_data['color']
    
    svg_data = {
        "width": 24, "height": 24, "background": "transparent",
        "shapes": []
    }
    
    if icon_data['icon'] == 'search':
        svg_data['shapes'] = [
            {"type": "circle", "cx": 11, "cy": 11, "r": 8, "fill": "none", "stroke": color, "stroke-width": "2"},
            {"type": "path", "d": "M 21 21 L 15 15", "fill": "none", "stroke": color, "stroke-width": "2", "stroke-linecap": "round"},
        ]
    elif icon_data['icon'] == 'calculator':
        svg_data['shapes'] = [
            {"type": "rect", "x": 4, "y": 2, "width": 16, "height": 20, "fill": "none", "stroke": color, "stroke-width": "2", "rx": "2"},
            {"type": "rect", "x": 6, "y": 4, "width": 12, "height": 5, "fill": color},
            {"type": "circle", "cx": 8, "cy": 13, "r": 1, "fill": color},
            {"type": "circle", "cx": 12, "cy": 13, "r": 1, "fill": color},
            {"type": "circle", "cx": 16, "cy": 13, "r": 1, "fill": color},
            {"type": "circle", "cx": 8, "cy": 17, "r": 1, "fill": color},
            {"type": "circle", "cx": 12, "cy": 17, "r": 1, "fill": color},
            {"type": "circle", "cx": 16, "cy": 17, "r": 1, "fill": color},
        ]
    elif icon_data['icon'] == 'warning':
        svg_data['shapes'] = [
            {"type": "path", "d": "M 12 2 L 2 20 L 22 20 Z", "fill": "none", "stroke": color, "stroke-width": "2", "stroke-linejoin": "round"},
            {"type": "rect", "x": 11, "y": 8, "width": 2, "height": 6, "fill": color},
            {"type": "circle", "cx": 12, "cy": 17, "r": 1, "fill": color},
        ]
    else:  # layers
        svg_data['shapes'] = [
            {"type": "path", "d": "M 12 2 L 2 7 L 12 12 L 22 7 Z", "fill": "none", "stroke": color, "stroke-width": "2", "stroke-linejoin": "round"},
            {"type": "path", "d": "M 2 17 L 12 22 L 22 17", "fill": "none", "stroke": color, "stroke-width": "2", "stroke-linejoin": "round"},
            {"type": "path", "d": "M 2 12 L 12 17 L 22 12", "fill": "none", "stroke": color, "stroke-width": "2", "stroke-linejoin": "round"},
        ]
    
    w, h = svg_data['width'], svg_data['height']
    svg = ET.Element('svg', xmlns='http://www.w3.org/2000/svg', width=str(w), height=str(h), viewBox=f'0 0 {w} {h}')
    
    for shape in svg_data['shapes']:
        attrs = {k: str(v) for k, v in shape.items() if k != 'type'}
        tag = shape['type']
        if tag == 'path':
            ET.SubElement(svg, tag, d=attrs.get('d'), **{k: v for k, v in attrs.items() if k != 'd'})
        else:
            ET.SubElement(svg, tag, **attrs)
    
    tree = ET.ElementTree(svg)
    ET.indent(tree, '  ')
    out_path = output_path or f'{module_name}_icon.svg'
    tree.write(out_path, encoding='unicode', xml_declaration=True)
    return out_path

if __name__ == '__main__':
    import sys
    out = '/home/ubuntu/terra-os/public/assets'
    os.makedirs(out, exist_ok=True)
    
    create_terra_logo_svg(os.path.join(out, 'terra_logo.svg'))
    print("Created: terra_logo.svg")
    
    for module in ['zwiad', 'kosztorys', 'silnik', 'decyzja']:
        create_module_icon_svg(module, os.path.join(out, f'{module}_icon.svg'))
        print(f"Created: {module}_icon.svg")
    
    print(f"All assets generated in {out}")
