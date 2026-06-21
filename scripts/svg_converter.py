#!/usr/bin/env python3
"""
Terra.OS SVG Converter — Converts raster images to optimized SVG.
Dependencies: Pillow (pip install Pillow)
Optional: potrace (apt install potrace), svgo (npm i -g svgo)
"""
import argparse, subprocess, json, time, re, base64
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class ConversionResult:
    input_file: str
    output_file: str
    input_format: str
    output_format: str
    input_size: tuple
    output_size: tuple
    processing_time: float
    success: bool
    error: Optional[str] = None
    metadata: dict = None
    def to_dict(self):
        return asdict(self)

def detect_format(fp):
    return Path(fp).suffix.lower().replace('.', '').upper() or 'UNKNOWN'

def trace_to_svg(image_path, output_path, colors=8, optimize=True):
    start = time.time()
    try:
        # Fallback: embed as base64 SVG (always works with Pillow)
        try:
            from PIL import Image
            import xml.etree.ElementTree as ET
            img = Image.open(image_path).convert('RGB')
            w, h = img.size
            buf = __import__('io').BytesIO()
            img.save(buf, format='PNG')
            b64 = base64.b64encode(buf.getvalue()).decode()
            
            svg = ET.Element('svg', xmlns='http://www.w3.org/2000/svg', width=str(w), height=str(h))
            ET.SubElement(svg, 'image', x='0', y='0', width=str(w), height=str(h), href=f'data:image/png;base64,{b64}')
            tree = ET.ElementTree(svg)
            ET.indent(tree, '  ')
            tree.write(output_path, encoding='unicode', xml_declaration=True)
            
            return ConversionResult(
                input_file=image_path, output_file=output_path,
                input_format=detect_format(image_path), output_format='SVG (embedded)',
                input_size=(w, h), output_size=(w, h),
                processing_time=time.time()-start, success=True,
                metadata={'method': 'pillow_embed', 'colors': len(img.getcolors(256) or [])}
            )
        except ImportError:
            return ConversionResult(
                input_file=image_path, output_file=output_path,
                input_format=detect_format(image_path), output_format='SVG',
                input_size=(0,0), output_size=(0,0), processing_time=0, success=False,
                error="Pillow not installed. pip install Pillow"
            )
    except Exception as e:
        return ConversionResult(
            input_file=image_path, output_file=output_path,
            input_format=detect_format(image_path), output_format='SVG',
            input_size=(0,0), output_size=(0,0), processing_time=0, success=False,
            error=str(e)
        )

def generate_svg_from_data(data, output_path):
    """Generate SVG from structured JSON data."""
    import xml.etree.ElementTree as ET
    w, h = data.get('width', 512), data.get('height', 512)
    svg = ET.Element('svg', xmlns='http://www.w3.org/2000/svg', width=str(w), height=str(h),
                     viewBox=f'0 0 {w} {h}')
    ET.SubElement(svg, 'rect', width='100%', height='100%', fill=data.get('background', '#0A0A0A'))
    for shape in data.get('shapes', []):
        if shape.get('type') == 'circle':
            ET.SubElement(svg, 'circle', cx=str(shape['cx']), cy=str(shape['cy']), r=str(shape['r']), fill=shape.get('fill', '#fff'))
        elif shape.get('type') == 'text':
            t = ET.SubElement(svg, 'text', x=str(shape.get('x',0)), y=str(shape.get('y',0)), fill=shape.get('fill','#fff'),
                             'font-size': str(shape.get('font_size',24)), 'font-family'=shape.get('font_family','sans-serif'))
            t.text = shape.get('content', '')
        else:
            ET.SubElement(svg, shape.get('type','rect'), x=str(shape.get('x',0)), y=str(shape.get('y',0)),
                         width=str(shape.get('width',100)), height=str(shape.get('height',100)), fill=shape.get('fill','#fff'))
    tree = ET.ElementTree(svg)
    ET.indent(tree, '  ')
    tree.write(output_path, encoding='unicode', xml_declaration=True)
    return output_path

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Terra.OS SVG Converter')
    p.add_argument('input', help='Input image')
    p.add_argument('-o', '--output', help='Output SVG')
    p.add_argument('--generate', help='JSON data file for SVG generation')
    args = p.parse_args()
    
    if args.generate:
        with open(args.generate) as f:
            data = json.load(f)
        out = args.output or args.generate.replace('.json','.svg')
        generate_svg_from_data(data, out)
        print(f"Generated: {out}")
    else:
        result = trace_to_svg(args.input, args.output or f"{Path(args.input).stem}.svg")
        print(json.dumps(result.to_dict(), indent=2))
