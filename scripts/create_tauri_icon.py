"""Create the small deterministic icon used by the Tauri bundle."""

from pathlib import Path

from PIL import Image, ImageDraw


def main() -> None:
    output = Path(__file__).resolve().parents[1] / "src-tauri" / "icons" / "icon.ico"
    output.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((12, 12, 244, 244), radius=44, fill=(30, 46, 62, 255))
    draw.rectangle((66, 72, 190, 104), fill=(247, 244, 236, 255))
    draw.rectangle((112, 104, 144, 184), fill=(247, 244, 236, 255))
    draw.ellipse((157, 157, 199, 199), fill=(184, 92, 56, 255))
    image.save(output, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


if __name__ == "__main__":
    main()
