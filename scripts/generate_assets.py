#!/usr/bin/env python3
"""Generate SVG assets for Terra.OS"""
import os
import json

# Create assets directory
os.makedirs('/home/ubuntu/terra-os/public/assets', exist_ok=True)

# Logo SVG
logo_svg = """<svg width="120" height="40" viewBox="0 0 120 40" fill="none" xmlns="http://www.w3.org/2000/svg">
  <text x="0" y="32" font-family="Space Grotesk, sans-serif" font-size="28" font-weight="bold" fill="#F4F4F0">Terra.</text>
  <text x="90" y="32" font-family="Space Grotesk, sans-serif" font-size="28" font-weight="bold" fill="#22C55E">OS</text>
</svg>"""

# Module icons
icons = {
    'shovel': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#22C55E" stroke-width="2"><path d="M2 22v-6l4-4"/><path d="M18 2L6 16"/><path d="M14 4l6 6-2 2-6-6z"/></svg>',
    'calculator': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" stroke-width="2"><rect x="4" y="2" width="16" height="20" rx="2"/><line x1="8" y1="6" x2="16" y2="6"/><line x1="8" y1="10" x2="8" y2="10.01"/><line x1="12" y1="10" x2="12" y2="10.01"/><line x1="16" y1="10" x2="16" y2="10.01"/><line x1="8" y1="14" x2="8" y2="14.01"/><line x1="12" y1="14" x2="12" y2="14.01"/><line x1="16" y1="14" x2="16" y2="14.01"/><line x1="8" y1="18" x2="8" y2="18.01"/><line x1="12" y1="18" x2="12" y2="18.01"/><line x1="16" y1="18" x2="16" y2="18.01"/></svg>',
    'brain': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2"><path d="M12 2a7 7 0 0 1 7 7c0 2.5-1.5 5-4 6l-3 2-3-2c-2.5-1-4-3.5-4-6a7 7 0 0 1 7-7z"/><path d="M9 22h6"/><path d="M10 2v3"/><path d="M14 2v3"/></svg>',
    'clipboard': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#8B5CF6" stroke-width="2"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/></svg>',
}

# Write assets
with open('/home/ubuntu/terra-os/public/assets/logo.svg', 'w') as f:
    f.write(logo_svg)

for name, svg in icons.items():
    with open(f'/home/ubuntu/terra-os/public/assets/{name}.svg', 'w') as f:
        f.write(svg)

print("Assets generated successfully!")
print(f"Files: logo.svg, shovel.svg, calculator.svg, brain.svg, clipboard.svg")
