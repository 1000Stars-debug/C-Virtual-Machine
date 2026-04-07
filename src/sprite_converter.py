#!/usr/bin/python3
from PIL import Image
import sys

def convert_to_rgb565(r, g, b):
	# 5 bits Red, 6 bits Green, 5 bits Blue
	r5 = (r * 31 // 255) << 11
	g6 = (g * 63 // 255) << 5
	b5 = (b * 31 // 255)
	return r5 | g6 | b5

def main(input_path, label_name):
	img = Image.open(input_path).convert("RGB")
	pixels = list(img.getdata())
	width, height = img.size

	print(f"// Sprite: {label_name} ({width}x{height})")
	print(".DATA")
	print(f"{label_name}: ", end="")
	
	hex_values = [hex(convert_to_rgb565(r, g, b)) for r, g, b in pixels]
	
	# Print in a clean block
	for i, val in enumerate(hex_values):
		if i > 0 and i % width == 0:
			print("\n\t", end="")
		print(f"{val}", end=", " if i < len(hex_values)-1 else "")
	print("\n")

if __name__ == "__main__":
	if len(sys.argv) < 3:
		print("Usage: python sprite_to_asm.py <image_path> <label_name>")
	else:
		main(sys.argv[1], sys.argv[2])
