#!/usr/bin/env python3
"""
Generate clean, hand-crafted SVGs for YU-NA assets.
Directly writes SVG XML for perfect control over vectors.
"""
import os

BASE_DIR = '/home/ubuntu/terra-os/public/assets'
LOGO_DIR = os.path.join(BASE_DIR, 'logo')
ICONS_DIR = os.path.join(BASE_DIR, 'icons')

os.makedirs(LOGO_DIR, exist_ok=True)
os.makedirs(ICONS_DIR, exist_ok=True)

# SVG Namespace
NS = 'http://www.w3.org/2000/svg'
NSX = 'http://www.w3.org/1999/xlink'

def save_svg(filename, content):
    path = os.path.join(filename.rsplit('/', 1)[0], filename.rsplit('/', 1)[1])
    # Ensure directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)
    print(f"[SAVE] {path}")

# --- Logo ---
logo_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 200" width="100%" height="100%">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <text x="400" y="130" font-family="system-ui, -apple-system, sans-serif" font-size="120" font-weight="bold" fill="#1A1A1A" text-anchor="middle">Terra</text>
  <text x="400" y="130" font-family="system-ui, -apple-system, sans-serif" font-size="120" font-weight="bold" fill="#22C55E" text-anchor="middle" dx="380">.OS</text>
</svg>'''
save_svg(os.path.join(LOGO_DIR, 'logo.svg'), logo_svg)

# --- Icons ---
# Helper to create simple icon SVG
def create_icon(name, color, content):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="100%" height="100%">
  <rect width="256" height="256" fill="transparent"/>
  {content}
</svg>'''

# Shovel: Handle + Head
shovel_svg = create_icon('shovel', '#22C55E', '''
  <line x1="128" y1="40" x2="128" y2="180" stroke="#1A1A1A" stroke-width="16" stroke-linecap="round"/>
  <path d="M80 180 Q128 240 176 180 Z" fill="#22C55E" stroke="#1A1A1A" stroke-width="12" stroke-linejoin="round"/>
''')
save_svg(os.path.join(ICONS_DIR, 'shovel.svg'), shovel_svg)

# Calculator: Body + Screen + Buttons
calc_svg = create_icon('calculator', '#3B82F6', '''
  <rect x="60" y="40" width="136" height="176" rx="16" fill="#3B82F6" stroke="#1A1A1A" stroke-width="10"/>
  <rect x="80" y="60" width="96" height="40" rx="4" fill="#1A1A1A"/>
  <rect x="80" y="120" width="30" height="24" rx="4" fill="#1A1A1A"/>
  <rect x="113" y="120" width="30" height="24" rx="4" fill="#1A1A1A"/>
  <rect x="146" y="120" width="30" height="24" rx="4" fill="#1A1A1A"/>
  <rect x="80" y="156" width="30" height="24" rx="4" fill="#1A1A1A"/>
  <rect x="113" y="156" width="30" height="24" rx="4" fill="#1A1A1A"/>
  <rect x="146" y="156" width="30" height="24" rx="4" fill="#1A1A1A"/>
''')
save_svg(os.path.join(ICONS_DIR, 'calculator.svg'), calc_svg)

# Brain: Wavy Circle
brain_svg = create_icon('brain', '#F59E0B', '''
  <path d="M80 128 C80 80 120 60 128 80 C136 60 176 80 176 128 C200 128 200 176 176 176 C176 200 128 200 128 176 C128 200 80 200 80 176 C56 176 56 128 80 128 Z" fill="#F59E0B" stroke="#1A1A1A" stroke-width="10"/>
''')
save_svg(os.path.join(ICONS_DIR, 'brain.svg'), brain_svg)

# Clipboard: Rect + Clip
clipboard_svg = create_icon('clipboard', '#8B5CF6', '''
  <rect x="80" y="60" width="96" height="140" rx="8" fill="#8B5CF6" stroke="#1A1A1A" stroke-width="10"/>
  <rect x="110" y="40" width="36" height="24" rx="4" fill="#1A1A1A"/>
  <rect x="120" y="80" width="76" height="10" rx="2" fill="#1A1A1A" opacity="0.3"/>
  <rect x="120" y="100" width="76" height="10" rx="2" fill="#1A1A1A" opacity="0.3"/>
  <rect x="120" y="120" width="76" height="10" rx="2" fill="#1A1A1A" opacity="0.3"/>
  <rect x="120" y="140" width="76" height="10" rx="2" fill="#1A1A1A" opacity="0.3"/>
''')
save_svg(os.path.join(ICONS_DIR, 'clipboard.svg'), clipboard_svg)

# Truck: Cab + Bed
truck_svg = create_icon('truck', '#9CA3AF', '''
  <rect x="40" y="100" width="120" height="60" rx="4" fill="#9CA3AF" stroke="#1A1A1A" stroke-width="10"/>
  <rect x="160" y="80" width="60" height="80" rx="4" fill="#9CA3AF" stroke="#1A1A1A" stroke-width="10"/>
  <circle cx="80" cy="160" r="20" fill="#1A1A1A"/>
  <circle cx="200" cy="160" r="20" fill="#1A1A1A"/>
''')
save_svg(os.path.join(ICONS_DIR, 'truck.svg'), truck_svg)

print("\n=== Done! ===")
