#!/usr/bin/env python3
"""
Generate high-contrast PNGs and convert them to SVG for YU-NA.
Uses ImageMagick and Potrace.
"""
import os
import subprocess
import sys

BASE_DIR = '/home/ubuntu/terra-os/public/assets'
LOGO_DIR = os.path.join(BASE_DIR, 'logo')
ICONS_DIR = os.path.join(BASE_DIR, 'icons')

os.makedirs(LOGO_DIR, exist_ok=True)
os.makedirs(ICONS_DIR, exist_ok=True)

def run_cmd(cmd, desc):
    print(f"[GENERATE] {desc}...")
    try:
        subprocess.run(cmd, check=True, shell=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to run '{desc}': {e}")
        return False

def convert_png_to_svg(png_path, svg_path, desc=""):
    """Convert PNG to SVG using Potrace (Color mode)."""
    if desc == "":
        desc = f'Converting {os.path.basename(png_path)} to SVG'
    
    tmp_ppm = png_path.replace('.png', '.ppm')
    if not run_cmd(f'convert {png_path} {tmp_ppm}', f'Converting to PPM for {desc}'):
        return False
    
    tmp_mask = tmp_ppm.replace(".ppm", "-mask.ppm")
    if not run_cmd(f'ppmcolormask {tmp_ppm} {tmp_mask}', f'Masking colors for {desc}'):
        return False
    
    if not run_cmd(f'potrace {tmp_ppm} -o {svg_path} --svg', f'Potrace vectorization for {desc}'):
        return False
    
    os.remove(tmp_ppm)
    if os.path.exists(tmp_mask):
        os.remove(tmp_mask)
    return True

def main():
    print("\n=== Generating Logo ===")
    logo_png = os.path.join(LOGO_DIR, 'logo_temp.png')
    # White background, Black text "Terra", Green text ".OS"
    run_cmd(f'convert -size 800x200 xc:white -fill black -pointsize 80 -gravity center -annotate 0 "Terra" {logo_png}', "Drawing Terra text")
    run_cmd(f'convert {logo_png} -gravity East -fill "#22C55E" -pointsize 60 -annotate +50+20 ".OS" {logo_png}', "Adding .OS text")
    
    logo_svg = os.path.join(LOGO_DIR, 'logo.svg')
    if convert_png_to_svg(logo_png, logo_svg, "Logo SVG"):
        print(f"[OK] Logo saved to {logo_svg}")
    os.remove(logo_png)

    print("\n=== Generating Icons ===")
    icons_config = [
        {
            'name': 'shovel',
            'color': '#22C55E',
            'desc': 'Shovel (handle + head)',
            'draw': 'M128 40 L128 180 M90 180 Q128 220 166 180 L90 180'
        },
        {
            'name': 'calculator',
            'color': '#3B82F6',
            'desc': 'Calculator (rect + screen + buttons)',
            # Simpler geometry: outer rect + inner rects
            'draw': 'rectangle 60 60 196 200 100 80 156 80 100 120 156 120 100 140 156 140 100 160 156 160'
        },
        {
            'name': 'brain',
            'color': '#F59E0B',
            'desc': 'Brain (wavy circle)',
            'draw': 'circle 128 128 80 128 128 80 128'
        },
        {
            'name': 'clipboard',
            'color': '#8B5CF6',
            'desc': 'Clipboard (rect + clip)',
            'draw': 'rectangle 80 40 176 220 128 30 150 40 106 40'
        },
        {
            'name': 'truck',
            'color': '#9CA3AF',
            'desc': 'Truck (cab + bed)',
            'draw': 'rectangle 40 100 180 160 180 140 220 140 220 100 200 100 200 160 40 160'
        }
    ]

    for icon in icons_config:
        icon_png = os.path.join(ICONS_DIR, f"{icon['name']}_temp.png")
        color = icon['color']
        draw_cmd = icon['draw']
        
        cmd = f'convert -size 256x256 xc:white -stroke black -strokewidth 4 -fill "{color}" -draw "{draw_cmd}" {icon_png}'
        
        if run_cmd(cmd, f'Drawing {icon["name"]} icon'):
            if convert_png_to_svg(icon_png, os.path.join(ICONS_DIR, f'{icon["name"]}.svg'), f"SVG for {icon['name']}"):
                print(f"[OK] {icon['name']}.svg saved")
            os.remove(icon_png)

    print("\n=== Done! ===")

if __name__ == '__main__':
    main()
