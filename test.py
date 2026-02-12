from escpos.printer import Usb
from PIL import Image, ImageDraw, ImageFont

p = Usb(0x28e9, 0x0289)

text = "R-TOFU  ♥"
printer_width = 384  # pixels
font_size = 72        # bigger = larger letters

# Use a TrueType font (system font or any TTF file you have)
# macOS default example:
font = ImageFont.truetype("/System/Library/Fonts/SFNS.ttf", font_size)

# Create canvas tall enough for your font
img = Image.new("1", (printer_width, font_size + 20), color=1)
draw = ImageDraw.Draw(img)

# Get text bounding box
bbox = draw.textbbox((0, 0), text, font=font)
text_width = bbox[2] - bbox[0]
text_height = bbox[3] - bbox[1]

# Center text
x = (printer_width - text_width) // 2
y = (font_size + 20 - text_height) // 2

draw.text((x, y), text, font=font, fill=0)

# Print
p.image(img)
p.cut()
